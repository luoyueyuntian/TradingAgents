"""Tencent-backed China A-share OHLCV and indicator adapters."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from importlib import import_module

import pandas as pd
from dateutil.relativedelta import relativedelta
from stockstats import wrap

from .china_equity_utils import to_tx_symbol
from .cn_stock import INDICATOR_DESCRIPTIONS
from .config import get_config
from .errors import NoMarketDataError, VendorNotConfiguredError
from .stockstats_utils import _assert_ohlcv_not_stale
from .utils import safe_ticker_component

logger = logging.getLogger(__name__)


def _load_akshare():
    return import_module("akshare")


def _normalize_tx_hist_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "close": "Close",
            "high": "High",
            "low": "Low",
            "amount": "Volume",
        }
    ).copy()
    if "Date" not in frame.columns:
        raise NoMarketDataError("cn_a_tx", "cn_a_tx", "Tencent A-share history is missing a date column")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    numeric_cols = [col for col in ("Open", "Close", "High", "Low", "Volume") if col in frame.columns]
    frame[numeric_cols] = frame[numeric_cols].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(subset=["Date", "Close"]).sort_values("Date")
    ordered_cols = [col for col in ("Date", "Open", "Close", "High", "Low", "Volume") if col in frame.columns]
    return frame[ordered_cols]


def _fetch_hist_with_retry(
    ak,
    *,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str,
    max_retries: int = 2,
    base_delay: float = 1.0,
):
    for attempt in range(max_retries + 1):
        try:
            return ak.stock_zh_a_hist_tx(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        except Exception:  # noqa: BLE001
            if attempt >= max_retries:
                raise
            delay = base_delay * (2**attempt)
            logger.warning(
                "Tencent stock vendor history fetch failed for %s, retrying in %.0fs (attempt %s/%s)",
                symbol,
                delay,
                attempt + 1,
                max_retries,
            )
            time.sleep(delay)


def load_ohlcv_china_tx(symbol: str, curr_date: str) -> pd.DataFrame:
    tx_symbol = to_tx_symbol(symbol)
    safe_symbol = safe_ticker_component(symbol.strip().upper())
    config = get_config()
    curr_date_dt = pd.Timestamp(curr_date)
    today_date = pd.Timestamp.today()
    start_date = (today_date - pd.DateOffset(years=5)).strftime("%Y-%m-%d")
    end_date = today_date.strftime("%Y-%m-%d")
    data_file: str | None = None
    try:
        os.makedirs(config["data_cache_dir"], exist_ok=True)
        data_file = os.path.join(
            config["data_cache_dir"],
            f"{safe_symbol}-CnATx-data-{start_date}-{end_date}.csv",
        )
    except OSError as exc:
        logger.warning("Tencent stock cache directory unavailable for %s: %s", symbol, exc)

    try:
        ak = _load_akshare()
    except Exception as exc:  # noqa: BLE001
        raise VendorNotConfiguredError(
            f"Tencent China stock vendor could not be loaded: {exc}"
        ) from exc

    raw = None
    if data_file and os.path.exists(data_file):
        try:
            cached = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
            if not cached.empty and "Close" in cached.columns:
                raw = cached
        except OSError as exc:
            logger.warning("Tencent stock cache read failed for %s: %s", symbol, exc)

    if raw is None:
        try:
            fetched = _fetch_hist_with_retry(
                ak,
                symbol=tx_symbol,
                start_date=start_date,
                end_date=end_date,
                adjust="",
            )
        except Exception as exc:  # noqa: BLE001
            raise NoMarketDataError(
                symbol,
                tx_symbol,
                f"Tencent history endpoint is currently unavailable ({exc})",
            ) from exc

        if fetched is None or fetched.empty:
            raise NoMarketDataError(symbol, tx_symbol, f"no Tencent rows through {curr_date}")

        normalized = _normalize_tx_hist_frame(fetched)
        if normalized.empty or "Close" not in normalized.columns:
            raise NoMarketDataError(symbol, tx_symbol, f"no Tencent rows through {curr_date}")
        if data_file:
            try:
                normalized.to_csv(data_file, index=False, encoding="utf-8")
            except OSError as exc:
                logger.warning("Tencent stock cache write failed for %s: %s", symbol, exc)
        raw = normalized

    frame = _normalize_tx_hist_frame(raw)
    frame = frame[frame["Date"] <= curr_date_dt]
    if frame.empty:
        raise NoMarketDataError(symbol, tx_symbol, f"no Tencent rows through {curr_date}")
    _assert_ohlcv_not_stale(frame, curr_date, symbol, tx_symbol)
    return frame


def get_stock_data_china_tx(symbol: str, start_date: str, end_date: str) -> str:
    frame = load_ohlcv_china_tx(symbol, end_date)
    window = frame[
        (frame["Date"] >= pd.Timestamp(start_date)) & (frame["Date"] <= pd.Timestamp(end_date))
    ].copy()
    if window.empty:
        raise NoMarketDataError(symbol, to_tx_symbol(symbol), f"no Tencent rows between {start_date} and {end_date}")
    window["Date"] = window["Date"].dt.strftime("%Y-%m-%d")
    return (
        f"# Stock data for {symbol} from {start_date} to {end_date}\n"
        f"# Total records: {len(window)}\n"
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{window.to_csv(index=False)}"
    )


def get_stock_stats_indicators_window_china_tx(
    symbol: str,
    indicator: str,
    curr_date: str,
    look_back_days: int,
) -> str:
    if indicator not in INDICATOR_DESCRIPTIONS:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(INDICATOR_DESCRIPTIONS.keys())}"
        )

    data = load_ohlcv_china_tx(symbol, curr_date)
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
