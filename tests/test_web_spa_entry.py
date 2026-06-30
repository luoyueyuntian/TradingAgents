"""SPA entrypoint tests for the Vue/PrimeVue frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from web.app import app


def test_root_serves_vue_spa_shell():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="app"' in html
    assert 'data-app="tradingagents-vue-spa"' in html
    assert "/static/spa/" in html
    assert "/static/app.js" not in html


def test_client_routes_fall_back_to_vue_spa_shell():
    client = TestClient(app)

    for path in ("/analysis", "/runs", "/workspace/settings"):
        response = client.get(path)

        assert response.status_code == 200
        assert 'data-app="tradingagents-vue-spa"' in response.text


def test_python_package_includes_nested_spa_assets():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '"static/spa/**/*"' in pyproject


def test_dockerfile_builds_vue_frontend_assets():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert "FROM node:22-slim AS frontend-builder" in dockerfile
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "COPY --from=frontend-builder" in dockerfile
    assert "frontend/node_modules" in dockerignore
