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
    out = cn_fundamentals.get_fundamentals_china("600519.SS")

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
    out = cn_fundamentals.get_fundamentals_china("600519.SS")

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
    out = cn_fundamentals.get_fundamentals_china("600519.SS")

    assert "Return on Assets: 9.7" in out
    assert "Current Ratio: 1.56" in out
    assert "Book Value: 178.43" in out
    assert "Operating Cash Flow Per Share: 24.88" in out


@pytest.mark.unit
def test_get_fundamentals_china_accepts_common_alias_columns(monkeypatch):
    from tradingagents.dataflows import cn_fundamentals

    indicator_df = pd.DataFrame(
        [
            {
                "REPORT_DATE": "2026-03-31",
                "营业总收入": 1000000000,
                "归母净利润": 200000000,
                "净资产收益率": 18.2,
                "总资产收益率": 9.7,
                "毛利率": 91.5,
                "流动比率": 1.56,
                "基本每股收益": 15.82,
                "每股净资产": 178.43,
                "每股经营现金流": 24.88,
                "总资产": 320000000000,
                "总负债": 98000000000,
                "经营活动产生的现金流量净额": 27500000000,
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
    out = cn_fundamentals.get_fundamentals_china("600519.SS")

    assert "Revenue (TTM): 1000000000" in out
    assert "Net Income: 200000000" in out
    assert "Return on Equity: 18.2" in out
    assert "Return on Assets: 9.7" in out
    assert "Gross Margin: 91.5" in out
    assert "Current Ratio: 1.56" in out
    assert "EPS (Basic): 15.82" in out
    assert "Book Value: 178.43" in out
    assert "Operating Cash Flow Per Share: 24.88" in out
    assert "Total Assets: 320000000000" in out
    assert "Total Liabilities: 98000000000" in out
    assert "Operating Cash Flow: 27500000000" in out
    assert "Asset Liability Ratio: 30.62" in out


@pytest.mark.unit
def test_get_balance_sheet_china_formats_csv(monkeypatch):
    from tradingagents.dataflows import cn_fundamentals

    fake_df = pd.DataFrame(
        [
            {"NOTICE_DATE": "2026-03-01", "REPORT_DATE": "2025-12-31", "TOTAL_ASSETS": 10, "TOTAL_LIABILITIES": 4},
            {"NOTICE_DATE": "2026-04-30", "REPORT_DATE": "2026-03-31", "TOTAL_ASSETS": 11, "TOTAL_LIABILITIES": 4.2},
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
        cn_fundamentals.get_fundamentals_china("000001.SZ")


def test_historical_overview_never_fetches_live_snapshot(monkeypatch):
    from tradingagents.dataflows import cn_fundamentals as vendor
    from tradingagents.dataflows.errors import NoMarketDataError
    monkeypatch.setattr(vendor, '_load_akshare', lambda: pytest.fail('live snapshot fetched'))
    with pytest.raises(NoMarketDataError, match='Historical fundamentals'):
        vendor.get_fundamentals_china('600519.SS', '2000-01-01')


def test_statement_cutoff_uses_publication_date():
    from tradingagents.dataflows.cn_fundamentals import _filter_statement_rows
    from tradingagents.dataflows.errors import NoMarketDataError
    frame = pd.DataFrame({'REPORT_DATE': ['2026-03-31'], 'NOTICE_DATE': ['2026-04-30']})
    assert _filter_statement_rows(frame, '2026-04-01').empty
    assert len(_filter_statement_rows(frame, '2026-04-30')) == 1
    with pytest.raises(NoMarketDataError, match='Publication dates'):
        _filter_statement_rows(frame.drop(columns='NOTICE_DATE'), '2026-04-01')
