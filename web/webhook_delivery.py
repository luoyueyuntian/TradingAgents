"""Webhook delivery for tenant-scoped external notifications."""

from __future__ import annotations

import logging
from typing import Any

import requests

from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import load_settings, save_settings

logger = logging.getLogger(__name__)

_DEFAULT_EVENT_KINDS = ["run", "alert", "action"]


def _load_webhook_config(tenant_id: str | None = None) -> dict[str, Any]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    integrations = settings.get("integrations", {})
    if not isinstance(integrations, dict):
        return {}
    webhook = integrations.get("webhook", {})
    return webhook if isinstance(webhook, dict) else {}


def _load_delivery_state(tenant_id: str | None = None) -> tuple[dict[str, str], dict[str, Any]]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    bucket = settings.get("webhook_notifications", {})
    if not isinstance(bucket, dict):
        return {}, {}

    delivered_raw = bucket.get("delivered_items", [])
    delivered: dict[str, str] = {}
    if isinstance(delivered_raw, list):
        for item in delivered_raw:
            if isinstance(item, str):
                if item:
                    delivered[item] = ""
                continue
            if not isinstance(item, dict):
                continue
            notification_id = item.get("id")
            delivered_at = item.get("delivered_at")
            if isinstance(notification_id, str) and notification_id:
                delivered[notification_id] = delivered_at if isinstance(delivered_at, str) else ""
    return delivered, bucket


def _save_delivery_state(
    tenant_id: str | None,
    delivered: dict[str, str],
    *,
    last_delivery_at: str | None = None,
    last_error: str | None = None,
) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = load_settings(path=settings_path)

    integrations = existing.get("integrations", {})
    if not isinstance(integrations, dict):
        integrations = {}
    webhook = integrations.get("webhook", {})
    if not isinstance(webhook, dict):
        webhook = {}
    webhook["last_delivery_at"] = last_delivery_at
    webhook["last_error"] = last_error
    integrations["webhook"] = webhook
    existing["integrations"] = integrations

    ordered = sorted(delivered.items(), key=lambda item: item[1] or "", reverse=True)[:500]
    existing["webhook_notifications"] = {
        "delivered_items": [
            {"id": notification_id, "delivered_at": delivered_at or None}
            for notification_id, delivered_at in ordered
        ]
    }
    save_settings(existing, path=settings_path)


def process_pending_webhook_notifications(
    tenant_id: str | None = None,
    *,
    notification_items: list[dict[str, Any]] | None = None,
) -> int:
    """Deliver any not-yet-delivered notifications to the configured webhook."""
    config = _load_webhook_config(tenant_id)
    if not config.get("enabled"):
        return 0

    url = str(config.get("url") or "").strip()
    if not url:
        return 0

    event_kinds = config.get("event_kinds")
    if not isinstance(event_kinds, list) or not event_kinds:
        event_kinds = list(_DEFAULT_EVENT_KINDS)
    allowed = {str(item).strip().lower() for item in event_kinds if str(item).strip()}
    bearer_token = str(config.get("bearer_token") or "").strip()

    if notification_items is None:
        from .routes import _build_notification_center_response  # lazy import to avoid circular dependency

        center = _build_notification_center_response(tenant_id)
        notification_items = [item.model_dump() for item in center.items]

    delivered, _ = _load_delivery_state(tenant_id)
    headers = {"Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    delivered_count = 0
    last_delivery_at: str | None = None
    last_error: str | None = None
    for item in notification_items:
        notification_id = str(item.get("id") or "").strip()
        kind = str(item.get("kind") or "").strip().lower()
        created_at = str(item.get("created_at") or "").strip()
        if not notification_id or not kind or notification_id in delivered or kind not in allowed:
            continue

        payload = {
            "tenant_id": tenant_id,
            "notification": item,
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning("Failed to deliver webhook notification %s: %s", notification_id, exc)
            continue

        delivered[notification_id] = created_at
        delivered_count += 1
        last_delivery_at = created_at
        last_error = None

    _save_delivery_state(
        tenant_id,
        delivered,
        last_delivery_at=last_delivery_at,
        last_error=last_error,
    )
    return delivered_count
