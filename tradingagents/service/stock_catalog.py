"""Persistent stock catalog for Web ticker selection."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Iterable

from tradingagents.service.web_state import get_web_state_base_dir

StockFetcher = Callable[[], Iterable["StockCatalogItem"]]

SUPPORTED_STOCK_MARKETS = ("us", "hk", "cn_a")
STOCK_MARKET_LABELS = {
    "us": "US Stocks",
    "hk": "Hong Kong Stocks",
    "cn_a": "China A-Shares",
}

_EXCLUDED_ENGLISH_TERMS = (
    "ETF",
    "ETN",
    "FUND",
    "WARRANT",
    "RIGHT",
    "RIGHTS",
    "UNIT",
    "UNITS",
    "PREFERRED",
    "PREFERENCE",
    "NOTE",
    "NOTES",
    "BOND",
    "DEBENTURE",
    "INDEX",
)

_EXCLUDED_CJK_TERMS = (
    "基金",
    "交易所买卖基金",
    "权证",
    "认股权证",
    "牛熊证",
    "债券",
    "优先股",
    "信托",
    "指数",
)

_EXCLUDED_PRODUCT_MARKERS = ("ETF", "ETN", "LOF", "REIT")

_ENGLISH_TOKEN_RE = re.compile(r"[A-Z0-9]+")


@dataclass(frozen=True)
class StockCatalogItem:
    market: str
    symbol: str
    name: str
    exchange: str


@dataclass(frozen=True)
class StockCatalogSnapshot:
    updated_on: str | None
    markets: dict[str, list[StockCatalogItem]]
    errors: dict[str, str] = field(default_factory=dict)
    refreshed: bool = False

    @property
    def counts(self) -> dict[str, int]:
        return {
            market: len(self.markets.get(market, []))
            for market in SUPPORTED_STOCK_MARKETS
        }


def default_stock_catalog_cache_path() -> Path:
    """Return the shared Web stock-catalog cache path."""
    return get_web_state_base_dir() / "stock-catalog.json"


def list_stock_markets() -> list[dict[str, str]]:
    return [
        {"value": market, "label": STOCK_MARKET_LABELS[market]}
        for market in SUPPORTED_STOCK_MARKETS
    ]


def refresh_stock_catalog(
    *,
    cache_path: Path | None = None,
    fetchers: dict[str, StockFetcher] | None = None,
    force: bool = False,
    today: date | None = None,
) -> StockCatalogSnapshot:
    """Refresh the full stock catalog at most once per day unless forced."""
    resolved_cache_path = cache_path or default_stock_catalog_cache_path()
    current = _read_snapshot(resolved_cache_path)
    today_text = (today or date.today()).isoformat()
    if current.updated_on == today_text and not force:
        return current

    resolved_fetchers = fetchers or default_stock_fetchers()
    markets: dict[str, list[StockCatalogItem]] = {}
    errors: dict[str, str] = {}
    for market in SUPPORTED_STOCK_MARKETS:
        fetcher = resolved_fetchers.get(market)
        if fetcher is None:
            errors[market] = "No stock catalog fetcher configured."
            markets[market] = current.markets.get(market, [])
            continue
        try:
            markets[market] = _normalize_catalog_items(market, fetcher())
        except Exception as exc:  # pragma: no cover - network/vendor failures vary
            errors[market] = str(exc)
            markets[market] = current.markets.get(market, [])

    if not any(markets.values()):
        raise RuntimeError("No stock catalog data available.")

    snapshot = StockCatalogSnapshot(
        updated_on=today_text,
        markets=markets,
        errors=errors,
        refreshed=True,
    )
    _write_snapshot(resolved_cache_path, snapshot)
    return snapshot


def search_stock_catalog(
    market: str,
    *,
    query: str = "",
    limit: int = 100,
    cache_path: Path | None = None,
    fetchers: dict[str, StockFetcher] | None = None,
    today: date | None = None,
    refresh_if_stale: bool = True,
) -> list[StockCatalogItem]:
    """Return matching stocks for one supported market."""
    normalized_market = market.strip().lower()
    if normalized_market not in SUPPORTED_STOCK_MARKETS:
        allowed = ", ".join(SUPPORTED_STOCK_MARKETS)
        raise ValueError(f"market must be one of: {allowed}")

    resolved_cache_path = cache_path or default_stock_catalog_cache_path()
    snapshot = _read_snapshot(resolved_cache_path)
    if refresh_if_stale and stock_catalog_needs_refresh(cache_path=resolved_cache_path, today=today):
        snapshot = refresh_stock_catalog(
            cache_path=resolved_cache_path,
            fetchers=fetchers,
            force=False,
            today=today,
        )
    max_items = min(max(int(limit), 1), 500)
    normalized_query = query.strip().lower()
    items = snapshot.markets.get(normalized_market, [])
    if not normalized_query:
        return items[:max_items]
    return [
        item for item in items
        if normalized_query in _search_text(item)
    ][:max_items]


def default_stock_fetchers() -> dict[str, StockFetcher]:
    return {
        "us": fetch_us_company_stocks,
        "hk": fetch_hk_company_stocks,
        "cn_a": fetch_cn_a_company_stocks,
    }


def stock_catalog_needs_refresh(
    *,
    cache_path: Path | None = None,
    today: date | None = None,
) -> bool:
    snapshot = _read_snapshot(cache_path or default_stock_catalog_cache_path())
    return snapshot.updated_on != (today or date.today()).isoformat()


def fetch_us_company_stocks() -> list[StockCatalogItem]:
    import akshare as ak

    frame = ak.get_us_stock_name()
    items: list[StockCatalogItem] = []
    for row in _records(frame):
        symbol = _text_value(row, "symbol", "代码", "code", "ticker", "证券代码").upper()
        name = _text_value(row, "name", "名称", "cname", "security name", "证券简称")
        exchange = _text_value(row, "exchange", "交易所", "market", "市场") or "US"
        if symbol and name:
            items.append(StockCatalogItem("us", _normalize_us_symbol(symbol), name, exchange))
    return items


def fetch_hk_company_stocks() -> list[StockCatalogItem]:
    import akshare as ak

    frame = ak.stock_hk_main_board_spot_em()
    items: list[StockCatalogItem] = []
    for row in _records(frame):
        code = _text_value(row, "代码", "symbol", "code", "证券代码")
        name = _text_value(row, "名称", "name", "证券简称")
        symbol = _normalize_hk_symbol(code)
        if symbol and name:
            items.append(StockCatalogItem("hk", symbol, name, "HKEX"))
    return items


def fetch_cn_a_company_stocks() -> list[StockCatalogItem]:
    import akshare as ak

    frame = ak.stock_info_a_code_name()
    items: list[StockCatalogItem] = []
    for row in _records(frame):
        code = _text_value(row, "code", "代码", "证券代码", "symbol")
        name = _text_value(row, "name", "名称", "证券简称")
        symbol, exchange = _normalize_cn_a_symbol(code)
        if symbol and name:
            items.append(StockCatalogItem("cn_a", symbol, name, exchange))
    return items


def _read_snapshot(cache_path: Path) -> StockCatalogSnapshot:
    if not cache_path.exists():
        return StockCatalogSnapshot(
            updated_on=None,
            markets={market: [] for market in SUPPORTED_STOCK_MARKETS},
        )
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return StockCatalogSnapshot(
            updated_on=None,
            markets={market: [] for market in SUPPORTED_STOCK_MARKETS},
        )

    raw_markets = payload.get("markets") if isinstance(payload, dict) else {}
    markets: dict[str, list[StockCatalogItem]] = {}
    for market in SUPPORTED_STOCK_MARKETS:
        markets[market] = [
            StockCatalogItem(
                market=market,
                symbol=str(item.get("symbol", "")).strip(),
                name=str(item.get("name", "")).strip(),
                exchange=str(item.get("exchange", "")).strip(),
            )
            for item in (raw_markets or {}).get(market, [])
            if isinstance(item, dict)
        ]
    return StockCatalogSnapshot(
        updated_on=str(payload.get("updated_on") or "") or None,
        markets=markets,
        errors=payload.get("errors") if isinstance(payload.get("errors"), dict) else {},
    )


def _write_snapshot(cache_path: Path, snapshot: StockCatalogSnapshot) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_on": snapshot.updated_on,
        "markets": {
            market: [asdict(item) for item in snapshot.markets.get(market, [])]
            for market in SUPPORTED_STOCK_MARKETS
        },
        "errors": snapshot.errors,
    }
    tmp_path = cache_path.with_suffix(f"{cache_path.suffix}.{os.getpid()}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(cache_path)


def _normalize_catalog_items(
    market: str,
    raw_items: Iterable[StockCatalogItem],
) -> list[StockCatalogItem]:
    by_symbol: dict[str, StockCatalogItem] = {}
    for item in raw_items:
        symbol = item.symbol.strip().upper()
        normalized = StockCatalogItem(
            market=market,
            symbol=symbol,
            name=item.name.strip(),
            exchange=item.exchange.strip(),
        )
        if not normalized.symbol or not normalized.name:
            continue
        if _is_regular_company_stock(normalized) and normalized.symbol not in by_symbol:
            by_symbol[normalized.symbol] = normalized
    return sorted(by_symbol.values(), key=lambda item: item.symbol)


def _is_regular_company_stock(item: StockCatalogItem) -> bool:
    uppercase_name = item.name.upper()
    english_tokens = set(_ENGLISH_TOKEN_RE.findall(uppercase_name))
    has_excluded_english_term = any(term in english_tokens for term in _EXCLUDED_ENGLISH_TERMS)
    has_excluded_cjk_term = any(term in item.name for term in _EXCLUDED_CJK_TERMS)
    has_product_marker = any(marker in uppercase_name for marker in _EXCLUDED_PRODUCT_MARKERS)
    return not (has_excluded_english_term or has_excluded_cjk_term or has_product_marker)


def _search_text(item: StockCatalogItem) -> str:
    return f"{item.symbol} {item.name} {item.exchange}".lower()


def _records(frame) -> list[dict]:
    if hasattr(frame, "to_dict"):
        return frame.to_dict("records")
    if isinstance(frame, list):
        return [item for item in frame if isinstance(item, dict)]
    return []


def _text_value(row: dict, *keys: str) -> str:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for key in keys:
        if key in row and row[key] is not None:
            return str(row[key]).strip()
        value = lowered.get(key.lower())
        if value is not None:
            return str(value).strip()
    return ""


def _normalize_us_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace("/", "-")


def _normalize_hk_symbol(code: str) -> str:
    digits = "".join(char for char in str(code).strip() if char.isdigit())
    if not digits:
        return ""
    return f"{digits.lstrip('0').zfill(4)}.HK"


def _normalize_cn_a_symbol(code: str) -> tuple[str, str]:
    raw_digits = "".join(char for char in str(code).strip() if char.isdigit())
    if not raw_digits:
        return "", ""
    digits = raw_digits.zfill(6)
    if digits.startswith("6"):
        return f"{digits}.SS", "SSE"
    if digits.startswith(("0", "3")):
        return f"{digits}.SZ", "SZSE"
    if digits.startswith(("4", "8", "9")):
        return f"{digits}.BJ", "BSE"
    return digits, "CN"
