"""In-process run orchestration service for the current Web runtime."""

from __future__ import annotations

import datetime
import logging
import queue
import threading
import uuid
from copy import deepcopy
from pathlib import Path
import time
from typing import Any

from tradingagents.default_config import apply_settings_payload
from tradingagents.graph.event_processor import build_run_config
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.service.execution_lock import PROCESS_EXECUTION_LOCK
from tradingagents.service.models import RunCancelledError, RunState, TERMINAL_RUN_STATUSES
from tradingagents.service.state_backend import StateBackendAdapter, get_state_backend_adapter
from tradingagents.service.runtime_context import RuntimeContext, build_runtime_context
from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import export_api_keys_to_env, load_settings

logger = logging.getLogger(__name__)

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
        self._next_queue_sequence = 1

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
        now = datetime.datetime.now().isoformat()
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
                key=lambda run: run.created_at or "",
                reverse=True,
            )

    def get_queue_position(self, run_id: str) -> int | None:
        """Return 1-based queue position for queued runs."""
        with self._runs_lock:
            queued_runs = sorted(
                (run for run in self._runs.values() if run.status == "queued"),
                key=lambda run: (run.queue_sequence or 10**12, run.created_at or ""),
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
                key=lambda item: item[1].completed_at or item[1].created_at or ""
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
            self._put_event(run, {"event": "report_update", "data": {"section": section, "content": content}})
            self._update_current_report(run)

    def _update_current_report(self, run: RunState) -> None:
        from tradingagents.graph.event_processor import build_current_report

        run.current_report = build_current_report(run.report_sections)

    def _update_final_report(self, run: RunState) -> None:
        from tradingagents.graph.event_processor import build_final_report

        run.final_report = build_final_report(run.report_sections)

    def _process_chunk(self, run: RunState, chunk: dict[str, Any]) -> None:
        cp = run._chunk_processor

        messages, tools = cp.get_messages_and_tools(chunk)
        for msg in messages:
            self._put_event(run, {"event": "progress", "data": {"message": msg}})
        for tool_name in tools:
            self._put_event(run, {"event": "progress", "data": {"tool_call": tool_name}})

        cp.process_chunk(chunk)

        for agent, status in cp.agent_status.items():
            if run.agents.get(agent) != status:
                self._emit_agent_status(run, agent, status)

        for section, content in cp.report_sections.items():
            if content and run.report_sections.get(section) != content:
                self._emit_report(run, section, content)

        run.current_report = cp.current_report

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
                run.completed_at = datetime.datetime.now().isoformat()
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
            status="queued",
            queue_sequence=self._next_queue_sequence,
        )
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
        try:
            with PROCESS_EXECUTION_LOCK:
                self.apply_tenant_api_keys()
                run.status = "running"
                run.started_at = datetime.datetime.now().isoformat()
                run.queue_sequence = None
                self._put_event(run, {"event": "progress", "data": {"message": f"Starting analysis for {run.ticker} on {run.date}"}})
                self.save_runs_index()
                if run.cancel_requested.is_set():
                    raise RunCancelledError()

                graph = self._graph_factory(
                    run.selected_analysts,
                    config=run.config,
                    debug=False,
                )

                stream = graph.stream_propagate(
                    run.ticker,
                    run.date,
                    asset_type=run.asset_type,
                )
                try:
                    for chunk in stream:
                        self._process_chunk(run, chunk)
                        if run.cancel_requested.is_set():
                            raise RunCancelledError()
                finally:
                    close = getattr(stream, "close", None)
                    if callable(close):
                        close()

                final_state = graph.curr_state or {}
                run.final_state = final_state
                run.signal = graph.last_signal or graph.process_signal(
                    final_state.get("final_trade_decision", "")
                )
                if graph.last_state_log_path is not None:
                    run.state_log_path = str(graph.last_state_log_path)
                if final_state:
                    report_path = graph.save_reports(final_state, run.ticker)
                    run.report_path = str(report_path)

                for section in run.report_sections:
                    if section in final_state and final_state[section]:
                        run.report_sections[section] = final_state[section]
                self._update_final_report(run)

                run._chunk_processor.finalize()
                for agent in run.agents:
                    run.agents[agent] = "completed"

                run.status = "completed"
                run.completed_at = datetime.datetime.now().isoformat()
                terminal_event = self.build_terminal_event(run)
                if terminal_event is not None:
                    self._put_event(run, terminal_event)
                self._persist_run(run)

        except RunCancelledError:
            logger.info("Analysis cancelled for run %s", run.run_id)
            run.status = "cancelled"
            run.error = None
            run.completed_at = datetime.datetime.now().isoformat()
            self._update_final_report(run)
            terminal_event = self.build_terminal_event(run)
            if terminal_event is not None:
                self._put_event(run, terminal_event)
            self._persist_run(run)
        except Exception as e:
            logger.exception("Analysis failed for run %s", run.run_id)
            run.status = "failed"
            run.error = str(e)
            run.completed_at = datetime.datetime.now().isoformat()
            terminal_event = self.build_terminal_event(run)
            if terminal_event is not None:
                self._put_event(run, terminal_event)
            self._persist_run(run)
        finally:
            self.prune_terminal_runs()

    def _enqueue_run(self, run_id: str) -> None:
        with self._runs_lock:
            if run_id not in self._queued_run_ids:
                self._queued_run_ids.append(run_id)
        self._run_queue.put(run_id)

    def process_next_queued_run(self) -> bool:
        """Process a single queued run if one exists."""
        try:
            run_id = self._run_queue.get_nowait()
        except queue.Empty:
            return False

        try:
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
                run.completed_at = run.completed_at or datetime.datetime.now().isoformat()
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
        finally:
            self._run_queue.task_done()

    def _run_worker_loop(self) -> None:
        while True:
            self._state_backend.write_worker_status("local_thread", path=self._worker_status_path)
            run_id = self._run_queue.get()
            try:
                with self._runs_lock:
                    if run_id not in self._queued_run_ids:
                        self._queued_run_ids.append(run_id)
                self.process_next_queued_run()
            except queue.Empty:
                continue

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
        run = RunState(
            run_id=run_id,
            ticker=req.ticker.upper(),
            date=req.date,
            asset_type=req.asset_type,
            config=config,
            selected_analysts=req.analysts,
            runtime_context=runtime_context,
            status="queued",
            queue_sequence=self._next_queue_sequence,
        )
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
