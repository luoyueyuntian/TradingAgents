"""SPA entrypoint tests for the Vue/PrimeVue frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from web import routes as web_routes
from web.app import app


def _write_spa_shell(tmp_path: Path) -> Path:
    index_path = tmp_path / "static" / "spa" / "index.html"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        """<!doctype html>
<html lang="en">
  <body>
    <div id="app" data-app="tradingagents-vue-spa"></div>
    <script type="module" src="/static/spa/assets/app.js"></script>
  </body>
</html>
""",
        encoding="utf-8",
    )
    return index_path


def test_root_serves_vue_spa_shell(monkeypatch, tmp_path):
    index_path = _write_spa_shell(tmp_path)
    monkeypatch.setattr(web_routes, "_spa_index_path", lambda: index_path)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="app"' in html
    assert 'data-app="tradingagents-vue-spa"' in html
    assert "/static/spa/" in html
    assert "/static/app.js" not in html


def test_client_routes_fall_back_to_vue_spa_shell(monkeypatch, tmp_path):
    index_path = _write_spa_shell(tmp_path)
    monkeypatch.setattr(web_routes, "_spa_index_path", lambda: index_path)
    client = TestClient(app)

    for path in ("/analysis", "/runs", "/runs/run-123", "/workspace/settings"):
        response = client.get(path)

        assert response.status_code == 200
        assert 'data-app="tradingagents-vue-spa"' in response.text


def test_root_returns_explicit_503_when_spa_assets_are_missing(monkeypatch, tmp_path):
    missing_index = tmp_path / "static" / "spa" / "index.html"
    monkeypatch.setattr(web_routes, "_spa_index_path", lambda: missing_index)
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Vue SPA assets are not built. Run `npm --prefix frontend run build`.",
    }


def test_python_package_no_longer_declares_nested_spa_assets():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '"static/spa/**/*"' not in pyproject
    assert 'web = ["static/*", "static/icons/*"]' in pyproject


def test_gitignore_ignores_generated_spa_bundle():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "web/static/spa/" in gitignore


def test_readme_documents_local_frontend_build_requirement():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "npm --prefix frontend run build" in readme
    assert "uvicorn web.app:app --host 0.0.0.0 --port 8000" in readme


def test_dockerfile_builds_vue_frontend_assets():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8")

    assert "FROM node:22-slim AS frontend-builder" in dockerfile
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "COPY --from=frontend-builder" in dockerfile
    assert "frontend/node_modules" in dockerignore


def test_spa_shell_and_worker_require_revalidation(monkeypatch, tmp_path):
    index_path = _write_spa_shell(tmp_path)
    monkeypatch.setattr(web_routes, '_spa_index_path', lambda: index_path)
    client = TestClient(app)
    assert client.get('/').headers.get('cache-control') == 'no-cache'
    assert client.get('/service-worker.js').headers.get('cache-control') == 'no-cache'


def test_frontend_build_uses_content_hashes_to_avoid_stale_scripts():
    config = Path('frontend/vite.config.ts').read_text()
    assert "entryFileNames: 'assets/app-[hash].js'" in config
    assert "chunkFileNames: 'assets/[name]-[hash].js'" in config


def test_legacy_spa_page_links_redirect_to_root_routes():
    client = TestClient(app)
    for old, new in [('/static/spa/', '/'), ('/static/spa/settings?tab=llm', '/settings?tab=llm'), ('/static/spa/runs/run-123', '/runs/run-123'), ('/static/spa/change-password', '/change-password')]:
        response = client.get(old, follow_redirects=False)
        assert response.status_code == 307
        assert response.headers['location'] == new
    assert client.get('/static/spa/assets/missing.js', follow_redirects=False).status_code == 404
