"""Tests for configurable web state paths."""

from __future__ import annotations

import json

import pytest

from tradingagents.service import web_state as web_state_module
from tradingagents.service.runtime_context import build_runtime_context


def test_get_web_state_dir_defaults_under_home(monkeypatch, tmp_path):
    monkeypatch.delenv("TRADINGAGENTS_WEB_STATE_DIR", raising=False)
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)

    state_dir = web_state_module.get_web_state_dir()

    assert state_dir == tmp_path / ".tradingagents" / "web"


def test_get_web_state_dir_honors_env_override(monkeypatch, tmp_path):
    target = tmp_path / "shared-web-state"
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_DIR", str(target))

    state_dir = web_state_module.get_web_state_dir()

    assert state_dir == target


def test_get_web_state_dir_appends_tenant_namespace(monkeypatch, tmp_path):
    monkeypatch.delenv("TRADINGAGENTS_WEB_STATE_DIR", raising=False)
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("TRADINGAGENTS_WEB_TENANT_ID", "tenant-a")

    state_dir = web_state_module.get_web_state_dir()

    assert state_dir == tmp_path / ".tradingagents" / "web" / "tenants" / "tenant-a"


def test_get_web_state_dir_accepts_explicit_tenant_override(monkeypatch, tmp_path):
    monkeypatch.delenv("TRADINGAGENTS_WEB_STATE_DIR", raising=False)
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("TRADINGAGENTS_WEB_TENANT_ID", "env-tenant")

    state_dir = web_state_module.get_web_state_dir("header-tenant")

    assert state_dir == tmp_path / ".tradingagents" / "web" / "tenants" / "header-tenant"


@pytest.mark.parametrize(
    "tenant_id",
    ["../escape", "..", ".", "tenant/a", "tenant\\a", "tenant a", "", "a" * 65],
)
def test_get_web_state_dir_rejects_unsafe_tenant_names(monkeypatch, tmp_path, tenant_id):
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)

    with pytest.raises(ValueError):
        web_state_module.get_web_state_dir(tenant_id)


def test_get_web_state_dir_resolves_tenant_under_tenant_root(monkeypatch, tmp_path):
    monkeypatch.delenv("TRADINGAGENTS_WEB_STATE_DIR", raising=False)
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)

    state_dir = web_state_module.get_web_state_dir("tenant.a-1")

    expected_root = tmp_path / ".tradingagents" / "web" / "tenants"
    assert state_dir == expected_root / "tenant.a-1"
    assert state_dir.resolve().is_relative_to(expected_root.resolve())


def test_build_runtime_context_uses_configured_web_state_dir(monkeypatch, tmp_path):
    target = tmp_path / "shared-web-state"
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_DIR", str(target))

    context = build_runtime_context("run-123")

    assert context.run_root == target / "runs" / "run-123"
    assert context.results_dir == target / "runs" / "run-123" / "results"
    assert context.cache_dir == target / "cache"
    assert context.memory_log_path == target / "memory" / "trading_memory.md"


def test_get_web_state_backend_defaults_to_file(monkeypatch):
    monkeypatch.delenv("TRADINGAGENTS_WEB_STATE_BACKEND", raising=False)

    assert web_state_module.get_web_state_backend() == "file"


def test_get_web_sqlite_path_honors_env_override(monkeypatch, tmp_path):
    target = tmp_path / "state.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_SQLITE_PATH", str(target))

    assert web_state_module.get_web_sqlite_path() == target


def test_list_web_tenant_ids_discovers_tenant_dirs(monkeypatch, tmp_path):
    monkeypatch.delenv("TRADINGAGENTS_WEB_STATE_DIR", raising=False)
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)
    base = tmp_path / ".tradingagents" / "web" / "tenants"
    (base / "tenant-a").mkdir(parents=True)
    (base / "tenant-b").mkdir(parents=True)

    tenant_ids = web_state_module.list_web_tenant_ids()

    assert tenant_ids == ["tenant-a", "tenant-b"]


def test_list_web_tenant_ids_honors_env_override(monkeypatch, tmp_path):
    override = tmp_path / "custom-web-state" / "tenants"
    (override / "tenant-a").mkdir(parents=True)
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_DIR", str(tmp_path / "custom-web-state"))

    tenant_ids = web_state_module.list_web_tenant_ids()

    assert tenant_ids == ["tenant-a"]


def test_migrate_all_web_settings_timestamps_to_ms_rewrites_default_and_tenant_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_DIR", str(tmp_path / "web-state"))
    default_settings_path = tmp_path / "web-state" / "settings.json"
    tenant_settings_path = tmp_path / "web-state" / "tenants" / "tenant-a" / "settings.json"
    tenant_settings_path.parent.mkdir(parents=True, exist_ok=True)

    default_settings_path.write_text(json.dumps({
        "notes": {
            "items": [
                {
                    "id": "note-1",
                    "content": "hello",
                    "created_at": "2026-07-04T08:00:00+00:00",
                    "updated_at": "2026-07-04T09:00:00+00:00",
                }
            ]
        },
        "notifications": {
            "read_items": [
                {
                    "id": "notif-1",
                    "read_at": "2026-07-04T10:00:00+00:00",
                }
            ]
        },
    }), encoding="utf-8")
    tenant_settings_path.write_text(json.dumps({
        "automations": {
            "items": [
                {
                    "id": "rule-1",
                    "name": "Daily",
                    "enabled": True,
                    "source": "watchlist",
                    "tickers": [],
                    "cadence": "daily",
                    "time_of_day": "09:00",
                    "created_at": "2026-07-04T11:00:00+00:00",
                    "updated_at": "2026-07-04T12:00:00+00:00",
                    "last_triggered_at": "2026-07-04T13:00:00+00:00",
                    "next_run_at": "2026-07-05T09:00:00+00:00",
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                }
            ]
        },
        "pinned_runs": {
            "items": [
                {
                    "run_id": "run-1",
                    "created_at": "2026-07-04T14:00:00+00:00",
                    "due_date": "2026-07-06",
                }
            ]
        },
    }), encoding="utf-8")

    updated = web_state_module.migrate_all_web_settings_timestamps_to_ms()

    assert updated == 2

    default_payload = json.loads(default_settings_path.read_text(encoding="utf-8"))
    tenant_payload = json.loads(tenant_settings_path.read_text(encoding="utf-8"))

    note = default_payload["notes"]["items"][0]
    read_item = default_payload["notifications"]["read_items"][0]
    rule = tenant_payload["automations"]["items"][0]
    pinned = tenant_payload["pinned_runs"]["items"][0]

    assert isinstance(note["created_at"], int)
    assert isinstance(note["updated_at"], int)
    assert isinstance(read_item["read_at"], int)
    assert isinstance(rule["created_at"], int)
    assert isinstance(rule["updated_at"], int)
    assert isinstance(rule["last_triggered_at"], int)
    assert isinstance(rule["next_run_at"], int)
    assert isinstance(pinned["created_at"], int)
    assert pinned["due_date"] == "2026-07-06"
    assert rule["time_of_day"] == "09:00"
