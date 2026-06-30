"""Tests for configurable web state paths."""

from __future__ import annotations

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
    monkeypatch.setattr(web_state_module.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("TRADINGAGENTS_WEB_TENANT_ID", "tenant-a")

    state_dir = web_state_module.get_web_state_dir()

    assert state_dir == tmp_path / ".tradingagents" / "web" / "tenants" / "tenant-a"


def test_get_web_state_dir_accepts_explicit_tenant_override(monkeypatch, tmp_path):
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
