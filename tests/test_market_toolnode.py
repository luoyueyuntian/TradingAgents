"""The market analyst is bound (and prompt-instructed) to call
get_verified_market_snapshot; if the executor ToolNode doesn't register it, the
call fails and the model reports the tool "unavailable" and skips verification.

Regression guard for that wiring gap (snapshot bound to the LLM but missing from
the market ToolNode).
"""
import pytest


@pytest.mark.unit
def test_market_toolnode_can_execute_verified_snapshot():
    # The executor registers the same tools offered to the analyst model.
    from langgraph.prebuilt import ToolNode

    from tradingagents.agents.analysts.market_analyst import TOOLS
    market_tools = set(ToolNode(list(TOOLS)).tools_by_name)
    assert "get_verified_market_snapshot" in market_tools, (
        "get_verified_market_snapshot is bound to the market analyst but not "
        "registered in the market ToolNode, so the model's call fails."
    )
    # the other core market tools must remain too
    assert {"get_stock_data", "get_indicators"} <= market_tools


@pytest.mark.unit
@pytest.mark.parametrize("vendor", ["cn_stock", "cn_stock_em", "cn_stock_tx"])
def test_canonical_snapshot_uses_china_loader_and_records_audit(monkeypatch, vendor):
    import pandas as pd

    from tradingagents.agents.tools import get_verified_market_snapshot
    from tradingagents.dataflows import market_data_validator as validator
    from tradingagents.dataflows.config import run_config
    from tradingagents.dataflows.provenance import get_data_fetch_audit, reset_data_fetch_audit

    calls = []

    def load(symbol, date):
        calls.append((symbol, date))
        return pd.DataFrame({
            "Date": pd.to_datetime(["2026-01-08", "2026-01-09", "2026-01-12"]),
            "Open": [10.0, 11.0, 999.0], "High": [11.0, 12.0, 999.0],
            "Low": [9.0, 10.0, 999.0], "Close": [10.5, 11.5, 999.0],
            "Volume": [1000, 1200, 1],
        })

    loader = {"cn_stock": "load_ohlcv_china", "cn_stock_em": "load_ohlcv_china_em",
              "cn_stock_tx": "load_ohlcv_china_tx"}[vendor]
    monkeypatch.setattr(validator, loader, load)
    reset_data_fetch_audit()
    try:
        with run_config({"market_profile": "cn_a", "data_vendors": {"core_stock_apis": vendor}}):
            snapshot = get_verified_market_snapshot.func(
                "600519.SS", "2026-01-12", trade_date="2026-01-09",
            )
        assert calls == [("600519.SS", "2026-01-09")]
        assert "Latest trading row used: 2026-01-09" in snapshot
        assert "999" not in snapshot
        audit = get_data_fetch_audit()
        assert any(item["method"] == "get_verified_market_snapshot"
                   and item["actual_source"] == vendor for item in audit)
    finally:
        reset_data_fetch_audit()
