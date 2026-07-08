"""China A-share OHLCV and indicator adapters."""

from __future__ import annotations

from datetime import datetime
from importlib import import_module

import pandas as pd
from dateutil.relativedelta import relativedelta
from stockstats import wrap

from .china_equity_utils import normalize_cn_hist_frame, split_cn_a_symbol
from .errors import NoMarketDataError, VendorNotConfiguredError
from .stockstats_utils import _assert_ohlcv_not_stale

INDICATOR_DESCRIPTIONS = {
    "close_50_sma": "50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance. Tips: It lags price; combine with faster indicators for timely signals.",
    "close_200_sma": "200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups. Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries.",
    "close_10_ema": "10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points. Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals.",
    "macd": "MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes. Tips: Confirm with other indicators in low-volatility or sideways markets.",
    "macds": "MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades. Tips: Should be part of a broader strategy to avoid false positives.",
    "macdh": "MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength and spot divergence early. Tips: Can be volatile; complement with additional filters in fast-moving markets.",
    "rsi": "RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis.",
    "boll": "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. Usage: Acts as a dynamic benchmark for price movement. Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals.",
    "boll_ub": "Bollinger Upper Band: Typically 2 standard deviations above the middle line. Usage: Signals potential overbought conditions and breakout zones. Tips: Confirm signals with other tools; prices may ride the band in strong trends.",
    "boll_lb": "Bollinger Lower Band: Typically 2 standard deviations below the middle line. Usage: Indicates potential oversold conditions. Tips: Use additional analysis to avoid false reversal signals.",
    "atr": "ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes based on current market volatility. Tips: It's a reactive measure, so use it as part of a broader risk management strategy.",
    "vwma": "VWMA: A moving average weighted by volume. Usage: Confirm trends by integrating price action with volume data. Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses.",
    "mfi": "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals.",
}


def _load_akshare():
    return import_module("akshare")


def load_ohlcv_china(symbol: str, curr_date: str) -> pd.DataFrame:
    """Fetch mainland A-share OHLCV and normalize it for downstream use."""
    digits, _exchange = split_cn_a_symbol(symbol)
    start_date = (pd.Timestamp(curr_date) - pd.DateOffset(years=5)).strftime("%Y%m%d")
    end_date = pd.Timestamp(curr_date).strftime("%Y%m%d")
    try:
        ak = _load_akshare()
    except Exception as exc:  # noqa: BLE001
        raise VendorNotConfiguredError(
            f"China stock vendor could not be loaded: {exc}"
        ) from exc

    try:
        raw = ak.stock_zh_a_hist(
            symbol=digits,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="",
        )
    except Exception as exc:  # noqa: BLE001
        raise NoMarketDataError(
            symbol,
            digits,
            f"China A-share history is currently unavailable ({exc})",
        ) from exc

    if raw is None or raw.empty:
        raise NoMarketDataError(symbol, digits, f"no China A-share rows through {curr_date}")

    frame = normalize_cn_hist_frame(raw)
    frame = frame[frame["Date"] <= pd.Timestamp(curr_date)]
    if frame.empty:
        raise NoMarketDataError(symbol, digits, f"no China A-share rows through {curr_date}")
    _assert_ohlcv_not_stale(frame, curr_date, symbol, digits)
    return frame


def get_stock_data_china(symbol: str, start_date: str, end_date: str) -> str:
    """Return China A-share OHLCV in the same text contract as yfinance."""
    frame = load_ohlcv_china(symbol, end_date)
    window = frame[
        (frame["Date"] >= pd.Timestamp(start_date)) & (frame["Date"] <= pd.Timestamp(end_date))
    ].copy()
    if window.empty:
        raise NoMarketDataError(
            symbol,
            symbol,
            f"no China A-share rows between {start_date} and {end_date}",
        )
    window["Date"] = window["Date"].dt.strftime("%Y-%m-%d")
    return (
        f"# Stock data for {symbol} from {start_date} to {end_date}\n"
        f"# Total records: {len(window)}\n"
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{window.to_csv(index=False)}"
    )


def get_stock_stats_indicators_window_china(
    symbol: str,
    indicator: str,
    curr_date: str,
    look_back_days: int,
) -> str:
    """Compute indicators locally from China-first OHLCV."""
    if indicator not in INDICATOR_DESCRIPTIONS:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(INDICATOR_DESCRIPTIONS.keys())}"
        )

    data = load_ohlcv_china(symbol, curr_date)
    df = wrap(data.copy())
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df[indicator]

    end_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = end_dt - relativedelta(days=look_back_days)
    lines = []
    current_dt = end_dt
    while current_dt >= start_dt:
        key = current_dt.strftime("%Y-%m-%d")
        rows = df[df["Date"] == key]
        if rows.empty:
            value = "N/A: Not a trading day (weekend or holiday)"
        else:
            raw_value = rows[indicator].iloc[0]
            value = "N/A" if pd.isna(raw_value) else str(raw_value)
        lines.append(f"{key}: {value}")
        current_dt -= relativedelta(days=1)

    return (
        f"## {indicator} values from {start_dt.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
        + "\n".join(lines)
        + "\n\n"
        + INDICATOR_DESCRIPTIONS[indicator]
    )
