"""Persistence helpers for tenant-scoped one-time analysis tasks."""

from __future__ import annotations

import datetime
import uuid
from copy import deepcopy

from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import load_settings, save_settings

from .runner import TERMINAL_RUN_STATUSES, get_service
from .schemas import (
    AnalysisRequest,
    ManualStockSelection,
    OneTimeTask,
    OneTimeTaskCreate,
    OneTimeTaskGroupSnapshot,
    OneTimeTaskPage,
    OneTimeTaskSelectionSnapshot,
    OneTimeTaskUpdate,
)

try:  # pragma: no cover - fallback only matters while the stock-group helper is absent
    from .stock_groups import list_stock_groups
except ImportError:  # pragma: no cover
    def list_stock_groups(tenant_id: str | None = None):  # type: ignore[no-redef]
        return []


def _now(now: datetime.datetime | None = None) -> datetime.datetime:
    return now or datetime.datetime.now()


def _now_iso(now: datetime.datetime | None = None) -> str:
    return _now(now).isoformat(timespec="seconds")


def _infer_asset_type(ticker: str) -> str:
    normalized = ticker.strip().upper()
    return "crypto" if "-USD" in normalized else "stock"


def _build_task_run_settings(task: OneTimeTask, tenant_settings: dict | None) -> dict:
    settings = deepcopy(tenant_settings) if isinstance(tenant_settings, dict) else {}

    llm_settings: dict[str, object] = {}
    if task.analysis_config.llm_provider:
        llm_settings["provider"] = task.analysis_config.llm_provider
    if task.analysis_config.quick_think_model is not None:
        llm_settings["quick_think_model"] = task.analysis_config.quick_think_model
    if task.analysis_config.deep_think_model is not None:
        llm_settings["deep_think_model"] = task.analysis_config.deep_think_model
    if task.analysis_config.backend_url is not None:
        llm_settings["backend_url"] = task.analysis_config.backend_url
    if task.analysis_config.temperature is not None:
        llm_settings["temperature"] = task.analysis_config.temperature
    if task.analysis_config.google_thinking_level is not None:
        llm_settings["google_thinking_level"] = task.analysis_config.google_thinking_level
    if task.analysis_config.openai_reasoning_effort is not None:
        llm_settings["openai_reasoning_effort"] = task.analysis_config.openai_reasoning_effort
    if task.analysis_config.anthropic_effort is not None:
        llm_settings["anthropic_effort"] = task.analysis_config.anthropic_effort

    analysis_settings: dict[str, object] = {
        "output_language": task.analysis_config.output_language,
        "research_depth": task.analysis_config.research_depth,
    }
    if task.analysis_config.market_profile is not None:
        analysis_settings["market_profile"] = task.analysis_config.market_profile
    if task.analysis_config.max_risk_discuss_rounds is not None:
        analysis_settings["max_risk_discuss_rounds"] = task.analysis_config.max_risk_discuss_rounds
    if task.analysis_config.max_recur_limit is not None:
        analysis_settings["max_recur_limit"] = task.analysis_config.max_recur_limit
    if task.analysis_config.checkpoint_enabled is not None:
        analysis_settings["checkpoint_enabled"] = task.analysis_config.checkpoint_enabled
    if task.analysis_config.benchmark_ticker is not None:
        analysis_settings["benchmark_ticker"] = task.analysis_config.benchmark_ticker

    settings["llm"] = llm_settings
    settings["analysis"] = analysis_settings
    return settings


def _load_settings_for_update(settings_path) -> dict:
    settings = load_settings(path=settings_path)
    return deepcopy(settings) if isinstance(settings, dict) else {}


def _load_one_time_tasks_raw(tenant_id: str | None = None) -> list[OneTimeTask]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw_bucket = settings.get("one_time_tasks", {}) if isinstance(settings, dict) else {}
    raw_items = raw_bucket.get("items", []) if isinstance(raw_bucket, dict) else []
    if not isinstance(raw_items, list):
        return []
    tasks: list[OneTimeTask] = []
    for item in raw_items:
        if isinstance(item, dict):
            try:
                tasks.append(OneTimeTask.model_validate(item))
            except Exception:
                continue
    return tasks


def _save_one_time_tasks_raw(tenant_id: str | None, tasks: list[OneTimeTask]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("one_time_tasks", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [task.model_dump() for task in tasks]
    existing["one_time_tasks"] = bucket
    save_settings(existing, path=settings_path)


def _load_watchlist_snapshot(tenant_id: str | None = None) -> list[str]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw_items = settings.get("watchlist", {}).get("tickers", []) if isinstance(settings, dict) else []
    if not isinstance(raw_items, list):
        return []
    tickers: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        ticker = ""
        if isinstance(item, str):
            ticker = item.strip().upper()
        elif isinstance(item, dict) and isinstance(item.get("ticker"), str):
            ticker = str(item["ticker"]).strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        tickers.append(ticker)
    return tickers


def _build_selection_snapshot(
    payload: OneTimeTaskCreate | OneTimeTaskUpdate,
    tenant_id: str | None = None,
) -> OneTimeTaskSelectionSnapshot:
    group_map = {group.id: group for group in list_stock_groups(tenant_id)}
    manual_stocks = [ManualStockSelection.model_validate(stock) for stock in payload.manual_stocks]
    group_snapshots: list[OneTimeTaskGroupSnapshot] = []
    resolved_tickers: list[str] = []
    seen: set[str] = set()

    def add_ticker(value: str) -> None:
        normalized = value.strip().upper()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        resolved_tickers.append(normalized)

    for stock in manual_stocks:
        add_ticker(stock.symbol)

    for group_id in payload.group_ids:
        group = group_map.get(group_id)
        if group is None:
            continue
        snapshot = OneTimeTaskGroupSnapshot(id=group.id, name=group.name, tickers=list(group.tickers))
        group_snapshots.append(snapshot)
        for ticker in snapshot.tickers:
            add_ticker(ticker)

    watchlist_snapshot = _load_watchlist_snapshot(tenant_id) if payload.include_watchlist else []
    for ticker in watchlist_snapshot:
        add_ticker(ticker)

    if not resolved_tickers:
        raise ValueError("resolved ticker set must not be empty")

    return OneTimeTaskSelectionSnapshot(
        manual_stocks=manual_stocks,
        group_snapshots=group_snapshots,
        include_watchlist=payload.include_watchlist,
        watchlist_snapshot=watchlist_snapshot,
        resolved_tickers=resolved_tickers,
    )


def create_one_time_task(
    payload: OneTimeTaskCreate,
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
) -> OneTimeTask:
    tasks = _load_one_time_tasks_raw(tenant_id)
    snapshot = _build_selection_snapshot(payload, tenant_id)
    timestamp = _now_iso(now)
    task = OneTimeTask(
        id=str(uuid.uuid4()),
        name=payload.name,
        status="scheduled",
        scheduled_for=payload.scheduled_for,
        analysis_date=payload.analysis_date,
        selection_snapshot=snapshot,
        analysis_config=payload.analysis_config,
        created_at=timestamp,
        updated_at=timestamp,
    )
    tasks.append(task)
    _save_one_time_tasks_raw(tenant_id, tasks)
    return task


def update_one_time_task(
    task_id: str,
    payload: OneTimeTaskUpdate,
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
) -> OneTimeTask | None:
    tasks = _load_one_time_tasks_raw(tenant_id)
    timestamp = _now_iso(now)
    for index, task in enumerate(tasks):
        if task.id != task_id:
            continue
        if task.status != "scheduled":
            raise ValueError("Only scheduled tasks can be edited")
        snapshot = _build_selection_snapshot(payload, tenant_id)
        updated = task.model_copy(
            update={
                "name": payload.name,
                "scheduled_for": payload.scheduled_for,
                "analysis_date": payload.analysis_date,
                "selection_snapshot": snapshot,
                "analysis_config": payload.analysis_config,
                "updated_at": timestamp,
            }
        )
        tasks[index] = updated
        _save_one_time_tasks_raw(tenant_id, tasks)
        return updated
    return None


def cancel_one_time_task(
    task_id: str,
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
) -> OneTimeTask | None:
    tasks = _load_one_time_tasks_raw(tenant_id)
    timestamp = _now_iso(now)
    for index, task in enumerate(tasks):
        if task.id != task_id:
            continue
        if task.status != "scheduled":
            raise ValueError("Only scheduled tasks can be cancelled")
        updated = task.model_copy(update={"status": "cancelled", "updated_at": timestamp})
        tasks[index] = updated
        _save_one_time_tasks_raw(tenant_id, tasks)
        return updated
    return None


def get_one_time_task_page(
    tenant_id: str | None = None,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> OneTimeTaskPage:
    tasks = _load_one_time_tasks_raw(tenant_id)
    if status is not None:
        normalized_status = status.strip().lower()
        tasks = [task for task in tasks if task.status == normalized_status]
    tasks.sort(key=lambda task: (task.scheduled_for, task.created_at), reverse=True)
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return OneTimeTaskPage(items=tasks[start:end], page=page, page_size=page_size, total_count=len(tasks))


def refresh_one_time_tasks(
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
) -> None:
    tasks = _load_one_time_tasks_raw(tenant_id)
    service = get_service(tenant_id)
    timestamp = _now_iso(now)
    changed = False

    for index, task in enumerate(tasks):
        if task.status not in {"queued", "running"} or not task.run_ids:
            continue

        statuses = {str(run.status) for run in (service.get_run(run_id) for run_id in task.run_ids) if run is not None}
        next_status = task.status
        if "running" in statuses:
            next_status = "running"
        elif statuses and statuses <= TERMINAL_RUN_STATUSES:
            next_status = "completed"
        elif "queued" in statuses:
            next_status = "queued"

        if next_status == task.status and (next_status != "completed" or task.completed_at is not None):
            continue

        tasks[index] = task.model_copy(
            update={
                "status": next_status,
                "completed_at": timestamp if next_status == "completed" else task.completed_at,
                "updated_at": timestamp,
            }
        )
        changed = True

    if changed:
        _save_one_time_tasks_raw(tenant_id, tasks)


def process_due_one_time_tasks(
    tenant_id: str | None = None,
    *,
    now: datetime.datetime | None = None,
    start_worker: bool = True,
) -> int:
    tasks = _load_one_time_tasks_raw(tenant_id)
    service = get_service(tenant_id)
    resolved_now = _now(now)
    timestamp = _now_iso(resolved_now)
    current_slot = resolved_now.strftime("%Y-%m-%d %H:%M")
    changed = False
    queued_total = 0
    tenant_settings = service.load_tenant_settings()

    for index, task in enumerate(tasks):
        if task.status != "scheduled":
            continue

        if task.scheduled_for < current_slot:
            if task.triggered_at is not None:
                continue
            tasks[index] = task.model_copy(update={"status": "missed", "updated_at": timestamp})
            changed = True
            continue

        if task.scheduled_for != current_slot:
            continue

        run_ids: list[str] = []
        last_error: str | None = None
        settings = _build_task_run_settings(task, tenant_settings)
        for ticker in task.selection_snapshot.resolved_tickers:
            request = AnalysisRequest(
                ticker=ticker,
                date=task.analysis_date,
                asset_type=_infer_asset_type(ticker),
                analysts=task.analysis_config.analysts,
                llm_provider=task.analysis_config.llm_provider,
                deep_think_model=task.analysis_config.deep_think_model,
                quick_think_model=task.analysis_config.quick_think_model,
                research_depth=task.analysis_config.research_depth,
                output_language=task.analysis_config.output_language,
                market_profile=task.analysis_config.market_profile,
                max_risk_discuss_rounds=task.analysis_config.max_risk_discuss_rounds,
                max_recur_limit=task.analysis_config.max_recur_limit,
                checkpoint_enabled=task.analysis_config.checkpoint_enabled,
                benchmark_ticker=task.analysis_config.benchmark_ticker,
                backend_url=task.analysis_config.backend_url,
                temperature=task.analysis_config.temperature,
                google_thinking_level=task.analysis_config.google_thinking_level,
                openai_reasoning_effort=task.analysis_config.openai_reasoning_effort,
                anthropic_effort=task.analysis_config.anthropic_effort,
            )
            try:
                run = service.create_run(request, start_worker=start_worker, settings=settings)
            except Exception as exc:
                last_error = str(exc)
                continue
            run_ids.append(run.run_id)

        status = "queued" if run_ids else "scheduled"
        triggered_at = timestamp
        tasks[index] = task.model_copy(
            update={
                "status": status,
                "triggered_at": triggered_at,
                "updated_at": timestamp,
                "last_queued_count": len(run_ids),
                "last_error": last_error,
                "run_ids": run_ids,
            }
        )
        queued_total += len(run_ids)
        changed = True

    if changed:
        _save_one_time_tasks_raw(tenant_id, tasks)
    return queued_total
