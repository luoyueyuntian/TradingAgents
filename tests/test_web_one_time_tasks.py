"""Tests for one-time analysis task schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from web.schemas import AutomationAnalysisConfig, ManualStockSelection, OneTimeTaskCreate, StockGroupCreate


def test_stock_group_create_normalizes_name_and_tickers():
    group = StockGroupCreate(name="  AI Leaders  ", tickers=[" nvda ", "msft", "NVDA", "  ", "aapl"])

    assert group.name == "AI Leaders"
    assert group.tickers == ["NVDA", "MSFT", "AAPL"]


def test_stock_group_create_rejects_blank_name():
    with pytest.raises(ValidationError, match="name.*must not be blank"):
        StockGroupCreate(name="   ", tickers=["NVDA"])


def test_manual_stock_selection_normalizes_market_and_symbol():
    stock = ManualStockSelection(market="  CN_A ", symbol=" 600519.sh ", name="贵州茅台", exchange="SSE")

    assert stock.market == "cn_a"
    assert stock.symbol == "600519.SH"


def test_manual_stock_selection_rejects_unknown_market():
    with pytest.raises(ValidationError, match="market.*cn_a.*hk.*us"):
        ManualStockSelection(market="crypto", symbol="BTC-USD", name="Bitcoin", exchange="CRYPTO")


def test_one_time_task_create_normalizes_selection_and_validates_dates():
    task = OneTimeTaskCreate(
        name="  Friday Basket  ",
        scheduled_for="2026-07-10 21:30",
        analysis_date="2026-07-10",
        manual_stocks=[
            {"market": "cn_a", "symbol": " 600519.sh ", "name": "贵州茅台", "exchange": "SSE"},
            {"market": "hk", "symbol": "0700.hk", "name": "腾讯控股", "exchange": "HKEX"},
        ],
        group_ids=["group-1", "group-2", "group-1", "group-3", "group-2"],
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
