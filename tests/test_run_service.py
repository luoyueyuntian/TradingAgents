"""Tests for the RunService orchestration layer."""

from __future__ import annotations

import sys
import threading
import time
import re
from pathlib import Path

import pytest

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.service.models import RunState
from tradingagents.service.runtime_context import build_runtime_context
from web.schemas import AnalysisRequest


def test_run_service_create_run_starts_queued(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    enqueued: list[str] = []
    service.ensure_worker_started = lambda: None
    service._enqueue_run = lambda run_id: enqueued.append(run_id)

    run = service.create_run(AnalysisRequest(ticker="AAPL", date="2026-01-15"))

    assert run.status == "queued"
    assert service.get_run(run.run_id) is run
    assert run.runtime_context.run_root == tmp_path / "runs" / run.run_id
    assert enqueued == [run.run_id]


def test_run_service_create_run_keeps_company_name(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service.ensure_worker_started = lambda: None
    service._enqueue_run = lambda run_id: None

    run = service.create_run(
        AnalysisRequest(
            ticker="AAPL",
            company_name="Apple Inc.",
            date="2026-01-15",
        )
    )

    assert run.company_name == "Apple Inc."


def test_run_service_retry_run_keeps_company_name(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    source = RunState(
        run_id="source-run",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("source-run", base_dir=tmp_path / "runs"),
        company_name="Apple Inc.",
        status="completed",
    )
    service._runs[source.run_id] = source

    retried = service.retry_run(source.run_id, start_worker=False)

    assert retried is not None
    assert retried.company_name == "Apple Inc."


def test_run_service_persists_terminal_output_from_analysis(tmp_path):
    from tradingagents.service.run_service import RunService

    class FakeGraph:
        def __init__(self, *args, **kwargs):
            self.curr_state = {
                "market_report": "Momentum is improving.",
                "final_trade_decision": "Hold",
            }
            self.last_signal = "Hold"
            self.last_state_log_path = None

        def stream_propagate(self, ticker, date, asset_type="stock"):
            print("stdout: downloading market data")
            print("stderr: vendor retry", file=sys.stderr)
            yield {"market_report": "Momentum is improving."}

        def process_signal(self, decision):
            return "Hold"

        def save_reports(self, final_state, ticker):
            path = tmp_path / "report.md"
            path.write_text("# Report\n", encoding="utf-8")
            return path

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
        graph_factory=FakeGraph,
    )
    run = RunState(
        run_id="terminal-run",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("terminal-run", base_dir=tmp_path / "runs"),
        status="running",
    )

    service._run_analysis_thread(run)

    terminal_output = Path(run.terminal_log_path).read_text(encoding="utf-8")
    assert "stdout: downloading market data" in terminal_output
    assert "stderr: vendor retry" in terminal_output
    assert any(
        item["event"] == "terminal_output"
        and item["data"]["line"] == "stdout: downloading market data"
        for item in run.event_history
    )


def test_run_service_terminal_log_uses_local_datetime_text_prefix(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    run = RunState(
        run_id="timestamp-run",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("timestamp-run", base_dir=tmp_path / "runs"),
        status="running",
    )

    service._write_terminal_line(run, "stdout", "Phase: smoke test")

    terminal_output = Path(run.terminal_log_path).read_text(encoding="utf-8").strip()
    assert re.match(
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \[run:timestamp-run\] Phase: smoke test$",
        terminal_output,
    )


def test_run_service_logs_run_configuration_and_execution_phases(tmp_path):
    from tradingagents.service.run_service import RunService

    class FakeGraph:
        def __init__(self, selected_analysts, config=None, debug=False):
            assert selected_analysts == ["market"]
            assert config["llm_provider"] == "openai"
            assert config["quick_think_llm"] == "quick-test"
            assert config["deep_think_llm"] == "deep-test"
            assert config["output_language"] == "Chinese"
            assert config["market_profile"] == "cn_a"
            assert config["max_debate_rounds"] == 3
            self.curr_state = {
                "market_report": "Momentum is improving.",
                "final_trade_decision": "Hold",
            }
            self.last_signal = "Hold"
            self.last_state_log_path = None

        def stream_propagate(self, ticker, date, asset_type="stock"):
            yield {"market_report": "Momentum is improving."}

        def process_signal(self, decision):
            return "Hold"

        def save_reports(self, final_state, ticker):
            path = tmp_path / "report.md"
            path.write_text("# Report\n", encoding="utf-8")
            return path

    config = DEFAULT_CONFIG.copy()
    config.update({
        "llm_provider": "openai",
        "quick_think_llm": "quick-test",
        "deep_think_llm": "deep-test",
        "output_language": "Chinese",
        "market_profile": "cn_a",
        "max_debate_rounds": 3,
        "max_risk_discuss_rounds": 2,
        "max_recur_limit": 88,
        "checkpoint_enabled": True,
    })
    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
        graph_factory=FakeGraph,
    )
    run = RunState(
        run_id="phase-run",
        ticker="600941.SS",
        date="2026-07-03",
        asset_type="stock",
        config=config,
        selected_analysts=["market"],
        runtime_context=build_runtime_context("phase-run", base_dir=tmp_path / "runs"),
        status="running",
    )

    service._run_analysis_thread(run)

    terminal_output = Path(run.terminal_log_path).read_text(encoding="utf-8")
    assert "Run configuration" in terminal_output
    assert "selected_analysts: market" in terminal_output
    assert "llm_provider: openai" in terminal_output
    assert "quick_think_llm: quick-test" in terminal_output
    assert "deep_think_llm: deep-test" in terminal_output
    assert "output_language: Chinese" in terminal_output
    assert "market_profile: cn_a" in terminal_output
    assert "max_debate_rounds: 3" in terminal_output
    assert "max_risk_discuss_rounds: 2" in terminal_output
    assert "max_recur_limit: 88" in terminal_output
    assert "checkpoint_enabled: True" in terminal_output
    assert "Phase: waiting for execution lock" in terminal_output
    assert "Phase: initializing trading graph" in terminal_output
    assert "Phase: starting graph stream" in terminal_output
    assert "Phase: processed graph chunk 1" in terminal_output
    assert "Phase: saving reports" in terminal_output
    assert "Phase: completed analysis" in terminal_output


def test_run_service_logs_multi_vendor_market_failure_details(tmp_path):
    from tradingagents.dataflows.errors import NoMarketDataError
    from tradingagents.service.run_service import RunService

    class FakeGraph:
        def __init__(self, *args, **kwargs):
            self.curr_state = {}
            self.last_signal = None
            self.last_state_log_path = None

        def stream_propagate(self, ticker, date, asset_type="stock"):
            raise NoMarketDataError(
                ticker,
                "600036",
                "cn_stock: China A-share history is currently unavailable (remote closed connection) | "
                "yfinance: Yahoo Finance returned no rows",
            )
            yield  # pragma: no cover

        def process_signal(self, decision):
            return "Hold"

        def save_reports(self, final_state, ticker):
            raise AssertionError("save_reports should not run on failure")

    config = DEFAULT_CONFIG.copy()
    config["market_profile"] = "cn_a"
    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
        graph_factory=FakeGraph,
    )
    run = RunState(
        run_id="failure-run",
        ticker="600036.SS",
        date="2026-07-09",
        asset_type="stock",
        config=config,
        selected_analysts=["market"],
        runtime_context=build_runtime_context("failure-run", base_dir=tmp_path / "runs"),
        status="running",
    )

    service._run_analysis_thread(run)

    terminal_output = Path(run.terminal_log_path).read_text(encoding="utf-8")
    assert "Phase: failed analysis:" in terminal_output
    assert "cn_stock: China A-share history is currently unavailable" in terminal_output
    assert "yfinance: Yahoo Finance returned no rows" in terminal_output
    assert run.status == "failed"
    assert "cn_stock: China A-share history is currently unavailable" in (run.error or "")
    assert "yfinance: Yahoo Finance returned no rows" in (run.error or "")


def test_local_worker_processes_enqueued_run(tmp_path):
    from tradingagents.service.run_service import RunService

    class FakeGraph:
        def __init__(self, *args, **kwargs):
            self.curr_state = {
                "market_report": "Momentum is improving.",
                "final_trade_decision": "Hold",
            }
            self.last_signal = "Hold"
            self.last_state_log_path = None

        def stream_propagate(self, ticker, date, asset_type="stock"):
            yield {"market_report": "Momentum is improving."}

        def process_signal(self, decision):
            return "Hold"

        def save_reports(self, final_state, ticker):
            path = tmp_path / "report.md"
            path.write_text("# Report\n", encoding="utf-8")
            return path

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
        graph_factory=FakeGraph,
    )

    run = service.create_run(AnalysisRequest(ticker="AAPL", date="2026-01-15"))

    deadline = time.time() + 2
    while time.time() < deadline and run.status != "completed":
        time.sleep(0.02)

    assert run.status == "completed"
    assert service.get_queue_position(run.run_id) is None


def test_run_service_rejects_key_required_provider_before_enqueue(monkeypatch, tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    enqueued: list[str] = []
    service.ensure_worker_started = lambda: None
    service._enqueue_run = lambda run_id: enqueued.append(run_id)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key-that-tenant-settings-would-clear")

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        service.create_run(
            AnalysisRequest(
                ticker="600941.SS",
                date="2026-07-03",
                llm_provider="deepseek",
                quick_think_model="deepseek-v4-flash",
                deep_think_model="deepseek-v4-pro",
            ),
            settings={
                "analysis": {"output_language": "Chinese"},
                "api_keys": {"deepseek": ""},
            },
        )

    assert enqueued == []
    assert service.list_runs() == []


def test_run_service_apply_tenant_api_keys_uses_tenant_settings(monkeypatch, tmp_path):
    from tradingagents.service.run_service import RunService

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "tradingagents.service.run_service.get_web_settings_path",
        lambda tenant_id=None: tmp_path / f"{tenant_id}.json",
    )
    monkeypatch.setattr(
        "tradingagents.service.run_service.load_settings",
        lambda path=None: {"api_keys": {"openai": "tenant-key"}, "security": {"web_api_token": "tenant-secret"}},
    )
    monkeypatch.setattr(
        "tradingagents.service.run_service.export_api_keys_to_env",
        lambda settings=None, overwrite=False, path=None: captured.update({"settings": settings, "overwrite": overwrite}),
    )

    service = RunService(
        tenant_id="tenant-a",
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )

    service.apply_tenant_api_keys()

    assert captured["settings"]["api_keys"]["openai"] == "tenant-key"
    assert captured["overwrite"] is True


def test_run_service_serializes_run_execution_across_tenants(monkeypatch, tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    release_first = threading.Event()
    first_stream_started = threading.Event()
    second_apply_started = threading.Event()
    apply_order: list[str] = []

    class FakeGraph:
        def __init__(self, tenant_id: str):
            self.curr_state = {}
            self.last_signal = "Hold"
            self.last_state_log_path = None
            self._tenant_id = tenant_id

        def stream_propagate(self, ticker, date, asset_type="stock"):
            if self._tenant_id == "tenant-a":
                first_stream_started.set()
                release_first.wait(timeout=2)
            yield from ()

        def process_signal(self, decision):
            return "Hold"

        def save_reports(self, final_state, ticker):
            target = tmp_path / f"{self._tenant_id}-report.md"
            target.write_text("# Report\n", encoding="utf-8")
            return target

    service_a = RunService(
        tenant_id="tenant-a",
        runs_index_path=tmp_path / "tenant-a-runs.json",
        run_events_dir=tmp_path / "tenant-a-events",
        runs_root_dir=tmp_path / "tenant-a-runs",
    )
    service_b = RunService(
        tenant_id="tenant-b",
        runs_index_path=tmp_path / "tenant-b-runs.json",
        run_events_dir=tmp_path / "tenant-b-events",
        runs_root_dir=tmp_path / "tenant-b-runs",
    )

    monkeypatch.setattr(service_a, "_graph_factory", lambda *args, **kwargs: FakeGraph("tenant-a"))
    monkeypatch.setattr(service_b, "_graph_factory", lambda *args, **kwargs: FakeGraph("tenant-b"))
    monkeypatch.setattr(service_a, "_persist_run", lambda run: None)
    monkeypatch.setattr(service_b, "_persist_run", lambda run: None)
    monkeypatch.setattr(service_a, "prune_terminal_runs", lambda *args, **kwargs: None)
    monkeypatch.setattr(service_b, "prune_terminal_runs", lambda *args, **kwargs: None)

    def _mark_apply(service: RunService):
        def _inner():
            apply_order.append(service._tenant_id or "default")
            if service._tenant_id == "tenant-b":
                second_apply_started.set()
        return _inner

    monkeypatch.setattr(service_a, "apply_tenant_api_keys", _mark_apply(service_a))
    monkeypatch.setattr(service_b, "apply_tenant_api_keys", _mark_apply(service_b))

    run_a = RunState(
        run_id="run-a",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("run-a", base_dir=tmp_path / "tenant-a-runs"),
        status="running",
    )
    run_b = RunState(
        run_id="run-b",
        ticker="MSFT",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("run-b", base_dir=tmp_path / "tenant-b-runs"),
        status="running",
    )

    thread_a = threading.Thread(target=service_a._run_analysis_thread, args=(run_a,))
    thread_b = threading.Thread(target=service_b._run_analysis_thread, args=(run_b,))

    thread_a.start()
    assert first_stream_started.wait(timeout=1), "first run never started streaming"

    thread_b.start()
    time.sleep(0.1)
    assert second_apply_started.is_set() is False

    release_first.set()
    thread_a.join(timeout=2)
    thread_b.join(timeout=2)

    assert apply_order == ["tenant-a", "tenant-b"]
    assert run_a.status == "completed"
    assert run_b.status == "completed"


def test_run_service_uses_injected_state_backend(tmp_path):
    from pathlib import Path

    from tradingagents.service.run_service import RunService

    class FakeBackend:
        kind = "fake"
        location = tmp_path / "fake"

        def __init__(self):
            self.upserted: list[str] = []

        def upsert_run(self, run, *, index_path=None):
            self.upserted.append(run.run_id)

        def delete_run(self, run_id, *, index_path=None):
            return None

        def delete_run_state(self, run_id, **kwargs):
            return None

        def load_runs(self, *, runs_root_dir, index_path=None):
            return {}

        def save_runs(self, runs, *, index_path=None):
            return None

        def append_event(self, run_id, event, *, event_log_path=None, base_dir=None):
            return Path("fake"), {"event": event["event"], "data": event["data"], "timestamp": "now"}

        def load_events(self, run_id, *, event_log_path=None, base_dir=None):
            return Path("fake"), []

        def write_worker_status(self, worker_mode, *, path=None):
            return None

        def read_worker_status(self, *, path=None, stale_after_seconds=5):
            return {"worker_running": False, "worker_mode": "fake", "last_seen": None}

        def acquire_claim(self, run_id, *, claims_dir=None):
            return Path("fake")

        def release_claim(self, path=None, *, run_id=None, claims_dir=None):
            return None

    backend = FakeBackend()
    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
        state_backend=backend,
    )
    service.ensure_worker_started = lambda: None
    service._enqueue_run = lambda run_id: None

    run = service.create_run(AnalysisRequest(ticker="AAPL", date="2026-01-15"), start_worker=False)
    snapshot = service.get_status_snapshot()

    assert backend.upserted == [run.run_id]
    assert snapshot["worker_mode"] == "fake"


def test_run_service_resume_incomplete_runs_requeues_active_work(tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_claims import acquire_run_claim, claim_path
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
        claims_dir=tmp_path / "claims",
    )

    queued = RunState(
        run_id="queued",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("queued", base_dir=tmp_path / "runs"),
        status="queued",
    )
    running = RunState(
        run_id="running",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("running", base_dir=tmp_path / "runs"),
        status="running",
    )
    cancelling = RunState(
        run_id="cancelling",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("cancelling", base_dir=tmp_path / "runs"),
        status="cancelling",
    )
    service._runs = {queued.run_id: queued, running.run_id: running, cancelling.run_id: cancelling}
    stale_claim = acquire_run_claim(running.run_id, claims_dir=tmp_path / "claims")
    assert stale_claim is not None and stale_claim.exists()

    enqueued: list[str] = []
    service._enqueue_run = lambda run_id: enqueued.append(run_id)

    service.resume_incomplete_runs()

    assert queued.status == "queued"
    assert running.status == "queued"
    assert cancelling.status == "cancelled"
    assert enqueued == ["queued", "running"]
    assert not claim_path(running.run_id, claims_dir=tmp_path / "claims").exists()


def test_run_service_delete_run_removes_terminal_state_and_files(tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    context = build_runtime_context("done", base_dir=tmp_path / "runs")
    run = RunState(
        run_id="done",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=context,
        status="completed",
    )
    report_file = context.results_dir / "complete_report.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("report", encoding="utf-8")
    event_file = tmp_path / "events" / "done.jsonl"
    event_file.parent.mkdir(parents=True, exist_ok=True)
    event_file.write_text("{}", encoding="utf-8")
    run.report_path = str(report_file)
    run.event_log_path = str(event_file)
    service._runs = {run.run_id: run}

    deleted = service.delete_run(run.run_id)

    assert deleted is run
    assert service.get_run(run.run_id) is None
    assert not report_file.exists()
    assert not event_file.exists()


def test_run_service_delete_run_cleans_sqlite_state(monkeypatch, tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.event_publisher import append_event_record, load_event_history
    from tradingagents.service.models import RunState
    from tradingagents.service.run_claims import acquire_run_claim
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    db_path = tmp_path / "state.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("TRADINGAGENTS_WEB_SQLITE_PATH", str(db_path))

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
        claims_dir=tmp_path / "claims",
    )
    context = build_runtime_context("done", base_dir=tmp_path / "runs")
    run = RunState(
        run_id="done",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=context,
        status="completed",
    )
    service._runs = {run.run_id: run}
    service.save_runs_index()
    append_event_record(run.run_id, {"event": "progress", "data": {"message": "hello"}})
    claim = acquire_run_claim(run.run_id, claims_dir=tmp_path / "claims")
    assert claim is not None

    deleted = service.delete_run(run.run_id)

    assert deleted is run
    service.load_runs_index()
    assert service.get_run(run.run_id) is None
    _, history = load_event_history(run.run_id)
    assert history == []
    assert acquire_run_claim(run.run_id, claims_dir=tmp_path / "claims") is not None


def test_run_service_prune_terminal_runs_deletes_pruned_files(tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )

    old_context = build_runtime_context("old", base_dir=tmp_path / "runs")
    old_run = RunState(
        run_id="old",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=old_context,
        status="completed",
        created_at="2026-01-15T00:00:00",
        completed_at="2026-01-15T00:10:00",
    )
    old_report = old_context.results_dir / "complete_report.md"
    old_report.parent.mkdir(parents=True, exist_ok=True)
    old_report.write_text("old", encoding="utf-8")
    old_event = tmp_path / "events" / "old.jsonl"
    old_event.parent.mkdir(parents=True, exist_ok=True)
    old_event.write_text("{}", encoding="utf-8")
    old_run.report_path = str(old_report)
    old_run.event_log_path = str(old_event)

    new_context = build_runtime_context("new", base_dir=tmp_path / "runs")
    new_run = RunState(
        run_id="new",
        ticker="MSFT",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=new_context,
        status="failed",
        created_at="2026-01-15T01:00:00",
        completed_at="2026-01-15T01:10:00",
    )
    service._runs = {"old": old_run, "new": new_run}

    service.prune_terminal_runs(max_completed=1)

    assert sorted(service._runs) == ["new"]
    assert not old_context.run_root.exists()
    assert not old_event.exists()


def test_run_service_retry_run_clones_terminal_run(tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service.ensure_worker_started = lambda: None
    enqueued: list[str] = []
    service._enqueue_run = lambda run_id: enqueued.append(run_id)

    source = RunState(
        run_id="done",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market", "news"],
        runtime_context=build_runtime_context("done", base_dir=tmp_path / "runs"),
        status="completed",
    )
    service._runs = {source.run_id: source}

    retried = service.retry_run(source.run_id)

    assert retried is not None
    assert retried.run_id != source.run_id
    assert retried.status == "queued"
    assert retried.ticker == source.ticker
    assert retried.date == source.date
    assert retried.selected_analysts == source.selected_analysts
    source_config = dict(source.config)
    retried_config = dict(retried.config)
    assert retried_config.pop("runtime_run_id") == retried.run_id
    assert retried_config == source_config
    assert "runtime_run_id" not in source.config
    assert enqueued == [retried.run_id]


def test_run_service_retry_run_rejects_active_run(tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    active = RunState(
        run_id="active",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("active", base_dir=tmp_path / "runs"),
        status="running",
    )
    service._runs = {active.run_id: active}

    assert service.retry_run(active.run_id) is None


def test_run_service_retry_run_without_local_worker_skips_local_queue(tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service.ensure_worker_started = lambda: None
    enqueued: list[str] = []
    service._enqueue_run = lambda run_id: enqueued.append(run_id)

    source = RunState(
        run_id="done",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("done", base_dir=tmp_path / "runs"),
        status="completed",
    )
    service._runs = {source.run_id: source}

    retried = service.retry_run(source.run_id, start_worker=False)

    assert retried is not None
    assert retried.status == "queued"
    assert enqueued == []


def test_run_service_queue_position_tracks_enqueued_runs(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service.ensure_worker_started = lambda: None
    enqueued: list[str] = []
    service._enqueue_run = lambda run_id: enqueued.append(run_id) or service._queued_run_ids.append(run_id)

    first = service.create_run(AnalysisRequest(ticker="AAPL", date="2026-01-15"))
    second = service.create_run(AnalysisRequest(ticker="MSFT", date="2026-01-15"))

    assert service.get_queue_position(first.run_id) == 1
    assert service.get_queue_position(second.run_id) == 2


def test_run_service_create_run_without_local_worker_skips_local_queue(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service.ensure_worker_started = lambda: None
    enqueued: list[str] = []
    service._enqueue_run = lambda run_id: enqueued.append(run_id)

    run = service.create_run(
        AnalysisRequest(ticker="AAPL", date="2026-01-15"),
        start_worker=False,
    )

    assert run.status == "queued"
    assert enqueued == []


def test_run_service_status_snapshot_reports_queue_depth(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service.ensure_worker_started = lambda: None
    service._enqueue_run = lambda run_id: service._queued_run_ids.append(run_id)

    service.create_run(AnalysisRequest(ticker="AAPL", date="2026-01-15"), start_worker=False)
    service.create_run(AnalysisRequest(ticker="MSFT", date="2026-01-15"), start_worker=False)

    snapshot = service.get_status_snapshot()

    assert snapshot["queue_depth"] == 2
    assert snapshot["run_count"] == 2
    assert snapshot["worker_running"] is False


def test_run_service_queue_position_survives_reload(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service.ensure_worker_started = lambda: None
    service._enqueue_run = lambda run_id: service._queued_run_ids.append(run_id)

    first = service.create_run(AnalysisRequest(ticker="AAPL", date="2026-01-15"), start_worker=False)
    second = service.create_run(AnalysisRequest(ticker="MSFT", date="2026-01-15"), start_worker=False)
    service.save_runs_index()

    restored = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    restored.load_runs_index()

    assert restored.get_queue_position(first.run_id) == 1
    assert restored.get_queue_position(second.run_id) == 2


def test_run_service_process_next_queued_run_executes_one_job(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service.ensure_worker_started = lambda: None
    run = service.create_run(AnalysisRequest(ticker="AAPL", date="2026-01-15"), start_worker=False)
    service._enqueue_run(run.run_id)
    executed: list[str] = []
    service._run_analysis_thread = lambda queued_run: executed.append(queued_run.run_id)

    processed = service.process_next_queued_run()

    assert processed is True
    assert executed == [run.run_id]
    assert service.get_queue_position(run.run_id) is None


def test_run_service_process_next_queued_run_returns_false_when_empty(tmp_path):
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )

    assert service.process_next_queued_run() is False


def test_run_service_save_runs_index_preserves_unloaded_runs(tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_repository import save_runs_to_index
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    existing = RunState(
        run_id="existing",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("existing", base_dir=tmp_path / "runs"),
        status="completed",
    )
    save_runs_to_index([existing], index_path=tmp_path / "runs.json")

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    new_run = RunState(
        run_id="new",
        ticker="MSFT",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("new", base_dir=tmp_path / "runs"),
        status="queued",
    )
    service._runs = {new_run.run_id: new_run}

    service.save_runs_index()

    reloaded = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    reloaded.load_runs_index()

    assert sorted(reloaded._runs) == ["existing", "new"]


def test_run_service_create_run_does_not_reinsert_deleted_stale_run(tmp_path):
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.service.models import RunState
    from tradingagents.service.run_service import RunService
    from tradingagents.service.runtime_context import build_runtime_context

    index_path = tmp_path / "runs.json"
    service_a = RunService(
        runs_index_path=index_path,
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    service_b = RunService(
        runs_index_path=index_path,
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    old_run = RunState(
        run_id="old",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("old", base_dir=tmp_path / "runs"),
        status="completed",
    )
    service_a._runs = {old_run.run_id: old_run}
    service_a.save_runs_index()
    service_a.load_runs_index()
    service_b.load_runs_index()

    service_b.delete_run("old")

    service_a.ensure_worker_started = lambda: None
    service_a._enqueue_run = lambda run_id: None
    service_a.create_run(AnalysisRequest(ticker="MSFT", date="2026-01-15"), start_worker=False)

    reloaded = RunService(
        runs_index_path=index_path,
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
    )
    reloaded.load_runs_index()

    assert "old" not in reloaded._runs


def test_run_service_process_next_queued_run_skips_claimed_run(tmp_path):
    from tradingagents.service.run_claims import acquire_run_claim
    from tradingagents.service.run_service import RunService

    service = RunService(
        runs_index_path=tmp_path / "runs.json",
        run_events_dir=tmp_path / "events",
        runs_root_dir=tmp_path / "runs",
        claims_dir=tmp_path / "claims",
    )
    service.ensure_worker_started = lambda: None
    run = service.create_run(AnalysisRequest(ticker="AAPL", date="2026-01-15"), start_worker=False)
    claim = acquire_run_claim(run.run_id, claims_dir=tmp_path / "claims")
    assert claim is not None
    executed: list[str] = []
    service._run_analysis_thread = lambda queued_run: executed.append(queued_run.run_id)

    processed = service.process_next_queued_run()

    assert processed is False
    assert executed == []
