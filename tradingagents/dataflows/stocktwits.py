"""StockTwits public symbol-stream fetcher.

StockTwits exposes a per-symbol message stream at
``api.stocktwits.com/api/2/streams/symbol/{ticker}.json`` that requires no
API key, no OAuth, and no registration. Each message includes a
user-labeled sentiment field (``Bullish``/``Bearish``/null), the message
body, timestamp, and posting user.

The function is deliberately self-contained: short timeout, graceful
degradation on any HTTP or parse failure, and a string return type so
the calling agent gets a uniform interface regardless of whether the
network call succeeded.
"""

from __future__ import annotations

import http.client
import json
import logging
from urllib.request import Request, urlopen

from .market_profiles import get_market_profile, is_china_a_profile
from .provenance import record_data_fetch, summarize_request

logger = logging.getLogger(__name__)

_API = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
_UA = "tradingagents/0.2 (+https://github.com/TauricResearch/TradingAgents)"


def fetch_stocktwits_messages(ticker: str, limit: int = 30, timeout: float = 10.0) -> str:
    """Fetch recent StockTwits messages for ``ticker`` and return them as a
    formatted plaintext block ready for prompt injection.

    Returns a placeholder string when the endpoint is unreachable, the
    symbol has no messages, or the response shape is unexpected — the
    caller never has to special-case None or exceptions.
    """
    request_label = summarize_request("fetch_stocktwits_messages", ticker)
    if is_china_a_profile(get_market_profile()):
        record_data_fetch(
            method="fetch_stocktwits_messages",
            category="social_sentiment",
            request_label=request_label,
            status="not_applicable",
            required=False,
            configured_sources=["stocktwits"],
            attempted_sources=[],
            actual_source=None,
            fallback_used=False,
            incomplete=False,
            detail="Disabled for cn_a market profile.",
            warning=None,
        )
        return "<stocktwits disabled for cn_a market profile>"

    url = _API.format(ticker=ticker.upper())
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
        # OSError covers URLError/TimeoutError/connection resets; HTTPException
        # covers chunked-transfer errors (IncompleteRead/BadStatusLine, #1024).
        logger.warning("StockTwits fetch failed for %s: %s", ticker, exc)
        record_data_fetch(
            method="fetch_stocktwits_messages",
            category="social_sentiment",
            request_label=request_label,
            status="unavailable",
            required=True,
            configured_sources=["stocktwits"],
            attempted_sources=["stocktwits"],
            actual_source=None,
            fallback_used=False,
            incomplete=True,
            detail=str(exc),
            warning=f"StockTwits sentiment data was unavailable for {ticker.upper()}.",
        )
        return f"<stocktwits unavailable: {type(exc).__name__}>"

    messages = data.get("messages", []) if isinstance(data, dict) else []
    if not messages:
        record_data_fetch(
            method="fetch_stocktwits_messages",
            category="social_sentiment",
            request_label=request_label,
            status="unavailable",
            required=True,
            configured_sources=["stocktwits"],
            attempted_sources=["stocktwits"],
            actual_source=None,
            fallback_used=False,
            incomplete=True,
            detail=f"No StockTwits messages found for ${ticker.upper()}",
            warning=f"StockTwits returned no recent messages for {ticker.upper()}.",
        )
        return f"<no StockTwits messages found for ${ticker.upper()}>"

    lines = []
    bullish = bearish = unlabeled = 0
    for m in messages[:limit]:
        created = m.get("created_at", "")
        user = (m.get("user") or {}).get("username", "?")
        entities = m.get("entities") or {}
        sentiment_obj = entities.get("sentiment") or {}
        sentiment = sentiment_obj.get("basic") if isinstance(sentiment_obj, dict) else None
        body = (m.get("body") or "").replace("\n", " ").strip()
        if len(body) > 280:
            body = body[:280] + "…"

        if sentiment == "Bullish":
            bullish += 1
            tag = "Bullish"
        elif sentiment == "Bearish":
            bearish += 1
            tag = "Bearish"
        else:
            unlabeled += 1
            tag = "no-label"
        lines.append(f"[{created} · @{user} · {tag}] {body}")

    total = bullish + bearish + unlabeled
    bull_pct = round(100 * bullish / total) if total else 0
    bear_pct = round(100 * bearish / total) if total else 0
    summary = (
        f"Bullish: {bullish} ({bull_pct}%) · "
        f"Bearish: {bearish} ({bear_pct}%) · "
        f"Unlabeled: {unlabeled} · "
        f"Total: {total} most-recent messages"
    )
    rendered = summary + "\n\n" + "\n".join(lines)
    record_data_fetch(
        method="fetch_stocktwits_messages",
        category="social_sentiment",
        request_label=request_label,
        status="success",
        required=True,
        configured_sources=["stocktwits"],
        attempted_sources=["stocktwits"],
        actual_source="stocktwits",
        fallback_used=False,
        incomplete=False,
        detail=summary,
        warning=None,
        result=rendered,
    )
    return rendered
