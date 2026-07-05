"""Persistence helpers for tenant-scoped static stock groups."""

from __future__ import annotations

import datetime
import uuid
from copy import deepcopy

from pydantic import ValidationError

from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import load_settings, save_settings

from .schemas import StockGroup, StockGroupCreate, StockGroupUpdate


def _load_stock_groups_raw(tenant_id: str | None = None) -> list[StockGroup]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw_groups = {}
    if isinstance(settings, dict):
        raw_groups = settings.get("stock_groups", {})
    raw_items = raw_groups.get("items", []) if isinstance(raw_groups, dict) else []
    if not isinstance(raw_items, list):
        return []
    groups: list[StockGroup] = []
    for item in raw_items:
        if isinstance(item, dict):
            try:
                groups.append(StockGroup.model_validate(item))
            except ValidationError:
                continue
    return groups


def _save_stock_groups_raw(tenant_id: str | None, groups: list[StockGroup]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    settings = load_settings(path=settings_path)
    existing = deepcopy(settings) if isinstance(settings, dict) else {}
    bucket = existing.get("stock_groups", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [group.model_dump() for group in groups]
    existing["stock_groups"] = bucket
    save_settings(existing, path=settings_path)


def list_stock_groups(tenant_id: str | None = None) -> list[StockGroup]:
    return _load_stock_groups_raw(tenant_id)


def create_stock_group(payload: StockGroupCreate, tenant_id: str | None = None) -> StockGroup:
    groups = _load_stock_groups_raw(tenant_id)
    if any(group.name.lower() == payload.name.lower() for group in groups):
        raise ValueError(f"Stock group '{payload.name}' already exists")
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    group = StockGroup(
        id=str(uuid.uuid4()),
        name=payload.name,
        tickers=payload.tickers,
        created_at=timestamp,
        updated_at=timestamp,
    )
    groups.append(group)
    _save_stock_groups_raw(tenant_id, groups)
    return group


def update_stock_group(group_id: str, payload: StockGroupUpdate, tenant_id: str | None = None) -> StockGroup | None:
    groups = _load_stock_groups_raw(tenant_id)
    for index, group in enumerate(groups):
        if group.id != group_id:
            continue
        if any(other.id != group_id and other.name.lower() == payload.name.lower() for other in groups):
            raise ValueError(f"Stock group '{payload.name}' already exists")
        updated = group.model_copy(
            update={
                "name": payload.name,
                "tickers": payload.tickers,
                "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            }
        )
        groups[index] = updated
        _save_stock_groups_raw(tenant_id, groups)
        return updated
    return None


def delete_stock_group(group_id: str, tenant_id: str | None = None) -> int:
    groups = _load_stock_groups_raw(tenant_id)
    kept = [group for group in groups if group.id != group_id]
    deleted = 1 if len(kept) != len(groups) else 0
    if deleted:
        _save_stock_groups_raw(tenant_id, kept)
    return deleted
