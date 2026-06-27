"""China forward-looking market-signal adapter tests."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.mark.unit
def test_northbound_signal_formats_summary(monkeypatch):
    from tradingagents.dataflows import china_market_signals

    hsgt = pd.DataFrame(
        [
            {
                "交易日": "2026-06-26",
                "类型": "沪港通",
                "板块": "沪股通",
                "资金方向": "北向",
                "成交净买额": 123.45,
                "资金净流入": 200.0,
                "相关指数": "上证指数",
                "指数涨跌幅": -1.2,
            }
        ]
    )

    class FakeAK:
        @staticmethod
        def stock_hsgt_fund_flow_summary_em():
            return hsgt

    monkeypatch.setattr(china_market_signals, "_load_akshare", lambda: FakeAK)
    out = china_market_signals.get_china_market_signals("northbound flow", 3)

    assert "## China Forward-Looking Signals" in out
    assert "北向" in out
    assert "123.45" in out


@pytest.mark.unit
def test_margin_signal_formats_summary(monkeypatch):
    from tradingagents.dataflows import china_market_signals

    margin = pd.DataFrame(
        [
            {"信用交易日期": "2026-06-26", "融资余额": 1000.0, "融券余额": 80.0},
            {"信用交易日期": "2026-06-25", "融资余额": 980.0, "融券余额": 70.0},
        ]
    )

    class FakeAK:
        @staticmethod
        def stock_margin_sse(start_date: str, end_date: str):
            return margin

    monkeypatch.setattr(china_market_signals, "_load_akshare", lambda: FakeAK)
    out = china_market_signals.get_china_market_signals("margin financing", 2)

    assert "融资余额" in out
    assert "1000.0" in out


@pytest.mark.unit
def test_unknown_signal_topic_returns_guidance():
    from tradingagents.dataflows.china_market_signals import get_china_market_signals

    out = get_china_market_signals("fed rate cut", 3)
    assert "Supported China signal topics" in out
    assert "northbound" in out
