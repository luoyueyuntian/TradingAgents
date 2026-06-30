"""UI smoke tests for runtime-maintenance sections."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from web.app import app


def _app_js() -> str:
    return (Path(__file__).resolve().parents[1] / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    match = re.search(rf"(?:async\s+)?function\s+{name}\b", source)
    assert match is not None, f"could not locate function {name}"

    signature_end = source.find(")", match.end())
    assert signature_end != -1, f"could not locate closing signature for function {name}"

    body_start = source.find("{", signature_end)
    assert body_start != -1, f"could not locate opening brace for function {name}"

    depth = 0
    for idx in range(body_start, len(source)):
        char = source[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():idx + 1]

    raise AssertionError(f"could not locate closing brace for function {name}")


def test_index_html_exposes_runtime_maintenance_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="tenant-suggestions"' in html
    assert 'id="runtime-refresh"' in html
    assert 'id="runtime-checkpoints-list"' in html
    assert 'id="runtime-memory-list"' in html
    assert 'id="runtime-clear-checkpoints"' in html
    assert 'id="runtime-clear-memory"' in html


def test_index_html_exposes_pwa_metadata():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'rel="manifest"' in html
    assert '/static/app.webmanifest' in html
    assert 'name="theme-color"' in html


def test_index_html_exposes_install_app_mount_point():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="install-app-btn"' in html


def test_index_html_exposes_command_palette_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="command-palette-btn"' in html
    assert 'id="command-palette-overlay"' in html
    assert 'id="command-palette-input"' in html
    assert 'id="command-palette-results"' in html
    assert 'id="command-palette-close"' in html


def test_static_pwa_assets_are_served():
    client = TestClient(app)

    manifest = client.get("/static/app.webmanifest")
    service_worker = client.get("/service-worker.js")
    icon = client.get("/static/icons/app-icon.svg")

    assert manifest.status_code == 200
    assert '"display": "standalone"' in manifest.text
    assert service_worker.status_code == 200
    assert "CACHE_NAME" in service_worker.text
    assert icon.status_code == 200
    assert "<svg" in icon.text


def test_index_html_exposes_current_member_header_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="current-member"' in html
    assert 'id="member-workspace-btn"' in html


def test_index_html_exposes_webhook_settings_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="s-webhook-enabled"' in html
    assert 'id="s-webhook-url"' in html
    assert 'id="s-webhook-token"' in html
    assert 'id="s-webhook-token-toggle"' in html
    assert 'id="s-webhook-kind-run"' in html
    assert 'id="s-webhook-kind-alert"' in html
    assert 'id="s-webhook-kind-action"' in html
    assert 'id="s-webhook-kind-comment"' in html
    assert 'id="s-webhook-status"' in html


def test_index_html_exposes_default_home_setting_mount_point():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="s-default-home-view"' in html
    assert 'id="s-default-saved-view"' in html


def test_index_html_exposes_advanced_config_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="run-market-profile"' in html
    assert 'id="run-risk-rounds"' in html
    assert 'id="run-max-recur"' in html
    assert 'id="run-checkpoint-enabled"' in html
    assert 'id="run-benchmark-ticker"' in html
    assert 'id="run-temperature"' in html
    assert 'id="run-backend-url"' in html
    assert 'id="s-benchmark-ticker"' in html
    assert 'id="s-memory-log-max-entries"' in html
    assert 'id="s-global-news-queries"' in html
    assert 'id="tool-vendors-grid"' in html
    assert 'id="vendor-chain-help"' in html
    assert 'id="tool-vendor-help"' in html
    assert 'id="batch-tickers"' in html
    assert 'id="run-batch-tickers"' in html
    assert 'id="run-watchlist-batch"' in html


def test_index_html_exposes_ticker_home_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="ticker-home-panel"' in html
    assert 'id="refresh-ticker-home"' in html
    assert 'id="ticker-home-empty"' in html
    assert 'id="ticker-home-content"' in html
    assert 'id="ticker-home-title"' in html
    assert 'id="ticker-home-summary"' in html
    assert 'id="ticker-home-runs"' in html


def test_index_html_exposes_history_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="history-panel"' in html
    assert 'id="refresh-history"' in html
    assert 'id="export-history-csv"' in html
    assert 'id="history-select-all"' in html
    assert 'id="history-bulk-retry"' in html
    assert 'id="history-bulk-delete"' in html
    assert 'id="history-query"' in html
    assert 'id="history-archived-filter"' in html
    assert 'id="history-status-filter"' in html
    assert 'id="history-provider-filter"' in html
    assert 'id="history-asset-filter"' in html
    assert 'id="history-empty"' in html
    assert 'id="history-list"' in html


def test_index_html_exposes_recently_viewed_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="recently-viewed-panel"' in html
    assert 'id="refresh-recently-viewed"' in html
    assert 'id="clear-recently-viewed"' in html
    assert 'id="recently-viewed-empty"' in html
    assert 'id="recently-viewed-list"' in html
    assert 'id="panel-toggle-recently-viewed-panel"' in html


def test_index_html_exposes_artifact_library_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="artifacts-library-panel"' in html
    assert 'id="refresh-artifacts-library"' in html
    assert 'id="export-artifacts-library-csv"' in html
    assert 'id="artifacts-library-query"' in html
    assert 'id="artifacts-library-empty"' in html
    assert 'id="artifacts-library-list"' in html
    assert 'id="panel-toggle-artifacts-library-panel"' in html


def test_index_html_exposes_watchlist_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="watchlist-panel"' in html
    assert 'id="refresh-watchlist"' in html
    assert 'id="add-watchlist"' in html
    assert 'id="watchlist-import-dropzone"' in html
    assert 'id="watchlist-import-file"' in html
    assert 'id="watchlist-import-file-status"' in html
    assert 'id="watchlist-import-text"' in html
    assert 'id="import-watchlist"' in html
    assert 'id="watchlist-empty"' in html
    assert 'id="watchlist-list"' in html


def test_index_html_exposes_compare_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="compare-panel"' in html
    assert 'id="compare-left-run"' in html
    assert 'id="compare-right-run"' in html
    assert 'id="compare-section"' in html
    assert 'id="compare-run-button"' in html
    assert 'id="compare-empty"' in html
    assert 'id="compare-content"' in html
    assert 'id="compare-left-content"' in html
    assert 'id="compare-right-content"' in html


def test_index_html_exposes_follow_up_chat_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="follow-up-panel"' in html
    assert 'id="follow-up-question"' in html
    assert 'id="follow-up-ask"' in html
    assert 'id="follow-up-empty"' in html
    assert 'id="follow-up-transcript"' in html


def test_index_html_exposes_alert_center_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="alert-panel"' in html
    assert 'id="refresh-alerts"' in html
    assert 'id="add-alert-rule"' in html
    assert 'id="alert-field"' in html
    assert 'id="alert-value"' in html
    assert 'id="alert-rules-list"' in html
    assert 'id="alert-hits-list"' in html


def test_index_html_exposes_portfolio_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="portfolio-panel"' in html
    assert 'id="refresh-portfolio"' in html
    assert 'id="add-portfolio-position"' in html
    assert 'id="portfolio-import-dropzone"' in html
    assert 'id="portfolio-import-file"' in html
    assert 'id="portfolio-import-file-status"' in html
    assert 'id="portfolio-import-text"' in html
    assert 'id="import-portfolio"' in html
    assert 'id="portfolio-quantity"' in html
    assert 'id="portfolio-average-cost"' in html
    assert 'id="portfolio-summary"' in html
    assert 'id="portfolio-list"' in html


def test_index_html_exposes_briefing_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="briefing-panel"' in html
    assert 'id="refresh-briefing"' in html
    assert 'id="briefing-empty"' in html
    assert 'id="briefing-content"' in html
    assert 'id="briefing-summary"' in html
    assert 'id="briefing-alerts"' in html
    assert 'id="briefing-watchlist"' in html
    assert 'id="briefing-portfolio"' in html
    assert 'id="briefing-runs"' in html


def test_index_html_exposes_dashboard_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="dashboard-panel"' in html
    assert 'id="refresh-dashboard"' in html
    assert 'id="dashboard-empty"' in html
    assert 'id="dashboard-content"' in html
    assert 'id="dashboard-summary"' in html
    assert 'id="dashboard-getting-started"' in html
    assert 'id="dashboard-getting-started-summary"' in html
    assert 'id="dashboard-getting-started-list"' in html
    assert 'id="dashboard-bullish"' in html
    assert 'id="dashboard-attention"' in html
    assert 'id="dashboard-alerts"' in html
    assert 'id="dashboard-portfolio"' in html
    assert 'id="dashboard-pinned-actions"' in html
    assert 'id="dashboard-runs"' in html
    assert 'id="dashboard-widget-controls"' in html
    assert 'id="dashboard-section-bullish_focus"' in html
    assert 'id="dashboard-section-needs_attention"' in html
    assert 'id="dashboard-section-active_alerts"' in html
    assert 'id="dashboard-section-portfolio_focus"' in html
    assert 'id="dashboard-section-pinned_actions"' in html
    assert 'id="dashboard-section-pending_reviews"' in html
    assert 'id="dashboard-section-automations"' in html
    assert 'id="dashboard-section-saved_shortcuts"' in html
    assert 'id="dashboard-section-operational_runs"' in html
    assert 'id="dashboard-move-up-bullish_focus"' in html
    assert 'id="dashboard-move-down-bullish_focus"' in html
    assert 'id="workspace-import-dropzone"' in html
    assert 'id="workspace-import-file"' in html
    assert 'id="workspace-import-file-status"' in html
    assert 'id="workspace-import-text"' in html
    assert 'id="workspace-import-mode"' in html
    assert 'id="import-workspace-json"' in html
    assert 'id="dashboard-reviews"' in html
    assert 'id="dashboard-automations"' in html
    assert 'id="dashboard-shortcuts"' in html
    assert 'id="reset-dashboard-layout"' in html


def test_index_html_exposes_analytics_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="analytics-panel"' in html
    assert 'id="refresh-analytics"' in html
    assert 'id="export-analytics-csv"' in html
    assert 'id="analytics-empty"' in html
    assert 'id="analytics-content"' in html
    assert 'id="analytics-summary"' in html
    assert 'id="analytics-status"' in html
    assert 'id="analytics-providers"' in html
    assert 'id="analytics-signals"' in html
    assert 'id="analytics-assets"' in html
    assert 'id="analytics-tickers"' in html
    assert 'id="analytics-daily"' in html
    assert 'id="panel-toggle-analytics-panel"' in html


def test_index_html_exposes_screener_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="screener-panel"' in html
    assert 'id="refresh-screener"' in html
    assert 'id="screener-scope"' in html
    assert 'id="screener-query"' in html
    assert 'id="screener-signal-filter"' in html
    assert 'id="screener-status-filter"' in html
    assert 'id="screener-asset-filter"' in html
    assert 'id="screener-provider-filter"' in html
    assert 'id="export-screener-csv"' in html
    assert 'id="screener-empty"' in html
    assert 'id="screener-content"' in html
    assert 'id="screener-summary"' in html
    assert 'id="screener-list"' in html
    assert 'id="panel-toggle-screener-panel"' in html


def test_index_html_exposes_notification_center_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="notifications-btn"' in html
    assert 'id="notifications-unread-badge"' in html
    assert 'id="notifications-panel"' in html
    assert 'id="export-notifications-csv"' in html
    assert 'id="refresh-notifications"' in html
    assert 'id="mark-all-notifications-read"' in html
    assert 'id="notifications-unread-only"' in html
    assert 'id="notifications-member-filter"' in html
    assert 'id="notifications-kind-filter"' in html
    assert 'id="notifications-severity-filter"' in html
    assert 'id="notifications-browser-toggle"' in html
    assert 'id="notifications-browser-status"' in html
    assert 'id="notifications-empty"' in html
    assert 'id="notifications-list"' in html
    assert 'id="panel-toggle-notifications-panel"' in html


def test_index_html_exposes_automation_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="automations-panel"' in html
    assert 'id="refresh-automations"' in html
    assert 'id="automation-name"' in html
    assert 'id="automation-source"' in html
    assert 'id="automation-cadence"' in html
    assert 'id="automation-weekday"' in html
    assert 'id="automation-time"' in html
    assert 'id="automation-enabled"' in html
    assert 'id="automation-tickers"' in html
    assert 'id="save-automation"' in html
    assert 'id="automations-empty"' in html
    assert 'id="automations-list"' in html
    assert 'id="panel-toggle-automations-panel"' in html


def test_index_html_exposes_preset_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="preset-panel"' in html
    assert 'id="preset-name"' in html
    assert 'id="save-preset"' in html
    assert 'id="refresh-presets"' in html
    assert 'id="preset-list"' in html


def test_index_html_exposes_timeline_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="timeline-panel"' in html
    assert 'id="refresh-timeline"' in html
    assert 'id="export-timeline-csv"' in html
    assert 'id="timeline-empty"' in html
    assert 'id="timeline-list"' in html
    assert 'id="timeline-kind-run"' in html
    assert 'id="timeline-kind-note"' in html
    assert 'id="timeline-kind-search"' in html
    assert 'id="timeline-kind-view"' in html
    assert 'id="timeline-kind-member"' in html
    assert 'id="timeline-kind-share"' in html


def test_index_html_exposes_calendar_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="calendar-panel"' in html
    assert 'id="refresh-calendar"' in html
    assert 'id="calendar-empty"' in html
    assert 'id="calendar-list"' in html


def test_index_html_exposes_notes_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="notes-panel"' in html
    assert 'id="notes-scope"' in html
    assert 'id="notes-mode"' in html
    assert 'id="notes-search"' in html
    assert 'id="notes-tag-cloud"' in html
    assert 'id="note-content"' in html
    assert 'id="note-tags"' in html
    assert 'id="save-note"' in html
    assert 'id="notes-empty"' in html
    assert 'id="notes-list"' in html


def test_index_html_exposes_run_comment_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="comments-panel"' in html
    assert 'id="comments-scope"' in html
    assert 'id="comment-author"' in html
    assert 'id="comment-content"' in html
    assert 'id="comments-hide-resolved"' in html
    assert 'id="save-comment"' in html
    assert 'id="comments-empty"' in html
    assert 'id="comments-list"' in html
    assert 'id="panel-toggle-comments-panel"' in html
    assert 'id="timeline-kind-comment"' in html


def test_index_html_exposes_share_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="share-run-link"' in html
    assert 'id="share-ticker-link"' in html
    assert 'id="share-public-run-link"' in html
    assert 'id="revoke-public-run-link"' in html
    assert 'id="share-compare-link"' in html
    assert 'id="share-briefing-link"' in html


def test_index_html_exposes_workspace_export_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="export-workspace-json"' in html
    assert 'id="export-workspace-md"' in html


def test_index_html_exposes_workspace_search_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="search-panel"' in html
    assert 'id="workspace-search"' in html
    assert 'id="run-search"' in html
    assert 'id="export-search-csv"' in html
    assert 'id="search-kind-run"' in html
    assert 'id="search-kind-note"' in html
    assert 'id="search-kind-search"' in html
    assert 'id="search-kind-view"' in html
    assert 'id="search-kind-member"' in html
    assert 'id="search-kind-share"' in html
    assert 'id="search-kind-comment"' in html
    assert 'id="search-kind-review"' in html
    assert 'id="saved-search-name"' in html
    assert 'id="saved-search-group"' in html
    assert 'id="saved-search-pinned"' in html
    assert 'id="saved-search-filter-group"' in html
    assert 'id="saved-search-filter-status"' in html
    assert 'id="saved-search-filter-pinned"' in html
    assert 'id="save-search"' in html
    assert 'id="saved-searches-list"' in html
    assert 'id="search-empty"' in html
    assert 'id="search-results"' in html


def test_index_html_exposes_workspace_members_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="members-panel"' in html
    assert 'id="refresh-members"' in html
    assert 'id="member-name"' in html
    assert 'id="member-role"' in html
    assert 'id="save-member"' in html
    assert 'id="members-empty"' in html
    assert 'id="members-list"' in html
    assert 'id="panel-toggle-members-panel"' in html


def test_index_html_exposes_member_workspace_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="member-workspace-panel"' in html
    assert 'id="refresh-member-workspace"' in html
    assert 'id="member-workspace-filter"' in html
    assert 'id="member-workspace-empty"' in html
    assert 'id="member-workspace-content"' in html
    assert 'id="member-workspace-summary"' in html
    assert 'id="member-workspace-actions"' in html
    assert 'id="member-workspace-mentions"' in html
    assert 'id="member-workspace-comments"' in html
    assert 'id="panel-toggle-member-workspace-panel"' in html


def test_index_html_exposes_saved_views_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="saved-views-panel"' in html
    assert 'id="saved-view-name"' in html
    assert 'id="saved-view-group"' in html
    assert 'id="saved-view-pinned"' in html
    assert 'id="saved-view-filter-group"' in html
    assert 'id="saved-view-filter-status"' in html
    assert 'id="saved-view-filter-pinned"' in html
    assert 'id="saved-view-display-mode"' in html
    assert 'id="save-view"' in html
    assert 'id="refresh-views"' in html
    assert 'id="panel-visibility-controls"' in html
    assert 'id="panel-toggle-config-panel"' in html
    assert 'id="panel-toggle-history-panel"' in html
    assert 'id="saved-views-list"' in html


def test_index_html_exposes_public_shares_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="public-shares-panel"' in html
    assert 'id="refresh-public-shares"' in html
    assert 'id="export-public-shares-csv"' in html
    assert 'id="public-shares-query"' in html
    assert 'id="public-shares-availability-filter"' in html
    assert 'id="public-shares-empty"' in html
    assert 'id="public-shares-list"' in html
    assert 'id="panel-toggle-public-shares-panel"' in html


def test_index_html_exposes_pinned_runs_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="pinned-runs-panel"' in html
    assert 'id="refresh-pinned-runs"' in html
    assert 'id="pin-run-note"' in html
    assert 'id="pin-run-category"' in html
    assert 'id="pin-run-priority"' in html
    assert 'id="pin-run-next-action"' in html
    assert 'id="pin-run-action-status"' in html
    assert 'id="pin-run-assignee"' in html
    assert 'id="pin-run-due-date"' in html
    assert 'id="pin-run-snoozed-until"' in html
    assert 'id="pinned-category-filter"' in html
    assert 'id="pinned-action-status-filter"' in html
    assert 'id="pinned-assignee-filter"' in html
    assert 'id="pin-current-run"' in html
    assert 'id="pinned-runs-list"' in html


def test_index_html_exposes_action_board_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="action-board-panel"' in html
    assert 'id="refresh-action-board"' in html
    assert 'id="action-board-todo"' in html
    assert 'id="action-board-doing"' in html
    assert 'id="action-board-done"' in html


def test_index_html_exposes_run_annotation_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="annotation-panel"' in html
    assert 'id="annotation-label"' in html
    assert 'id="annotation-summary"' in html
    assert 'id="annotation-next-step"' in html
    assert 'id="save-annotation"' in html
    assert 'id="clear-annotation"' in html


def test_index_html_exposes_run_review_mount_points():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    html = response.text
    assert 'id="review-panel"' in html
    assert 'id="review-scope"' in html
    assert 'id="reviewer-member"' in html
    assert 'id="review-status"' in html
    assert 'id="review-note"' in html
    assert 'id="review-history-reviewer-filter"' in html
    assert 'id="review-history-status-filter"' in html
    assert 'id="review-history-query"' in html
    assert 'id="export-review-history-csv"' in html
    assert 'id="review-history-summary"' in html
    assert 'id="review-history-empty"' in html
    assert 'id="review-history-list"' in html
    assert 'id="save-review"' in html
    assert 'id="clear-review"' in html
    assert 'id="panel-toggle-review-panel"' in html
    assert 'id="timeline-kind-review"' in html


def test_runtime_context_change_refreshes_settings_source():
    body = _function_body(_app_js(), "handleRuntimeContextChange")

    assert "await loadSettings();" in body
    assert "applySettingsToMainForm();" in body


def test_ticker_home_functions_are_wired_from_input_and_run_loading():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")
    open_body = _function_body(source, "openRunDetails")

    assert "scheduleTickerHomeRefresh(e.target.value);" in form_body
    assert "document.getElementById('refresh-ticker-home')" in form_body
    assert "void loadTickerHome();" in history_body
    assert "void loadTickerHome(run.ticker);" in open_body


def test_watchlist_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")

    assert "document.getElementById('refresh-watchlist')" in form_body
    assert "document.getElementById('add-watchlist')" in form_body
    assert "document.getElementById('import-watchlist')" in form_body
    assert "void loadWatchlist();" in history_body


def test_watchlist_import_function_posts_pasted_content():
    source = _app_js()
    body = _function_body(source, "importWatchlist")

    assert "watchlist-import-text" in body
    assert "/api/watchlist/import" in body
    assert "await loadWatchlist();" in body


def test_import_file_surfaces_are_wired_from_form_handlers():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    bind_body = _function_body(source, "bindImportFileSurface")
    load_body = _function_body(source, "loadImportFileIntoTextarea")

    assert "watchlist-import-dropzone" in form_body
    assert "watchlist-import-file" in form_body
    assert "portfolio-import-dropzone" in form_body
    assert "portfolio-import-file" in form_body
    assert "workspace-import-dropzone" in form_body
    assert "workspace-import-file" in form_body
    assert "dragover" in bind_body
    assert "drop" in bind_body
    assert "file.text()" in load_body
    assert "textarea.value = text;" in load_body


def test_history_filters_and_export_are_wired():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    downloads_body = _function_body(source, "initDownloads")
    history_body = _function_body(source, "loadRunHistory")
    export_body = _function_body(source, "downloadRunHistoryCsv")
    bulk_body = _function_body(source, "bulkUpdateRuns")

    assert "document.getElementById('refresh-history')" in form_body
    assert "document.getElementById('history-query')" in form_body
    assert "document.getElementById('history-archived-filter')" in form_body
    assert "document.getElementById('history-status-filter')" in form_body
    assert "document.getElementById('history-provider-filter')" in form_body
    assert "document.getElementById('history-asset-filter')" in form_body
    assert "document.getElementById('history-select-all')" in form_body
    assert "document.getElementById('history-bulk-archive')" in form_body
    assert "document.getElementById('history-bulk-restore')" in form_body
    assert "document.getElementById('history-bulk-retry')" in form_body
    assert "document.getElementById('history-bulk-delete')" in form_body
    assert "document.getElementById('export-history-csv')" in downloads_body
    assert "history-query" in history_body
    assert "history-archived-filter" in history_body
    assert "history-status-filter" in history_body
    assert "history-provider-filter" in history_body
    assert "history-asset-filter" in history_body
    assert "/api/runs/export" in export_body
    assert "/api/runs/bulk" in bulk_body


def test_recently_viewed_functions_are_wired_from_initialization_and_context_changes():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    init_body = _function_body(source, "initProviders")
    focus_body = _function_body(source, "focusTicker")
    open_body = _function_body(source, "openRunDetails")
    saved_view_body = _function_body(source, "applySavedViewItem")
    render_body = _function_body(source, "renderRecentlyViewed")

    assert "document.getElementById('refresh-recently-viewed')" in form_body
    assert "document.getElementById('clear-recently-viewed')" in form_body
    assert "loadRecentlyViewed();" in init_body
    assert "rememberRecentlyViewedItem" in focus_body
    assert "rememberRecentlyViewedItem" in open_body
    assert "rememberRecentlyViewedItem" in saved_view_body
    assert "recently-viewed-list" in render_body
    assert "openRecentlyViewedItem" in render_body


def test_artifact_library_functions_are_wired_from_form_history_and_route_state():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    downloads_body = _function_body(source, "initDownloads")
    history_body = _function_body(source, "loadRunHistory")
    route_body = _function_body(source, "applyInitialRouteState")
    url_body = _function_body(source, "buildCurrentViewUrl")
    export_body = _function_body(source, "downloadArtifactLibraryCsv")

    assert "document.getElementById('refresh-artifacts-library')" in form_body
    assert "document.getElementById('artifacts-library-query')" in form_body
    assert "document.getElementById('export-artifacts-library-csv')" in downloads_body
    assert "void loadArtifactLibrary();" in history_body
    assert "params.get('artifacts_q')" in route_body
    assert "view === 'artifacts'" in route_body
    assert "params.set('artifacts_q'" in url_body
    assert "/api/artifacts/library/export" in export_body


def test_compare_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")

    assert "document.getElementById('compare-run-button')" in form_body
    assert "document.getElementById('compare-section')" in form_body
    assert "populateCompareRunOptions();" in history_body


def test_follow_up_chat_functions_are_wired_from_form_and_run_opening():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    open_body = _function_body(source, "openRunDetails")

    assert "document.getElementById('follow-up-ask')" in form_body
    assert "void askFollowUpQuestion();" in form_body
    assert "prepareFollowUpChat(run);" in open_body


def test_alert_center_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")

    assert "document.getElementById('refresh-alerts')" in form_body
    assert "document.getElementById('add-alert-rule')" in form_body
    assert "void loadAlerts();" in history_body


def test_portfolio_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")

    assert "document.getElementById('refresh-portfolio')" in form_body
    assert "document.getElementById('add-portfolio-position')" in form_body
    assert "document.getElementById('import-portfolio')" in form_body
    assert "void loadPortfolio();" in history_body


def test_portfolio_import_function_posts_pasted_content():
    source = _app_js()
    body = _function_body(source, "importPortfolio")

    assert "portfolio-import-text" in body
    assert "/api/portfolio/import" in body
    assert "await loadPortfolio();" in body


def test_briefing_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")

    assert "document.getElementById('refresh-briefing')" in form_body
    assert "void loadBriefing();" in history_body


def test_dashboard_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")

    assert "document.getElementById('refresh-dashboard')" in form_body
    assert "DASHBOARD_SECTION_IDS.forEach" in form_body
    assert "dashboard-section-${sectionId}" in form_body
    assert "dashboard-move-up-${sectionId}" in form_body
    assert "moveDashboardSection" in form_body
    assert "reset-dashboard-layout" in form_body
    assert "document.getElementById('import-workspace-json')" in form_body
    assert "void loadDashboard();" in history_body


def test_dashboard_getting_started_rendering_is_present():
    source = _app_js()
    render_body = _function_body(source, "renderDashboard")
    item_body = _function_body(source, "renderDashboardGettingStartedItem")
    open_body = _function_body(source, "openGettingStartedTarget")

    assert "dashboard-getting-started" in render_body
    assert "dashboard-getting-started-list" in render_body
    assert "payload.getting_started" in render_body
    assert "item.action_label" in item_body
    assert "item.target_panel" in item_body
    assert "loadWatchlist" in open_body
    assert "loadPortfolio" in open_body
    assert "loadAutomations" in open_body
    assert "loadWorkspaceMembers" in open_body


def test_service_worker_registration_runs_during_boot():
    source = _app_js()
    boot_body = _function_body(source, "registerServiceWorker")
    root_source = source[source.find("document.addEventListener('DOMContentLoaded'"):]

    assert "navigator.serviceWorker.register('/service-worker.js')" in boot_body
    assert "window.addEventListener('load'" in boot_body
    assert "registerServiceWorker();" in root_source


def test_install_prompt_functions_are_wired_during_boot():
    source = _app_js()
    init_body = _function_body(source, "initInstallPrompt")
    prompt_body = _function_body(source, "promptInstallApp")
    root_source = source[source.find("document.addEventListener('DOMContentLoaded'"):]

    assert "initInstallPrompt();" in root_source
    assert "install-app-btn" in init_body
    assert "beforeinstallprompt" in init_body
    assert "appinstalled" in init_body
    assert "deferredInstallPrompt.prompt()" in prompt_body
    assert "updateInstallPromptVisibility()" in prompt_body


def test_command_palette_bootstrap_and_shortcuts_are_wired():
    source = _app_js()
    root_source = source[source.find("document.addEventListener('DOMContentLoaded'"):]
    init_body = _function_body(source, "initCommandPalette")
    shortcut_body = _function_body(source, "initKeyboardShortcuts")

    assert "initCommandPalette();" in root_source
    assert "initKeyboardShortcuts();" in root_source
    assert "command-palette-overlay" in init_body
    assert "command-palette-btn" in init_body
    assert "command-palette-input" in init_body
    assert "command-palette-results" in init_body
    assert "event.key.toLowerCase() === 'k'" in shortcut_body
    assert "event.metaKey || event.ctrlKey" in shortcut_body


def test_command_palette_render_and_execute_functions_cover_navigation_and_actions():
    source = _app_js()
    build_body = _function_body(source, "buildCommandPaletteCommands")
    render_body = _function_body(source, "renderCommandPaletteResults")
    execute_body = _function_body(source, "executeCommandPaletteCommand")

    assert "command-palette-results" in render_body
    assert "command.label" in render_body
    assert "command.keywords" in render_body
    assert "scrollToPanel" in build_body
    assert "loadRunHistory" in build_body
    assert "startAnalysis" in build_body
    assert "showSettings" in build_body
    assert "await command.action()" in execute_body


def test_workspace_import_function_posts_snapshot_json_and_refreshes_surfaces():
    source = _app_js()
    body = _function_body(source, "importWorkspaceSnapshot")

    assert "workspace-import-text" in body
    assert "workspace-import-mode" in body
    assert "/api/workspace/import" in body
    assert "await refreshWorkspaceAfterImport();" in body


def test_analytics_functions_are_wired_from_form_history_and_initial_route():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")
    init_body = _function_body(source, "initProviders")
    downloads_body = _function_body(source, "initDownloads")
    route_body = _function_body(source, "applyInitialRouteState")

    assert "document.getElementById('refresh-analytics')" in form_body
    assert "document.getElementById('export-analytics-csv')" in downloads_body
    assert "await loadAnalytics();" in init_body
    assert "void loadAnalytics();" in history_body
    assert "view === 'analytics'" in route_body


def test_screener_functions_are_wired_from_form_history_initial_route_and_providers():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")
    init_body = _function_body(source, "initProviders")
    downloads_body = _function_body(source, "initDownloads")
    route_body = _function_body(source, "applyInitialRouteState")

    assert "document.getElementById('refresh-screener')" in form_body
    assert "document.getElementById('screener-scope')" in form_body
    assert "document.getElementById('screener-query')" in form_body
    assert "document.getElementById('screener-provider-filter')" in form_body
    assert "document.getElementById('export-screener-csv')" in downloads_body
    assert "populateScreenerProviderFilter();" in init_body
    assert "await loadScreener();" in init_body
    assert "void loadScreener();" in history_body
    assert "view === 'screener'" in route_body


def test_notification_functions_are_wired_from_form_history_and_initial_route():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")
    downloads_body = _function_body(source, "initDownloads")
    route_body = _function_body(source, "applyInitialRouteState")

    assert "document.getElementById('refresh-notifications')" in form_body
    assert "document.getElementById('mark-all-notifications-read')" in form_body
    assert "document.getElementById('notifications-unread-only')" in form_body
    assert "document.getElementById('notifications-member-filter')" in form_body
    assert "document.getElementById('notifications-kind-filter')" in form_body
    assert "document.getElementById('notifications-severity-filter')" in form_body
    assert "document.getElementById('notifications-browser-toggle')" in form_body
    assert "document.getElementById('notifications-btn')" in form_body
    assert "document.getElementById('export-notifications-csv')" in downloads_body
    assert "void loadNotifications();" in history_body
    assert "view === 'notifications'" in route_body


def test_browser_notification_functions_are_present_and_connected():
    source = _app_js()
    toggle_body = _function_body(source, "toggleDesktopNotifications")
    load_body = _function_body(source, "loadNotifications")
    status_body = _function_body(source, "updateDesktopNotificationControls")
    notify_body = _function_body(source, "maybeSendDesktopNotifications")

    assert "Notification.requestPermission" in toggle_body
    assert "notifications-browser-status" in status_body
    assert "notifications-browser-toggle" in status_body
    assert "maybeSendDesktopNotifications(payload)" in load_body
    assert "new Notification" in notify_body
    assert "document.visibilityState" in notify_body


def test_automation_functions_are_wired_from_form_history_and_initial_route():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")
    init_body = _function_body(source, "initProviders")
    route_body = _function_body(source, "applyInitialRouteState")

    assert "document.getElementById('refresh-automations')" in form_body
    assert "document.getElementById('save-automation')" in form_body
    assert "document.getElementById('automation-cadence')" in form_body
    assert "document.getElementById('automation-source')" in form_body
    assert "await loadAutomations();" in init_body
    assert "void loadAutomations();" in history_body
    assert "view === 'automations'" in route_body


def test_preset_functions_are_wired_from_form_and_initialization():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    init_body = _function_body(source, "initProviders")
    preset_body = _function_body(source, "renderPresets")

    assert "document.getElementById('save-preset')" in form_body
    assert "document.getElementById('refresh-presets')" in form_body
    assert "void saveCurrentPreset();" in form_body
    assert "await loadPresets();" in init_body
    assert "Rename" in preset_body
    assert "Duplicate" in preset_body


def test_timeline_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")
    downloads_body = _function_body(source, "initDownloads")

    assert "document.getElementById('refresh-timeline')" in form_body
    assert "document.getElementById('export-timeline-csv')" in downloads_body
    assert "document.getElementById('timeline-kind-run')" in form_body
    assert "document.getElementById('timeline-kind-search')" in form_body
    assert "document.getElementById('timeline-kind-view')" in form_body
    assert "document.getElementById('timeline-kind-member')" in form_body
    assert "document.getElementById('timeline-kind-share')" in form_body
    assert "void loadTimeline();" in history_body


def test_calendar_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")

    assert "document.getElementById('refresh-calendar')" in form_body
    assert "void loadCalendar();" in history_body


def test_notes_functions_are_wired_from_form_and_context_changes():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    open_body = _function_body(source, "openRunDetails")
    render_body = _function_body(source, "renderNotes")
    tag_body = _function_body(source, "applyNotesTagFilter")
    load_body = _function_body(source, "loadNotes")

    assert "document.getElementById('save-note')" in form_body
    assert "document.getElementById('notes-search')" in form_body
    assert "document.getElementById('notes-mode')" in form_body
    assert "void saveNote();" in form_body
    assert "prepareNotesContext(run);" in open_body
    assert "notes-tag-cloud" in render_body
    assert "note.tags" in render_body
    assert "applyNotesTagFilter" in render_body
    assert "document.getElementById('notes-search')" in tag_body
    assert "void loadNotes();" in tag_body
    assert "notes-mode" in load_body


def test_notes_route_state_preserves_mode_and_query():
    source = _app_js()
    route_body = _function_body(source, "applyInitialRouteState")
    url_body = _function_body(source, "buildCurrentViewUrl")

    assert "params.get('notes_mode')" in route_body
    assert "params.get('notes_q')" in route_body
    assert "view === 'notes'" in route_body
    assert "params.set('notes_mode'" in url_body
    assert "params.set('notes_q'" in url_body


def test_run_comment_functions_are_wired_from_form_and_run_loading():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    open_body = _function_body(source, "openRunDetails")

    assert "document.getElementById('save-comment')" in form_body
    assert "timeline-kind-comment" in form_body
    assert "comments-hide-resolved" in form_body
    assert "void saveRunComment();" in form_body
    assert "prepareCommentsContext(run);" in open_body


def test_share_functions_are_wired_for_copy_and_initial_route_restore():
    source = _app_js()
    init_body = _function_body(source, "initDownloads")
    route_body = _function_body(source, "applyInitialRouteState")

    assert "document.getElementById('share-run-link')" in init_body
    assert "document.getElementById('share-ticker-link')" in init_body
    assert "document.getElementById('share-public-run-link')" in init_body
    assert "document.getElementById('revoke-public-run-link')" in init_body
    assert "document.getElementById('share-compare-link')" in init_body
    assert "document.getElementById('share-briefing-link')" in init_body
    assert "params.get('run_id')" in route_body
    assert "params.get('ticker')" in route_body
    assert "params.get('compare_left_run_id')" in route_body
    assert "params.get('history_q')" in route_body
    assert "params.get('history_archived')" in route_body
    assert "params.get('view')" in route_body
    assert "params.get('panels')" in route_body


def test_public_run_share_functions_are_present():
    source = _app_js()
    share_body = _function_body(source, "copyPublicRunShareLink")
    revoke_body = _function_body(source, "revokePublicRunShare")
    sync_body = _function_body(source, "syncPublicShareActions")
    open_body = _function_body(source, "openRunDetails")

    assert "/api/runs/" in share_body
    assert "/public-share" in share_body
    assert "currentRunId" in revoke_body
    assert "revoke-public-run-link" in sync_body
    assert "share-public-run-link" in sync_body
    assert "run.public_share" in sync_body
    assert "renderRunStatus(run)" in open_body


def test_batch_run_functions_are_wired_from_form_handlers():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")

    assert "document.getElementById('run-batch-tickers')" in form_body
    assert "document.getElementById('run-watchlist-batch')" in form_body
    assert "runBatchAnalysis('manual')" in form_body
    assert "runBatchAnalysis('watchlist')" in form_body


def test_workspace_export_functions_are_wired_for_downloads():
    source = _app_js()
    init_body = _function_body(source, "initDownloads")

    assert "document.getElementById('export-workspace-json')" in init_body
    assert "document.getElementById('export-workspace-md')" in init_body
    assert "downloadWorkspaceExport('json')" in init_body
    assert "downloadWorkspaceExport('markdown')" in init_body


def test_csv_export_download_functions_use_current_filters():
    source = _app_js()
    screener_body = _function_body(source, "downloadScreenerCsv")
    timeline_body = _function_body(source, "downloadTimelineCsv")
    search_body = _function_body(source, "downloadWorkspaceSearchCsv")

    assert "/api/screener/export" in screener_body
    assert "screener-scope" in screener_body
    assert "screener-provider-filter" in screener_body
    assert "/api/timeline/export" in timeline_body
    assert "collectTimelineKinds()" in timeline_body
    assert "/api/search/export" in search_body
    assert "workspace-search" in search_body
    assert "collectWorkspaceSearchKinds()" in search_body


def test_webhook_settings_functions_are_wired_from_settings_init():
    source = _app_js()
    init_body = _function_body(source, "initSettings")

    assert "document.getElementById('s-webhook-token-toggle')" in init_body
    assert "s-webhook-kind-comment" in source


def test_workspace_search_functions_are_wired_from_form():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    init_body = _function_body(source, "initProviders")
    downloads_body = _function_body(source, "initDownloads")
    search_action_body = _function_body(source, "runWorkspaceSearch")
    saved_searches_body = _function_body(source, "renderSavedSearches")
    render_body = _function_body(source, "renderWorkspaceSearchResults")

    assert "document.getElementById('run-search')" in form_body
    assert "document.getElementById('workspace-search')" in search_action_body
    assert "document.getElementById('export-search-csv')" in downloads_body
    assert "search-kind-comment" in source
    assert "search-kind-review" in source
    assert "search-kind-search" in source
    assert "search-kind-view" in source
    assert "search-kind-member" in source
    assert "search-kind-share" in source
    assert "void runWorkspaceSearch();" in form_body
    assert "document.getElementById('save-search')" in form_body
    assert "saved-search-filter-group" in form_body
    assert "saved-search-filter-status" in form_body
    assert "saved-search-filter-pinned" in form_body
    assert "await loadSavedSearches();" in init_body
    assert "CURRENT_MEMBER_STORAGE_KEY" in saved_searches_body
    assert "Duplicate" in saved_searches_body
    assert "Rename" in saved_searches_body
    assert "currentSavedSearches.find" in render_body
    assert "currentSavedViews.find" in render_body
    assert "currentWorkspaceMembers.find" in render_body
    assert "currentPublicShares.find" in render_body
    assert "`/shared/${encodeURIComponent(result.entity_id)}`" in render_body
    assert "window.open(url" in render_body


def test_workspace_member_functions_are_wired_from_form_and_initialization():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    init_body = _function_body(source, "initProviders")
    populate_body = _function_body(source, "populateMemberFilterOptions")
    render_body = _function_body(source, "renderWorkspaceMembers")
    save_body = _function_body(source, "saveWorkspaceMember")

    assert "document.getElementById('refresh-members')" in form_body
    assert "document.getElementById('save-member')" in form_body
    assert "document.getElementById('member-role')" in save_body
    assert "void saveWorkspaceMember();" in form_body
    assert "await loadWorkspaceMembers();" in init_body
    assert "member.role" in populate_body
    assert "member.role" in render_body


def test_member_workspace_functions_are_wired_from_form_and_members_loading():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    members_body = _function_body(source, "loadWorkspaceMembers")

    assert "document.getElementById('refresh-member-workspace')" in form_body
    assert "document.getElementById('member-workspace-filter')" in form_body
    assert "document.getElementById('member-workspace-btn')" in form_body
    assert "CURRENT_MEMBER_STORAGE_KEY" in form_body
    assert "void loadMemberWorkspace();" in form_body
    assert "void loadMemberWorkspace();" in members_body


def test_current_member_context_is_applied_from_header_and_route_state():
    source = _app_js()
    route_body = _function_body(source, "applyInitialRouteState")
    init_body = _function_body(source, "initCurrentMemberField")
    url_body = _function_body(source, "buildCurrentViewUrl")
    member_options_body = _function_body(source, "populateMemberFilterOptions")
    notifications_body = _function_body(source, "loadNotifications")
    default_home_body = _function_body(source, "openDefaultHomeSurface")
    settings_body = _function_body(source, "populateSettingsForm")
    saved_view_options_body = _function_body(source, "populateDefaultSavedViewOptions")

    assert "params.get('member_id')" in route_body
    assert "view === 'member-workspace'" in route_body
    assert "params.get('dashboard_sections')" in route_body
    assert "params.get('dashboard_order')" in route_body
    assert "params.get('notifications_member')" in route_body
    assert "params.get('notifications_kind')" in route_body
    assert "params.get('notifications_severity')" in route_body
    assert "params.get('history_q')" in route_body
    assert "params.get('history_status')" in route_body
    assert "params.get('history_provider')" in route_body
    assert "params.get('history_asset')" in route_body
    assert "params.get('history_archived')" in route_body
    assert "params.get('review_reviewer')" in route_body
    assert "params.get('screener_scope')" in route_body
    assert "await openDefaultHomeSurface();" in route_body
    assert "if (getCurrentMemberId())" in default_home_body
    assert "CURRENT_MEMBER_STORAGE_KEY" in init_body
    assert "member-workspace-panel').scrollIntoView" in init_body
    assert "params.set('member_id'" in url_body
    assert "params.set('dashboard_sections'" in url_body
    assert "params.set('dashboard_order'" in url_body
    assert "view', 'dashboard'" in url_body
    assert "params.set('notifications_member'" in url_body
    assert "params.set('notifications_kind'" in url_body
    assert "params.set('notifications_severity'" in url_body
    assert "params.set('history_q'" in url_body
    assert "params.set('history_status'" in url_body
    assert "params.set('history_provider'" in url_body
    assert "params.set('history_asset'" in url_body
    assert "params.set('history_archived'" in url_body
    assert "params.set('review_reviewer'" in url_body
    assert "params.set('screener_scope'" in url_body
    assert "valueField === 'id' ? member.id : member.name" in member_options_body
    assert "currentMemberScopedView()" in notifications_body
    assert "default_home_view" in default_home_body
    assert "default_saved_view_id" in default_home_body
    assert "populateDefaultSavedViewOptions" in settings_body
    assert "s-default-saved-view" in saved_view_options_body


def test_saved_views_functions_are_wired_from_form_and_initialization():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    init_body = _function_body(source, "initProviders")
    saved_views_body = _function_body(source, "renderSavedViews")
    card_body = _function_body(source, "renderSavedViewCard")
    apply_body = _function_body(source, "applySavedViewItem")

    assert "document.getElementById('save-view')" in form_body
    assert "document.getElementById('refresh-views')" in form_body
    assert "saved-view-filter-group" in form_body
    assert "saved-view-filter-status" in form_body
    assert "saved-view-filter-pinned" in form_body
    assert "saved-view-display-mode" in form_body
    assert "void saveCurrentView();" in form_body
    assert "await loadSavedViews();" in init_body
    assert "applyPanelVisibility" in init_body or "syncPanelVisibilityControls" in init_body
    assert "CURRENT_MEMBER_STORAGE_KEY" in apply_body
    assert "default_saved_view_id" in saved_views_body
    assert "setDefaultHomeSavedView" in saved_views_body
    assert "applySavedViewItem" in card_body
    assert "Set Home" in card_body or "Clear Home" in card_body
    assert "Duplicate" in saved_views_body
    assert "Rename" in saved_views_body


def test_public_shares_functions_are_wired_from_form_and_initialization():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    init_body = _function_body(source, "initProviders")
    downloads_body = _function_body(source, "initDownloads")
    public_shares_body = _function_body(source, "renderPublicRunShares")
    update_body = _function_body(source, "updatePublicRunShareExpiry")

    assert "document.getElementById('refresh-public-shares')" in form_body
    assert "document.getElementById('public-shares-query')" in form_body
    assert "document.getElementById('public-shares-availability-filter')" in form_body
    assert "document.getElementById('export-public-shares-csv')" in downloads_body
    assert "await loadPublicRunShares();" in init_body
    assert "copyToClipboard" in public_shares_body
    assert "revokePublicRunShareByRunId" in public_shares_body
    assert "updatePublicRunShareExpiry" in public_shares_body
    assert "/public-share" in update_body


def test_pinned_runs_functions_are_wired_from_form_and_run_loading():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    open_body = _function_body(source, "openRunDetails")

    assert "document.getElementById('refresh-pinned-runs')" in form_body
    assert "document.getElementById('pin-current-run')" in form_body
    assert "document.getElementById('pinned-category-filter')" in form_body
    assert "document.getElementById('pinned-action-status-filter')" in form_body
    assert "document.getElementById('pinned-assignee-filter')" in form_body
    assert "void pinCurrentRun();" in form_body
    assert "void loadPinnedRuns();" in open_body


def test_action_board_functions_are_wired_from_form_and_history_updates():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    history_body = _function_body(source, "loadRunHistory")

    assert "document.getElementById('refresh-action-board')" in form_body
    assert "void loadActionBoard();" in history_body


def test_run_annotation_functions_are_wired_from_form_and_run_loading():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    open_body = _function_body(source, "openRunDetails")

    assert "document.getElementById('save-annotation')" in form_body
    assert "document.getElementById('clear-annotation')" in form_body
    assert "void saveRunAnnotation();" in form_body
    assert "void clearRunAnnotation();" in form_body
    assert "loadRunAnnotation(run.run_id);" in open_body


def test_run_review_functions_are_wired_from_form_and_run_loading():
    source = _app_js()
    form_body = _function_body(source, "initFormHandlers")
    downloads_body = _function_body(source, "initDownloads")
    open_body = _function_body(source, "openRunDetails")

    assert "document.getElementById('save-review')" in form_body
    assert "document.getElementById('clear-review')" in form_body
    assert "document.getElementById('review-history-reviewer-filter')" in form_body
    assert "document.getElementById('review-history-status-filter')" in form_body
    assert "document.getElementById('review-history-query')" in form_body
    assert "document.getElementById('export-review-history-csv')" in downloads_body
    assert "timeline-kind-review" in form_body
    assert "void saveRunReview();" in form_body
    assert "void clearRunReview();" in form_body
    assert "prepareReviewContext(run);" in open_body


def test_runtime_maintenance_renderers_use_text_content_for_runtime_data():
    source = _app_js()
    checkpoints_body = _function_body(source, "renderRuntimeCheckpoints")
    memory_body = _function_body(source, "renderRuntimeMemoryEntries")

    assert "${item.path}" not in checkpoints_body
    assert "pathEl.textContent = item.path;" in checkpoints_body
    assert "${item.decision}" not in memory_body
    assert "${item.reflection}" not in memory_body
    assert "decisionEl.textContent = item.decision;" in memory_body
    assert "reflectionEl.textContent = reflection;" in memory_body
