"""Startup regression tests for the FastAPI application."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient


def test_web_app_imports_in_fresh_process():
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "-c", "import web.app"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_docker_compose_binds_web_port_to_localhost_by_default():
    repo_root = Path(__file__).resolve().parents[1]
    compose = (repo_root / "docker-compose.yml").read_text(encoding="utf-8")

    assert '127.0.0.1:8000:8000' in compose
    assert 'TRADINGAGENTS_WEB_API_TOKEN=${TRADINGAGENTS_WEB_API_TOKEN:-}' in compose


def test_web_app_cors_default_is_not_wildcard():
    repo_root = Path(__file__).resolve().parents[1]
    app_source = (repo_root / "web" / "app.py").read_text(encoding="utf-8")

    assert 'allow_origins=["*"]' not in app_source
    assert "TRADINGAGENTS_WEB_CORS_ORIGINS" in app_source


def test_web_app_startup_bootstraps_first_admin_from_env(monkeypatch, tmp_path):
    from web.app import app
    from web.user_store import UserStore

    auth_db = tmp_path / "auth.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_AUTH_DB", str(auth_db))
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_DIR", str(tmp_path / "web-state"))
    monkeypatch.setenv("TRADINGAGENTS_WEB_RUN_MODE", "manual")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_PASSWORD", "StrongAdmin123!")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_TENANT_ID", "tenant-a")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_USERNAME", "root-admin")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_DISPLAY_NAME", "Root Admin")

    with TestClient(app):
        pass

    store = UserStore(auth_db)
    user = store.get_user_by_identifier("admin@example.com")

    assert user is not None
    assert user.username == "root-admin"
    assert user.role == "admin"
    assert user.tenant_id == "tenant-a"
    assert user.must_change_password is True


def test_web_app_startup_restores_discovered_tenant_runs(monkeypatch, tmp_path):
    import web.app as web_app

    calls: list[tuple[str, str | None]] = []
    monkeypatch.setenv("TRADINGAGENTS_WEB_AUTH_DB", str(tmp_path / "auth.db"))
    monkeypatch.setenv("TRADINGAGENTS_WEB_RUN_MODE", "local_thread")
    monkeypatch.setattr(web_app, "list_web_tenant_ids", lambda: ["default"], raising=False)
    monkeypatch.setattr(web_app, "load_runs_index", lambda tenant_id=None: calls.append(("load", tenant_id)))
    monkeypatch.setattr(web_app, "ensure_worker_started", lambda tenant_id=None: calls.append(("worker", tenant_id)))
    monkeypatch.setattr(web_app, "resume_incomplete_runs", lambda tenant_id=None: calls.append(("resume", tenant_id)))

    asyncio.run(web_app._load_persisted_runs())

    assert calls == [
        ("load", None),
        ("worker", None),
        ("resume", None),
        ("load", "default"),
        ("worker", "default"),
        ("resume", "default"),
    ]
