"""Tests for optional web API token authentication."""

from __future__ import annotations

from fastapi.testclient import TestClient

from web.app import app


def test_api_allows_requests_when_no_token_configured(monkeypatch):
    client = TestClient(app)
    monkeypatch.delenv("TRADINGAGENTS_WEB_API_TOKEN", raising=False)

    response = client.get("/api/system/status")

    assert response.status_code == 200


def test_api_rejects_missing_token_when_configured(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("TRADINGAGENTS_WEB_API_TOKEN", "secret-token")

    response = client.get("/api/system/status")

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_api_accepts_bearer_token_header(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("TRADINGAGENTS_WEB_API_TOKEN", "secret-token")

    response = client.get(
        "/api/system/status",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200


def test_api_accepts_query_token_for_sse_style_requests(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("TRADINGAGENTS_WEB_API_TOKEN", "secret-token")

    response = client.get("/api/system/status?api_token=secret-token")

    assert response.status_code == 200


def test_api_rejects_missing_tenant_scoped_token(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.delenv("TRADINGAGENTS_WEB_API_TOKEN", raising=False)

    settings_path = tmp_path / "tenant-a.json"
    settings_path.write_text('{"security":{"web_api_token":"tenant-secret"}}', encoding="utf-8")
    monkeypatch.setattr("web.auth.get_web_settings_path", lambda tenant_id=None: settings_path)

    response = client.get("/api/system/status?tenant_id=tenant-a")

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_api_accepts_tenant_scoped_token(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.delenv("TRADINGAGENTS_WEB_API_TOKEN", raising=False)

    settings_path = tmp_path / "tenant-a.json"
    settings_path.write_text('{"security":{"web_api_token":"tenant-secret"}}', encoding="utf-8")
    monkeypatch.setattr("web.auth.get_web_settings_path", lambda tenant_id=None: settings_path)

    response = client.get(
        "/api/system/status?tenant_id=tenant-a",
        headers={"Authorization": "Bearer tenant-secret"},
    )

    assert response.status_code == 200


def test_api_rejects_token_bound_to_different_tenant(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.delenv("TRADINGAGENTS_WEB_API_TOKEN", raising=False)

    def _settings_path(tenant_id=None):
        return tmp_path / f"{tenant_id}.json"

    (tmp_path / "tenant-a.json").write_text('{"security":{"web_api_token":"token-a"}}', encoding="utf-8")
    (tmp_path / "tenant-b.json").write_text('{"security":{"web_api_token":"token-b"}}', encoding="utf-8")
    monkeypatch.setattr("web.auth.get_web_settings_path", _settings_path)

    response = client.get(
        "/api/system/status?tenant_id=tenant-b",
        headers={"Authorization": "Bearer token-a"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_api_rejects_unsafe_tenant_id_before_path_lookup(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.delenv("TRADINGAGENTS_WEB_API_TOKEN", raising=False)
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_DIR", str(tmp_path))

    response = client.get("/api/system/status?tenant_id=../../escape")

    assert response.status_code == 400
    assert "tenant_id" in response.json()["detail"]
