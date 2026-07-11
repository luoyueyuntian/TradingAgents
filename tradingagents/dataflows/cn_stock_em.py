"""Eastmoney China A-share OHLCV adapter using a Chrome-like HTTP fingerprint."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from importlib import import_module

import pandas as pd
from dateutil.relativedelta import relativedelta
from stockstats import wrap

from .china_equity_utils import normalize_cn_hist_frame, split_cn_a_symbol
from .cn_stock import INDICATOR_DESCRIPTIONS
from .config import get_config
from .errors import NoMarketDataError, VendorNotConfiguredError
from .stockstats_utils import _assert_ohlcv_not_stale
from .utils import safe_ticker_component

logger = logging.getLogger(__name__)

EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
CHROME_IMPERSONATION = "chrome"


def _load_curl_requests():
    return import_module("curl_cffi.requests")


def _market_code(digits: str, exchange: str) -> int:
    if exchange == "SH" or digits.startswith("6"):
        return 1
    return 0


def _parse_eastmoney_klines(payload: dict, symbol: str, canonical: str) -> pd.DataFrame:
    data = payload.get("data") if isinstance(payload, dict) else None
    klines = data.get("klines") if isinstance(data, dict) else None
    if not klines:
        raise NoMarketDataError(symbol, canonical, "Eastmoney Chrome endpoint returned no rows")

    rows = [str(item).split(",") for item in klines]
    frame = pd.DataFrame(rows)
    if frame.empty or frame.shape[1] < 6:
        raise NoMarketDataError(symbol, canonical, "Eastmoney Chrome endpoint returned malformed rows")

    frame = frame.iloc[:, :6].copy()
    frame.columns = ["日期", "开盘", "收盘", "最高", "最低", "成交量"]
    return normalize_cn_hist_frame(frame)


def _fetch_kline_with_retry(
    client,
    *,
    symbol: str,
    canonical: str,
    secid: str,
    start_date: str,
    end_date: str,
    max_retries: int = 0,
    base_delay: float = 1.0,
) -> pd.DataFrame:
    params = {
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f116",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
        "klt": "101",
        "fqt": "0",
        "secid": secid,
        "beg": start_date,
        "end": end_date,
    }
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": f"https://quote.eastmoney.com/{'sh' if secid.startswith('1.') else 'sz'}{canonical}.html",
    }

    for attempt in range(max_retries + 1):
        try:
            response = client.get(
                EASTMONEY_KLINE_URL,
                params=params,
                headers=headers,
                timeout=15,
                impersonate=CHROME_IMPERSONATION,
            )
            response.raise_for_status()
            return _parse_eastmoney_klines(response.json(), symbol, canonical)
        except Exception:  # noqa: BLE001 - curl_cffi and vendor errors vary by platform
            if attempt >= max_retries:
                raise
            delay = base_delay * (2**attempt)
            logger.warning(
                "Eastmoney Chrome history fetch failed for %s, retrying in %.0fs (attempt %s/%s)",
                canonical,
                delay,
                attempt + 1,
                max_retries,
            )
            time.sleep(delay)

    raise NoMarketDataError(symbol, canonical, "Eastmoney Chrome endpoint returned no rows")


def load_ohlcv_china_em(symbol: str, curr_date: str) -> pd.DataFrame:
    """Fetch Eastmoney A-share OHLCV with curl_cffi's Chrome impersonation."""
    digits, exchange = split_cn_a_symbol(symbol)
    secid = f"{_market_code(digits, exchange)}.{digits}"
    safe_symbol = safe_ticker_component(symbol.strip().upper())
    config = get_config()
    curr_date_dt = pd.Timestamp(curr_date)
    today_date = pd.Timestamp.today()
    start_date = (today_date - pd.DateOffset(years=5)).strftime("%Y%m%d")
    end_date = today_date.strftime("%Y%m%d")
    data_file: str | None = None
    try:
        os.makedirs(config["data_cache_dir"], exist_ok=True)
        data_file = os.path.join(
            config["data_cache_dir"],
            f"{safe_symbol}-CnAEm-data-{start_date}-{end_date}.csv",
        )
    except OSError as exc:
        logger.warning("Eastmoney Chrome stock cache directory unavailable for %s: %s", symbol, exc)

    raw = None
    if data_file and os.path.exists(data_file):
        try:
            cached = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
            if not cached.empty and "Close" in cached.columns:
                raw = cached
        except OSError as exc:
            logger.warning("Eastmoney Chrome stock cache read failed for %s: %s", symbol, exc)

    if raw is None:
        try:
            client = _load_curl_requests()
        except Exception as exc:  # noqa: BLE001
            raise VendorNotConfiguredError(
                f"Eastmoney Chrome fingerprint vendor could not be loaded: {exc}"
            ) from exc

        try:
            normalized = _fetch_kline_with_retry(
                client,
                symbol=symbol,
                canonical=digits,
                secid=secid,
                start_date=start_date,
                end_date=end_date,
            )
        except NoMarketDataError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise NoMarketDataError(
                symbol,
                digits,
                f"Eastmoney Chrome history endpoint is currently unavailable ({exc})",
            ) from exc

        if normalized.empty or "Close" not in normalized.columns:
            raise NoMarketDataError(symbol, digits, f"no Eastmoney Chrome rows through {curr_date}")
        if data_file:
            try:
                normalized.to_csv(data_file, index=False, encoding="utf-8")
            except OSError as exc:
                logger.warning("Eastmoney Chrome stock cache write failed for %s: %s", symbol, exc)
        raw = normalized

    frame = normalize_cn_hist_frame(raw)
    frame = frame[frame["Date"] <= curr_date_dt]
    if frame.empty:
        raise NoMarketDataError(symbol, digits, f"no Eastmoney Chrome rows through {curr_date}")
    _assert_ohlcv_not_stale(frame, curr_date, symbol, digits)
    return frame


def get_stock_data_china_em(symbol: str, start_date: str, end_date: str) -> str:
    """Return Eastmoney Chrome-fingerprint A-share OHLCV as CSV text."""
    frame = load_ohlcv_china_em(symbol, end_date)
    window = frame[
        (frame["Date"] >= pd.Timestamp(start_date)) & (frame["Date"] <= pd.Timestamp(end_date))
    ].copy()
    if window.empty:
        raise NoMarketDataError(
            symbol,
            symbol,
            f"no Eastmoney Chrome rows between {start_date} and {end_date}",
        )
    window["Date"] = window["Date"].dt.strftime("%Y-%m-%d")
    return (
        f"# Stock data for {symbol} from {start_date} to {end_date}\n"
        f"# Total records: {len(window)}\n"
        f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"{window.to_csv(index=False)}"
    )


def get_stock_stats_indicators_window_china_em(
    symbol: str,
    indicator: str,
    curr_date: str,
    look_back_days: int,
) -> str:
    """Compute indicators from Eastmoney Chrome-fingerprint OHLCV."""
    if indicator not in INDICATOR_DESCRIPTIONS:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(INDICATOR_DESCRIPTIONS.keys())}"
        )

    data = load_ohlcv_china_em(symbol, curr_date)
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
