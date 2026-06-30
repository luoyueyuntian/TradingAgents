"""Tests for outbound webhook notification delivery."""

from __future__ import annotations

from types import SimpleNamespace

from web import webhook_delivery


def test_process_pending_webhook_notifications_delivers_and_persists(monkeypatch):
    state = {
        "integrations": {
            "webhook": {
                "enabled": True,
                "url": "https://example.com/hook",
                "bearer_token": "secret-token",
                "event_kinds": ["run", "alert"],
            }
        }
    }
    captured = {}

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    def _post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr(webhook_delivery, "load_settings", lambda path=None: state)
    monkeypatch.setattr(webhook_delivery, "save_settings", _save)
    monkeypatch.setattr(webhook_delivery.requests, "post", _post)

    delivered = webhook_delivery.process_pending_webhook_notifications(
        notification_items=[
            {"id": "run:abc:completed", "kind": "run", "created_at": "2026-01-15T10:00:00", "title": "Done"},
            {"id": "pin:abc", "kind": "action", "created_at": "2026-01-15T10:05:00", "title": "Due"},
        ]
    )

    assert delivered == 1
    assert captured["url"] == "https://example.com/hook"
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["json"]["notification"]["id"] == "run:abc:completed"
    assert state["webhook_notifications"]["delivered_items"][0]["id"] == "run:abc:completed"
    assert state["integrations"]["webhook"]["last_delivery_at"] == "2026-01-15T10:00:00"
    assert state["integrations"]["webhook"]["last_error"] is None


def test_process_pending_webhook_notifications_skips_delivered_and_records_error(monkeypatch):
    state = {
        "integrations": {
            "webhook": {
                "enabled": True,
                "url": "https://example.com/hook",
                "event_kinds": ["run"],
            }
        },
        "webhook_notifications": {
            "delivered_items": [{"id": "run:done:completed", "delivered_at": "2026-01-15T10:00:00"}]
        },
    }

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    def _post(url, json=None, headers=None, timeout=None):
        raise webhook_delivery.requests.RequestException("boom")

    monkeypatch.setattr(webhook_delivery, "load_settings", lambda path=None: state)
    monkeypatch.setattr(webhook_delivery, "save_settings", _save)
    monkeypatch.setattr(webhook_delivery.requests, "post", _post)

    delivered = webhook_delivery.process_pending_webhook_notifications(
        notification_items=[
            {"id": "run:done:completed", "kind": "run", "created_at": "2026-01-15T10:00:00"},
            {"id": "run:new:completed", "kind": "run", "created_at": "2026-01-15T10:10:00"},
        ]
    )

    assert delivered == 0
    assert len(state["webhook_notifications"]["delivered_items"]) == 1
    assert state["integrations"]["webhook"]["last_error"] == "boom"
