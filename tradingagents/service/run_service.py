"""In-process run orchestration service for the current Web runtime."""

from __future__ import annotations

import datetime
import json
import logging
import os
import queue
import sys
import threading
import time
import traceback
import uuid
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path
from typing import Any, TextIO

from tradingagents.default_config import apply_settings_payload
from tradingagents.dataflows.provenance import (
    build_data_warnings,
    get_data_fetch_audit,
    install_data_fetch_event_sink,
    reset_data_fetch_audit,
    reset_data_fetch_event_sink,
)
from tradingagents.graph.event_processor import build_run_config
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.llm_clients.api_key_env import get_api_key_env
from tradingagents.service.execution_lock import PROCESS_EXECUTION_LOCK
from tradingagents.service.models import TERMINAL_RUN_STATUSES, RunCancelledError, RunState
from tradingagents.service.runtime_context import RuntimeContext, build_runtime_context
from tradingagents.service.state_backend import StateBackendAdapter, get_state_backend_adapter
from tradingagents.service.timestamps import (
    coerce_timestamp_ms,
    current_timestamp_ms,
    local_timestamp_text,
)
from tradingagents.service.usage_tracking import RunUsageTracker
from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import export_api_keys_to_env, load_settings

logger = logging.getLogger(__name__)

_KEY_OPTIONAL_PROVIDERS = {"bedrock", "ollama", "openai_compatible"}
_RUN_CONFIG_LOG_KEYS = (
    "llm_provider",
    "quick_think_llm",
    "deep_think_llm",
    "output_language",
    "market_profile",
    "max_debate_rounds",
    "max_risk_discuss_rounds",
    "max_recur_limit",
    "checkpoint_enabled",
    "benchmark_ticker",
    "temperature",
    "google_thinking_level",
    "openai_reasoning_effort",
    "anthropic_effort",
)


def _timestamp_sort_value(value: object | None) -> int:
    return coerce_timestamp_ms(value) or 0


class _TerminalOutputRecorder:
    """Thread-safe tee for run-scoped terminal output."""

    def __init__(self, service: "RunService", run: RunState, handle: TextIO) -> None:
        self._service = service
        self._run = run
        self._handle = handle
        self._lock = threading.RLock()

    def write_chunk(self, stream_name: str, text: str, passthrough: TextIO | None = None) -> None:
        with self._lock:
            self._handle.write(text)
            self._handle.flush()
        if passthrough is not None:
            try:
                passthrough.write(text)
                passthrough.flush()
            except Exception:
                pass

    def emit_line(self, stream_name: str, line: str) -> None:
        if not line:
            return
        self._service._put_event(
            self._run,
            {
                "event": "terminal_output",
                "data": {
                    "stream": stream_name,
                    "line": line,
                },
            },
        )

    def flush(self) -> None:
        with self._lock:
            self._handle.flush()


class _TerminalStreamWriter:
    """File-like stream that records full text and emits complete lines."""

    def __init__(
        self,
        recorder: _TerminalOutputRecorder,
        stream_name: str,
        passthrough: TextIO | None,
    ) -> None:
        self._recorder = recorder
        self._stream_name = stream_name
        self._passthrough = passthrough
        self._buffer = ""

    @property
    def encoding(self) -> str:
        return str(getattr(self._passthrough, "encoding", "utf-8") or "utf-8")

    def write(self, text: str) -> int:
        if not text:
            return 0
        value = str(text)
        self._recorder.write_chunk(self._stream_name, value, self._passthrough)
        self._buffer += value.replace("\r", "\n")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._recorder.emit_line(self._stream_name, line)
        return len(value)

    def flush(self) -> None:
        if self._buffer:
            self._recorder.emit_line(self._stream_name, self._buffer)
            self._buffer = ""
        self._recorder.flush()
        if self._passthrough is not None:
            try:
                self._passthrough.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return bool(getattr(self._passthrough, "isatty", lambda: False)())


def _settings_api_key(settings: dict[str, Any] | None, provider: str) -> str:
    api_keys = settings.get("api_keys", {}) if isinstance(settings, dict) else {}
    if not isinstance(api_keys, dict):
        return ""
    value = api_keys.get(provider, "")
    return str(value).strip() if value is not None else ""


def _ensure_provider_api_key_available(config: dict[str, Any], settings: dict[str, Any] | None) -> None:
    provider = str(config.get("llm_provider") or "").strip().lower()
    if not provider or provider in _KEY_OPTIONAL_PROVIDERS:
        return

    api_key_env = get_api_key_env(provider)
    if not api_key_env:
        return

    if settings:
        has_key = bool(_settings_api_key(settings, provider))
    else:
        has_key = bool(os.environ.get(api_key_env))
    if has_key:
        return

    raise ValueError(
        f"API key for provider '{provider}' is not set. "
        f"Please configure {provider} in Settings > API Keys or set {api_key_env}."
    )

class RunService:
    """Owns run state, local queue/worker execution, and persistence."""

    def __init__(
        self,
        *,
        tenant_id: str | None = None,
        runs_index_path: Path,
        run_events_dir: Path,
        runs_root_dir: Path,
        max_completed_runs: int = 100,
        graph_factory=TradingAgentsGraph,
        worker_status_path: Path | None = None,
        claims_dir: Path | None = None,
        state_backend: StateBackendAdapter | None = None,
    ) -> None:
        self._tenant_id = tenant_id
        self._runs_index_path = runs_index_path
        self._run_events_dir = run_events_dir
        self._runs_root_dir = runs_root_dir
        self._max_completed_runs = max_completed_runs
        self._graph_factory = graph_factory
        self._worker_status_path = worker_status_path or runs_index_path.parent / "worker-status.json"
        self._claims_dir = claims_dir or runs_index_path.parent / "claims"
        self._state_backend = state_backend or get_state_backend_adapter()

        self._runs_lock = threading.Lock()
        self._runs: dict[str, RunState] = {}
        self._run_queue: queue.Queue[str] = queue.Queue()
        self._queued_run_ids: list[str] = []
        self._worker_thread: threading.Thread | None = None
        self._worker_lock = threading.Lock()
        self._terminal_log_lock = threading.Lock()
        self._next_queue_sequence = 1

    def _terminal_log_path(self, run: RunState) -> Path:
        """Return the durable terminal output path for a run."""
        if run.terminal_log_path:
            return Path(run.terminal_log_path)
        return run.runtime_context.run_root / "terminal_output.log"

    def _ensure_terminal_log(self, run: RunState) -> Path:
        """Create the per-run terminal output file if needed."""
        path = self._terminal_log_path(run)
        run.terminal_log_path = str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        return path

    def _terminal_log_has_content(self, run: RunState) -> bool:
        path = self._ensure_terminal_log(run)
        try:
            return path.stat().st_size > 0
        except OSError:
            return False

    def _write_terminal_line(self, run: RunState, stream_name: str, line: str) -> None:
        if not line:
            return
        path = self._ensure_terminal_log(run)
        timestamp = local_timestamp_text()
        rendered = f"{timestamp} [run:{run.run_id}] {line}"
        with self._terminal_log_lock:
            try:
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(rendered + "\n")
            except OSError:
                logger.warning("Failed to write terminal output for run %s", run.run_id)
        self._put_event(
            run,
            {
                "event": "terminal_output",
                "data": {
                    "stream": stream_name,
                    "line": rendered,
                },
            },
        )

    def _log_run_phase(self, run: RunState, message: str, *, stream_name: str = "stdout") -> None:
        self._write_terminal_line(run, stream_name, f"Phase: {message}")

    def _log_run_configuration(self, run: RunState) -> None:
        self._write_terminal_line(run, "stdout", "Run configuration")
        self._write_terminal_line(run, "stdout", f"ticker: {run.ticker}")
        self._write_terminal_line(run, "stdout", f"date: {run.date}")
        self._write_terminal_line(run, "stdout", f"asset_type: {run.asset_type}")
        self._write_terminal_line(
            run,
            "stdout",
            f"selected_analysts: {', '.join(run.selected_analysts)}",
        )
        for key in _RUN_CONFIG_LOG_KEYS:
            value = run.config.get(key)
            if value is None or value == "":
                continue
            self._write_terminal_line(run, "stdout", f"{key}: {value}")

    @contextmanager
    def _capture_terminal_output(self, run: RunState):
        """Tee stdout/stderr and root logging into the run terminal log."""
        path = self._ensure_terminal_log(run)
        stdout = sys.stdout
        stderr = sys.stderr
        with path.open("a", encoding="utf-8") as handle:
            recorder = _TerminalOutputRecorder(self, run, handle)
            stdout_writer = _TerminalStreamWriter(recorder, "stdout", stdout)
            stderr_writer = _TerminalStreamWriter(recorder, "stderr", stderr)
            log_handler = logging.StreamHandler(stderr_writer)
            log_handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            root_logger = logging.getLogger()
            root_logger.addHandler(log_handler)
            try:
                with redirect_stdout(stdout_writer), redirect_stderr(stderr_writer):
                    yield
            finally:
                root_logger.removeHandler(log_handler)
                stdout_writer.flush()
                stderr_writer.flush()

    def load_tenant_settings(self) -> dict[str, Any]:
        """Load persisted settings for this service's tenant scope."""
        return load_settings(path=get_web_settings_path(self._tenant_id))

    def apply_tenant_api_keys(self) -> None:
        """Load the tenant-scoped settings and apply their API keys to this process."""
        settings = self.load_tenant_settings()
        if settings:
            export_api_keys_to_env(settings, overwrite=True)

    def save_runs_index(self) -> None:
        """Persist known runs so history survives process restarts."""
        with self._runs_lock:
            ordered_runs = list(self._runs.values())

        try:
            self._state_backend.save_runs(ordered_runs, index_path=self._runs_index_path)
        except OSError:
            logger.warning("Failed to persist run history to %s", self._runs_index_path)

    def _persist_run(self, run: RunState) -> None:
        """Persist one run without rewriting unrelated entries."""
        try:
            self._state_backend.upsert_run(run, index_path=self._runs_index_path)
        except OSError:
            logger.warning("Failed to persist run %s to %s", run.run_id, self._runs_index_path)

    def _persist_runs(self, runs: list[RunState]) -> None:
        """Persist a small set of changed runs."""
        for run in runs:
            self._persist_run(run)

    def load_runs_index(self) -> None:
        """Load persisted run history into memory."""
        restored = self._state_backend.load_runs(
            runs_root_dir=self._runs_root_dir,
            index_path=self._runs_index_path,
        )
        with self._runs_lock:
            self._runs.clear()
            self._runs.update(restored)
            self._next_queue_sequence = (
                max((run.queue_sequence or 0) for run in restored.values()) + 1
                if restored else 1
            )
        for run in restored.values():
            self.load_run_event_history(run)

    def resume_incomplete_runs(self) -> None:
        """Requeue unfinished work after startup."""
        to_enqueue: list[str] = []
        now = current_timestamp_ms(datetime.datetime.now())
        with self._runs_lock:
            for run in self._runs.values():
                if run.status in TERMINAL_RUN_STATUSES:
                    continue
                self._state_backend.release_claim(run_id=run.run_id, claims_dir=self._claims_dir)
                if run.status == "cancelling":
                    run.status = "cancelled"
                    run.completed_at = run.completed_at or now
                    run.queue_sequence = None
                    continue
                run.status = "queued"
                run.error = None
                run.started_at = None
                run.completed_at = None
                run.cancel_requested.clear()
                if run.queue_sequence is None:
                    run.queue_sequence = self._next_queue_sequence
                    self._next_queue_sequence += 1
                to_enqueue.append(run.run_id)
        if to_enqueue:
            self._persist_runs([self._runs[run_id] for run_id in to_enqueue if run_id in self._runs])
        for run_id in to_enqueue:
            self._enqueue_run(run_id)

    def load_run_event_history(self, run: RunState) -> None:
        """Load persisted event history for a run when available."""
        event_log_path, history = self._state_backend.load_events(
            run.run_id,
            event_log_path=Path(run.event_log_path) if run.event_log_path else None,
            base_dir=self._run_events_dir,
        )
        run.event_log_path = str(event_log_path)
        run.event_history = history

    def _record_event(self, run: RunState, event: dict[str, Any]) -> None:
        """Append an event to in-memory and durable history."""
        event_log_path, record = self._state_backend.append_event(
            run.run_id,
            event,
            event_log_path=Path(run.event_log_path) if run.event_log_path else None,
            base_dir=self._run_events_dir,
        )
        run.event_history.append(record)
        run.event_log_path = str(event_log_path)

    def get_run(self, run_id: str) -> RunState | None:
        with self._runs_lock:
            return self._runs.get(run_id)

    def list_runs(self) -> list[RunState]:
        """Return runs ordered by newest first."""
        with self._runs_lock:
            return sorted(
                self._runs.values(),
                key=lambda run: _timestamp_sort_value(run.created_at),
                reverse=True,
            )

    def get_queue_position(self, run_id: str) -> int | None:
        """Return 1-based queue position for queued runs."""
        with self._runs_lock:
            queued_runs = sorted(
                (run for run in self._runs.values() if run.status == "queued"),
                key=lambda run: (run.queue_sequence or 10**12, _timestamp_sort_value(run.created_at)),
            )
        for index, run in enumerate(queued_runs, start=1):
            if run.run_id == run_id:
                return index
        return None

    def get_status_snapshot(self) -> dict[str, object]:
        """Return a compact operational snapshot for status APIs."""
        heartbeat = self._state_backend.read_worker_status(path=self._worker_status_path, stale_after_seconds=5)
        with self._runs_lock:
            return {
                "queue_depth": sum(1 for run in self._runs.values() if run.status == "queued"),
                "run_count": len(self._runs),
                "worker_running": heartbeat["worker_running"] or bool(self._worker_thread and self._worker_thread.is_alive()),
                "worker_mode": heartbeat["worker_mode"],
                "worker_last_seen": heartbeat["last_seen"],
            }

    def subscribe_run_events(self, run: RunState):
        return run.subscribe_events()

    def unsubscribe_run_events(self, run: RunState, subscriber_id: str) -> None:
        run.unsubscribe_events(subscriber_id)

    def build_terminal_event(self, run: RunState) -> dict[str, Any] | None:
        if run.status == "completed":
            return {
                "event": "complete",
                "data": {
                    "signal": run.signal,
                    "report": run.final_report or "",
                },
            }
        if run.status == "cancelled":
            return {
                "event": "cancelled",
                "data": {
                    "message": "Analysis cancelled",
                },
            }
        if run.status == "failed":
            return {
                "event": "error",
                "data": {
                    "message": run.error or "Analysis failed",
                },
            }
        return None

    def prune_terminal_runs(self, max_completed: int | None = None) -> None:
        """Keep only the newest completed/failed runs to cap memory use."""
        limit = self._max_completed_runs if max_completed is None else max_completed
        if limit < 0:
            raise ValueError("max_completed must be >= 0")

        with self._runs_lock:
            terminal_runs = [
                (run_id, run)
                for run_id, run in self._runs.items()
                if run.status in TERMINAL_RUN_STATUSES
            ]
            terminal_runs.sort(
                key=lambda item: _timestamp_sort_value(item[1].completed_at or item[1].created_at)
            )

            while len(terminal_runs) > limit:
                oldest_run_id, oldest_run = terminal_runs.pop(0)
                self._runs.pop(oldest_run_id, None)
                try:
                    self._state_backend.delete_run_state(
                        oldest_run_id,
                        run_root=oldest_run.runtime_context.run_root,
                        event_log_path=Path(oldest_run.event_log_path) if oldest_run.event_log_path else None,
                        claims_dir=self._claims_dir,
                        index_path=self._runs_index_path,
                    )
                except OSError:
                    logger.warning("Failed to delete run %s from index %s", oldest_run_id, self._runs_index_path)

    def _put_event(self, run: RunState, event: dict) -> None:
        """Thread-safe event push to the run's asyncio subscribers."""
        self._record_event(run, event)
        for loop, subscriber_queue in run.snapshot_event_subscribers():
            try:
                if loop.is_closed():
                    continue
                import asyncio

                asyncio.run_coroutine_threadsafe(subscriber_queue.put(event), loop)
            except RuntimeError:
                continue

    def _emit_agent_status(self, run: RunState, agent: str, status: str) -> None:
        if agent in run.agents:
            run.agents[agent] = status
            self._put_event(run, {"event": "agent_status", "data": {"agent": agent, "status": status}})

    def _emit_report(self, run: RunState, section: str, content: str) -> None:
        if section in run.report_sections:
            run.report_sections[section] = content
            self._put_event(
                run,
                {
                    "event": "report_update",
                    "data": {
                        "section": section,
                        "content": content,
                        "content_length": len(content),
                    },
                },
            )
            self._update_current_report(run)

    def _update_current_report(self, run: RunState) -> None:
        from tradingagents.graph.event_processor import build_current_report

        run.current_report = build_current_report(run.report_sections)

    def _update_final_report(self, run: RunState) -> None:
        from tradingagents.graph.event_processor import build_final_report

        run.final_report = build_final_report(run.report_sections)

    def _capture_data_fetch_audit(self, run: RunState) -> None:
        """Persist context-local structured data-fetch metadata onto the run."""
        run.data_fetches = get_data_fetch_audit()
        run.data_warnings = build_data_warnings(run.data_fetches)

    def _log_data_fetch_audit(self, run: RunState) -> None:
        """Write a concise provenance summary into the terminal log."""
        if not run.data_fetches:
            return
        self._write_terminal_line(run, "stdout", "Data fetch audit")
        for entry in run.data_fetches:
            source = entry.get("actual_source") or "n/a"
            status = entry.get("status") or "unknown"
            request_label = entry.get("request_label") or entry.get("item") or entry.get("method")
            detail = entry.get("detail")
            summary = f"Data source: {request_label} -> {source} [{status}]"
            if detail:
                summary += f" ({detail})"
            self._write_terminal_line(run, "stdout", summary)
        for warning in run.data_warnings:
            stream_name = "stderr" if warning.get("severity") == "warning" else "stdout"
            self._write_terminal_line(
                run,
                stream_name,
                f"Data warning: {warning.get('message')}",
            )

    def _capture_usage_summary(self, run: RunState, tracker: RunUsageTracker) -> None:
        """Persist one run-scoped aggregate of LLM usage."""
        run.usage_summary = tracker.snapshot()

    def _augment_state_log(self, run: RunState) -> None:
        """Merge run-level audit summaries into the saved full-state JSON."""
        if not run.state_log_path:
            return
        path = Path(run.state_log_path)
        if not path.exists() or not path.is_file():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return
            payload["data_fetches"] = deepcopy(run.data_fetches)
            payload["data_warnings"] = deepcopy(run.data_warnings)
            payload["usage_summary"] = deepcopy(run.usage_summary)
            path.write_text(json.dumps(payload, indent=4), encoding="utf-8")
        except (OSError, json.JSONDecodeError, TypeError):
            logger.warning("Failed to augment state log for run %s", run.run_id, exc_info=True)

    def _emit_llm_usage_event(self, run: RunState, payload: dict[str, Any]) -> None:
        """Publish structured LLM prompt / call summaries into the run timeline."""
        event_name = "llm_prompt" if "prompt_preview" in payload else "llm_call"
        self._put_event(run, {"event": event_name, "data": deepcopy(payload)})

    def _emit_data_fetch_event(self, run: RunState, entry: dict[str, Any]) -> None:
        """Publish one structured data-fetch event into the run timeline."""
        self._put_event(run, {"event": "data_fetch", "data": deepcopy(entry)})
        warning = str(entry.get("warning") or "").strip()
        if not warning:
            return
        self._put_event(
            run,
            {
                "event": "data_warning",
                "data": {
                    "key": str(entry.get("key") or ""),
                    "method": str(entry.get("method") or ""),
                    "item": str(entry.get("item") or ""),
                    "severity": "warning" if entry.get("required") else "info",
                    "message": warning,
                },
            },
        )

    def _emit_state_snapshot(self, run: RunState, chunk: dict[str, Any]) -> None:
        """Capture one structured snapshot of run progress after a graph chunk."""
        in_progress_agents = sorted(
            agent for agent, status in run.agents.items() if status == "in_progress"
        )
        completed_agents = sum(1 for status in run.agents.values() if status == "completed")
        report_sections_present = sorted(
            section for section, content in run.report_sections.items() if content
        )
        investment_debate_state = chunk.get("investment_debate_state") or {}
        risk_debate_state = chunk.get("risk_debate_state") or {}
        self._put_event(
            run,
            {
                "event": "state_snapshot",
                "data": {
                    "chunk_keys": sorted(str(key) for key in chunk.keys())[:16],
                    "in_progress_agents": in_progress_agents,
                    "completed_agent_count": completed_agents,
                    "report_sections_present": report_sections_present,
                    "investment_debate_count": investment_debate_state.get("count"),
                    "risk_debate_count": risk_debate_state.get("count"),
                },
            },
        )

    def _process_chunk(self, run: RunState, chunk: dict[str, Any]) -> None:
        cp = run._chunk_processor

        messages, tools = cp.get_messages_and_tools(chunk)
        for msg in messages:
            self._put_event(run, {"event": "progress", "data": {"message": msg}})
        for tool in tools:
            tool_name = str(tool.get("name") or "")
            if tool_name:
                self._put_event(run, {"event": "progress", "data": {"tool_call": tool_name}})
            self._put_event(run, {"event": "tool_call", "data": tool})

        cp.process_chunk(chunk)

        for agent, status in cp.agent_status.items():
            if run.agents.get(agent) != status:
                self._emit_agent_status(run, agent, status)

        for section, content in cp.report_sections.items():
            if content and run.report_sections.get(section) != content:
                self._emit_report(run, section, content)

        run.current_report = cp.current_report
        self._emit_state_snapshot(run, chunk)

    def cancel_run(self, run_id: str) -> RunState | None:
        """Request cancellation for a run if it is still active."""
        with self._runs_lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            if run.status in TERMINAL_RUN_STATUSES:
                return run
            run.cancel_requested.set()
            if run.status == "queued":
                run.status = "cancelled"
                run.error = None
                run.completed_at = current_timestamp_ms(datetime.datetime.now())
                run.queue_sequence = None
                if run_id in self._queued_run_ids:
                    self._queued_run_ids.remove(run_id)
            elif run.status in {"pending", "running"}:
                run.status = "cancelling"
        if run.status == "cancelled":
            terminal_event = self.build_terminal_event(run)
            if terminal_event is not None:
                self._put_event(run, terminal_event)
        self._persist_run(run)
        return run

    def delete_run(self, run_id: str) -> RunState | None:
        """Delete a terminal run and its persisted artifacts."""
        with self._runs_lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            if run.status not in TERMINAL_RUN_STATUSES:
                return None
            self._runs.pop(run_id, None)
            run.queue_sequence = None
            if run_id in self._queued_run_ids:
                self._queued_run_ids.remove(run_id)

        try:
            self._state_backend.delete_run_state(
                run_id,
                run_root=run.runtime_context.run_root,
                event_log_path=Path(run.event_log_path) if run.event_log_path else None,
                claims_dir=self._claims_dir,
                index_path=self._runs_index_path,
            )
        except OSError:
            logger.warning("Failed to delete run %s from index %s", run_id, self._runs_index_path)
        return run

    def retry_run(self, run_id: str, *, start_worker: bool = True) -> RunState | None:
        """Clone a terminal run into a new queued run."""
        source = self.get_run(run_id)
        if source is None or source.status not in TERMINAL_RUN_STATUSES:
            return None

        self.prune_terminal_runs()
        if start_worker:
            self.ensure_worker_started()

        new_run_id = str(uuid.uuid4())
        runtime_context = build_runtime_context(new_run_id, base_dir=self._runs_root_dir)
        run = RunState(
            run_id=new_run_id,
            ticker=source.ticker,
            date=source.date,
            asset_type=source.asset_type,
            config=deepcopy(source.config),
            selected_analysts=list(source.selected_analysts),
            runtime_context=runtime_context,
            company_name=source.company_name,
            status="queued",
            queue_sequence=self._next_queue_sequence,
        )
        run.config["runtime_run_id"] = new_run_id
        self._ensure_terminal_log(run)
        self._log_run_configuration(run)
        self._log_run_phase(run, f"queued retry from {source.run_id}")
        self._next_queue_sequence += 1
        with self._runs_lock:
            self._runs[new_run_id] = run
        self._put_event(
            run,
            {
                "event": "queued",
                "data": {
                    "message": f"Queued retry for {run.ticker} on {run.date}",
                    "source_run_id": source.run_id,
                },
            },
        )
        if start_worker:
            self._enqueue_run(new_run_id)
        self._persist_run(run)
        return run

    def _run_analysis_thread(self, run: RunState) -> None:
        """Execute the analysis in a background thread."""
        self._ensure_terminal_log(run)
        if not self._terminal_log_has_content(run):
            self._log_run_configuration(run)
        reset_data_fetch_audit()
        usage_tracker = RunUsageTracker(
            provider=str(run.config.get("llm_provider") or ""),
            event_sink=lambda payload: self._emit_llm_usage_event(run, payload),
        )
        event_sink_token = install_data_fetch_event_sink(
            lambda entry: self._emit_data_fetch_event(run, entry),
        )
        self._log_run_phase(run, "waiting for execution lock")
        try:
            with PROCESS_EXECUTION_LOCK:
                self._log_run_phase(run, "acquired execution lock")
                with self._capture_terminal_output(run):
                    self._log_run_phase(run, "applying tenant API keys")
                    self.apply_tenant_api_keys()
                    run.status = "running"
                    run.started_at = current_timestamp_ms(datetime.datetime.now())
                    run.queue_sequence = None
                    self._log_run_phase(run, "status set to running")
                    self._put_event(run, {"event": "progress", "data": {"message": f"Starting analysis for {run.ticker} on {run.date}"}})
                    self._log_run_phase(run, "persisting run start")
                    self.save_runs_index()
                    if run.cancel_requested.is_set():
                        raise RunCancelledError()

                    self._log_run_phase(run, "initializing trading graph")
                    graph = self._graph_factory(
                        run.selected_analysts,
                        config=run.config,
                        debug=False,
                        callbacks=[usage_tracker],
                    )

                    self._log_run_phase(run, "starting graph stream")
                    stream = graph.stream_propagate(
                        run.ticker,
                        run.date,
                        asset_type=run.asset_type,
                    )
                    chunk_count = 0
                    try:
                        for chunk in stream:
                            chunk_count += 1
                            chunk_keys = ", ".join(sorted(str(key) for key in chunk.keys())[:8]) or "none"
                            self._log_run_phase(
                                run,
                                f"processed graph chunk {chunk_count}: keys={chunk_keys}",
                            )
                            self._process_chunk(run, chunk)
                            if run.cancel_requested.is_set():
                                raise RunCancelledError()
                    finally:
                        close = getattr(stream, "close", None)
                        if callable(close):
                            close()
                    self._log_run_phase(run, f"graph stream finished after {chunk_count} chunk(s)")

                    final_state = graph.curr_state or {}
                    run.final_state = final_state
                    self._capture_data_fetch_audit(run)
                    self._capture_usage_summary(run, usage_tracker)
                    final_state_keys = ", ".join(sorted(str(key) for key in final_state.keys())[:12]) or "none"
                    self._log_run_phase(run, f"final state collected: keys={final_state_keys}")
                    run.signal = graph.last_signal or graph.process_signal(
                        final_state.get("final_trade_decision", "")
                    )
                    if graph.last_state_log_path is not None:
                        run.state_log_path = str(graph.last_state_log_path)
                        self._augment_state_log(run)
                    if final_state:
                        self._log_run_phase(run, "saving reports")
                        report_path = graph.save_reports(final_state, run.ticker)
                        run.report_path = str(report_path)
                    self._log_data_fetch_audit(run)

                    self._log_run_phase(run, "updating report sections")
                    for section in run.report_sections:
                        if section in final_state and final_state[section]:
                            run.report_sections[section] = final_state[section]
                    self._update_final_report(run)

                    self._log_run_phase(run, "finalizing run state")
                    run._chunk_processor.finalize()
                    for agent in run.agents:
                        run.agents[agent] = "completed"

                    run.status = "completed"
                    run.completed_at = current_timestamp_ms(datetime.datetime.now())
                    self._log_run_phase(run, "completed analysis")
                    terminal_event = self.build_terminal_event(run)
                    if terminal_event is not None:
                        self._put_event(run, terminal_event)
                    self._persist_run(run)

        except RunCancelledError:
            logger.info("Analysis cancelled for run %s", run.run_id)
            self._capture_data_fetch_audit(run)
            self._capture_usage_summary(run, usage_tracker)
            self._augment_state_log(run)
            self._log_data_fetch_audit(run)
            self._log_run_phase(run, "cancelled analysis")
            run.status = "cancelled"
            run.error = None
            run.completed_at = current_timestamp_ms(datetime.datetime.now())
            self._update_final_report(run)
            terminal_event = self.build_terminal_event(run)
            if terminal_event is not None:
                self._put_event(run, terminal_event)
            self._persist_run(run)
        except Exception as e:
            logger.exception("Analysis failed for run %s", run.run_id)
            self._capture_data_fetch_audit(run)
            self._capture_usage_summary(run, usage_tracker)
            self._augment_state_log(run)
            self._log_data_fetch_audit(run)
            self._log_run_phase(run, f"failed analysis: {e}", stream_name="stderr")
            for line in traceback.format_exc().splitlines():
                self._write_terminal_line(run, "stderr", line)
            run.status = "failed"
            run.error = str(e)
            run.completed_at = current_timestamp_ms(datetime.datetime.now())
            terminal_event = self.build_terminal_event(run)
            if terminal_event is not None:
                self._put_event(run, terminal_event)
            self._persist_run(run)
        finally:
            reset_data_fetch_event_sink(event_sink_token)
            self.prune_terminal_runs()

    def _enqueue_run(self, run_id: str) -> None:
        with self._runs_lock:
            if run_id not in self._queued_run_ids:
                self._queued_run_ids.append(run_id)
        self._run_queue.put(run_id)

    def _process_queued_run_id(self, run_id: str) -> bool:
        """Process one queued run id that has already been pulled from the queue."""
        run = self.get_run(run_id)
        with self._runs_lock:
            if run_id in self._queued_run_ids:
                self._queued_run_ids.remove(run_id)
        if run is None:
            return False
        if run.status in TERMINAL_RUN_STATUSES:
            return False
        claim = self._state_backend.acquire_claim(run_id, claims_dir=self._claims_dir)
        if claim is None:
            return False
        run.queue_sequence = None
        if run.cancel_requested.is_set():
            run.status = "cancelled"
            run.completed_at = run.completed_at or current_timestamp_ms(datetime.datetime.now())
            terminal_event = self.build_terminal_event(run)
            if terminal_event is not None:
                self._put_event(run, terminal_event)
            self._persist_run(run)
            self._state_backend.release_claim(claim)
            return True
        run.status = "running"
        try:
            self._run_analysis_thread(run)
            return True
        finally:
            self._state_backend.release_claim(claim)

    def process_next_queued_run(self) -> bool:
        """Process a single queued run if one exists."""
        try:
            run_id = self._run_queue.get_nowait()
        except queue.Empty:
            return False

        try:
            return self._process_queued_run_id(run_id)
        finally:
            self._run_queue.task_done()

    def _run_worker_loop(self) -> None:
        while True:
            self._state_backend.write_worker_status("local_thread", path=self._worker_status_path)
            run_id = self._run_queue.get()
            try:
                self._process_queued_run_id(run_id)
            finally:
                self._run_queue.task_done()

    def run_worker_forever(self, *, poll_interval: float = 1.0) -> None:
        """Poll persisted runs and process queued work in the current process."""
        self.load_runs_index()
        self.resume_incomplete_runs()
        while True:
            self._state_backend.write_worker_status("external_worker", path=self._worker_status_path)
            if self.process_next_queued_run():
                continue
            self.load_runs_index()
            self.resume_incomplete_runs()
            time.sleep(poll_interval)

    def ensure_worker_started(self) -> None:
        """Ensure the in-process background worker is running."""
        with self._worker_lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return
            self._worker_thread = threading.Thread(
                target=self._run_worker_loop,
                name="tradingagents-web-worker",
                daemon=True,
            )
            self._worker_thread.start()

    def create_run(self, req: Any, *, start_worker: bool = True, settings: dict[str, Any] | None = None) -> RunState:
        """Create a new analysis run and enqueue it."""
        self.prune_terminal_runs()
        if start_worker:
            self.ensure_worker_started()
        effective_settings = settings if settings is not None else self.load_tenant_settings()

        run_id = str(uuid.uuid4())
        runtime_context = build_runtime_context(run_id, base_dir=self._runs_root_dir)
        config = self.build_run_request_config(req, runtime_context=runtime_context, settings=effective_settings)
        config["runtime_run_id"] = run_id
        _ensure_provider_api_key_available(config, effective_settings)
        run = RunState(
            run_id=run_id,
            ticker=req.ticker.upper(),
            date=req.date,
            asset_type=req.asset_type,
            config=config,
            selected_analysts=req.analysts,
            runtime_context=runtime_context,
            company_name=req.company_name,
            status="queued",
            queue_sequence=self._next_queue_sequence,
        )
        self._ensure_terminal_log(run)
        self._log_run_configuration(run)
        self._log_run_phase(run, "queued analysis")
        self._next_queue_sequence += 1
        with self._runs_lock:
            self._runs[run_id] = run
        self._put_event(
            run,
            {
                "event": "queued",
                "data": {
                    "message": f"Queued analysis for {run.ticker} on {run.date}",
                },
            },
        )
        if start_worker:
            self._enqueue_run(run_id)
        self._persist_run(run)
        return run

    def build_run_request_config(
        self,
        req: Any,
        *,
        runtime_context: RuntimeContext | None = None,
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build run config from persisted settings plus per-request overrides."""
        base_config = build_run_config({})
        if settings:
            apply_settings_payload(base_config, settings)
        provided_fields = set(getattr(req, "model_fields_set", set()))
        overrides = {}
        if "llm_provider" in provided_fields:
            overrides["llm_provider"] = req.llm_provider.lower() if req.llm_provider else None
        if "quick_think_model" in provided_fields:
            overrides["quick_think_llm"] = req.quick_think_model
        if "deep_think_model" in provided_fields:
            overrides["deep_think_llm"] = req.deep_think_model
        if "output_language" in provided_fields:
            overrides["output_language"] = req.output_language
        if "market_profile" in provided_fields:
            overrides["market_profile"] = req.market_profile
        if "max_risk_discuss_rounds" in provided_fields:
            overrides["max_risk_discuss_rounds"] = req.max_risk_discuss_rounds
        if "max_recur_limit" in provided_fields:
            overrides["max_recur_limit"] = req.max_recur_limit
        if "checkpoint_enabled" in provided_fields:
            overrides["checkpoint_enabled"] = req.checkpoint_enabled
        if "benchmark_ticker" in provided_fields:
            overrides["benchmark_ticker"] = req.benchmark_ticker
        if "backend_url" in provided_fields:
            overrides["backend_url"] = req.backend_url
        if "temperature" in provided_fields:
            overrides["temperature"] = req.temperature
        if "research_depth" in provided_fields:
            overrides["max_debate_rounds"] = req.research_depth
        if "google_thinking_level" in provided_fields:
            overrides["google_thinking_level"] = req.google_thinking_level
        if "openai_reasoning_effort" in provided_fields:
            overrides["openai_reasoning_effort"] = req.openai_reasoning_effort
        if "anthropic_effort" in provided_fields:
            overrides["anthropic_effort"] = req.anthropic_effort
        if runtime_context is not None:
            overrides.update({
                "results_dir": str(runtime_context.results_dir),
                "data_cache_dir": str(runtime_context.cache_dir),
                "memory_log_path": str(runtime_context.memory_log_path),
            })
        for key, value in overrides.items():
            if key not in base_config:
                continue
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            base_config[key] = value
        return base_config
