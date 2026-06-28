"""China forward-looking market-structure signals."""

from __future__ import annotations

from datetime import datetime, timedelta
from importlib import import_module

import pandas as pd

from .errors import NoMarketDataError, VendorNotConfiguredError

SUPPORTED_TOPICS = {
    "northbound": "沪深港通北向资金流向",
    "margin": "融资融券余额变化",
    "fund_flow": "大盘主力资金流向",
}


def _load_akshare():
    return import_module("akshare")


def _normalize_topic(topic: str) -> str:
    value = topic.strip().lower()
    if any(token in value for token in ("northbound", "hsgt", "北向", "沪股通", "深股通")):
        return "northbound"
    if any(token in value for token in ("margin", "融资", "融券")):
        return "margin"
    if any(token in value for token in ("fund flow", "资金流", "主力资金")):
        return "fund_flow"
    return ""


def _format_markdown_table(df: pd.DataFrame) -> str:
    cols = [str(col) for col in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for row in df.itertuples(index=False, name=None):
        rows.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join([header, sep, *rows])


def _northbound_signal(ak, limit: int) -> pd.DataFrame:
    frame = ak.stock_hsgt_fund_flow_summary_em().copy()
    keep = frame[frame["资金方向"].astype(str).str.contains("北向", na=False)]
    if keep.empty:
        keep = frame[frame["板块"].astype(str).isin(["沪股通", "深股通"])]
    return keep.tail(limit)


def _margin_signal(ak, limit: int) -> pd.DataFrame:
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=max(limit * 7, 14))
    frame = ak.stock_margin_sse(
        start_date=start_dt.strftime("%Y%m%d"),
        end_date=end_dt.strftime("%Y%m%d"),
    ).copy()
    cols = [col for col in ("信用交易日期", "融资余额", "融券余额", "融资买入额", "融资偿还额") if col in frame.columns]
    return frame[cols].tail(limit) if cols else frame.tail(limit)


def _fund_flow_signal(ak, limit: int) -> pd.DataFrame:
    frame = ak.stock_market_fund_flow().copy()
    cols = [
        col
        for col in (
            "日期",
            "上证-收盘价",
            "上证-涨跌幅",
            "深证-收盘价",
            "深证-涨跌幅",
            "主力净流入-净额",
            "主力净流入-净占比",
        )
        if col in frame.columns
    ]
    return frame[cols].tail(limit) if cols else frame.tail(limit)


def get_china_market_signals(topic: str, limit: int | None = None) -> str:
    """Return China forward-looking market-structure signals as markdown."""
    signal_type = _normalize_topic(topic)
    if not signal_type:
        choices = ", ".join(sorted(SUPPORTED_TOPICS))
        return (
            f"Supported China signal topics: {choices}. "
            f"The requested topic '{topic}' is not mapped to a China market signal."
        )

    if limit is None:
        limit = 6

    try:
        ak = _load_akshare()
    except Exception as exc:  # noqa: BLE001
        raise VendorNotConfiguredError(
            f"China market-signal vendor could not be loaded: {exc}"
        ) from exc

    try:
        if signal_type == "northbound":
            frame = _northbound_signal(ak, limit)
        elif signal_type == "margin":
            frame = _margin_signal(ak, limit)
        else:
            frame = _fund_flow_signal(ak, limit)
    except Exception as exc:  # noqa: BLE001
        raise NoMarketDataError(
            symbol=topic,
            detail=(
                f"China market signals for {SUPPORTED_TOPICS[signal_type]} "
                f"are currently unavailable ({exc})"
            ),
        ) from exc

    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise NoMarketDataError(
            symbol=topic,
            detail=f"China market signals for {SUPPORTED_TOPICS[signal_type]} returned no rows",
        )

    trimmed = frame.copy()
    for col in ("交易日", "日期", "信用交易日期"):
        if col in trimmed.columns:
            parsed = pd.to_datetime(trimmed[col], errors="coerce")
            if parsed.notna().any():
                trimmed[col] = parsed.dt.strftime("%Y-%m-%d")

    return (
        "## China Forward-Looking Signals\n"
        f"- Topic: `{topic}`\n"
        f"- Signal family: {SUPPORTED_TOPICS[signal_type]}\n\n"
        f"{_format_markdown_table(trimmed)}"
    )
