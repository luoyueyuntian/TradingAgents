"""China A-share fundamentals adapters."""

from __future__ import annotations

from datetime import datetime
from importlib import import_module

import pandas as pd

from .china_equity_utils import split_cn_a_symbol
from .errors import NoMarketDataError, VendorNotConfiguredError


def _load_akshare():
    return import_module("akshare")


def _eastmoney_symbol(symbol: str) -> str:
    digits, exchange = split_cn_a_symbol(symbol)
    return f"{exchange}{digits}"


def _filter_statement_rows(frame: pd.DataFrame, curr_date: str | None) -> pd.DataFrame:
    if frame is None or frame.empty or not curr_date:
        return frame

    filtered = frame.copy()
    date_col = next(
        (col for col in ("REPORT_DATE", "REPORT_DATE_NAME", "Date", "日期") if col in filtered.columns),
        None,
    )
    if date_col is None:
        return filtered

    filtered[date_col] = pd.to_datetime(filtered[date_col], errors="coerce")
    filtered = filtered.dropna(subset=[date_col])
    filtered = filtered[filtered[date_col] <= pd.Timestamp(curr_date)].sort_values(date_col)
    if date_col == "REPORT_DATE":
        filtered[date_col] = filtered[date_col].dt.strftime("%Y-%m-%d")
    return filtered


def _format_statement(
    frame: pd.DataFrame,
    ticker: str,
    freq: str,
    title: str,
    curr_date: str | None,
) -> str:
    normalized = _filter_statement_rows(frame, curr_date)
    if normalized is None or normalized.empty:
        raise NoMarketDataError(ticker, ticker, f"no {title.lower()} data")

    return (
        f"# {title} data for {ticker} ({freq})\n"
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{normalized.to_csv(index=False)}"
    )


def get_fundamentals_china(ticker: str, curr_date: str | None = None) -> str:
    digits, _exchange = split_cn_a_symbol(ticker)
    try:
        ak = _load_akshare()
    except Exception as exc:  # noqa: BLE001
        raise VendorNotConfiguredError(
            f"China fundamentals vendor could not be loaded: {exc}"
        ) from exc

    try:
        info_df = ak.stock_individual_info_em(symbol=digits)
        abstract_df = ak.stock_financial_abstract_ths(symbol=digits, indicator="按报告期")
    except Exception as exc:  # noqa: BLE001
        raise NoMarketDataError(
            ticker,
            digits,
            f"China fundamentals are currently unavailable ({exc})",
        ) from exc

    lines: list[str] = []
    if isinstance(info_df, pd.DataFrame) and not info_df.empty:
        key_col = info_df.columns[0]
        value_col = info_df.columns[1]
        info_map = dict(zip(info_df[key_col], info_df[value_col], strict=False))
        if info_map.get("股票简称"):
            lines.append(f"Name: {info_map['股票简称']}")
        if info_map.get("行业"):
            lines.append(f"Industry: {info_map['行业']}")

    if isinstance(abstract_df, pd.DataFrame) and not abstract_df.empty:
        filtered = _filter_statement_rows(abstract_df, curr_date)
        row = filtered.iloc[-1].to_dict() if filtered is not None and not filtered.empty else abstract_df.iloc[-1].to_dict()
        field_map = {
            "TOTAL_OPERATE_INCOME": "Revenue (TTM)",
            "PARENT_NETPROFIT": "Net Income",
            "ROE_WEIGHTED": "Return on Equity",
            "GROSS_PROFIT_RATE": "Gross Margin",
        }
        for source_col, label in field_map.items():
            value = row.get(source_col)
            if pd.notna(value):
                lines.append(f"{label}: {value}")

    if not lines:
        raise NoMarketDataError(ticker, digits, "no fundamental fields returned")

    return (
        f"# Company Fundamentals for {ticker}\n"
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        + "\n".join(lines)
    )


def get_balance_sheet_china(
    ticker: str,
    freq: str = "quarterly",
    curr_date: str | None = None,
) -> str:
    try:
        ak = _load_akshare()
        frame = ak.stock_balance_sheet_by_report_em(symbol=_eastmoney_symbol(ticker))
    except Exception as exc:  # noqa: BLE001
        raise NoMarketDataError(
            ticker,
            ticker,
            f"China balance sheet is currently unavailable ({exc})",
        ) from exc
    return _format_statement(frame, ticker, freq, "Balance Sheet", curr_date)


def get_cashflow_china(
    ticker: str,
    freq: str = "quarterly",
    curr_date: str | None = None,
) -> str:
    try:
        ak = _load_akshare()
        frame = ak.stock_cash_flow_sheet_by_report_em(symbol=_eastmoney_symbol(ticker))
    except Exception as exc:  # noqa: BLE001
        raise NoMarketDataError(
            ticker,
            ticker,
            f"China cash flow is currently unavailable ({exc})",
        ) from exc
    return _format_statement(frame, ticker, freq, "Cash Flow", curr_date)


def get_income_statement_china(
    ticker: str,
    freq: str = "quarterly",
    curr_date: str | None = None,
) -> str:
    try:
        ak = _load_akshare()
        frame = ak.stock_profit_sheet_by_report_em(symbol=_eastmoney_symbol(ticker))
    except Exception as exc:  # noqa: BLE001
        raise NoMarketDataError(
            ticker,
            ticker,
            f"China income statement is currently unavailable ({exc})",
        ) from exc
    return _format_statement(frame, ticker, freq, "Income Statement", curr_date)
