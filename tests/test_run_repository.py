"""Tests for persisted run repository helpers."""

from __future__ import annotations

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.service.models import RunState
from tradingagents.service.run_repository import (
    delete_run_from_index,
    deserialize_run_state,
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
    run.company_name = "Apple Inc."
    run.queue_sequence = 7
    run.report_sections["market_report"] = "report"
    run.data_fetches = [
        {
            "key": "get_stock_data#1",
            "method": "get_stock_data",
            "status": "fallback",
            "actual_source": "cn_stock_tx",
            "warning": None,
            "result_preview": "sample csv preview",
        }
    ]
    run.data_warnings = [
        {
            "key": "get_fundamentals#1",
            "severity": "warning",
            "message": "Fundamentals data was unavailable.",
        }
    ]
    run.usage_summary = {
        "provider": "openai",
        "total_calls": 3,
        "prompt_tokens": 120,
        "completion_tokens": 45,
        "total_tokens": 165,
        "calls_by_model": {"gpt-5.5": 2, "gpt-5.4-mini": 1},
    }

    payload = serialize_run_state(run)
    restored = deserialize_run_state(payload, runs_root_dir=tmp_path)

    assert isinstance(payload["created_at"], int)
    assert restored.run_id == run.run_id
    assert restored.status == "completed"
    assert restored.signal == "Buy"
    assert restored.company_name == "Apple Inc."
    assert restored.queue_sequence == 7
    assert restored.report_sections["market_report"] == "report"
    assert restored.data_fetches[0]["actual_source"] == "cn_stock_tx"
    assert restored.data_fetches[0]["result_preview"] == "sample csv preview"
    assert restored.data_warnings[0]["message"] == "Fundamentals data was unavailable."
    assert restored.usage_summary["total_tokens"] == 165


def test_load_runs_from_index_preserves_incomplete_status(tmp_path):
    index_path = tmp_path / "runs.json"
    payload = [{
        "run_id": "run-1",
        "ticker": "AAPL",
        "date": "2026-01-15",
        "asset_type": "stock",
        "config": DEFAULT_CONFIG.copy(),
        "selected_analysts": ["market"],
        "run_root": str(tmp_path / "runs" / "run-1"),
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
        "created_at": 1_768_435_200_000,
        "started_at": 1_768_435_260_000,
        "completed_at": None,
    }]
    index_path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    runs = load_runs_from_index(index_path=index_path, runs_root_dir=tmp_path / "runs")

    assert runs["run-1"].status == "running"
    assert runs["run-1"].error is None


def test_save_runs_to_index_writes_ordered_payload(tmp_path):
    old_run = _make_run("old")
    old_run.created_at = 1_768_435_200_000
    new_run = _make_run("new")
    new_run.created_at = 1_768_438_800_000

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
