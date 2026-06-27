"""China macroeconomic adapter.

Provides mainland-China macro series with a FRED-like text report contract so
the existing news analyst can consume it without graph changes.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from importlib import import_module

import pandas as pd

CHINA_MACRO_ALIASES: dict[str, tuple[str, str]] = {
    "cpi": ("CPI", "macro_china_cpi_yearly"),
    "ppi": ("PPI", "macro_china_ppi_yearly"),
    "pmi": ("PMI", "macro_china_pmi_yearly"),
    "m2": ("M2", "macro_china_m2_yearly"),
    "social_financing": ("Social Financing", "macro_china_shrzgm"),
    "lpr": ("LPR", "macro_china_lpr"),
}

DEFAULT_LOOKBACK_DAYS = 365
MAX_ROWS = 24


def _load_akshare():
    return import_module("akshare")


def _normalize_alias(indicator: str) -> str:
    return indicator.strip().lower().replace("-", "_").replace(" ", "_")


def _pick_date_column(df: pd.DataFrame) -> str | None:
    for col in ("日期", "TRADE_DATE", "date", "Date"):
        if col in df.columns:
            return col
    return None


def _latest_available_date(frame: pd.DataFrame, date_col: str | None) -> str | None:
    if date_col is None or date_col not in frame.columns:
        return None
    parsed = pd.to_datetime(frame[date_col], errors="coerce").dropna()
    if parsed.empty:
        return None
    return parsed.max().strftime("%Y-%m-%d")


def _format_markdown_table(df: pd.DataFrame) -> str:
    cols = [str(col) for col in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows = []
    for row in df.itertuples(index=False, name=None):
        rows.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join([header, sep, *rows])


def get_china_macro_data(
    indicator: str,
    curr_date: str,
    look_back_days: int | None = None,
) -> str:
    """Return a China macro series as a formatted markdown report."""
    alias = _normalize_alias(indicator)
    if alias not in CHINA_MACRO_ALIASES:
        choices = ", ".join(sorted(CHINA_MACRO_ALIASES))
        return (
            f"China macro alias '{indicator}' is not supported. "
            f"Use one of: {choices}."
        )

    if look_back_days is None:
        look_back_days = DEFAULT_LOOKBACK_DAYS

    label, function_name = CHINA_MACRO_ALIASES[alias]
    try:
        ak = _load_akshare()
    except Exception as exc:  # noqa: BLE001
        return f"DATA_UNAVAILABLE: China macro vendor could not be loaded ({exc})."

    try:
        df = getattr(ak, function_name)()
    except Exception as exc:  # noqa: BLE001
        return (
            f"DATA_UNAVAILABLE: China macro data for {label} is currently unavailable "
            f"({exc})."
        )

    if not isinstance(df, pd.DataFrame) or df.empty:
        return f"DATA_UNAVAILABLE: China macro data for {label} returned no rows."

    frame = df.copy()
    date_col = _pick_date_column(frame)
    end_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=look_back_days)

    if date_col is not None:
        frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
        frame = frame.dropna(subset=[date_col])
        frame = frame[(frame[date_col] >= start_dt) & (frame[date_col] <= end_dt)]
        frame = frame.sort_values(date_col)
        if frame.empty:
            latest = _latest_available_date(df, date_col)
            stale_note = (
                f" The latest available observation is {latest}."
                if latest
                else ""
            )
            return (
                f"DATA_UNAVAILABLE: China macro data for {label} has no observations "
                f"between {start_dt.strftime('%Y-%m-%d')} and {curr_date}.{stale_note}"
            )

    if alias == "lpr":
        selected_cols = [col for col in ("TRADE_DATE", "LPR1Y", "LPR5Y", "RATE_1", "RATE_2") if col in frame.columns]
    else:
        selected_cols = [col for col in ("日期", "今值", "预测值", "前值") if col in frame.columns]
    if not selected_cols:
        selected_cols = list(frame.columns[: min(len(frame.columns), 6)])

    trimmed = frame[selected_cols].tail(MAX_ROWS).copy()
    if date_col is not None and date_col in trimmed.columns:
        trimmed[date_col] = trimmed[date_col].dt.strftime("%Y-%m-%d")

    return (
        f"## China Macro: {label}\n"
        f"- Alias: `{alias}`\n"
        f"- Window end: {curr_date}\n"
        f"- Window length: {look_back_days} days\n\n"
        f"{_format_markdown_table(trimmed)}"
    )
