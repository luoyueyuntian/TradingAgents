"""Scheduled automation helpers for the TradingAgents web workspace."""

from __future__ import annotations

import datetime
import threading
import uuid

from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import load_settings, save_settings

from .runner import get_execution_mode, get_service
from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AutomationRule,
    AutomationRuleCreate,
    AutomationRuleToggleUpdate,
    AutomationRunResponse,
)

_CRYPTO_TICKER_HINTS = ("BTC", "ETH", "USDT", "BNB", "SOL", "XRP", "DOGE", "ADA", "-USD")
_WEEKDAY_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}
_AUTOMATION_LOCK = threading.Lock()


def _now(now: datetime.datetime | None = None) -> datetime.datetime:
    return now or datetime.datetime.now()


def _now_iso(now: datetime.datetime | None = None) -> str:
    return _now(now).isoformat()


def _infer_asset_type(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if any(hint in normalized for hint in _CRYPTO_TICKER_HINTS):
        return "crypto"
    return "stock"


def _analysis_response_from_run(run) -> AnalysisResponse:
    return AnalysisResponse(
        run_id=run.run_id,
        status=run.status,
        ticker=run.ticker,
        date=run.date,
    )


def _load_watchlist_tickers_from_settings(tenant_id: str | None = None) -> list[str]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("watchlist", {}).get("tickers", [])
    if not isinstance(raw, list):
        return []

    tickers: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            normalized = item.strip().upper()
        elif isinstance(item, dict) and isinstance(item.get("ticker"), str):
            normalized = str(item["ticker"]).strip().upper()
        else:
            continue
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        tickers.append(normalized)
    return tickers


def _load_automation_rules_raw(tenant_id: str | None = None) -> list[AutomationRule]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("automations", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    rules: list[AutomationRule] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            rules.append(AutomationRule.model_validate(item))
        except Exception:
            continue
    return rules


def _save_automation_rules_raw(tenant_id: str | None, rules: list[AutomationRule]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = load_settings(path=settings_path)
    bucket = existing.get("automations", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [
        rule.model_dump(exclude_none=True, exclude={"next_run_at"})
        for rule in rules
    ]
    existing["automations"] = bucket
    save_settings(existing, path=settings_path)


def _combine_date_and_time(day: datetime.date, time_of_day: str) -> datetime.datetime:
    hour, minute = [int(part) for part in time_of_day.split(":", 1)]
    return datetime.datetime.combine(day, datetime.time(hour=hour, minute=minute))


def _parse_last_triggered(rule: AutomationRule) -> datetime.datetime | None:
    if not rule.last_triggered_at:
        return None
    try:
        return datetime.datetime.fromisoformat(rule.last_triggered_at)
    except ValueError:
        return None


def _current_slot(rule: AutomationRule, now: datetime.datetime) -> datetime.datetime | None:
    if rule.cadence == "daily":
        slot = _combine_date_and_time(now.date(), rule.time_of_day)
        return slot if now >= slot else None

    weekday = _WEEKDAY_INDEX.get(rule.weekday or "")
    if weekday is None or now.weekday() != weekday:
        return None
    slot = _combine_date_and_time(now.date(), rule.time_of_day)
    return slot if now >= slot else None


def _next_run_at(rule: AutomationRule, now: datetime.datetime) -> str | None:
    if not rule.enabled:
        return None

    if rule.cadence == "daily":
        today_slot = _combine_date_and_time(now.date(), rule.time_of_day)
        next_slot = today_slot if now < today_slot else today_slot + datetime.timedelta(days=1)
        return next_slot.isoformat()

    weekday = _WEEKDAY_INDEX.get(rule.weekday or "")
    if weekday is None:
        return None
    today_slot = _combine_date_and_time(now.date(), rule.time_of_day)
    days_ahead = (weekday - now.weekday()) % 7
    if days_ahead == 0 and now >= today_slot:
        days_ahead = 7
    if days_ahead == 0:
        next_slot = today_slot
    else:
        next_slot = _combine_date_and_time(now.date() + datetime.timedelta(days=days_ahead), rule.time_of_day)
    return next_slot.isoformat()


def _decorate_rule(rule: AutomationRule, now: datetime.datetime | None = None) -> AutomationRule:
    resolved_now = _now(now)
    return rule.model_copy(update={"next_run_at": _next_run_at(rule, resolved_now)})


def list_automation_rules(tenant_id: str | None = None, *, now: datetime.datetime | None = None) -> list[AutomationRule]:
    resolved_now = _now(now)
    return [_decorate_rule(rule, resolved_now) for rule in _load_automation_rules_raw(tenant_id)]


def create_automation_rule(payload: AutomationRuleCreate, tenant_id: str | None = None, *, now: datetime.datetime | None = None) -> AutomationRule:
    timestamp = _now_iso(now)
    rule = AutomationRule(
        id=str(uuid.uuid4()),
        name=payload.name,
        enabled=payload.enabled,
        source=payload.source,
        tickers=payload.tickers,
        cadence=payload.cadence,
        weekday=payload.weekday,
        time_of_day=payload.time_of_day,
        created_at=timestamp,
        updated_at=timestamp,
        analysis_config=payload.analysis_config,
    )
    rules = _load_automation_rules_raw(tenant_id)
    rules.append(rule)
    _save_automation_rules_raw(tenant_id, rules)
    return _decorate_rule(rule, _now(now))


def delete_automation_rule(rule_id: str, tenant_id: str | None = None) -> int:
    rules = _load_automation_rules_raw(tenant_id)
    kept = [rule for rule in rules if rule.id != rule_id]
    deleted = 1 if len(kept) != len(rules) else 0
    if deleted:
        _save_automation_rules_raw(tenant_id, kept)
    return deleted


def update_automation_rule_enabled(
    rule_id: str,
    payload: AutomationRuleToggleUpdate,
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
) -> AutomationRule | None:
    rules = _load_automation_rules_raw(tenant_id)
    updated_rule: AutomationRule | None = None
    timestamp = _now_iso(now)
    for index, rule in enumerate(rules):
        if rule.id != rule_id:
            continue
        updated_rule = rule.model_copy(update={
            "enabled": payload.enabled,
            "updated_at": timestamp,
        })
        rules[index] = updated_rule
        break
    if updated_rule is None:
        return None
    _save_automation_rules_raw(tenant_id, rules)
    return _decorate_rule(updated_rule, _now(now))


def _resolve_rule_tickers(rule: AutomationRule, tenant_id: str | None = None) -> list[str]:
    if rule.source == "watchlist":
        return _load_watchlist_tickers_from_settings(tenant_id)
    return list(rule.tickers)


def _build_analysis_request_for_rule(rule: AutomationRule, ticker: str, run_date: str) -> AnalysisRequest:
    config = rule.analysis_config
    return AnalysisRequest(
        ticker=ticker,
        date=run_date,
        asset_type=_infer_asset_type(ticker),
        analysts=config.analysts,
        llm_provider=config.llm_provider,
        deep_think_model=config.deep_think_model,
        quick_think_model=config.quick_think_model,
        research_depth=config.research_depth,
        output_language=config.output_language,
        market_profile=config.market_profile,
        max_risk_discuss_rounds=config.max_risk_discuss_rounds,
        max_recur_limit=config.max_recur_limit,
        checkpoint_enabled=config.checkpoint_enabled,
        benchmark_ticker=config.benchmark_ticker,
        backend_url=config.backend_url,
        temperature=config.temperature,
        google_thinking_level=config.google_thinking_level,
        openai_reasoning_effort=config.openai_reasoning_effort,
        anthropic_effort=config.anthropic_effort,
    )


def _queue_rule_runs(
    rule: AutomationRule,
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
    start_worker: bool | None = None,
) -> tuple[AutomationRule, AutomationRunResponse]:
    resolved_now = _now(now)
    date_str = resolved_now.date().isoformat()
    tickers = _resolve_rule_tickers(rule, tenant_id)
    service = get_service(tenant_id)
    settings = service.load_tenant_settings()
    should_start_worker = (get_execution_mode() != "external_worker") if start_worker is None else start_worker
    runs: list[AnalysisResponse] = []
    for ticker in tickers:
        req = _build_analysis_request_for_rule(rule, ticker, date_str)
        run = service.create_run(req, start_worker=should_start_worker, settings=settings)
        runs.append(_analysis_response_from_run(run))

    updated_rule = rule.model_copy(update={
        "last_triggered_at": resolved_now.isoformat(),
        "last_queued_count": len(runs),
        "updated_at": resolved_now.isoformat(),
    })
    response = AutomationRunResponse(
        rule_id=rule.id,
        source=rule.source,
        tickers=tickers,
        created_count=len(runs),
        runs=runs,
    )
    return updated_rule, response


def run_automation_rule_now(
    rule_id: str,
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
    start_worker: bool | None = None,
) -> AutomationRunResponse | None:
    rules = _load_automation_rules_raw(tenant_id)
    resolved_now = _now(now)
    for index, rule in enumerate(rules):
        if rule.id != rule_id:
            continue
        updated_rule, response = _queue_rule_runs(rule, tenant_id, now=resolved_now, start_worker=start_worker)
        rules[index] = updated_rule
        _save_automation_rules_raw(tenant_id, rules)
        return response
    return None


def process_due_automation_rules(
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
    start_worker: bool | None = None,
) -> int:
    resolved_now = _now(now)
    queued_total = 0
    with _AUTOMATION_LOCK:
        rules = _load_automation_rules_raw(tenant_id)
        changed = False
        for index, rule in enumerate(rules):
            if not rule.enabled:
                continue
            slot = _current_slot(rule, resolved_now)
            if slot is None:
                continue
            last_triggered = _parse_last_triggered(rule)
            if last_triggered is not None and last_triggered >= slot:
                continue
            updated_rule, response = _queue_rule_runs(rule, tenant_id, now=resolved_now, start_worker=start_worker)
            rules[index] = updated_rule
            queued_total += response.created_count
            changed = True
        if changed:
            _save_automation_rules_raw(tenant_id, rules)
    return queued_total
