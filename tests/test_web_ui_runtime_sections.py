"""SPA smoke tests for the Vue/PrimeVue web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from web.app import app


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_index_html_is_vue_spa_shell_with_pwa_metadata():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'data-app="tradingagents-vue-spa"' in html
    assert 'id="app"' in html
    assert 'rel="manifest"' in html
    assert "/static/app.webmanifest" in html
    assert 'name="theme-color"' in html
    assert "/static/spa/assets/app.js" in html
    assert "/static/spa/assets/index.css" in html
    assert "/static/app.js" not in html


def test_static_pwa_assets_are_served_from_spa_build():
    client = TestClient(app)

    manifest = client.get("/static/app.webmanifest")
    service_worker = client.get("/service-worker.js")
    icon = client.get("/static/icons/app-icon.svg")
    app_js = client.get("/static/spa/assets/app.js")
    app_css = client.get("/static/spa/assets/index.css")

    assert manifest.status_code == 200
    assert '"display": "standalone"' in manifest.text
    assert service_worker.status_code == 200
    assert "tradingagents-spa-v1" in service_worker.text
    assert "/static/spa/assets/app.js" in service_worker.text
    assert "url.pathname.startsWith('/static/spa/')" in service_worker.text
    assert "fetchAndCache(request)" in service_worker.text
    assert "/static/app.js" not in service_worker.text
    assert icon.status_code == 200
    assert "<svg" in icon.text
    assert app_js.status_code == 200
    assert "serviceWorker" in app_js.text
    assert app_css.status_code == 200
    assert ".app-shell" in app_css.text


def test_vue_router_splits_primary_workflows_into_pages():
    pages_ts = _read(FRONTEND_SRC / "router" / "pages.ts")
    expected_routes = {
        "dashboard": ("/", "DashboardPage.vue"),
        "analysis": ("/analysis", "AnalyzePage.vue"),
        "runs": ("/runs", "RunsPage.vue"),
        "portfolio": ("/portfolio", "PortfolioPage.vue"),
        "workspace": ("/workspace", "WorkspacePage.vue"),
        "automations": ("/automations", "AutomationsPage.vue"),
        "settings": ("/settings", "SettingsPage.vue"),
    }

    for route_name, (path, component) in expected_routes.items():
        assert f"path: '{path}'" in pages_ts
        assert f"name: '{route_name}'" in pages_ts
        assert f"labelKey: 'nav.{route_name}'" in pages_ts
        assert component in pages_ts

    assert pages_ts.count("name:") == len(expected_routes)


def test_vue_i18n_sources_include_english_and_chinese_copy():
    messages_ts = _read(FRONTEND_SRC / "i18n" / "messages.ts")
    i18n_ts = _read(FRONTEND_SRC / "i18n" / "index.ts")

    assert "'nav.dashboard': 'Dashboard'" in messages_ts
    assert "'nav.dashboard': '仪表盘'" in messages_ts
    assert "'common.publicSnapshot': '{ticker} public snapshot'" in messages_ts
    assert "'common.publicSnapshot': '{ticker} 公开快照'" in messages_ts
    assert "tradingagents.locale" in i18n_ts
    assert "setLocale" in i18n_ts
    assert "useI18n" in i18n_ts


def test_page_components_keep_existing_backend_api_boundaries():
    page_expectations = {
        "DashboardPage.vue": ["/api/dashboard", "/api/briefing/daily", "/api/notifications"],
        "AnalyzePage.vue": ["/api/providers", "/api/runs", "/events", "/cancel"],
        "RunsPage.vue": ["/api/runs", "/artifacts", "/retry"],
        "PortfolioPage.vue": ["/api/watchlist", "/api/portfolio", "/api/alerts", "/api/screener"],
        "WorkspacePage.vue": ["/api/search", "/api/notes", "/api/members", "/api/views", "/api/public-shares"],
        "AutomationsPage.vue": ["/api/automations", "/run-now", "time_of_day", "analysis_config"],
        "SettingsPage.vue": ["/api/settings", "/api/providers"],
    }

    for filename, api_markers in page_expectations.items():
        source = _read(FRONTEND_SRC / "pages" / filename)
        if filename == "AutomationsPage.vue":
            source += _read(FRONTEND_SRC / "pages" / "automationPayload.ts")
        assert "PageHeader" in source
        for marker in api_markers:
            assert marker in source


def test_api_service_preserves_tenant_context_for_existing_backend():
    api_source = _read(FRONTEND_SRC / "services" / "api.ts")

    assert "tenant_id" in api_source
    assert "api_token" in api_source
    assert "X-TradingAgents-Tenant" in api_source
    assert "X-TradingAgents-Token" in api_source
    assert "buildApiUrl" in api_source


def test_app_layout_exposes_page_navigation_and_session_context():
    layout_source = _read(FRONTEND_SRC / "layout" / "AppLayout.vue")

    assert "navigationGroups" in layout_source
    assert "RouterLink" in layout_source
    assert "useI18n" in layout_source
    assert 'v-model="locale"' in layout_source
    assert ':options="locales"' in layout_source
    assert "t(item.labelKey)" in layout_source
    assert "session.state.tenantId" in layout_source
    assert "session.state.apiToken" in layout_source
    assert "t('topbar.workspaceSearch')" in layout_source
    assert 'aria-label="Settings"' not in layout_source
    assert "router.push('/settings')" not in layout_source
