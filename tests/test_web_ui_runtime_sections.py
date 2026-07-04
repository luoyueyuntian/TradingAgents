"""SPA smoke tests for the Vue/PrimeVue web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from web import routes as web_routes
from web.app import app

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_spa_shell(tmp_path: Path) -> Path:
    index_path = tmp_path / "static" / "spa" / "index.html"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        """<!doctype html>
<html lang="en">
  <head>
    <meta name="theme-color" content="#162326">
    <link rel="manifest" href="/static/app.webmanifest">
    <link rel="stylesheet" href="/static/spa/assets/index.css">
  </head>
  <body>
    <div id="app" data-app="tradingagents-vue-spa"></div>
    <script type="module" src="/static/spa/assets/app.js"></script>
  </body>
</html>
""",
        encoding="utf-8",
    )
    return index_path


def test_index_html_is_vue_spa_shell_with_pwa_metadata(monkeypatch, tmp_path):
    index_path = _write_spa_shell(tmp_path)
    monkeypatch.setattr(web_routes, "_spa_index_path", lambda: index_path)
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


def test_static_pwa_assets_are_served_without_checked_in_spa_bundle():
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
    assert app_js.status_code == 404
    assert app_css.status_code == 404


def test_vue_router_splits_primary_workflows_into_pages():
    pages_ts = _read(FRONTEND_SRC / "router" / "pages.ts")
    expected_routes = {
        "dashboard": ("/", "DashboardPage.vue"),
        "analysis": ("/analysis", "AnalyzePage.vue"),
        "runs": ("/runs", "RunsPage.vue"),
        "run-detail": ("/runs/:runId", "RunDetailPage.vue"),
        "portfolio": ("/portfolio", "PortfolioPage.vue"),
        "workspace": ("/workspace", "WorkspacePage.vue"),
        "automations": ("/automations", "AutomationsPage.vue"),
        "settings": ("/settings", "SettingsPage.vue"),
        "users": ("/users", "UserManagementPage.vue"),
        "login": ("/login", "LoginPage.vue"),
        "change-password": ("/change-password", "ForcePasswordChangePage.vue"),
    }

    for route_name, (path, component) in expected_routes.items():
        assert f"path: '{path}'" in pages_ts
        assert f"name: '{route_name}'" in pages_ts
        if route_name in {"dashboard", "analysis", "runs", "portfolio", "workspace", "automations", "settings", "users"}:
            assert f"labelKey: 'nav.{route_name}'" in pages_ts
        if component:
            assert component in pages_ts

    assert pages_ts.count("name:") == len(expected_routes)
    assert "requiresAuth: true" in pages_ts
    assert "minRole: 'admin'" in pages_ts


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
        "RunsPage.vue": ["/api/runs"],
        "RunDetailPage.vue": ["/api/runs", "/artifacts", "/retry", "/terminal-output"],
        "PortfolioPage.vue": ["/api/watchlist", "/api/portfolio", "/api/alerts", "/api/screener"],
        "WorkspacePage.vue": ["/api/search", "/api/notes", "/api/members", "/api/views", "/api/public-shares"],
        "AutomationsPage.vue": ["/api/automations", "/run-now", "time_of_day", "analysis_config"],
        "SettingsPage.vue": ["/api/settings", "/api/providers"],
        "UserManagementPage.vue": ["/api/admin/users", "resetPassword", "expires_at", "disabled"],
    }

    for filename, api_markers in page_expectations.items():
        source = _read(FRONTEND_SRC / "pages" / filename)
        if filename == "AutomationsPage.vue":
            source += _read(FRONTEND_SRC / "pages" / "automationPayload.ts")
        assert "PageHeader" in source
        for marker in api_markers:
            assert marker in source


def test_automations_page_includes_one_time_task_backend_boundaries():
    source = _read(FRONTEND_SRC / "pages" / "AutomationsPage.vue")
    source += _read(FRONTEND_SRC / "pages" / "automationPayload.ts")
    source += _read(FRONTEND_SRC / "pages" / "oneTimeTaskPayload.ts")
    source += _read(FRONTEND_SRC / "pages" / "oneTimeTaskSelection.ts")
    source += _read(FRONTEND_SRC / "pages" / "analyzeStockSelection.ts")

    expected_markers = [
        "/api/one-time-tasks",
        "/api/stock-groups",
        "/api/watchlist",
        "/api/stocks",
        "/cancel",
        "/runs/",
        "run_ids",
        "scheduled_for",
        "resolved_tickers",
        "group_snapshots",
        "buildOneTimeTaskPayload",
        "mergeResolvedTickers",
        "buildStockSearchPath",
        "MultiSelect",
    ]

    assert "PageHeader" in source
    for marker in expected_markers:
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
    assert 'data-testid="language-trigger"' in layout_source
    assert "currentLocaleLabel" in layout_source
    assert "changeLocale(option.value)" in layout_source
    assert ":data-testid=\"`language-option-${option.value}`\"" in layout_source
    assert "t(item.labelKey)" in layout_source
    assert "session.state.currentUser?.display_name" in layout_source
    assert "session.state.currentUser?.tenant_id" in layout_source
    assert 'data-testid="user-menu"' in layout_source
    assert "@mouseenter=\"userMenuOpen = true\"" in layout_source
    assert "visibleNavigationGroups" in layout_source
    assert "session.isAdmin.value" in layout_source
    assert "handleLogout" in layout_source
    assert "t('topbar.workspaceSearch')" in layout_source
    assert "t('auth.logout')" in layout_source
    assert 'aria-label="Settings"' not in layout_source
    assert "router.push('/settings')" not in layout_source
