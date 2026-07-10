"""China A-share stock adapter tests."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.mark.unit
def test_split_cn_symbol_for_hist_vendor():
    from tradingagents.dataflows.china_equity_utils import split_cn_a_symbol

    assert split_cn_a_symbol("600519.SS") == ("600519", "SH")
    assert split_cn_a_symbol("000001.SZ") == ("000001", "SZ")


@pytest.mark.unit
def test_get_stock_data_china_formats_csv(monkeypatch):
    from tradingagents.dataflows import cn_stock

    fake_df = pd.DataFrame(
        [
            {"日期": "2026-06-25", "开盘": 1450.0, "收盘": 1462.0, "最高": 1465.0, "最低": 1448.0, "成交量": 123456},
            {"日期": "2026-06-26", "开盘": 1462.0, "收盘": 1470.0, "最高": 1472.0, "最低": 1458.0, "成交量": 120000},
        ]
    )

    class FakeAK:
        @staticmethod
        def stock_zh_a_hist(symbol, period, start_date, end_date, adjust):
            assert symbol == "600519"
            assert period == "daily"
            return fake_df

    monkeypatch.setattr(cn_stock, "_load_akshare", lambda: FakeAK)
    out = cn_stock.get_stock_data_china("600519.SS", "2026-06-25", "2026-06-26")

    assert "# Stock data for 600519.SS from 2026-06-25 to 2026-06-26" in out
    assert "2026-06-26" in out
    assert "Date,Open,Close,High,Low,Volume" in out


@pytest.mark.unit
def test_get_stock_data_china_rejects_stale_rows(monkeypatch):
    from tradingagents.dataflows import cn_stock
    from tradingagents.dataflows.errors import NoMarketDataError

    stale_df = pd.DataFrame(
        [{"日期": "2025-01-02", "开盘": 10, "收盘": 11, "最高": 11, "最低": 9, "成交量": 1}]
    )

    class FakeAK:
        @staticmethod
        def stock_zh_a_hist(symbol, period, start_date, end_date, adjust):
            return stale_df

    monkeypatch.setattr(cn_stock, "_load_akshare", lambda: FakeAK)
    with pytest.raises(NoMarketDataError, match="stale"):
        cn_stock.get_stock_data_china("000001.SZ", "2026-06-20", "2026-06-27")


@pytest.mark.unit
def test_get_stock_data_china_retries_transient_vendor_errors(monkeypatch):
    from tradingagents.dataflows import cn_stock

    fake_df = pd.DataFrame(
        [{"日期": "2026-06-26", "开盘": 1462.0, "收盘": 1470.0, "最高": 1472.0, "最低": 1458.0, "成交量": 120000}]
    )
    calls = {"count": 0}

    class FakeAK:
        @staticmethod
        def stock_zh_a_hist(symbol, period, start_date, end_date, adjust):
            calls["count"] += 1
            if calls["count"] < 3:
                raise ConnectionError("remote closed connection")
            return fake_df

    monkeypatch.setattr(cn_stock, "_load_akshare", lambda: FakeAK)
    monkeypatch.setattr(cn_stock.time, "sleep", lambda *_args, **_kwargs: None)

    out = cn_stock.get_stock_data_china("600519.SS", "2026-06-26", "2026-06-26")

    assert calls["count"] == 3
    assert "2026-06-26" in out


@pytest.mark.unit
def test_cn_indicator_window_uses_cn_ohlcv(monkeypatch):
    from tradingagents.dataflows import cn_stock

    fake_df = pd.DataFrame(
        [
            {"Date": "2026-06-25", "Open": 10.0, "High": 11.0, "Low": 9.0, "Close": 10.5, "Volume": 1000},
            {"Date": "2026-06-26", "Open": 10.5, "High": 11.2, "Low": 10.1, "Close": 11.0, "Volume": 1200},
        ]
    )

    monkeypatch.setattr(
        cn_stock,
        "load_ohlcv_china",
        lambda symbol, curr_date: fake_df.assign(Date=pd.to_datetime(fake_df["Date"])),
    )
    out = cn_stock.get_stock_stats_indicators_window_china("000001.SZ", "rsi", "2026-06-26", 1)

    assert "## rsi values from 2026-06-25 to 2026-06-26" in out
    assert "2026-06-26:" in out
