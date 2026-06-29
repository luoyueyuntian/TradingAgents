"""Tests for selecting and describing the active web state backend."""

from __future__ import annotations

from tradingagents.service import web_state as web_state_module
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.service.models import RunState
from tradingagents.service.runtime_context import build_runtime_context


def test_get_state_backend_adapter_defaults_to_file(monkeypatch, tmp_path):
    monkeypatch.delenv("TRADINGAGENTS_WEB_STATE_BACKEND", raising=False)
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)

    from tradingagents.service.state_backend import get_state_backend_adapter

    backend = get_state_backend_adapter()

    assert backend.kind == "file"
    assert backend.location == tmp_path / ".tradingagents" / "web"


def test_get_state_backend_adapter_uses_sqlite_path(monkeypatch, tmp_path):
    db_path = tmp_path / "state.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("TRADINGAGENTS_WEB_SQLITE_PATH", str(db_path))

    from tradingagents.service.state_backend import get_state_backend_adapter

    backend = get_state_backend_adapter()

    assert backend.kind == "sqlite"
    assert backend.location == db_path


def test_file_backend_adapter_round_trip_for_runs(monkeypatch, tmp_path):
    monkeypatch.delenv("TRADINGAGENTS_WEB_STATE_BACKEND", raising=False)
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)

    from tradingagents.service.state_backend import get_state_backend_adapter

    backend = get_state_backend_adapter()
    run = RunState(
        run_id="run-1",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context("run-1"),
    )

    backend.upsert_run(run)
    runs = backend.load_runs(runs_root_dir=tmp_path / ".tradingagents" / "web" / "runs")

    assert sorted(runs) == ["run-1"]


def test_sqlite_backend_adapter_round_trip_for_events(monkeypatch, tmp_path):
    db_path = tmp_path / "state.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("TRADINGAGENTS_WEB_SQLITE_PATH", str(db_path))

    from tradingagents.service.state_backend import get_state_backend_adapter

    backend = get_state_backend_adapter()
    backend.append_event("run-1", {"event": "progress", "data": {"message": "hello"}})
    _, history = backend.load_events("run-1")

    assert len(history) == 1
    assert history[0]["data"]["message"] == "hello"
