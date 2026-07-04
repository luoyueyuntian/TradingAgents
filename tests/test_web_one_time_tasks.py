"""Tests for one-time analysis task schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from web.schemas import (
    AutomationAnalysisConfig,
    ManualStockSelection,
    OneTimeTask,
    OneTimeTaskCreate,
    OneTimeTaskPage,
    OneTimeTaskSelectionSnapshot,
    OneTimeTaskUpdate,
    StockGroup,
    StockGroupCreate,
    StockGroupUpdate,
)


def test_stock_group_create_normalizes_name_and_tickers():
    group = StockGroupCreate(name="  AI Leaders  ", tickers=[" nvda ", "msft", "NVDA", "  ", "aapl"])

    assert group.name == "AI Leaders"
    assert group.tickers == ["NVDA", "MSFT", "AAPL"]


def test_stock_group_update_normalizes_name_and_tickers():
    group = StockGroupUpdate(name="  Core Basket  ", tickers=[" nvda ", "MSFT", "nvda", "aapl "])

    assert group.name == "Core Basket"
    assert group.tickers == ["NVDA", "MSFT", "AAPL"]


def test_stock_group_saved_model_rejects_empty_ticker_list():
    with pytest.raises(ValidationError, match="tickers.*must not be empty"):
        StockGroup(id="group-1", name="AI Leaders", tickers=[], created_at="2026-07-01T12:00:00", updated_at="2026-07-01T12:00:00")


def test_stock_group_create_rejects_blank_name():
    with pytest.raises(ValidationError, match="name.*must not be blank"):
        StockGroupCreate(name="   ", tickers=["NVDA"])


def test_manual_stock_selection_accepts_minimal_shape():
    stock = ManualStockSelection(market="  CN_A ", symbol=" 600519.sh ")

    assert stock.market == "cn_a"
    assert stock.symbol == "600519.SH"
    assert stock.name is None
    assert stock.exchange is None


def test_manual_stock_selection_normalizes_optional_metadata():
    stock = ManualStockSelection(
        market="  CN_A ",
        symbol=" 600519.sh ",
        name=" 贵州茅台 ",
        exchange=" sse ",
    )

    assert stock.market == "cn_a"
    assert stock.symbol == "600519.SH"
    assert stock.name == "贵州茅台"
    assert stock.exchange == "sse"


def test_manual_stock_selection_rejects_unknown_market():
    with pytest.raises(ValidationError, match="market.*cn_a.*hk.*us"):
        ManualStockSelection(market="crypto", symbol="BTC-USD")


def test_one_time_task_shared_models_round_trip():
    snapshot = OneTimeTaskSelectionSnapshot(
        manual_stocks=[ManualStockSelection(market="cn_a", symbol="600519.sh", name="贵州茅台", exchange="SSE")],
        group_snapshots=[{"id": "group-1", "name": "AI Leaders", "tickers": ["NVDA", "MSFT"]}],
        include_watchlist=True,
        watchlist_snapshot=["AAPL", "0700.hk", "AAPL"],
        resolved_tickers=["600519.SH", "NVDA", "MSFT", "AAPL", "0700.HK"],
    )
    task = OneTimeTask(
        id="task-1",
        name="  Friday Basket  ",
        status="scheduled",
        scheduled_for="2026-07-10 21:30",
        analysis_date="2026-07-10",
        selection_snapshot=snapshot,
        analysis_config=AutomationAnalysisConfig(
            analysts=["market", "news"],
            llm_provider="openai",
            research_depth=3,
            output_language="Chinese",
        ),
        created_at="2026-07-01T12:00:00",
        updated_at="2026-07-01T12:00:00",
        triggered_at=None,
        completed_at=None,
        last_error=None,
        last_queued_count=0,
        run_ids=["run-1", "run-2"],
    )
    page = OneTimeTaskPage(items=[task], page=1, page_size=20, total_count=1)

    assert task.name == "Friday Basket"
    assert task.status == "scheduled"
    assert task.selection_snapshot.resolved_tickers == ["600519.SH", "NVDA", "MSFT", "AAPL", "0700.HK"]
    assert page.items[0].id == "task-1"
    assert page.total_count == 1


def test_one_time_task_update_normalizes_selection_and_validates_dates():
    task = OneTimeTaskUpdate(
        name="  Friday Basket  ",
        scheduled_for="2026-07-10 21:30",
        analysis_date="2026-07-10",
        manual_stocks=[
            {"market": "cn_a", "symbol": " 600519.sh ", "name": "贵州茅台", "exchange": "SSE"},
            {"market": "hk", "symbol": "0700.hk", "name": "腾讯控股", "exchange": "HKEX"},
        ],
        group_ids=["group-1", "group-2", "group-1", "group-3", "group-2"],
        include_watchlist=True,
        analysis_config=AutomationAnalysisConfig(
            analysts=["market", "news"],
            llm_provider="openai",
            research_depth=3,
            output_language="Chinese",
        ),
    )

    assert task.name == "Friday Basket"
    assert task.scheduled_for == "2026-07-10 21:30"
    assert task.analysis_date == "2026-07-10"
    assert task.group_ids == ["group-1", "group-2", "group-3"]
    assert [stock.symbol for stock in task.manual_stocks] == ["600519.SH", "0700.HK"]
    assert [stock.market for stock in task.manual_stocks] == ["cn_a", "hk"]
    assert task.include_watchlist is True


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"scheduled_for": "2026-07-10"}, "scheduled_for must be in YYYY-MM-DD HH:MM format"),
        ({"analysis_date": "2026/07/10"}, "analysis_date must be in YYYY-MM-DD format"),
    ],
)
def test_one_time_task_create_rejects_invalid_date_formats(kwargs, message):
    base_kwargs = dict(
        name="Friday Basket",
        scheduled_for="2026-07-10 21:30",
        analysis_date="2026-07-10",
        manual_stocks=[],
        group_ids=[],
        analysis_config=AutomationAnalysisConfig(
            analysts=["market"],
            llm_provider="openai",
            research_depth=1,
            output_language="English",
        ),
    )
    base_kwargs.update(kwargs)

    with pytest.raises(ValidationError, match=message):
        OneTimeTaskCreate(**base_kwargs)
