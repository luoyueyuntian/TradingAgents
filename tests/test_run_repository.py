"""Tests for persisted run repository helpers."""

from __future__ import annotations

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.service.models import RunState
from tradingagents.service.run_repository import (
    deserialize_run_state,
    delete_run_from_index,
    index_lock_path,
    load_runs_from_index,
    save_runs_to_index,
    serialize_run_state,
    upsert_run_in_index,
)
from tradingagents.service.runtime_context import build_runtime_context


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


def test_serialize_and_deserialize_run_round_trip(tmp_path):
    run = _make_run("run-1")
    run.status = "completed"
    run.signal = "Buy"
    run.queue_sequence = 7
    run.report_sections["market_report"] = "report"

    payload = serialize_run_state(run)
    restored = deserialize_run_state(payload, runs_root_dir=tmp_path)

    assert restored.run_id == run.run_id
    assert restored.status == "completed"
    assert restored.signal == "Buy"
    assert restored.queue_sequence == 7
    assert restored.report_sections["market_report"] == "report"


def test_load_runs_from_index_preserves_incomplete_status(tmp_path):
    index_path = tmp_path / "runs.json"
    payload = [{
        "run_id": "run-1",
        "ticker": "AAPL",
        "date": "2026-01-15",
        "asset_type": "stock",
        "config": DEFAULT_CONFIG.copy(),
        "selected_analysts": ["market"],
        "run_root": str((tmp_path / "runs" / "run-1")),
        "status": "running",
        "agents": {},
        "report_sections": {},
        "current_report": None,
        "final_report": None,
        "signal": None,
        "error": None,
        "report_path": None,
        "state_log_path": None,
        "event_log_path": None,
        "created_at": "2026-01-15T00:00:00",
        "started_at": "2026-01-15T00:01:00",
        "completed_at": None,
    }]
    index_path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    runs = load_runs_from_index(index_path=index_path, runs_root_dir=tmp_path / "runs")

    assert runs["run-1"].status == "running"
    assert runs["run-1"].error is None


def test_save_runs_to_index_writes_ordered_payload(tmp_path):
    old_run = _make_run("old")
    old_run.created_at = "2026-01-15T00:00:00"
    new_run = _make_run("new")
    new_run.created_at = "2026-01-15T01:00:00"

    save_runs_to_index(
        [old_run, new_run],
        index_path=tmp_path / "runs.json",
    )

    payload = __import__("json").loads((tmp_path / "runs.json").read_text(encoding="utf-8"))
    assert [item["run_id"] for item in payload] == ["new", "old"]
    assert not index_lock_path(tmp_path / "runs.json").exists()


def test_upsert_run_in_index_preserves_other_runs(tmp_path):
    old_run = _make_run("old")
    new_run = _make_run("new")
    index_path = tmp_path / "runs.json"
    save_runs_to_index([old_run], index_path=index_path)

    upsert_run_in_index(new_run, index_path=index_path)

    payload = __import__("json").loads(index_path.read_text(encoding="utf-8"))
    assert sorted(item["run_id"] for item in payload) == ["new", "old"]
    assert not index_lock_path(index_path).exists()


def test_delete_run_from_index_removes_only_target(tmp_path):
    old_run = _make_run("old")
    new_run = _make_run("new")
    index_path = tmp_path / "runs.json"
    save_runs_to_index([old_run, new_run], index_path=index_path)

    delete_run_from_index("old", index_path=index_path)

    payload = __import__("json").loads(index_path.read_text(encoding="utf-8"))
    assert [item["run_id"] for item in payload] == ["new"]
    assert not index_lock_path(index_path).exists()
