"""Tests for the optional SQLite-backed web state backend."""

from __future__ import annotations

from pathlib import Path

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.service.event_publisher import append_event_record, load_event_history
from tradingagents.service.models import RunState
from tradingagents.service.run_claims import acquire_run_claim, claim_path, release_run_claim
from tradingagents.service.run_repository import (
    delete_run_from_index,
    load_runs_from_index,
    upsert_run_in_index,
)
from tradingagents.service.runtime_context import build_runtime_context
from tradingagents.service.worker_status import read_worker_status, write_worker_status


def _make_run(run_id: str = "run-1") -> RunState:
    return RunState(
        run_id=run_id,
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=build_runtime_context(run_id),
    )


def test_sqlite_backend_round_trip_for_run_repository(monkeypatch, tmp_path):
    db_path = tmp_path / "web-state.db"
    index_path = tmp_path / "ignored.json"
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("TRADINGAGENTS_WEB_SQLITE_PATH", str(db_path))

    first = _make_run("first")
    second = _make_run("second")

    upsert_run_in_index(first, index_path=index_path)
    upsert_run_in_index(second, index_path=index_path)
    runs = load_runs_from_index(index_path=index_path, runs_root_dir=tmp_path / "runs")
    assert sorted(runs) == ["first", "second"]
    assert db_path.exists()
    assert not index_path.exists()

    delete_run_from_index("first", index_path=index_path)
    runs = load_runs_from_index(index_path=index_path, runs_root_dir=tmp_path / "runs")
    assert sorted(runs) == ["second"]


def test_sqlite_backend_round_trip_for_event_history(monkeypatch, tmp_path):
    db_path = tmp_path / "web-state.db"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("TRADINGAGENTS_WEB_SQLITE_PATH", str(db_path))

    append_event_record("run-1", {"event": "progress", "data": {"message": "hello"}})
    _, history = load_event_history("run-1")

    assert len(history) == 1
    assert history[0]["event"] == "progress"
    assert history[0]["data"]["message"] == "hello"
    assert db_path.exists()
    assert not (tmp_path / "run-1.jsonl").exists()


def test_sqlite_backend_round_trip_for_worker_status(monkeypatch, tmp_path):
    db_path = tmp_path / "web-state.db"
    path = tmp_path / "ignored.json"
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("TRADINGAGENTS_WEB_SQLITE_PATH", str(db_path))

    write_worker_status(path=path, worker_mode="external_worker")
    status = read_worker_status(path=path, stale_after_seconds=30)

    assert status["worker_running"] is True
    assert status["worker_mode"] == "external_worker"
    assert db_path.exists()
    assert not path.exists()


def test_sqlite_backend_round_trip_for_run_claims(monkeypatch, tmp_path):
    db_path = tmp_path / "web-state.db"
    claims_dir = tmp_path / "claims"
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_BACKEND", "sqlite")
    monkeypatch.setenv("TRADINGAGENTS_WEB_SQLITE_PATH", str(db_path))

    claim = acquire_run_claim("run-1", claims_dir=claims_dir)
    assert claim is not None
    second = acquire_run_claim("run-1", claims_dir=claims_dir)
    assert second is None

    release_run_claim(claim)
    third = acquire_run_claim("run-1", claims_dir=claims_dir)
    assert third is not None
    assert claim_path("run-1", claims_dir=claims_dir).name == "run-1.lock"
    assert db_path.exists()
    assert not claim_path("run-1", claims_dir=claims_dir).exists()
