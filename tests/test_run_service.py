"""Tests for the RunService orchestration layer."""

from __future__ import annotations

from pathlib import Path

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
    from tradingagents.service.run_claims import acquire_run_claim, claim_path
    from tradingagents.service.models import RunState
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
    assert retried.config == source.config
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
    from tradingagents.service.run_service import RunService
    from tradingagents.service.run_repository import save_runs_to_index
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
