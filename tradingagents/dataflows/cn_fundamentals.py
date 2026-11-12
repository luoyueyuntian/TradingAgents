"""China A-share fundamentals adapters."""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
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
        (col for col in ("NOTICE_DATE", "ANNOUNCEMENT_DATE", "公告日期", "披露日期") if col in filtered.columns),
        None,
    )
    if date_col is None:
        raise NoMarketDataError("financial statements", detail="Publication dates unavailable; cannot verify historical availability")

    filtered[date_col] = pd.to_datetime(filtered[date_col], errors="coerce")
    filtered = filtered.dropna(subset=[date_col])
    filtered = filtered[filtered[date_col] <= pd.Timestamp(curr_date)].sort_values(date_col)
    if date_col == "REPORT_DATE":
        filtered[date_col] = filtered[date_col].dt.strftime("%Y-%m-%d")
    return filtered


def _first_present(row: dict, *candidates: str):
    for candidate in candidates:
        value = row.get(candidate)
        if pd.notna(value):
            return value
    return None


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
    if curr_date and curr_date < datetime.now().strftime("%Y-%m-%d"):
        raise NoMarketDataError(ticker, digits, "Historical fundamentals overview unavailable: live company snapshot cannot be dated as of the requested date")
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
        if pd.notna(info_map.get("总市值")):
            lines.append(f"Market Cap: {info_map['总市值']}")

    if isinstance(abstract_df, pd.DataFrame) and not abstract_df.empty:
        # Historical overviews are rejected above; this is explicitly a live snapshot.
        filtered = _filter_statement_rows(abstract_df, None)
        row = filtered.iloc[-1].to_dict() if filtered is not None and not filtered.empty else {}
        field_map = {
            "Revenue (TTM)": ("TOTAL_OPERATE_INCOME", "营业总收入"),
            "Net Income": ("PARENT_NETPROFIT", "归母净利润"),
            "Return on Equity": ("ROE_WEIGHTED", "净资产收益率"),
            "Return on Assets": ("ROA", "总资产收益率"),
            "Gross Margin": ("GROSS_PROFIT_RATE", "毛利率"),
            "Current Ratio": ("CURRENT_RATIO", "流动比率"),
            "EPS (Basic)": ("BASIC_EPS", "基本每股收益"),
            "Book Value": ("BPS", "每股净资产"),
            "Operating Cash Flow Per Share": ("OCFPS", "每股经营现金流"),
            "Total Assets": ("TOTAL_ASSETS", "总资产"),
            "Total Liabilities": ("TOTAL_LIABILITIES", "总负债"),
            "Operating Cash Flow": ("NET_CASH_FLOWS_OPER_ACT", "经营活动产生的现金流量净额"),
        }
        for label, aliases in field_map.items():
            value = _first_present(row, *aliases)
            if pd.notna(value):
                lines.append(f"{label}: {value}")
        total_assets = _first_present(row, "TOTAL_ASSETS", "总资产")
        total_liabilities = _first_present(row, "TOTAL_LIABILITIES", "总负债")
        if pd.notna(total_assets) and pd.notna(total_liabilities) and float(total_assets) != 0:
            ratio = (
                Decimal(str(total_liabilities))
                / Decimal(str(total_assets))
                * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            lines.append(f"Asset Liability Ratio: {ratio}")

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
