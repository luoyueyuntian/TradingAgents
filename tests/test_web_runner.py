"""Regression tests for the FastAPI web runner layer."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.event_processor import build_run_config
from tradingagents.service.runtime_context import build_runtime_context
from web import runner as web_runner
from web.schemas import AnalysisRequest


def _make_run_state(
    *,
    run_id: str = "run-1",
    status: str = "pending",
    completed_at: str | None = None,
):
    runtime_context = build_runtime_context(run_id, base_dir=Path("/tmp/tradingagents-tests"))
    run = web_runner.RunState(
        run_id=run_id,
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=runtime_context,
    )
    run.status = status
    run.completed_at = completed_at
    return run


@pytest.mark.unit
def test_analysis_request_normalizes_blank_optional_strings_to_none():
    req = AnalysisRequest(
        ticker="AAPL",
        date="2026-01-15",
        quick_think_model="",
        deep_think_model="  ",
        backend_url="",
    )

    assert req.quick_think_model is None
    assert req.deep_think_model is None
    assert req.backend_url is None


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("analysts", []),
        ("analysts", ["bogus"]),
        ("research_depth", 0),
        ("date", "2026/01/15"),
    ],
)
def test_analysis_request_rejects_invalid_inputs(field, value):
    kwargs = {"ticker": "AAPL", "date": "2026-01-15"}
    kwargs[field] = value

    with pytest.raises(ValidationError):
        AnalysisRequest(**kwargs)


@pytest.mark.unit
def test_build_run_config_ignores_blank_string_overrides():
    config = build_run_config(
        {
            "quick_think_llm": "",
            "deep_think_llm": "   ",
            "backend_url": "",
        }
    )

    assert config["quick_think_llm"] == DEFAULT_CONFIG["quick_think_llm"]
    assert config["deep_think_llm"] == DEFAULT_CONFIG["deep_think_llm"]
    assert config["backend_url"] == DEFAULT_CONFIG["backend_url"]


@pytest.mark.unit
def test_build_run_request_config_preserves_non_form_settings():
    req = AnalysisRequest(
        ticker="AAPL",
        date="2026-01-15",
        research_depth=3,
    )

    runtime_context = build_runtime_context("run-123", base_dir=Path("/tmp/tradingagents-tests"))
    config = web_runner.build_run_request_config(req, runtime_context=runtime_context)

    assert config["max_debate_rounds"] == 3
    assert config["max_risk_discuss_rounds"] == DEFAULT_CONFIG["max_risk_discuss_rounds"]
    assert config["results_dir"] == str(runtime_context.results_dir)
    assert config["data_cache_dir"] == str(runtime_context.cache_dir)
    assert config["memory_log_path"] == str(runtime_context.memory_log_path)


@pytest.mark.unit
def test_build_run_request_config_applies_settings_payload():
    req = AnalysisRequest(
        ticker="AAPL",
        date="2026-01-15",
    )
    settings = {
        "llm": {"provider": "google", "quick_think_model": "gemini-3.5-flash"},
        "analysis": {"output_language": "Chinese", "research_depth": 3, "market_profile": "cn_a"},
        "data": {"data_vendors": {"news_data": "cn_news"}},
    }

    config = web_runner.build_run_request_config(req, settings=settings)

    assert config["llm_provider"] == "google"
    assert config["quick_think_llm"] == "gemini-3.5-flash"
    assert config["output_language"] == "Chinese"
    assert config["max_debate_rounds"] == 3
    assert config["market_profile"] == "cn_a"
    assert config["data_vendors"]["news_data"] == "cn_news"


@pytest.mark.unit
def test_build_run_request_config_applies_advanced_request_overrides():
    req = AnalysisRequest(
        ticker="AAPL",
        date="2026-01-15",
        market_profile="cn_a",
        max_risk_discuss_rounds=2,
        max_recur_limit=150,
        checkpoint_enabled=True,
        benchmark_ticker="QQQ",
    )

    config = web_runner.build_run_request_config(req)

    assert config["market_profile"] == "cn_a"
    assert config["max_risk_discuss_rounds"] == 2
    assert config["max_recur_limit"] == 150
    assert config["checkpoint_enabled"] is True
    assert config["benchmark_ticker"] == "QQQ"


@pytest.mark.unit
def test_create_run_enqueues_and_returns_queued_status(monkeypatch):
    req = AnalysisRequest(ticker="AAPL", date="2026-01-15")
    enqueued: list[str] = []

    class DummyLoop:
        def is_closed(self):
            return False

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        web_runner._service,
        "create_run",
        lambda incoming_req, *, start_worker=True, settings=None: (
            captured.update({"req": incoming_req, "start_worker": start_worker, "settings": settings}) or _make_run_state(status="queued")
        ),
    )

    run = web_runner.create_run(req, DummyLoop())

    assert run.status == "queued"
    assert captured["start_worker"] is True


@pytest.mark.unit
def test_create_run_can_disable_local_worker(monkeypatch):
    req = AnalysisRequest(ticker="AAPL", date="2026-01-15")
    captured: dict[str, object] = {}

    monkeypatch.setenv("TRADINGAGENTS_WEB_RUN_MODE", "external_worker")
    monkeypatch.setattr(
        web_runner._service,
        "create_run",
        lambda incoming_req, *, start_worker=True, settings=None: (
            captured.update({"req": incoming_req, "start_worker": start_worker, "settings": settings}) or _make_run_state(status="queued")
        ),
    )

    run = web_runner.create_run(req, None)

    assert run.status == "queued"
    assert captured["start_worker"] is False


@pytest.mark.unit
def test_create_run_loads_tenant_scoped_settings(monkeypatch, tmp_path):
    req = AnalysisRequest(ticker="AAPL", date="2026-01-15")
    captured: dict[str, object] = {}

    monkeypatch.setattr(web_runner, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id}.json")
    monkeypatch.setattr(web_runner, "load_settings", lambda path=None: {"analysis": {"output_language": "Chinese"}})
    fake_service = type("FakeService", (), {
        "create_run": lambda self, incoming_req, *, start_worker=True, settings=None: (
            captured.update({"settings": settings}) or _make_run_state(status="queued")
        )
    })()
    monkeypatch.setattr(
        web_runner,
        "get_service",
        lambda tenant_id=None: fake_service,
    )

    run = web_runner.create_run(req, None, tenant_id="tenant-a")

    assert run.status == "queued"
    assert captured["settings"]["analysis"]["output_language"] == "Chinese"


@pytest.mark.unit
def test_retry_run_can_disable_local_worker(monkeypatch):
    captured: dict[str, object] = {}

    monkeypatch.setenv("TRADINGAGENTS_WEB_RUN_MODE", "external_worker")
    monkeypatch.setattr(
        web_runner._service,
        "retry_run",
        lambda run_id, *, start_worker=True: (
            captured.update({"run_id": run_id, "start_worker": start_worker}) or _make_run_state(status="queued")
        ),
    )

    run = web_runner.retry_run("source-run")

    assert run.status == "queued"
    assert captured["run_id"] == "source-run"
    assert captured["start_worker"] is False


@pytest.mark.unit
def test_get_run_refreshes_from_storage_in_external_worker_mode(monkeypatch):
    fresh_run = _make_run_state(run_id="fresh", status="completed")
    monkeypatch.setenv("TRADINGAGENTS_WEB_RUN_MODE", "external_worker")
    monkeypatch.setattr(web_runner._service, "load_runs_index", lambda: web_runner._service._runs.update({fresh_run.run_id: fresh_run}))
    monkeypatch.setattr(web_runner._service, "_runs", {})

    run = web_runner.get_run("fresh")

    assert run is fresh_run


@pytest.mark.unit
def test_list_runs_refreshes_from_storage_in_external_worker_mode(monkeypatch):
    run = _make_run_state(run_id="fresh", status="completed")
    monkeypatch.setenv("TRADINGAGENTS_WEB_RUN_MODE", "external_worker")
    monkeypatch.setattr(web_runner._service, "load_runs_index", lambda: web_runner._service._runs.update({run.run_id: run}))
    monkeypatch.setattr(web_runner._service, "_runs", {})

    runs = web_runner.list_runs()

    assert runs == [run]


@pytest.mark.unit
def test_get_queue_position_refreshes_from_storage_in_external_worker_mode(monkeypatch):
    first = _make_run_state(run_id="first", status="queued")
    first.queue_sequence = 1
    second = _make_run_state(run_id="second", status="queued")
    second.queue_sequence = 2
    monkeypatch.setenv("TRADINGAGENTS_WEB_RUN_MODE", "external_worker")
    monkeypatch.setattr(
        web_runner._service,
        "load_runs_index",
        lambda: web_runner._service._runs.update({first.run_id: first, second.run_id: second}),
    )
    monkeypatch.setattr(web_runner._service, "_runs", {})

    assert web_runner.get_queue_position("first") == 1
    assert web_runner.get_queue_position("second") == 2


@pytest.mark.unit
def test_get_service_returns_distinct_instances_per_tenant(monkeypatch, tmp_path):
    import web.runner as runner_module

    class FakeService:
        def __init__(self, *, tenant_id, **kwargs):
            self.tenant_id = tenant_id

    monkeypatch.setattr(runner_module, "_services", {})
    monkeypatch.setattr(runner_module, "RunService", FakeService)
    monkeypatch.setattr(runner_module, "get_web_runs_index_path", lambda tenant_id=None: tmp_path / (tenant_id or "default") / "runs.json")
    monkeypatch.setattr(runner_module, "get_web_events_dir", lambda tenant_id=None: tmp_path / (tenant_id or "default") / "events")
    monkeypatch.setattr(runner_module, "get_web_runs_root", lambda tenant_id=None: tmp_path / (tenant_id or "default") / "runs")
    monkeypatch.setattr(runner_module, "get_web_worker_status_path", lambda tenant_id=None: tmp_path / (tenant_id or "default") / "worker-status.json")
    monkeypatch.setattr(runner_module, "get_web_claims_dir", lambda tenant_id=None: tmp_path / (tenant_id or "default") / "claims")

    tenant_a = runner_module.get_service("tenant-a")
    tenant_b = runner_module.get_service("tenant-b")
    tenant_a_again = runner_module.get_service("tenant-a")

    assert tenant_a is tenant_a_again
    assert tenant_a is not tenant_b


@pytest.mark.unit
def test_get_state_location_uses_tenant_namespace(monkeypatch):
    monkeypatch.setenv("TRADINGAGENTS_WEB_TENANT_ID", "env-tenant")
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_BACKEND", "file")

    assert "header-tenant" in web_runner.get_state_location("header-tenant")



@pytest.mark.unit
def test_run_events_are_fanned_out_to_each_subscriber():
    async def exercise():
        run = _make_run_state()
        sub1, queue1 = web_runner.subscribe_run_events(run)
        sub2, queue2 = web_runner.subscribe_run_events(run)

        try:
            event = {"event": "progress", "data": {"message": "hello"}}
            web_runner._put_event(run, event)

            assert await asyncio.wait_for(queue1.get(), timeout=1) == event
            assert await asyncio.wait_for(queue2.get(), timeout=1) == event
        finally:
            web_runner.unsubscribe_run_events(run, sub1)
            web_runner.unsubscribe_run_events(run, sub2)

    asyncio.run(exercise())


@pytest.mark.unit
def test_put_event_persists_event_history(monkeypatch, tmp_path):
    async def exercise():
        run = _make_run_state(run_id="events")
        run.event_log_path = str(tmp_path / "events.jsonl")
        sub, queue = web_runner.subscribe_run_events(run)
        try:
            event = {"event": "progress", "data": {"message": "hello"}}
            web_runner._put_event(run, event)
            assert await asyncio.wait_for(queue.get(), timeout=1) == event
        finally:
            web_runner.unsubscribe_run_events(run, sub)

        assert len(run.event_history) == 1
        assert run.event_history[0]["event"] == "progress"
        assert "hello" in Path(run.event_log_path).read_text(encoding="utf-8")

    from pathlib import Path

    asyncio.run(exercise())


@pytest.mark.unit
def test_prune_terminal_runs_keeps_active_and_newest_completed(monkeypatch):
    old_run = _make_run_state(
        run_id="old",
        status="completed",
        completed_at="2026-01-15T00:00:00",
    )
    new_run = _make_run_state(
        run_id="new",
        status="failed",
        completed_at="2026-01-15T01:00:00",
    )
    active_run = _make_run_state(run_id="active", status="running")

    monkeypatch.setattr(web_runner._service, "_runs", {"old": old_run, "new": new_run, "active": active_run})

    web_runner.prune_terminal_runs(max_completed=1)

    assert set(web_runner._service._runs) == {"new", "active"}


@pytest.mark.unit
def test_list_runs_returns_newest_first(monkeypatch):
    old_run = _make_run_state(run_id="old")
    old_run.created_at = "2026-01-15T00:00:00"
    new_run = _make_run_state(run_id="new")
    new_run.created_at = "2026-01-15T01:00:00"

    monkeypatch.setattr(web_runner._service, "_runs", {"old": old_run, "new": new_run})

    runs = web_runner.list_runs()

    assert [run.run_id for run in runs] == ["new", "old"]


@pytest.mark.unit
def test_cancel_run_marks_active_run_as_cancelling(monkeypatch):
    run = _make_run_state(status="running")
    monkeypatch.setattr(web_runner._service, "_runs", {run.run_id: run})

    result = web_runner.cancel_run(run.run_id)

    assert result is run
    assert run.status == "cancelling"
    assert run.cancel_requested.is_set() is True


@pytest.mark.unit
def test_cancel_run_marks_queued_run_cancelled(monkeypatch):
    run = _make_run_state(status="queued")
    monkeypatch.setattr(web_runner._service, "_runs", {run.run_id: run})

    result = web_runner.cancel_run(run.run_id)

    assert result is run
    assert run.status == "cancelled"
    assert run.completed_at is not None


@pytest.mark.unit
def test_delete_run_removes_terminal_run_and_files(monkeypatch, tmp_path):
    run = _make_run_state(run_id="delete-me", status="completed")
    run.runtime_context = build_runtime_context("delete-me", base_dir=tmp_path / "runs")
    run.report_path = str(run.runtime_context.results_dir / "complete_report.md")
    run.state_log_path = str(run.runtime_context.results_dir / "full_state.json")
    run.event_log_path = str(tmp_path / "events" / "delete-me.jsonl")

    report_file = Path(run.report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("report", encoding="utf-8")
    state_file = Path(run.state_log_path)
    state_file.write_text("{}", encoding="utf-8")
    event_file = Path(run.event_log_path)
    event_file.parent.mkdir(parents=True, exist_ok=True)
    event_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(web_runner._service, "_runs", {run.run_id: run})
    monkeypatch.setattr(web_runner._service, "_runs_index_path", tmp_path / "runs.json")

    deleted = web_runner.delete_run(run.run_id)

    assert deleted is run
    assert web_runner.get_run(run.run_id) is None
    assert not report_file.exists()
    assert not state_file.exists()
    assert not event_file.exists()


@pytest.mark.unit
def test_delete_run_rejects_active_run(monkeypatch):
    run = _make_run_state(status="running")
    monkeypatch.setattr(web_runner._service, "_runs", {run.run_id: run})

    deleted = web_runner.delete_run(run.run_id)

    assert deleted is None
    assert web_runner.get_run(run.run_id) is run


@pytest.mark.unit
def test_build_terminal_event_returns_cancelled_payload():
    run = _make_run_state(status="cancelled")
    run.completed_at = "2026-01-15T02:00:00"

    event = web_runner.build_terminal_event(run)

    assert event == {
        "event": "cancelled",
        "data": {"message": "Analysis cancelled"},
    }


@pytest.mark.unit
def test_persist_and_reload_runs_round_trip(monkeypatch, tmp_path):
    run = _make_run_state(run_id="persisted")
    run.status = "completed"
    run.signal = "Buy"
    run.report_sections["market_report"] = "Market section"
    run.final_report = "Full report"
    run.report_path = str(tmp_path / "complete_report.md")
    run.state_log_path = str(tmp_path / "full_state.json")

    index_path = tmp_path / "runs.json"
    monkeypatch.setattr(web_runner._service, "_runs_index_path", index_path)
    monkeypatch.setattr(web_runner._service, "_runs", {run.run_id: run})

    web_runner.save_runs_index()

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload[0]["run_id"] == "persisted"

    monkeypatch.setattr(web_runner._service, "_runs", {})
    web_runner.load_runs_index()

    restored = web_runner.get_run("persisted")
    assert restored is not None
    assert restored.status == "completed"
    assert restored.signal == "Buy"
    assert restored.report_sections["market_report"] == "Market section"
    assert restored.final_report == "Full report"


@pytest.mark.unit
def test_load_runs_index_preserves_incomplete_status(monkeypatch, tmp_path):
    index_path = tmp_path / "runs.json"
    payload = [
        {
            "run_id": "stale",
            "ticker": "AAPL",
            "date": "2026-01-15",
            "asset_type": "stock",
            "config": DEFAULT_CONFIG.copy(),
            "selected_analysts": ["market"],
            "status": "running",
            "agents": {},
            "report_sections": {},
            "current_report": None,
            "final_report": None,
            "signal": None,
            "error": None,
            "report_path": None,
            "state_log_path": None,
            "created_at": "2026-01-15T00:00:00",
            "started_at": "2026-01-15T00:01:00",
            "completed_at": None,
        }
    ]
    index_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(web_runner._service, "_runs_index_path", index_path)
    monkeypatch.setattr(web_runner._service, "_runs", {})

    web_runner.load_runs_index()

    restored = web_runner.get_run("stale")
    assert restored is not None
    assert restored.status == "running"
    assert restored.error is None


@pytest.mark.unit
def test_resume_incomplete_runs_requeues_pending_work(monkeypatch):
    queued_run = _make_run_state(run_id="queued", status="queued")
    running_run = _make_run_state(run_id="running", status="running")
    cancelling_run = _make_run_state(run_id="cancelling", status="cancelling")
    completed_run = _make_run_state(run_id="completed", status="completed")
    enqueued: list[str] = []

    monkeypatch.setattr(
        web_runner._service,
        "_runs",
        {
            queued_run.run_id: queued_run,
            running_run.run_id: running_run,
            cancelling_run.run_id: cancelling_run,
            completed_run.run_id: completed_run,
        },
    )
    monkeypatch.setattr(web_runner._service, "_enqueue_run", lambda run_id: enqueued.append(run_id))
    monkeypatch.setattr(web_runner._service, "save_runs_index", lambda: None)

    web_runner.resume_incomplete_runs()

    assert queued_run.status == "queued"
    assert running_run.status == "queued"
    assert cancelling_run.status == "cancelled"
    assert completed_run.status == "completed"
    assert enqueued == ["queued", "running"]
