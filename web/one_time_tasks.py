"""Persistence helpers for tenant-scoped one-time analysis tasks."""

from __future__ import annotations

import datetime
import uuid
from copy import deepcopy

from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import load_settings, save_settings

from .schemas import (
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
