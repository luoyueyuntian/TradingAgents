"""Structured per-run data-fetch provenance for logs, APIs, and UI surfaces."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from copy import deepcopy
import json
from typing import Any, Callable

_audit_var: ContextVar[list[dict[str, Any]]] = ContextVar(
    "tradingagents_data_fetch_audit",
    default=None,  # type: ignore[arg-type]
)
_event_sink_var: ContextVar[Callable[[dict[str, Any]], None] | None] = ContextVar(
    "tradingagents_data_fetch_event_sink",
    default=None,
)

logger = logging.getLogger(__name__)

_SENTINEL = object()

METHOD_ITEM_LABELS = {
    "get_stock_data": "Market Price Data",
    "get_indicators": "Technical Indicators",
    "get_verified_market_snapshot": "Verified Market Snapshot",
    "get_news": "Company News",
    "get_global_news": "Global News",
    "get_insider_transactions": "Insider Transactions",
    "get_macro_indicators": "Macro Indicators",
    "get_prediction_markets": "Market Signals",
    "get_fundamentals": "Fundamentals",
    "get_balance_sheet": "Balance Sheet",
    "get_cashflow": "Cash Flow",
    "get_income_statement": "Income Statement",
    "fetch_stocktwits_messages": "StockTwits Sentiment",
    "fetch_reddit_posts": "Reddit Sentiment",
}


def _ensure() -> list[dict[str, Any]]:
    audit = _audit_var.get(_SENTINEL)
    if audit is _SENTINEL:
        audit = []
        _audit_var.set(audit)
    return audit


def reset_data_fetch_audit() -> None:
    """Clear the current context-local data-fetch audit trail."""
    _audit_var.set([])


def install_data_fetch_event_sink(sink):
    """Install one context-local callback that receives each recorded fetch entry."""
    return _event_sink_var.set(sink)


def reset_data_fetch_event_sink(token) -> None:
    """Restore the previous context-local data-fetch event sink."""
    _event_sink_var.reset(token)


def get_data_fetch_audit() -> list[dict[str, Any]]:
    """Return a deep-copied snapshot of the current audit trail."""
    return deepcopy(_ensure())


def item_label_for_method(method: str) -> str:
    """Return a stable human-facing label for one data-fetch method."""
    return METHOD_ITEM_LABELS.get(method, method.replace("_", " ").title())


def summarize_request(method: str, *args, **kwargs) -> str:
    """Create a short request label for UI and terminal summaries."""
    if method == "get_stock_data" and len(args) >= 3:
        return f"{args[0]} · {args[1]} → {args[2]}"
    if method == "get_indicators" and len(args) >= 4:
        return f"{args[0]} · {args[1]} · {args[2]}"
    if method == "get_verified_market_snapshot" and len(args) >= 2:
        look_back = args[2] if len(args) >= 3 else kwargs.get("look_back_days", 30)
        return f"{args[0]} · {args[1]} · {look_back} rows"
    if method == "get_news" and len(args) >= 3:
        return f"{args[0]} · {args[1]} → {args[2]}"
    if method == "get_global_news" and len(args) >= 1:
        look_back = args[1] if len(args) >= 2 and args[1] is not None else "default"
        limit = args[2] if len(args) >= 3 and args[2] is not None else "default"
        return f"{args[0]} · {look_back}d · limit {limit}"
    if method == "get_insider_transactions" and args:
        return str(args[0])
    if method == "get_macro_indicators" and len(args) >= 2:
        look_back = args[2] if len(args) >= 3 and args[2] is not None else "default"
        return f"{args[0]} · {args[1]} · {look_back}d"
    if method == "get_prediction_markets" and args:
        limit = args[1] if len(args) >= 2 else kwargs.get("limit", "default")
        return f"{args[0]} · limit {limit}"
    if method == "get_fundamentals" and len(args) >= 2:
        return f"{args[0]} · {args[1]}"
    if method in {"get_balance_sheet", "get_cashflow", "get_income_statement"} and args:
        freq = args[1] if len(args) >= 2 else kwargs.get("freq", "quarterly")
        curr_date = args[2] if len(args) >= 3 else kwargs.get("curr_date")
        return " · ".join(part for part in (str(args[0]), str(freq), str(curr_date or "")) if part)
    if method in {"fetch_stocktwits_messages", "fetch_reddit_posts"} and args:
        return str(args[0]).upper()
    joined = [str(arg) for arg in args[:3] if arg not in (None, "")]
    return " · ".join(joined)


def summarize_result(result: Any, *, max_chars: int = 320) -> tuple[str, str]:
    """Return a compact ``(kind, preview)`` summary for one tool result."""
    if result is None:
        return "none", ""

    if hasattr(result, "shape") and hasattr(result, "columns"):
        try:
            rows = getattr(result, "shape")[0]
            cols = list(getattr(result, "columns"))[:6]
            cols_preview = ", ".join(str(col) for col in cols)
            return "dataframe", f"rows={rows} cols=[{cols_preview}]"
        except Exception:
            pass

    if isinstance(result, str):
        kind = "text"
        text = result.strip()
    elif isinstance(result, dict):
        kind = "dict"
        text = json.dumps(result, ensure_ascii=False, sort_keys=True)
    elif isinstance(result, (list, tuple)):
        kind = type(result).__name__
        preview_payload = list(result[:3]) if isinstance(result, tuple) else result[:3]
        text = f"len={len(result)} {json.dumps(preview_payload, ensure_ascii=False)}"
    else:
        kind = type(result).__name__.lower()
        text = str(result).strip()

    if len(text) > max_chars:
        text = text[: max_chars - 1] + "…"
    return kind, text


def record_data_fetch(
    *,
    method: str,
    category: str,
    request_label: str,
    status: str,
    required: bool,
    configured_sources: list[str] | None = None,
    attempted_sources: list[str] | None = None,
    actual_source: str | None = None,
    fallback_used: bool = False,
    incomplete: bool = False,
    detail: str | None = None,
    warning: str | None = None,
    result: Any = _SENTINEL,
) -> dict[str, Any]:
    """Append one structured audit entry and return a copy."""
    audit = _ensure()
    result_kind = ""
    result_preview = ""
    if result is not _SENTINEL:
        result_kind, result_preview = summarize_result(result)
    entry = {
        "key": f"{method}#{len(audit) + 1}",
        "method": method,
        "item": item_label_for_method(method),
        "category": category,
        "request_label": request_label,
        "status": status,
        "required": bool(required),
        "actual_source": actual_source,
        "configured_sources": list(configured_sources or []),
        "attempted_sources": list(attempted_sources or []),
        "fallback_used": bool(fallback_used),
        "incomplete": bool(incomplete),
        "detail": detail,
        "warning": warning,
        "result_kind": result_kind,
        "result_preview": result_preview,
    }
    audit.append(entry)
    entry_copy = deepcopy(entry)
    sink = _event_sink_var.get()
    if callable(sink):
        try:
            sink(deepcopy(entry_copy))
        except Exception:
            logger.warning("Failed to emit data-fetch event for %s", method, exc_info=True)
    return entry_copy


def build_data_warnings(entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Derive flattened warning payloads from recorded data-fetch entries."""
    warnings: list[dict[str, str]] = []
    for entry in entries:
        warning = str(entry.get("warning") or "").strip()
        if not warning:
            continue
        warnings.append(
            {
                "key": str(entry.get("key") or ""),
                "severity": "warning" if entry.get("required") else "info",
                "message": warning,
            }
        )
    return warnings
