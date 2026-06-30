"""Helpers for importing workspace data from pasted text."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field

_WATCHLIST_HEADERS = {"ticker", "symbol"}
_PORTFOLIO_HEADER_ALIASES = {
    "ticker": {"ticker", "symbol"},
    "quantity": {"quantity", "qty", "shares", "share_quantity", "units"},
    "average_cost": {
        "average_cost",
        "averagecost",
        "avg_cost",
        "avgcost",
        "average_price",
        "avg_price",
        "price",
        "cost",
        "entry_price",
    },
}


@dataclass(frozen=True)
class ParsedImportError:
    line_number: int
    message: str
    raw_value: str | None = None


@dataclass(frozen=True)
class ParsedPortfolioPosition:
    ticker: str
    quantity: float
    average_cost: float


@dataclass
class ParsedWatchlistImport:
    tickers: list[str] = field(default_factory=list)
    skipped_count: int = 0
    errors: list[ParsedImportError] = field(default_factory=list)


@dataclass
class ParsedPortfolioImport:
    positions: list[ParsedPortfolioPosition] = field(default_factory=list)
    skipped_count: int = 0
    errors: list[ParsedImportError] = field(default_factory=list)


def parse_watchlist_import(content: str) -> ParsedWatchlistImport:
    """Parse pasted watchlist content into normalized ticker symbols."""
    delimiter = _detect_delimiter(content)
    if delimiter is None:
        tokens = [token.strip() for token in re.split(r"[\s;]+", content) if token.strip()]
        if tokens and _normalize_header(tokens[0]) in _WATCHLIST_HEADERS:
            tokens = tokens[1:]
        return _dedupe_tickers(tokens)

    seen: set[str] = set()
    tickers: list[str] = []
    skipped_count = 0
    first_row = True
    for _, _, cells in _iter_rows(content, delimiter):
        first_value = next((cell.strip() for cell in cells if cell.strip()), "")
        if not first_value:
            continue
        if first_row and _normalize_header(first_value) in _WATCHLIST_HEADERS:
            first_row = False
            continue
        first_row = False
        normalized = first_value.upper()
        if normalized in seen:
            skipped_count += 1
            continue
        seen.add(normalized)
        tickers.append(normalized)
    return ParsedWatchlistImport(tickers=tickers, skipped_count=skipped_count)


def parse_portfolio_import(content: str) -> ParsedPortfolioImport:
    """Parse pasted portfolio content into normalized position rows."""
    delimiter = _detect_delimiter(content)
    header_map: dict[str, int] | None = None
    positions: list[ParsedPortfolioPosition] = []
    errors: list[ParsedImportError] = []

    for line_number, raw_line, cells in _iter_rows(content, delimiter):
        if header_map is None:
            maybe_header_map = _resolve_portfolio_header_map(cells)
            if maybe_header_map is not None:
                header_map = maybe_header_map
                continue
            header_map = {"ticker": 0, "quantity": 1, "average_cost": 2}

        extracted = _extract_portfolio_fields(cells, header_map)
        ticker = extracted["ticker"].strip().upper()
        quantity_text = extracted["quantity"].strip()
        average_cost_text = extracted["average_cost"].strip()

        if not ticker:
            errors.append(ParsedImportError(line_number, "Ticker is required.", raw_line))
            continue
        try:
            quantity = float(quantity_text)
        except ValueError:
            errors.append(ParsedImportError(line_number, "Quantity must be a number.", raw_line))
            continue
        if quantity <= 0:
            errors.append(ParsedImportError(line_number, "Quantity must be greater than 0.", raw_line))
            continue
        try:
            average_cost = float(average_cost_text)
        except ValueError:
            errors.append(ParsedImportError(line_number, "Average cost must be a number.", raw_line))
            continue
        if average_cost < 0:
            errors.append(ParsedImportError(line_number, "Average cost must be 0 or greater.", raw_line))
            continue

        positions.append(ParsedPortfolioPosition(
            ticker=ticker,
            quantity=quantity,
            average_cost=average_cost,
        ))

    return ParsedPortfolioImport(positions=positions, errors=errors)


def _dedupe_tickers(tokens: list[str]) -> ParsedWatchlistImport:
    seen: set[str] = set()
    tickers: list[str] = []
    skipped_count = 0
    for token in tokens:
        normalized = token.strip().upper()
        if not normalized:
            continue
        if normalized in seen:
            skipped_count += 1
            continue
        seen.add(normalized)
        tickers.append(normalized)
    return ParsedWatchlistImport(tickers=tickers, skipped_count=skipped_count)


def _detect_delimiter(content: str) -> str | None:
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if "\t" in raw_line:
            return "\t"
        if "," in raw_line:
            return ","
    return None


def _iter_rows(content: str, delimiter: str | None):
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        if not raw_line.strip():
            continue
        if delimiter is None:
            cells = re.split(r"\s+", raw_line.strip())
        else:
            cells = next(csv.reader([raw_line], delimiter=delimiter))
        yield line_number, raw_line, [cell.strip() for cell in cells]


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _resolve_portfolio_header_map(cells: list[str]) -> dict[str, int] | None:
    header_map: dict[str, int] = {}
    for index, cell in enumerate(cells):
        normalized = _normalize_header(cell)
        for canonical, aliases in _PORTFOLIO_HEADER_ALIASES.items():
            if normalized in aliases and canonical not in header_map:
                header_map[canonical] = index
                break
    if {"ticker", "quantity", "average_cost"}.issubset(header_map):
        return header_map
    return None


def _extract_portfolio_fields(cells: list[str], header_map: dict[str, int]) -> dict[str, str]:
    extracted: dict[str, str] = {}
    for field, index in header_map.items():
        extracted[field] = cells[index] if index < len(cells) else ""
    return extracted
