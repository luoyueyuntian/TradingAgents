"""China macro adapter tests."""

from __future__ import annotations

import pandas as pd
import pytest
from tradingagents.dataflows.errors import NoMarketDataError, VendorNotConfiguredError


@pytest.mark.unit
def test_china_macro_alias_returns_markdown_table(monkeypatch):
    from tradingagents.dataflows import china_macro

    fake_df = pd.DataFrame(
        [
            {"日期": "2026-04-01", "今值": 2.3, "预测值": 2.2, "前值": 2.1},
            {"日期": "2026-05-01", "今值": 2.1, "预测值": 2.0, "前值": 2.3},
        ]
    )

    class FakeAK:
        @staticmethod
        def macro_china_cpi_yearly():
            return fake_df

    monkeypatch.setattr(china_macro, "_load_akshare", lambda: FakeAK)
    out = china_macro.get_china_macro_data("cpi", "2026-05-31", 90)

    assert "## China Macro: CPI" in out
    assert "| 日期 | 今值 | 预测值 | 前值 |" in out
    assert "2026-05-01" in out


@pytest.mark.unit
def test_china_macro_unknown_alias_returns_guidance():
    from tradingagents.dataflows.china_macro import get_china_macro_data

    out = get_china_macro_data("fed_funds_rate", "2026-05-31", 90)
    assert "China macro alias" in out
    assert "cpi" in out


@pytest.mark.unit
def test_china_macro_vendor_unavailable_is_explicit(monkeypatch):
    from tradingagents.dataflows import china_macro
    from tradingagents.dataflows.errors import VendorNotConfiguredError

    monkeypatch.setattr(
        china_macro,
        "_load_akshare",
        lambda: (_ for _ in ()).throw(ImportError("akshare missing")),
    )
    with pytest.raises(VendorNotConfiguredError, match="akshare missing"):
        china_macro.get_china_macro_data("cpi", "2026-05-31", 90)


@pytest.mark.unit
def test_china_macro_does_not_fall_back_to_stale_rows(monkeypatch):
    from tradingagents.dataflows import china_macro

    stale_df = pd.DataFrame(
        [
            {"日期": "2024-01-01", "今值": 1.0, "预测值": 1.1, "前值": 0.9},
            {"日期": "2024-02-01", "今值": 1.2, "预测值": 1.1, "前值": 1.0},
        ]
    )

    class FakeAK:
        @staticmethod
        def macro_china_cpi_yearly():
            return stale_df

    monkeypatch.setattr(china_macro, "_load_akshare", lambda: FakeAK)
    with pytest.raises(NoMarketDataError, match="latest available observation is 2024-02-01"):
        china_macro.get_china_macro_data("cpi", "2026-06-27", 120)
