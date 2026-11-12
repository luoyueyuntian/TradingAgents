"""Tests for the deterministic market-data verification snapshot (#830/#881)."""

from __future__ import annotations

import pandas as pd
import pytest

import tradingagents.dataflows.config as config_module
import tradingagents.dataflows.market_data_validator as validator
from tradingagents.dataflows.errors import NoMarketDataError
from tradingagents.dataflows.provenance import (
    get_data_fetch_audit,
    reset_data_fetch_audit,
)


def _sample_ohlcv() -> pd.DataFrame:
    dates = pd.bdate_range("2026-04-01", "2026-05-20")
    closes = [100 + i for i in range(len(dates))]
    return pd.DataFrame({
        "Date": dates,
        "Open": [c - 0.5 for c in closes],
        "High": [c + 1.0 for c in closes],
        "Low": [c - 1.0 for c in closes],
        "Close": closes,
        "Volume": [1_000_000 + i for i in range(len(dates))],
    })


@pytest.mark.unit
class TestVerifiedSnapshot:
    def setup_method(self):
        reset_data_fetch_audit()

    def teardown_method(self):
        reset_data_fetch_audit()

    def test_excludes_future_rows(self, monkeypatch):
        data = pd.concat([
            _sample_ohlcv(),
            pd.DataFrame({"Date": [pd.Timestamp("2026-06-01")], "Open": [999.0],
                          "High": [999.0], "Low": [999.0], "Close": [999.0], "Volume": [999]}),
        ], ignore_index=True)
        monkeypatch.setattr(validator, "load_ohlcv", lambda s, d: data)

        snap = validator.build_verified_market_snapshot("COF", "2026-05-13")
        assert "Verified market data snapshot for COF" in snap
        assert "Requested analysis date: 2026-05-13" in snap
        assert "Latest trading row used: 2026-05-13" in snap
        assert "999.00" not in snap          # future row excluded
        assert "boll_lb" in snap             # indicators present

    def test_uses_previous_trading_day_when_date_is_weekend(self, monkeypatch):
        monkeypatch.setattr(validator, "load_ohlcv", lambda s, d: _sample_ohlcv())
        # 2026-05-16 is a Saturday; latest row should be Fri 2026-05-15
        snap = validator.build_verified_market_snapshot("COF", "2026-05-16")
        assert "Latest trading row used: 2026-05-15" in snap
        assert "Recent verified closes" in snap

    def test_raises_when_no_rows_on_or_before_date(self, monkeypatch):
        monkeypatch.setattr(validator, "load_ohlcv", lambda s, d: _sample_ohlcv())
        with pytest.raises(NoMarketDataError):
            validator.build_verified_market_snapshot("COF", "2020-01-01")

    def test_raises_on_empty_data(self, monkeypatch):
        monkeypatch.setattr(validator, "load_ohlcv", lambda s, d: pd.DataFrame())
        with pytest.raises(NoMarketDataError):
            validator.build_verified_market_snapshot("COF", "2026-05-13")

    def test_look_back_window_capped_at_30(self, monkeypatch):
        monkeypatch.setattr(validator, "load_ohlcv", lambda s, d: _sample_ohlcv())
        snap = validator.build_verified_market_snapshot("COF", "2026-05-20", look_back_days=999)
        # last-N closes table has at most 30 data rows
        close_rows = [ln for ln in snap.splitlines() if ln.startswith("| 2026-")]
        assert 0 < len(close_rows) <= 30

    def test_cn_a_snapshot_prefers_china_ohlcv_before_yfinance(self, monkeypatch):
        config_module.set_config({"market_profile": "cn_a"})

        def _unexpected_yfinance(*_args, **_kwargs):
            raise AssertionError("cn_a snapshot should not call the yfinance-only OHLCV path first")

        monkeypatch.setattr(validator, "load_ohlcv", _unexpected_yfinance)
        monkeypatch.setattr(
            validator, "load_ohlcv_china", lambda s, d: _sample_ohlcv(), raising=False
        )

        snap = validator.build_verified_market_snapshot("600036.SS", "2026-05-20")

        assert "Verified market data snapshot for 600036.SS" in snap

    def test_cn_a_snapshot_falls_back_to_yfinance_when_china_has_no_rows(self, monkeypatch):
        config_module.set_config({"market_profile": "cn_a"})

        def _no_china_rows(symbol, _curr_date):
            raise NoMarketDataError(symbol, "600036", "no China A-share rows through 2026-05-20")

        monkeypatch.setattr(validator, "load_ohlcv_china", _no_china_rows, raising=False)
        monkeypatch.setattr(validator, "load_ohlcv", lambda s, d: _sample_ohlcv())

        snap = validator.build_verified_market_snapshot("600036.SS", "2026-05-20")

        assert "Verified market data snapshot for 600036.SS" in snap

    def test_cn_a_snapshot_falls_back_to_tencent_before_yfinance(self, monkeypatch):
        config_module.set_config({"market_profile": "cn_a"})

        def _no_china_rows(symbol, _curr_date):
            raise NoMarketDataError(symbol, "600036", "no China A-share rows through 2026-05-20")

        def _tx_rows(symbol, _curr_date):
            return _sample_ohlcv()

        def _unexpected_yfinance(*_args, **_kwargs):
            raise AssertionError("cn_a snapshot should use Tencent fallback before yfinance")

        monkeypatch.setattr(validator, "load_ohlcv_china", _no_china_rows, raising=False)
        monkeypatch.setattr(validator, "load_ohlcv_china_tx", _tx_rows, raising=False)
        monkeypatch.setattr(validator, "load_ohlcv", _unexpected_yfinance)

        snap = validator.build_verified_market_snapshot("600036.SS", "2026-05-20")

        assert "Verified market data snapshot for 600036.SS" in snap
        audit = get_data_fetch_audit()
        assert audit[-1]["method"] == "get_verified_market_snapshot"
        assert audit[-1]["actual_source"] == "cn_stock_tx"
        assert audit[-1]["status"] == "fallback"
        assert audit[-1]["fallback_used"] is True
        assert audit[-1]["result_kind"] == "dataframe"
        assert "rows=" in audit[-1]["result_preview"]

    def test_cn_a_snapshot_preserves_china_failure_detail_when_fallback_also_fails(self, monkeypatch):
        config_module.set_config({"market_profile": "cn_a"})

        def _china_unavailable(symbol, _curr_date):
            raise NoMarketDataError(
                symbol,
                "600036",
                "China A-share history is currently unavailable (remote closed connection)",
            )

        def _yahoo_empty(symbol, _curr_date):
            raise NoMarketDataError(symbol, symbol, "Yahoo Finance returned no rows")

        monkeypatch.setattr(validator, "load_ohlcv_china", _china_unavailable, raising=False)
        monkeypatch.setattr(
            validator,
            "load_ohlcv_china_tx",
            lambda symbol, _curr_date: (_ for _ in ()).throw(
                NoMarketDataError(symbol, "sh600036", "Tencent history endpoint returned no rows")
            ),
            raising=False,
        )
        monkeypatch.setattr(validator, "load_ohlcv", _yahoo_empty)

        with pytest.raises(NoMarketDataError) as exc_info:
            validator.build_verified_market_snapshot("600036.SS", "2026-05-20")

        message = str(exc_info.value)
        assert "China A-share history is currently unavailable" in message
        assert "Tencent history endpoint returned no rows" in message
        assert "Yahoo Finance returned no rows" in message


@pytest.mark.unit
class TestTool:
    def test_tool_delegates_to_builder(self, monkeypatch):
        from tradingagents.agents.utils.market_data_validation_tools import (
            get_verified_market_snapshot,
        )
        monkeypatch.setattr(validator, "load_ohlcv", lambda s, d: _sample_ohlcv())
        out = get_verified_market_snapshot.invoke(
            {"symbol": "COF", "curr_date": "2026-05-20"}
        )
        assert "Verified market data snapshot for COF" in out
