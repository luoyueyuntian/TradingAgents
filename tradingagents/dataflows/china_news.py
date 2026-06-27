"""China-market news and disclosure adapters."""

from __future__ import annotations

from datetime import datetime, timedelta
from importlib import import_module
import re

import pandas as pd


def _load_akshare():
    return import_module("akshare")


def _normalize_symbol(symbol: str) -> str:
    value = symbol.strip().upper()
    if "." in value:
        return value.split(".", 1)[0]
    return value


def _parse_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _looks_like_multi_stock_roundup(title: str, body: str) -> bool:
    """Heuristic to skip broad listicles that only mention the ticker incidentally."""
    combined = f"{title} {body}"
    codes = set(re.findall(r"\b\d{6}\b", combined))
    if len(codes) >= 4:
        return True

    roundup_tokens = (
        "股获",
        "净买入",
        "净流入",
        "主力资金",
        "融资资金",
        "龙虎榜",
        "A股",
        "收盘",
        "午评",
        "早盘",
        "尾盘",
        "沪指",
        "深成指",
        "创业板",
    )
    return len(codes) >= 2 and any(token in title for token in roundup_tokens)


def _format_article_block(title: str, body: str, source: str, link: str, when: str) -> str:
    lines = [f"### {title} (source: {source})"]
    if when:
        lines.append(f"Published: {when}")
    if body:
        lines.append(body)
    if link:
        lines.append(f"Link: {link}")
    return "\n".join(lines)


def get_news_china(ticker: str, start_date: str, end_date: str) -> str:
    """Return China-market ticker news filtered to the requested window."""
    try:
        ak = _load_akshare()
    except Exception as exc:  # noqa: BLE001
        return f"DATA_UNAVAILABLE: China news vendor could not be loaded ({exc})."

    symbol = _normalize_symbol(ticker)
    try:
        frame = ak.stock_news_em(symbol=symbol).copy()
    except Exception as exc:  # noqa: BLE001
        return f"DATA_UNAVAILABLE: China market news for {ticker} is currently unavailable ({exc})."

    if frame.empty:
        return f"No China market news found for {ticker}"

    frame["发布时间"] = _parse_datetime(frame["发布时间"])
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    frame = frame[(frame["发布时间"] >= start_dt) & (frame["发布时间"] < end_dt)]
    if frame.empty:
        return f"No China market news found for {ticker} between {start_date} and {end_date}"

    parts = []
    for _, row in frame.sort_values("发布时间", ascending=False).head(20).iterrows():
        title = str(row.get("新闻标题", "No title"))
        body = str(row.get("新闻内容", "")).strip()
        if _looks_like_multi_stock_roundup(title, body):
            continue
        parts.append(
            _format_article_block(
                title,
                body,
                str(row.get("文章来源", "Unknown")),
                str(row.get("新闻链接", "")).strip(),
                row["发布时间"].strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row["发布时间"]) else "",
            )
        )

    if not parts:
        return (
            f"No China market news found for {ticker} between {start_date} and {end_date} "
            "after filtering out broad multi-stock market roundups"
        )

    return f"## {ticker} China Market News, from {start_date} to {end_date}:\n\n" + "\n\n".join(parts)


def get_global_news_china(curr_date: str, look_back_days: int = 7, limit: int = 10) -> str:
    """Return broad China market policy and macro news."""
    try:
        ak = _load_akshare()
    except Exception as exc:  # noqa: BLE001
        return f"DATA_UNAVAILABLE: China macro/news vendor could not be loaded ({exc})."

    try:
        frame = ak.stock_news_main_cx().copy()
    except Exception as exc:  # noqa: BLE001
        return f"DATA_UNAVAILABLE: China policy and macro news is currently unavailable ({exc})."

    if frame.empty:
        return f"No China policy and macro news found for {curr_date}"

    if "pubTime" in frame.columns:
        date_col = "pubTime"
    elif "发布时间" in frame.columns:
        date_col = "发布时间"
    else:
        date_col = None

    if date_col is not None:
        frame[date_col] = _parse_datetime(frame[date_col])
        end_dt = datetime.strptime(curr_date, "%Y-%m-%d") + timedelta(days=1)
        start_dt = end_dt - timedelta(days=look_back_days)
        frame = frame[(frame[date_col] >= start_dt) & (frame[date_col] < end_dt)]

    if frame.empty:
        return f"No China policy and macro news found between the requested dates ending {curr_date}"

    parts = []
    for _, row in frame.head(limit).iterrows():
        title = str(row.get("title", row.get("标题", "No title")))
        body = str(row.get("summary", row.get("内容", ""))).strip()
        link = str(row.get("url", row.get("链接", ""))).strip()
        when = ""
        if date_col is not None and pd.notna(row.get(date_col)):
            when = row[date_col].strftime("%Y-%m-%d %H:%M:%S")
        parts.append(_format_article_block(title, body, "Caixin/Eastmoney", link, when))

    start_date = (datetime.strptime(curr_date, "%Y-%m-%d") - timedelta(days=look_back_days)).strftime("%Y-%m-%d")
    return (
        f"## China Market Policy and Macro News, from {start_date} to {curr_date}:\n\n"
        + "\n\n".join(parts)
    )


def get_insider_transactions_china(ticker: str) -> str:
    """Return an explicit placeholder for unsupported insider/disclosure detail."""
    return (
        "DATA_UNAVAILABLE: China mainland insider/disclosure detail is not yet "
        "mapped to a structured adapter here. Use company announcements, major "
        "shareholder pledge disclosures, and shareholder increase/decrease "
        "announcements as the primary substitute signal for now."
    )
