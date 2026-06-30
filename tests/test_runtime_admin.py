"""Tests for runtime-maintenance helpers used by the web layer."""

from __future__ import annotations

from tradingagents.agents.utils.memory import TradingMemoryLog
from tradingagents.service.runtime_admin import (
    clear_runtime_checkpoints,
    clear_runtime_memory_logs,
    list_runtime_checkpoints,
    list_runtime_memory_entries,
)


def test_list_runtime_checkpoints_discovers_run_scoped_files(tmp_path):
    checkpoint_dir = tmp_path / "cache" / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "NVDA.db").write_text("db", encoding="utf-8")
    (checkpoint_dir / "AAPL.db").write_text("db", encoding="utf-8")

    items = list_runtime_checkpoints(state_root=tmp_path)

    assert items == [
        {
            "run_id": None,
            "ticker": "AAPL",
            "path": str(checkpoint_dir / "AAPL.db"),
            "size_bytes": 2,
        },
        {
            "run_id": None,
            "ticker": "NVDA",
            "path": str(checkpoint_dir / "NVDA.db"),
            "size_bytes": 2,
        },
    ]


def test_clear_runtime_checkpoints_supports_ticker_filter(tmp_path):
    checkpoint_dir = tmp_path / "cache" / "checkpoints"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "NVDA.db").write_text("db", encoding="utf-8")
    (checkpoint_dir / "AAPL.db").write_text("db", encoding="utf-8")

    deleted = clear_runtime_checkpoints(state_root=tmp_path, ticker="NVDA")

    assert deleted == 1
    assert not (checkpoint_dir / "NVDA.db").exists()
    assert (checkpoint_dir / "AAPL.db").exists()


def test_list_runtime_memory_entries_parses_shared_tenant_log(tmp_path):
    log_path = tmp_path / "memory" / "trading_memory.md"
    log = TradingMemoryLog({"memory_log_path": str(log_path)})
    log.store_decision("NVDA", "2026-01-10", "Rating: Buy\nBuild a position.")
    log.store_decision("AAPL", "2026-01-11", "Rating: Hold\nWait.")
    log.update_with_outcome(
        "AAPL",
        "2026-01-11",
        raw_return=0.12,
        alpha_return=0.03,
        holding_days=5,
        reflection="Patience helped.",
    )

    items = list_runtime_memory_entries(state_root=tmp_path)

    assert items == [
        {
            "run_id": None,
            "date": "2026-01-11",
            "ticker": "AAPL",
            "rating": "Hold",
            "pending": False,
            "raw": "+12.0%",
            "alpha": "+3.0%",
            "holding": "5d",
            "decision": "Rating: Hold\nWait.",
            "reflection": "Patience helped.",
        },
        {
            "run_id": None,
            "date": "2026-01-10",
            "ticker": "NVDA",
            "rating": "Buy",
            "pending": True,
            "raw": None,
            "alpha": None,
            "holding": None,
            "decision": "Rating: Buy\nBuild a position.",
            "reflection": "",
        },
    ]


def test_clear_runtime_memory_logs_deletes_shared_tenant_log(tmp_path):
    log_path = tmp_path / "memory" / "trading_memory.md"
    TradingMemoryLog({"memory_log_path": str(log_path)}).store_decision(
        "NVDA",
        "2026-01-10",
        "Rating: Buy\nBuild a position.",
    )

    deleted = clear_runtime_memory_logs(state_root=tmp_path)

    assert deleted == 1
    assert not log_path.exists()
