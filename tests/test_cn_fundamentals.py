"""China A-share fundamentals adapter tests."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.mark.unit
def test_get_fundamentals_china_formats_key_value_lines(monkeypatch):
    from tradingagents.dataflows import cn_fundamentals

    indicator_df = pd.DataFrame(
        [
            {
                "REPORT_DATE": "2026-03-31",
                "TOTAL_OPERATE_INCOME": 1000000000,
                "PARENT_NETPROFIT": 200000000,
                "ROE_WEIGHTED": 18.2,
            },
        ]
    )
    info_df = pd.DataFrame([["股票简称", "贵州茅台"], ["行业", "白酒"]], columns=["item", "value"])

    class FakeAK:
        @staticmethod
        def stock_financial_abstract_ths(symbol, indicator):
            assert symbol == "600519"
            assert indicator == "按报告期"
            return indicator_df

        @staticmethod
        def stock_individual_info_em(symbol):
            assert symbol == "600519"
            return info_df

    monkeypatch.setattr(cn_fundamentals, "_load_akshare", lambda: FakeAK)
    out = cn_fundamentals.get_fundamentals_china("600519.SS", "2026-06-27")

    assert "# Company Fundamentals for 600519.SS" in out
    assert "Name: 贵州茅台" in out
    assert "Industry: 白酒" in out
    assert "Revenue (TTM): 1000000000" in out


@pytest.mark.unit
def test_get_fundamentals_china_maps_richer_fields(monkeypatch):
    from tradingagents.dataflows import cn_fundamentals

    indicator_df = pd.DataFrame(
        [
            {
                "REPORT_DATE": "2026-03-31",
                "TOTAL_OPERATE_INCOME": 1000000000,
                "PARENT_NETPROFIT": 200000000,
                "ROE_WEIGHTED": 18.2,
                "GROSS_PROFIT_RATE": 91.5,
                "BASIC_EPS": 15.82,
                "TOTAL_ASSETS": 320000000000,
                "TOTAL_LIABILITIES": 98000000000,
                "NET_CASH_FLOWS_OPER_ACT": 27500000000,
            },
        ]
    )
    info_df = pd.DataFrame(
        [["股票简称", "贵州茅台"], ["行业", "白酒"], ["总市值", 1850000000000]],
        columns=["item", "value"],
    )

    class FakeAK:
        @staticmethod
        def stock_financial_abstract_ths(symbol, indicator):
            return indicator_df

        @staticmethod
        def stock_individual_info_em(symbol):
            return info_df

    monkeypatch.setattr(cn_fundamentals, "_load_akshare", lambda: FakeAK)
    out = cn_fundamentals.get_fundamentals_china("600519.SS", "2026-06-27")

    assert "Market Cap: 1850000000000" in out
    assert "Gross Margin: 91.5" in out
    assert "EPS (Basic): 15.82" in out
    assert "Total Assets: 320000000000" in out
    assert "Total Liabilities: 98000000000" in out
    assert "Operating Cash Flow: 27500000000" in out
    assert "Asset Liability Ratio: 30.62" in out


@pytest.mark.unit
def test_get_fundamentals_china_maps_efficiency_and_per_share_fields(monkeypatch):
    from tradingagents.dataflows import cn_fundamentals

    indicator_df = pd.DataFrame(
        [
            {
                "REPORT_DATE": "2026-03-31",
                "ROA": 9.7,
                "CURRENT_RATIO": 1.56,
                "BPS": 178.43,
                "OCFPS": 24.88,
            },
        ]
    )
    info_df = pd.DataFrame([["股票简称", "贵州茅台"], ["行业", "白酒"]], columns=["item", "value"])

    class FakeAK:
        @staticmethod
        def stock_financial_abstract_ths(symbol, indicator):
            return indicator_df

        @staticmethod
        def stock_individual_info_em(symbol):
            return info_df

    monkeypatch.setattr(cn_fundamentals, "_load_akshare", lambda: FakeAK)
    out = cn_fundamentals.get_fundamentals_china("600519.SS", "2026-06-27")

    assert "Return on Assets: 9.7" in out
    assert "Current Ratio: 1.56" in out
    assert "Book Value: 178.43" in out
    assert "Operating Cash Flow Per Share: 24.88" in out


@pytest.mark.unit
def test_get_balance_sheet_china_formats_csv(monkeypatch):
    from tradingagents.dataflows import cn_fundamentals

    fake_df = pd.DataFrame(
        [
            {"REPORT_DATE": "2025-12-31", "TOTAL_ASSETS": 10, "TOTAL_LIABILITIES": 4},
            {"REPORT_DATE": "2026-03-31", "TOTAL_ASSETS": 11, "TOTAL_LIABILITIES": 4.2},
        ]
    )

    class FakeAK:
        @staticmethod
        def stock_balance_sheet_by_report_em(symbol):
            assert symbol == "SH600519"
            return fake_df

    monkeypatch.setattr(cn_fundamentals, "_load_akshare", lambda: FakeAK)
    out = cn_fundamentals.get_balance_sheet_china("600519.SS", "quarterly", "2026-06-27")

    assert "# Balance Sheet data for 600519.SS (quarterly)" in out
    assert "2026-03-31" in out


@pytest.mark.unit
def test_get_fundamentals_china_raises_when_no_usable_fields(monkeypatch):
    from tradingagents.dataflows import cn_fundamentals
    from tradingagents.dataflows.errors import NoMarketDataError

    class FakeAK:
        @staticmethod
        def stock_financial_abstract_ths(symbol, indicator):
            return pd.DataFrame()

        @staticmethod
        def stock_individual_info_em(symbol):
            return pd.DataFrame(columns=["item", "value"])

    monkeypatch.setattr(cn_fundamentals, "_load_akshare", lambda: FakeAK)
    with pytest.raises(NoMarketDataError, match="no fundamental fields returned"):
        cn_fundamentals.get_fundamentals_china("000001.SZ", "2026-06-27")
