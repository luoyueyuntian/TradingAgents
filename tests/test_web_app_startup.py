"""Startup regression tests for the FastAPI application."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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
