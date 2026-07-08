"""Helpers shared by mainland China equity data adapters."""

from __future__ import annotations

import pandas as pd

from .errors import NoMarketDataError


def split_cn_a_symbol(symbol: str) -> tuple[str, str]:
    """Split a normalized A-share symbol into raw digits and exchange code."""
    value = str(symbol).strip().upper()
    if value.endswith(".SS"):
        return value[:-3], "SH"
    if value.endswith(".SZ"):
        return value[:-3], "SZ"
    raise NoMarketDataError(
        symbol,
        value,
        "expected a mainland A-share symbol ending in .SS or .SZ",
    )


def normalize_cn_hist_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize AKShare A-share history output into stockstats-friendly OHLCV."""
    frame = df.rename(
        columns={
            "日期": "Date",
            "开盘": "Open",
            "收盘": "Close",
            "最高": "High",
            "最低": "Low",
            "成交量": "Volume",
        }
    ).copy()
    if "Date" not in frame.columns:
        raise NoMarketDataError("cn_a", "cn_a", "China A-share history is missing a date column")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    numeric_cols = [
        col for col in ("Open", "Close", "High", "Low", "Volume") if col in frame.columns
    ]
    frame[numeric_cols] = frame[numeric_cols].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(subset=["Date", "Close"]).sort_values("Date")
    ordered_cols = [col for col in ("Date", "Open", "Close", "High", "Low", "Volume") if col in frame.columns]
    return frame[ordered_cols]
