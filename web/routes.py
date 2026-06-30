"""FastAPI API endpoints for TradingAgents web."""

from __future__ import annotations

import asyncio
import csv
import datetime
import html
import io
import json
import statistics
import uuid
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from sse_starlette.sse import EventSourceResponse

from tradingagents.llm_clients.factory import create_llm_client
from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
from tradingagents.service.artifact_store import build_run_artifacts, resolve_run_artifact
from tradingagents.service.execution_lock import PROCESS_EXECUTION_LOCK
from tradingagents.service.runtime_admin import (
    clear_runtime_checkpoints,
    clear_runtime_memory_logs,
    list_runtime_checkpoints,
    list_runtime_memory_entries,
)
from tradingagents.service.web_state import (
    get_web_settings_path,
    get_web_state_dir,
    list_web_tenant_ids,
)
from tradingagents.settings import (
    export_api_keys_to_env,
    load_settings,
    mask_api_keys,
    save_settings,
)

from .auth import get_auth_scope
from .automation import (
    create_automation_rule,
    delete_automation_rule,
    list_automation_rules,
    process_due_automation_rules,
    run_automation_rule_now,
    update_automation_rule_enabled,
)
from .runner import (
    TERMINAL_RUN_STATUSES,
    build_terminal_event,
    cancel_run,
    create_run,
    delete_run,
    get_execution_mode,
    get_queue_position,
    get_run,
    get_service_status,
    get_state_backend,
    get_state_location,
    get_tenant_id,
    list_runs,
    retry_run,
    subscribe_run_events,
    unsubscribe_run_events,
)
from .schemas import (
    ActionBoardResponse,
    AlertCenterResponse,
    AlertHit,
    AlertRule,
    AlertRuleCreate,
    AnalysisPreset,
    AnalysisPresetCreate,
    AnalysisPresetUpdate,
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSettings,
    AnalyticsBucket,
    AnalyticsDailyActivity,
    AnalyticsSummary,
    ArtifactContent,
    ArtifactInfo,
    ArtifactLibraryItem,
    AutomationRule,
    AutomationRuleCreate,
    AutomationRuleToggleUpdate,
    AutomationRunResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    CheckpointInfo,
    CompareRun,
    DailyBriefingResponse,
    DailyBriefingSummary,
    DashboardPreferences,
    DashboardResponse,
    DashboardSummary,
    DataSettings,
    DataVendorSettings,
    DeleteResult,
    GettingStartedChecklist,
    GettingStartedChecklistItem,
    ImportRowError,
    IntegrationsSettings,
    LLMSettings,
    MemberWorkspaceResponse,
    MemberWorkspaceSummary,
    MemoryEntryInfo,
    Note,
    NoteCreate,
    NoteUpdate,
    NotificationCenterResponse,
    NotificationItem,
    NotificationReadResult,
    PinnedRun,
    PinnedRunAssigneeUpdate,
    PinnedRunCreate,
    PinnedRunStatusUpdate,
    PortfolioPosition,
    PortfolioPositionCreate,
    PortfolioResponse,
    PortfolioSummary,
    ProviderInfo,
    ProviderModel,
    PublicRunShareInfo,
    PublicRunShareListItem,
    PublicRunShareSnapshot,
    PublicRunShareUpdate,
    RunAnnotation,
    RunAnnotationCreate,
    RunBulkAction,
    RunBulkActionResult,
    RunChatRequest,
    RunChatResponse,
    RunComment,
    RunCommentCreate,
    RunCommentResolveUpdate,
    RunComparison,
    RunEvent,
    RunReview,
    RunReviewCreate,
    RunReviewHistoryResponse,
    RunReviewHistoryRow,
    RunReviewHistorySummary,
    RunStatus,
    RunSummary,
    SavedItemBulkAction,
    SavedItemBulkActionResult,
    SavedSearch,
    SavedSearchCreate,
    SavedSearchUpdate,
    SavedShortcutItem,
    SavedView,
    SavedViewCreate,
    SavedViewUpdate,
    ScreenerRow,
    ScreenerSummary,
    SecuritySettings,
    SettingsResponse,
    SettingsUpdate,
    ShareLink,
    TenantInfo,
    TickerOverview,
    ToolVendorSettings,
    WatchlistEntry,
    WatchlistUpdate,
    WorkspaceAnalyticsResponse,
    WorkspaceCalendarDay,
    WorkspaceCalendarResponse,
    WorkspaceExport,
    WorkspaceExportSummary,
    WorkspaceImportRequest,
    WorkspaceImportResult,
    WorkspaceMember,
    WorkspaceMemberCreate,
    WorkspaceScreenerResponse,
    WorkspaceSearchResponse,
    WorkspaceSearchResult,
    WorkspaceSettings,
    WorkspaceSnapshotImportRequest,
    WorkspaceSnapshotImportResult,
    WorkspaceTimelineEvent,
    WorkspaceTimelineResponse,
)
from .webhook_delivery import process_pending_webhook_notifications
from .workspace_import import (
    ParsedImportError,
    parse_portfolio_import,
    parse_watchlist_import,
)

router = APIRouter()

# Friendly display names for providers
_PROVIDER_DISPLAY_NAMES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google Gemini",
    "xai": "xAI (Grok)",
    "deepseek": "DeepSeek",
    "qwen": "Qwen (International)",
    "qwen-cn": "Qwen (China)",
    "glm": "GLM (Z.AI International)",
    "glm-cn": "GLM (BigModel China)",
    "minimax": "MiniMax (International)",
    "minimax-cn": "MiniMax (China)",
    "ollama": "Ollama (Local)",
    "openai_compatible": "OpenAI-Compatible",
    "mistral": "Mistral",
    "kimi": "Kimi",
    "groq": "Groq",
    "nvidia": "NVIDIA",
    "bedrock": "AWS Bedrock",
}

_CRYPTO_TICKER_HINTS = ("BTC", "ETH", "USDT", "BNB", "SOL", "XRP", "DOGE", "ADA", "-USD")
_DEFAULT_DASHBOARD_SECTIONS = [
    "bullish_focus",
    "needs_attention",
    "active_alerts",
    "portfolio_focus",
    "pinned_actions",
    "pending_reviews",
    "automations",
    "saved_shortcuts",
    "operational_runs",
]


def _request_tenant_id(request: Request) -> str | None:
    return request.headers.get("X-TradingAgents-Tenant") or request.query_params.get("tenant_id") or None


def _process_due_automations_if_local(tenant_id: str | None = None) -> None:
    if get_execution_mode() == "external_worker":
        return
    process_due_automation_rules(tenant_id, start_worker=True)


def _process_webhook_notifications_if_local(tenant_id: str | None = None) -> None:
    if get_execution_mode() == "external_worker":
        return
    process_pending_webhook_notifications(tenant_id)


def _infer_asset_type(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if any(hint in normalized for hint in _CRYPTO_TICKER_HINTS):
        return "crypto"
    return "stock"


def _analysis_response_from_run(run) -> AnalysisResponse:
    return AnalysisResponse(
        run_id=run.run_id,
        status=run.status,
        ticker=run.ticker,
        date=run.date,
    )


def _require_tenant_scoped_system_access(request: Request) -> None:
    """Protect explicit tenant maintenance APIs until real tenant membership exists."""
    requested_tenant_id = _request_tenant_id(request)
    if requested_tenant_id and get_auth_scope(requested_tenant_id) != "tenant":
        raise HTTPException(
            status_code=403,
            detail="Explicit tenant system access requires a tenant-scoped API token.",
        )


@router.get("/api/system/status")
async def get_system_status(request: Request):
    """Return a compact operational snapshot for the current Web runtime."""
    tenant_id = _request_tenant_id(request)
    _process_due_automations_if_local(tenant_id)
    _process_webhook_notifications_if_local(tenant_id)
    return {
        "execution_mode": get_execution_mode(),
        "tenant_id": get_tenant_id(tenant_id),
        "auth_scope": get_auth_scope(tenant_id),
        "state_backend": get_state_backend(),
        "state_location": get_state_location(tenant_id),
        **get_service_status(tenant_id),
    }


@router.get("/api/system/tenants", response_model=list[TenantInfo])
async def get_system_tenants(request: Request):
    """Return known tenant namespaces for quick switching in the UI."""
    if get_auth_scope(_request_tenant_id(request)) != "tenant":
        raise HTTPException(
            status_code=403,
            detail="Tenant discovery requires a tenant-scoped API token.",
        )
    current_tenant_id = get_tenant_id(_request_tenant_id(request))
    discovered = list_web_tenant_ids()
    entries: list[TenantInfo] = []
    seen: set[str] = set()

    def _append(tenant_id: str | None, label: str, active: bool) -> None:
        key = tenant_id or "__default__"
        if key in seen:
            return
        seen.add(key)
        entries.append(TenantInfo(tenant_id=tenant_id, label=label, active=active))

    _append(None, "default", current_tenant_id is None)
    for tenant_id in discovered:
        _append(tenant_id, tenant_id, tenant_id == current_tenant_id)
    if current_tenant_id is not None and current_tenant_id not in discovered:
        _append(current_tenant_id, current_tenant_id, True)
    return entries


@router.get("/api/system/checkpoints", response_model=list[CheckpointInfo])
async def get_runtime_checkpoints(request: Request):
    """List checkpoint DB files stored for the current tenant."""
    _require_tenant_scoped_system_access(request)
    tenant_id = _request_tenant_id(request)
    return list_runtime_checkpoints(state_root=get_web_state_dir(tenant_id))


@router.delete("/api/system/checkpoints", response_model=DeleteResult)
async def delete_runtime_checkpoints(request: Request, ticker: str | None = None):
    """Delete checkpoint DB files for the current tenant."""
    _require_tenant_scoped_system_access(request)
    tenant_id = _request_tenant_id(request)
    deleted = clear_runtime_checkpoints(
        state_root=get_web_state_dir(tenant_id),
        ticker=ticker,
    )
    return DeleteResult(deleted=deleted)


@router.get("/api/system/memory", response_model=list[MemoryEntryInfo])
async def get_runtime_memory(request: Request):
    """List tenant-scoped decision-memory entries for the current tenant."""
    _require_tenant_scoped_system_access(request)
    tenant_id = _request_tenant_id(request)
    return list_runtime_memory_entries(state_root=get_web_state_dir(tenant_id))


@router.delete("/api/system/memory", response_model=DeleteResult)
async def delete_runtime_memory(request: Request):
    """Delete the tenant-scoped decision-memory log for the current tenant."""
    _require_tenant_scoped_system_access(request)
    tenant_id = _request_tenant_id(request)
    deleted = clear_runtime_memory_logs(state_root=get_web_state_dir(tenant_id))
    return DeleteResult(deleted=deleted)


def _run_config_summary(run) -> dict[str, object]:
    config = run.config or {}
    return {
        "selected_analysts": list(run.selected_analysts),
        "llm_provider": config.get("llm_provider"),
        "quick_think_model": config.get("quick_think_llm"),
        "deep_think_model": config.get("deep_think_llm"),
        "output_language": config.get("output_language"),
        "market_profile": config.get("market_profile"),
        "research_depth": config.get("max_debate_rounds"),
        "max_risk_discuss_rounds": config.get("max_risk_discuss_rounds"),
        "checkpoint_enabled": config.get("checkpoint_enabled"),
        "benchmark_ticker": config.get("benchmark_ticker"),
        "memory_log_max_entries": config.get("memory_log_max_entries"),
        "temperature": config.get("temperature"),
        "backend_url": config.get("backend_url"),
        "data_vendors": dict(config.get("data_vendors", {})),
        "tool_vendors": dict(config.get("tool_vendors", {})),
        "news_article_limit": config.get("news_article_limit"),
        "global_news_article_limit": config.get("global_news_article_limit"),
        "global_news_lookback_days": config.get("global_news_lookback_days"),
        "global_news_queries": list(config.get("global_news_queries", [])),
    }


def _normalize_ticker_symbol(raw_ticker: str) -> str:
    ticker = raw_ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker must not be blank")
    return ticker


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


def _load_settings_for_update(settings_path) -> dict:
    """Load a detached settings snapshot before mutating and saving it."""
    settings = load_settings(path=settings_path)
    return deepcopy(settings) if isinstance(settings, dict) else {}


def _load_watchlist_items(tenant_id: str | None = None) -> list[dict[str, object]]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("watchlist", {}).get("tickers", [])
    if not isinstance(raw, list):
        return []

    items: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            normalized = item.strip().upper()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            items.append({
                "id": f"legacy-{normalized}",
                "ticker": normalized,
                "created_at": None,
            })
            continue
        if not isinstance(item, dict):
            continue
        ticker = item.get("ticker")
        if not isinstance(ticker, str):
            continue
        normalized = ticker.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        item_id = item.get("id")
        created_at = item.get("created_at")
        items.append({
            "id": item_id if isinstance(item_id, str) else f"legacy-{normalized}",
            "ticker": normalized,
            "created_at": created_at if isinstance(created_at, str) else None,
        })
    return items


def _load_watchlist_tickers(tenant_id: str | None = None) -> list[str]:
    return [str(item["ticker"]) for item in _load_watchlist_items(tenant_id)]


def _resolve_batch_tickers(payload: BatchAnalysisRequest, tenant_id: str | None) -> list[str]:
    if payload.source == "watchlist":
        return _load_watchlist_tickers(tenant_id)
    return payload.tickers


def _save_watchlist_items(tenant_id: str | None, items: list[dict[str, object]]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    watchlist = existing.get("watchlist", {})
    if not isinstance(watchlist, dict):
        watchlist = {}
    watchlist["tickers"] = items
    existing["watchlist"] = watchlist
    save_settings(existing, path=settings_path)


def _normalize_alert_value(field: str, value: str) -> str:
    trimmed = value.strip()
    if field == "signal":
        return trimmed.title()
    if field == "status":
        return trimmed.lower()
    return trimmed


def _load_alert_rules(tenant_id: str | None = None) -> list[AlertRule]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("alerts", {}).get("rules", [])
    if not isinstance(raw, list):
        return []

    rules: list[AlertRule] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        ticker = item.get("ticker")
        field = item.get("field")
        value = item.get("value")
        rule_id = item.get("id")
        if not all(isinstance(part, str) for part in (ticker, field, value, rule_id)):
            continue
        normalized_field = field.strip().lower()
        if normalized_field not in {"signal", "status"}:
            continue
        rules.append(AlertRule(
            id=rule_id,
            ticker=ticker.strip().upper(),
            field=normalized_field,
            value=_normalize_alert_value(normalized_field, value),
            created_at=item.get("created_at") if isinstance(item.get("created_at"), str) else None,
        ))
    return rules


def _save_alert_rules(tenant_id: str | None, rules: list[AlertRule]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    alerts = existing.get("alerts", {})
    if not isinstance(alerts, dict):
        alerts = {}
    alerts["rules"] = [rule.model_dump() for rule in rules]
    existing["alerts"] = alerts
    save_settings(existing, path=settings_path)


def _load_portfolio_positions(tenant_id: str | None = None) -> list[dict[str, object]]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("portfolio", {}).get("positions", [])
    if not isinstance(raw, list):
        return []

    positions: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if not isinstance(item.get("id"), str) or not isinstance(item.get("ticker"), str):
            continue
        try:
            quantity = float(item.get("quantity"))
            average_cost = float(item.get("average_cost"))
        except (TypeError, ValueError):
            continue
        if quantity <= 0 or average_cost < 0:
            continue
        positions.append({
            "id": item["id"],
            "ticker": item["ticker"].strip().upper(),
            "quantity": quantity,
            "average_cost": average_cost,
            "created_at": item.get("created_at") if isinstance(item.get("created_at"), str) else None,
        })
    return positions


def _save_portfolio_positions(tenant_id: str | None, positions: list[dict[str, object]]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    portfolio = existing.get("portfolio", {})
    if not isinstance(portfolio, dict):
        portfolio = {}
    portfolio["positions"] = positions
    existing["portfolio"] = portfolio
    save_settings(existing, path=settings_path)


def _build_workspace_import_result(
    *,
    imported_count: int,
    skipped_count: int = 0,
    errors: list[ParsedImportError] | None = None,
) -> WorkspaceImportResult:
    row_errors = [
        ImportRowError(
            line_number=item.line_number,
            message=item.message,
            raw_value=item.raw_value,
        )
        for item in (errors or [])
    ]
    return WorkspaceImportResult(
        imported_count=imported_count,
        skipped_count=skipped_count,
        error_count=len(row_errors),
        errors=row_errors,
    )


def _load_workspace_settings_model(tenant_id: str | None = None) -> WorkspaceSettings:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("workspace", {})
    if not isinstance(raw, dict):
        raw = {}
    try:
        return WorkspaceSettings.model_validate(raw)
    except Exception:
        return WorkspaceSettings()


def _save_workspace_settings_model(tenant_id: str | None, workspace_settings: WorkspaceSettings) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    existing["workspace"] = {
        "default_home_view": workspace_settings.default_home_view,
        "default_saved_view_id": workspace_settings.default_saved_view_id,
    }
    save_settings(existing, path=settings_path)


def _merge_model_items(existing: list, imported: list, key_func) -> list:
    merged = {key_func(item): item for item in existing}
    ordered_keys = [key_func(item) for item in existing]
    for item in imported:
        key = key_func(item)
        if key not in merged:
            ordered_keys.append(key)
        merged[key] = item
    return [merged[key] for key in ordered_keys if key in merged]


def _watchlist_items_from_export(entries: list[WatchlistEntry]) -> list[dict[str, object]]:
    seen: set[str] = set()
    items: list[dict[str, object]] = []
    for entry in entries:
        ticker = entry.ticker.strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        items.append({
            "id": f"import-{ticker.lower()}",
            "ticker": ticker,
            "created_at": entry.created_at,
        })
    return items


def _portfolio_positions_from_export(positions: list[PortfolioPosition]) -> list[dict[str, object]]:
    return [
        {
            "id": item.id,
            "ticker": item.ticker,
            "quantity": item.quantity,
            "average_cost": item.average_cost,
            "created_at": item.created_at,
        }
        for item in positions
    ]


def _build_workspace_snapshot_import_result(
    mode: str,
    *,
    watchlist_count: int,
    alert_rule_count: int,
    portfolio_position_count: int,
    pinned_run_count: int,
    note_count: int,
    preset_count: int,
    saved_search_count: int,
    saved_view_count: int,
    annotation_count: int,
    member_count: int,
    comment_count: int,
    review_count: int,
) -> WorkspaceSnapshotImportResult:
    return WorkspaceSnapshotImportResult(
        mode=mode,
        watchlist_count=watchlist_count,
        alert_rule_count=alert_rule_count,
        portfolio_position_count=portfolio_position_count,
        pinned_run_count=pinned_run_count,
        note_count=note_count,
        preset_count=preset_count,
        saved_search_count=saved_search_count,
        saved_view_count=saved_view_count,
        annotation_count=annotation_count,
        member_count=member_count,
        comment_count=comment_count,
        review_count=review_count,
    )


def _safe_tenant_slug(tenant_id: str | None) -> str:
    return "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-"
        for ch in (tenant_id or "default")
    ) or "default"


def _build_csv_download_response(
    *,
    tenant_id: str | None,
    prefix: str,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> Response:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({
            key: "" if row.get(key) is None else row.get(key)
            for key in fieldnames
        })
    timestamp = _now_iso()[:19].replace(":", "-")
    filename = f"tradingagents-{prefix}-{_safe_tenant_slug(tenant_id)}-{timestamp}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_artifact_library_items(
    tenant_id: str | None,
    *,
    q: str | None = None,
) -> list[ArtifactLibraryItem]:
    normalized_query = str(q or "").strip().lower()
    items: list[ArtifactLibraryItem] = []
    for run in list_runs(tenant_id):
        artifacts = build_run_artifacts(
            report_path=run.report_path,
            state_log_path=run.state_log_path,
        )
        if not artifacts:
            continue
        if normalized_query and not _matches_query(
            normalized_query,
            run.run_id,
            run.ticker,
            run.date,
            run.status,
            run.signal,
            run.error,
        ):
            continue
        report_artifact = next((item for item in artifacts if item.key == "complete-report"), None)
        state_artifact = next((item for item in artifacts if item.key == "full-state"), None)
        items.append(ArtifactLibraryItem(
            run_id=run.run_id,
            ticker=run.ticker,
            date=run.date,
            status=run.status,
            created_at=run.created_at,
            signal=run.signal,
            error=run.error,
            artifact_count=len(artifacts),
            report_download_url=(
                f"/api/runs/{run.run_id}/artifacts/download?name={report_artifact.key}"
                if report_artifact is not None else None
            ),
            state_download_url=(
                f"/api/runs/{run.run_id}/artifacts/download?name={state_artifact.key}"
                if state_artifact is not None else None
            ),
        ))
    items.sort(key=lambda item: item.created_at, reverse=True)
    return items


def _load_presets(tenant_id: str | None = None) -> list[AnalysisPreset]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("presets", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    presets: list[AnalysisPreset] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            presets.append(AnalysisPreset.model_validate(item))
        except Exception:
            continue
    return presets


def _save_presets(tenant_id: str | None, presets: list[AnalysisPreset]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    preset_bucket = existing.get("presets", {})
    if not isinstance(preset_bucket, dict):
        preset_bucket = {}
    preset_bucket["items"] = [preset.model_dump(exclude_none=True) for preset in presets]
    existing["presets"] = preset_bucket
    save_settings(existing, path=settings_path)


def _load_notes(tenant_id: str | None = None) -> list[Note]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("notes", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    notes: list[Note] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            notes.append(Note.model_validate(item))
        except Exception:
            continue
    notes.sort(key=lambda note: note.created_at, reverse=True)
    return notes


def _save_notes(tenant_id: str | None, notes: list[Note]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("notes", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [note.model_dump(exclude_none=True) for note in notes]
    existing["notes"] = bucket
    save_settings(existing, path=settings_path)


def _load_run_comments(tenant_id: str | None = None) -> list[RunComment]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("run_comments", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    comments: list[RunComment] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            comments.append(RunComment.model_validate(item))
        except Exception:
            continue
    comments.sort(key=lambda comment: comment.created_at)
    return comments


def _save_run_comments(tenant_id: str | None, comments: list[RunComment]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("run_comments", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [comment.model_dump(exclude_none=True) for comment in comments]
    existing["run_comments"] = bucket
    save_settings(existing, path=settings_path)


def _load_run_annotations(tenant_id: str | None = None) -> list[RunAnnotation]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("run_annotations", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    annotations: list[RunAnnotation] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            annotations.append(RunAnnotation.model_validate(item))
        except Exception:
            continue
    return annotations


def _save_run_annotations(tenant_id: str | None, annotations: list[RunAnnotation]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("run_annotations", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [item.model_dump(exclude_none=True) for item in annotations]
    existing["run_annotations"] = bucket
    save_settings(existing, path=settings_path)


def _get_run_annotation(run_id: str, tenant_id: str | None = None) -> RunAnnotation | None:
    return next((item for item in _load_run_annotations(tenant_id) if item.run_id == run_id), None)


def _load_run_reviews(tenant_id: str | None = None) -> list[RunReview]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("run_reviews", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    reviews: list[RunReview] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            reviews.append(RunReview.model_validate(item))
        except Exception:
            continue
    return reviews


def _save_run_reviews(tenant_id: str | None, reviews: list[RunReview]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("run_reviews", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [item.model_dump(exclude_none=True) for item in reviews]
    existing["run_reviews"] = bucket
    save_settings(existing, path=settings_path)


def _get_run_review(run_id: str, tenant_id: str | None = None) -> RunReview | None:
    return next((item for item in _load_run_reviews(tenant_id) if item.run_id == run_id), None)


def _load_notification_reads(tenant_id: str | None = None) -> dict[str, str]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("notifications", {}).get("read_items", [])
    if not isinstance(raw, list):
        return {}

    reads: dict[str, str] = {}
    for item in raw:
        if isinstance(item, str):
            if item:
                reads[item] = ""
            continue
        if not isinstance(item, dict):
            continue
        notification_id = item.get("id")
        read_at = item.get("read_at")
        if not isinstance(notification_id, str) or not notification_id:
            continue
        reads[notification_id] = read_at if isinstance(read_at, str) else ""
    return reads


def _save_notification_reads(tenant_id: str | None, reads: dict[str, str]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("notifications", {})
    if not isinstance(bucket, dict):
        bucket = {}
    ordered = sorted(reads.items(), key=lambda item: item[1] or "", reverse=True)[:500]
    bucket["read_items"] = [
        {"id": notification_id, "read_at": read_at or None}
        for notification_id, read_at in ordered
    ]
    existing["notifications"] = bucket
    save_settings(existing, path=settings_path)


def _load_archived_run_ids(tenant_id: str | None = None) -> set[str]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("archived_runs", {}).get("ids", [])
    if not isinstance(raw, list):
        return set()
    return {
        item.strip()
        for item in raw
        if isinstance(item, str) and item.strip()
    }


def _save_archived_run_ids(tenant_id: str | None, run_ids: set[str]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("archived_runs", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["ids"] = sorted(run_ids)
    existing["archived_runs"] = bucket
    save_settings(existing, path=settings_path)


def _load_public_run_shares(tenant_id: str | None = None) -> list[PublicRunShareSnapshot]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("public_run_shares", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    items: list[PublicRunShareSnapshot] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            items.append(PublicRunShareSnapshot.model_validate(item))
        except Exception:
            continue
    return items


def _save_public_run_shares(tenant_id: str | None, shares: list[PublicRunShareSnapshot]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("public_run_shares", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [item.model_dump() for item in shares]
    existing["public_run_shares"] = bucket
    save_settings(existing, path=settings_path)


def _build_public_share_url(share_id: str) -> str:
    return f"/shared/{share_id}"


def _get_public_run_share_for_run(run_id: str, tenant_id: str | None = None) -> PublicRunShareSnapshot | None:
    return next((item for item in _load_public_run_shares(tenant_id) if item.run_id == run_id), None)


def _build_public_share_info(snapshot: PublicRunShareSnapshot | None) -> PublicRunShareInfo | None:
    if snapshot is None:
        return None
    return PublicRunShareInfo(
        share_id=snapshot.share_id,
        url=_build_public_share_url(snapshot.share_id),
        created_at=snapshot.created_at,
        view_count=snapshot.view_count,
        last_viewed_at=snapshot.last_viewed_at,
        expires_at=snapshot.expires_at,
        share_title=snapshot.share_title,
        share_summary=snapshot.share_summary,
    )


def _build_public_share_list_item(snapshot: PublicRunShareSnapshot) -> PublicRunShareListItem:
    return PublicRunShareListItem(
        share_id=snapshot.share_id,
        url=_build_public_share_url(snapshot.share_id),
        created_at=snapshot.created_at,
        run_id=snapshot.run_id,
        ticker=snapshot.ticker,
        date=snapshot.date,
        status=snapshot.status,
        signal=snapshot.signal,
        view_count=snapshot.view_count,
        last_viewed_at=snapshot.last_viewed_at,
        expires_at=snapshot.expires_at,
        share_title=snapshot.share_title,
        share_summary=snapshot.share_summary,
    )


def _is_public_share_expired(snapshot: PublicRunShareSnapshot) -> bool:
    if not snapshot.expires_at:
        return False
    try:
        return datetime.datetime.fromisoformat(snapshot.expires_at) < datetime.datetime.now()
    except ValueError:
        return True


def _find_public_run_share(share_id: str) -> PublicRunShareSnapshot | None:
    located = _find_public_run_share_location(share_id)
    return located[1] if located is not None else None


def _find_public_run_share_location(share_id: str) -> tuple[str | None, PublicRunShareSnapshot] | None:
    for tenant_id in [None, *list_web_tenant_ids()]:
        match = next((item for item in _load_public_run_shares(tenant_id) if item.share_id == share_id), None)
        if match is not None:
            return tenant_id, match
    return None


def _load_saved_searches(tenant_id: str | None = None) -> list[SavedSearch]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("saved_searches", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    searches: list[SavedSearch] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            searches.append(SavedSearch.model_validate(item))
        except Exception:
            continue
    searches.sort(
        key=lambda item: (
            item.archived,
            not item.pinned,
            (item.group or "~").lower(),
            item.created_at or "",
            item.name.lower(),
        )
    )
    return searches


def _save_saved_searches(tenant_id: str | None, searches: list[SavedSearch]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("saved_searches", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [search.model_dump(exclude_none=True) for search in searches]
    existing["saved_searches"] = bucket
    save_settings(existing, path=settings_path)


def _load_saved_views(tenant_id: str | None = None) -> list[SavedView]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("saved_views", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    views: list[SavedView] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            views.append(SavedView.model_validate(item))
        except Exception:
            continue
    views.sort(
        key=lambda item: (
            item.archived,
            not item.pinned,
            (item.group or "~").lower(),
            item.created_at or "",
            item.name.lower(),
        )
    )
    return views


def _save_saved_views(tenant_id: str | None, views: list[SavedView]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("saved_views", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [view.model_dump(exclude_none=True) for view in views]
    existing["saved_views"] = bucket
    save_settings(existing, path=settings_path)


def _load_workspace_members(tenant_id: str | None = None) -> list[WorkspaceMember]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("workspace_members", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    members: list[WorkspaceMember] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            member = WorkspaceMember.model_validate(item)
        except Exception:
            continue
        normalized = member.name.strip().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        members.append(member)
    return members


def _save_workspace_members(tenant_id: str | None, members: list[WorkspaceMember]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("workspace_members", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [member.model_dump(exclude_none=True) for member in members]
    existing["workspace_members"] = bucket
    save_settings(existing, path=settings_path)


def _workspace_member_names(tenant_id: str | None = None) -> set[str]:
    return {member.name for member in _load_workspace_members(tenant_id)}


def _get_workspace_member(member_id: str, tenant_id: str | None = None) -> WorkspaceMember | None:
    return next((member for member in _load_workspace_members(tenant_id) if member.id == member_id), None)


def _extract_comment_mentions(content: str, tenant_id: str | None = None) -> list[str]:
    lowered = content.lower()
    mentions: list[str] = []
    for member in _load_workspace_members(tenant_id):
        needle = f"@{member.name}".lower()
        if needle in lowered:
            mentions.append(member.name)
    return mentions


def _load_pinned_runs(tenant_id: str | None = None) -> list[PinnedRun]:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("pinned_runs", {}).get("items", [])
    if not isinstance(raw, list):
        return []

    pinned: list[PinnedRun] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            pinned.append(PinnedRun.model_validate(item))
        except Exception:
            continue
    return pinned


def _load_dashboard_preferences(tenant_id: str | None = None) -> DashboardPreferences:
    settings = load_settings(path=get_web_settings_path(tenant_id))
    raw = settings.get("dashboard", {})
    if not isinstance(raw, dict):
        raw = {}
    try:
        prefs = DashboardPreferences.model_validate(raw)
    except Exception:
        prefs = DashboardPreferences()
    if not prefs.visible_sections:
        prefs.visible_sections = list(_DEFAULT_DASHBOARD_SECTIONS)
    order = prefs.section_order or []
    prefs.section_order = [
        *[section for section in order if section in _DEFAULT_DASHBOARD_SECTIONS],
        *[section for section in _DEFAULT_DASHBOARD_SECTIONS if section not in order],
    ]
    return prefs


def _save_dashboard_preferences(tenant_id: str | None, prefs: DashboardPreferences) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    existing["dashboard"] = {
        "visible_sections": prefs.visible_sections or list(_DEFAULT_DASHBOARD_SECTIONS),
        "section_order": prefs.section_order or list(_DEFAULT_DASHBOARD_SECTIONS),
    }
    save_settings(existing, path=settings_path)


def _save_pinned_runs(tenant_id: str | None, pinned_runs: list[PinnedRun]) -> None:
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)
    bucket = existing.get("pinned_runs", {})
    if not isinstance(bucket, dict):
        bucket = {}
    bucket["items"] = [item.model_dump(exclude_none=True) for item in pinned_runs]
    existing["pinned_runs"] = bucket
    save_settings(existing, path=settings_path)


def _note_matches_query(note: Note, query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return True
    if normalized in note.content.lower():
        return True
    return any(normalized in tag for tag in note.tags)


def _matches_query(query: str, *parts: object) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    return any(normalized in str(part).lower() for part in parts if part is not None)


def _build_duplicate_name(existing_names: list[str], base_name: str) -> str:
    trimmed = base_name.strip() or "Untitled"
    candidate = f"{trimmed} Copy"
    taken = {name.strip().lower() for name in existing_names}
    if candidate.strip().lower() not in taken:
        return candidate
    counter = 2
    while True:
        candidate = f"{trimmed} Copy {counter}"
        if candidate.strip().lower() not in taken:
            return candidate
        counter += 1


def _normalize_run_filter(raw_value: str | None) -> str | None:
    normalized = str(raw_value or "").strip().lower()
    return normalized or None


def _normalize_run_archive_scope(raw_value: str | None) -> str:
    normalized = str(raw_value or "active").strip().lower()
    return normalized if normalized in {"active", "archived", "all"} else "active"


def _filter_runs(
    runs: list,
    *,
    q: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    asset_type: str | None = None,
    archived_scope: str = "active",
    archived_run_ids: set[str] | None = None,
) -> list:
    normalized_query = str(q or "").strip().lower()
    normalized_status = _normalize_run_filter(status)
    normalized_provider = _normalize_run_filter(provider)
    normalized_asset = _normalize_run_filter(asset_type)
    resolved_scope = _normalize_run_archive_scope(archived_scope)
    archived_ids = archived_run_ids or set()

    filtered = []
    for run in runs:
        is_archived = run.run_id in archived_ids
        if resolved_scope == "active" and is_archived:
            continue
        if resolved_scope == "archived" and not is_archived:
            continue
        run_status = str(run.status or "").strip().lower()
        run_provider = str(run.config.get("llm_provider") or "").strip().lower()
        run_asset = str(run.asset_type or "").strip().lower()
        if normalized_status and run_status != normalized_status:
            continue
        if normalized_provider and run_provider != normalized_provider:
            continue
        if normalized_asset and run_asset != normalized_asset:
            continue
        if normalized_query and not _matches_query(
            normalized_query,
            run.run_id,
            run.ticker,
            run.date,
            run.signal,
            run.error,
            run.status,
            run_provider,
            run_asset,
            "archived" if is_archived else "active",
        ):
            continue
        filtered.append(run)
    return filtered


def _normalize_search_kinds(raw_kinds: str | None) -> list[str]:
    allowed = {"run", "note", "watchlist", "portfolio", "preset", "search", "view", "member", "share", "alert", "comment", "review"}
    if not raw_kinds:
        return []
    kinds: list[str] = []
    seen: set[str] = set()
    for item in raw_kinds.split(","):
        normalized = item.strip().lower()
        if normalized not in allowed or normalized in seen:
            continue
        seen.add(normalized)
        kinds.append(normalized)
    return kinds


def _normalize_timeline_kinds(raw_kinds: str | None) -> list[str]:
    allowed = {"run", "note", "watchlist", "portfolio", "preset", "search", "view", "member", "share", "alert", "pin", "annotation", "comment", "review"}
    if not raw_kinds:
        return []
    kinds: list[str] = []
    seen: set[str] = set()
    for item in raw_kinds.split(","):
        normalized = item.strip().lower()
        if normalized not in allowed or normalized in seen:
            continue
        seen.add(normalized)
        kinds.append(normalized)
    return kinds


def _build_run_summary(run, tenant_id: str | None = None) -> RunSummary:
    archived_run_ids = _load_archived_run_ids(tenant_id)
    return RunSummary(
        run_id=run.run_id,
        status=run.status,
        ticker=run.ticker,
        date=run.date,
        asset_type=run.asset_type,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        queue_position=get_queue_position(run.run_id, tenant_id),
        llm_provider=str(run.config.get("llm_provider") or "") or None,
        archived=run.run_id in archived_run_ids,
        signal=run.signal,
        error=run.error,
        annotation=_get_run_annotation(run.run_id, tenant_id),
        review=_get_run_review(run.run_id, tenant_id),
    )


def _build_ticker_overview(normalized: str, tenant_id: str | None, runs: list | None = None) -> TickerOverview:
    candidate_runs = runs if runs is not None else list_runs(tenant_id)
    matched_runs = [
        run for run in candidate_runs
        if run.ticker.upper() == normalized
    ]
    matched_runs.sort(key=lambda run: run.created_at or "", reverse=True)
    latest = matched_runs[0] if matched_runs else None

    return TickerOverview(
        ticker=normalized,
        run_count=len(matched_runs),
        latest_run_id=latest.run_id if latest else None,
        latest_signal=latest.signal if latest else None,
        latest_status=latest.status if latest else None,
        latest_date=latest.date if latest else None,
        latest_created_at=latest.created_at if latest else None,
        recent_runs=[_build_run_summary(run, tenant_id) for run in matched_runs[:5]],
    )


def _watchlist_entry_from_overview(overview: TickerOverview, *, created_at: str | None = None) -> WatchlistEntry:
    return WatchlistEntry(
        ticker=overview.ticker,
        run_count=overview.run_count,
        created_at=created_at,
        latest_run_id=overview.latest_run_id,
        latest_signal=overview.latest_signal,
        latest_status=overview.latest_status,
        latest_date=overview.latest_date,
        latest_created_at=overview.latest_created_at,
    )


def _build_watchlist_entries(tenant_id: str | None, runs: list | None = None) -> list[WatchlistEntry]:
    resolved_runs = list_runs(tenant_id) if runs is None else runs
    items = _load_watchlist_items(tenant_id)
    return [
        _watchlist_entry_from_overview(
            _build_ticker_overview(str(item["ticker"]), tenant_id, resolved_runs),
            created_at=item.get("created_at") if isinstance(item.get("created_at"), str) else None,
        )
        for item in items
    ]


def _build_compare_run(run) -> CompareRun:
    return CompareRun(
        run_id=run.run_id,
        status=run.status,
        ticker=run.ticker,
        date=run.date,
        asset_type=run.asset_type,
        created_at=run.created_at,
        signal=run.signal,
        error=run.error,
        config_summary=_run_config_summary(run),
        report_sections=dict(run.report_sections),
    )


def _get_provider_kwargs_from_config(config: dict[str, object]) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    provider = str(config.get("llm_provider", "")).lower()

    if provider == "google":
        thinking_level = config.get("google_thinking_level")
        if thinking_level:
            kwargs["thinking_level"] = thinking_level
    elif provider == "openai":
        reasoning_effort = config.get("openai_reasoning_effort")
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
    elif provider == "anthropic":
        effort = config.get("anthropic_effort")
        if effort:
            kwargs["effort"] = effort

    temperature = config.get("temperature")
    if temperature is not None and temperature != "":
        kwargs["temperature"] = float(temperature)
    return kwargs


def _diff_summary_fields(left: CompareRun, right: CompareRun) -> list[str]:
    differing: list[str] = []
    comparable_keys = sorted(set(left.config_summary) | set(right.config_summary))
    for key in comparable_keys:
        if left.config_summary.get(key) != right.config_summary.get(key):
            differing.append(key)

    top_level_pairs = {
        "status": (left.status, right.status),
        "signal": (left.signal, right.signal),
        "date": (left.date, right.date),
        "ticker": (left.ticker, right.ticker),
    }
    for key, (left_value, right_value) in top_level_pairs.items():
        if left_value != right_value:
            differing.append(key)
    return differing


def _diff_sections(left: CompareRun, right: CompareRun) -> tuple[list[str], list[str]]:
    section_keys = sorted(
        key for key in set(left.report_sections) | set(right.report_sections)
        if left.report_sections.get(key) or right.report_sections.get(key)
    )
    differing = [
        key for key in section_keys
        if (left.report_sections.get(key) or "") != (right.report_sections.get(key) or "")
    ]
    return section_keys, differing


def _build_run_chat_context(run) -> str:
    if run.final_report:
        return run.final_report
    if run.current_report:
        return run.current_report

    parts: list[str] = []
    for key, content in run.report_sections.items():
        if not content:
            continue
        label = key.replace("_", " ").title()
        parts.append(f"## {label}\n{content}")
    return "\n\n".join(parts)


def _build_follow_up_prompt(run, request: RunChatRequest) -> str:
    config_summary = _run_config_summary(run)
    summary_lines = [
        f"- ticker: {run.ticker}",
        f"- analysis_date: {run.date}",
        f"- signal: {run.signal or 'unknown'}",
        f"- status: {run.status}",
        f"- llm_provider: {config_summary.get('llm_provider')}",
        f"- research_depth: {config_summary.get('research_depth')}",
        f"- market_profile: {config_summary.get('market_profile')}",
    ]

    history_lines: list[str] = []
    for message in request.history:
        prefix = "User" if message.role == "user" else "Assistant"
        history_lines.append(f"{prefix}: {message.content}")

    report_context = _build_run_chat_context(run)
    return (
        "You are a follow-up research assistant for TradingAgents.\n"
        "Answer strictly from the saved run context below. If the answer is not supported by the saved run, say so explicitly.\n"
        "Be concise, evidence-based, and reference the saved analysis when possible.\n\n"
        "Run summary:\n"
        f"{chr(10).join(summary_lines)}\n\n"
        "Saved report context:\n"
        f"{report_context or 'No saved report context available.'}\n\n"
        "Prior chat history:\n"
        f"{chr(10).join(history_lines) if history_lines else 'No prior chat history.'}\n\n"
        f"User question: {request.question}\n"
        "Answer:"
    )


def _build_alert_hit(rule: AlertRule, overview: TickerOverview) -> AlertHit | None:
    if not overview.latest_run_id:
        return None

    actual_value = overview.latest_signal if rule.field == "signal" else overview.latest_status

    if not actual_value:
        return None
    if str(actual_value).lower() != str(rule.value).lower():
        return None

    return AlertHit(
        rule_id=rule.id,
        ticker=rule.ticker,
        field=rule.field,
        expected_value=rule.value,
        actual_value=str(actual_value),
        run_id=overview.latest_run_id,
        run_date=overview.latest_date or "",
        message=f"{rule.ticker} latest {rule.field} matched {rule.value}.",
    )


def _build_alert_center_response(tenant_id: str | None, runs: list | None = None) -> AlertCenterResponse:
    resolved_runs = list_runs(tenant_id) if runs is None else runs
    rules = _load_alert_rules(tenant_id)
    hits: list[AlertHit] = []
    for rule in rules:
        hit = _build_alert_hit(rule, _build_ticker_overview(rule.ticker, tenant_id, resolved_runs))
        if hit is not None:
            hits.append(hit)
    return AlertCenterResponse(rules=rules, hits=hits)


def _build_portfolio_position(position: dict[str, object], tenant_id: str | None, runs: list | None = None) -> PortfolioPosition:
    overview = _build_ticker_overview(str(position["ticker"]), tenant_id, runs)
    quantity = float(position["quantity"])
    average_cost = float(position["average_cost"])
    return PortfolioPosition(
        id=str(position["id"]),
        ticker=str(position["ticker"]),
        quantity=quantity,
        average_cost=average_cost,
        cost_basis=round(quantity * average_cost, 6),
        created_at=position.get("created_at") if isinstance(position.get("created_at"), str) else None,
        latest_signal=overview.latest_signal,
        latest_status=overview.latest_status,
        latest_date=overview.latest_date,
    )


def _build_portfolio_response(tenant_id: str | None) -> PortfolioResponse:
    raw_positions = _load_portfolio_positions(tenant_id)
    runs = list_runs(tenant_id)
    positions = [
        _build_portfolio_position(position, tenant_id, runs)
        for position in raw_positions
    ]

    signal_breakdown: dict[str, int] = {}
    for position in positions:
        key = position.latest_signal or position.latest_status or "No signal"
        signal_breakdown[key] = signal_breakdown.get(key, 0) + 1

    summary = PortfolioSummary(
        position_count=len(positions),
        unique_ticker_count=len({position.ticker for position in positions}),
        total_cost_basis=round(sum(position.cost_basis for position in positions), 6),
        signal_breakdown=signal_breakdown,
    )
    return PortfolioResponse(summary=summary, positions=positions)


def _build_daily_briefing_response(tenant_id: str | None) -> DailyBriefingResponse:
    runs = list_runs(tenant_id)
    watchlist_items = _load_watchlist_items(tenant_id)
    watchlist_focus = [
        _watchlist_entry_from_overview(
            _build_ticker_overview(str(item["ticker"]), tenant_id, runs),
            created_at=item.get("created_at") if isinstance(item.get("created_at"), str) else None,
        )
        for item in watchlist_items[:5]
    ]

    rules = _load_alert_rules(tenant_id)
    alert_hits: list[AlertHit] = []
    for rule in rules:
        hit = _build_alert_hit(rule, _build_ticker_overview(rule.ticker, tenant_id, runs))
        if hit is not None:
            alert_hits.append(hit)

    portfolio = _build_portfolio_response(tenant_id)
    recent_runs = [_build_run_summary(run, tenant_id) for run in runs[:5]]

    hit_count = len(alert_hits)
    watchlist_count = len(watchlist_items)
    position_count = portfolio.summary.position_count
    recent_count = len(runs)
    if hit_count:
        headline = f"{hit_count} active alert(s) need review across your saved workspace."
    else:
        headline = f"{recent_count} recent run(s), {position_count} position(s), and no active alerts right now."

    summary = DailyBriefingSummary(
        generated_at=datetime.datetime.now().isoformat(),
        headline=headline,
        alert_hit_count=hit_count,
        watchlist_count=watchlist_count,
        portfolio_position_count=position_count,
        recent_run_count=recent_count,
    )
    return DailyBriefingResponse(
        summary=summary,
        alert_hits=alert_hits[:5],
        watchlist_focus=watchlist_focus,
        portfolio_focus=portfolio.positions[:5],
        recent_runs=recent_runs,
    )


def _is_bullish_signal(signal: str | None) -> bool:
    return str(signal or "").lower() in {"buy", "overweight", "mildly bullish", "bullish"}


def _is_bearish_signal(signal: str | None) -> bool:
    return str(signal or "").lower() in {"sell", "underweight", "mildly bearish", "bearish"}


def _needs_attention_entry(entry: WatchlistEntry) -> bool:
    status = str(entry.latest_status or "").lower()
    signal = str(entry.latest_signal or "").lower()
    return status in {"failed", "cancelled"} or _is_bearish_signal(signal)


def _is_pinned_action_active(item: PinnedRun) -> bool:
    if item.snoozed_until:
        today = datetime.datetime.now().date().isoformat()
        if item.snoozed_until > today:
            return False
    return item.action_status != "done" or bool(item.next_action)


def _build_getting_started_checklist(
    *,
    runs: list,
    watchlist_count: int,
    portfolio_position_count: int,
    saved_search_count: int,
    saved_view_count: int,
    automation_count: int,
    member_count: int,
) -> GettingStartedChecklist:
    items = [
        GettingStartedChecklistItem(
            id="run_analysis",
            title="Run your first analysis",
            description="Use the analysis form to save the first research run in this workspace.",
            completed=bool(runs),
            action_label="Open Analysis",
            target_panel="config-panel",
        ),
        GettingStartedChecklistItem(
            id="build_watchlist",
            title="Build a watchlist",
            description="Save a few tickers so the workspace can track what matters most.",
            completed=watchlist_count > 0,
            action_label="Open Watchlist",
            target_panel="watchlist-panel",
        ),
        GettingStartedChecklistItem(
            id="track_portfolio",
            title="Track a portfolio position",
            description="Add at least one holding so portfolio context can show up across the app.",
            completed=portfolio_position_count > 0,
            action_label="Open Portfolio",
            target_panel="portfolio-panel",
        ),
        GettingStartedChecklistItem(
            id="save_shortcut",
            title="Save a reusable shortcut",
            description="Save a search or view so repeated workflows reopen in one click.",
            completed=(saved_search_count + saved_view_count) > 0,
            action_label="Open Search",
            target_panel="search-panel",
        ),
        GettingStartedChecklistItem(
            id="create_automation",
            title="Create an automation",
            description="Schedule a recurring watchlist sweep or manual basket so research keeps moving.",
            completed=automation_count > 0,
            action_label="Open Automations",
            target_panel="automations-panel",
        ),
        GettingStartedChecklistItem(
            id="add_member",
            title="Add workspace context",
            description="Create a lightweight member profile for assignments, mentions, and review ownership.",
            completed=member_count > 0,
            action_label="Open Members",
            target_panel="members-panel",
        ),
    ]
    completed_count = sum(1 for item in items if item.completed)
    total_count = len(items)
    return GettingStartedChecklist(
        completed_count=completed_count,
        remaining_count=total_count - completed_count,
        total_count=total_count,
        items=items,
    )


def _build_dashboard_response(tenant_id: str | None) -> DashboardResponse:
    runs = list_runs(tenant_id)
    prefs = _load_dashboard_preferences(tenant_id)
    watchlist_items = _load_watchlist_items(tenant_id)
    watchlist_entries = [
        _watchlist_entry_from_overview(
            _build_ticker_overview(str(item["ticker"]), tenant_id, runs),
            created_at=item.get("created_at") if isinstance(item.get("created_at"), str) else None,
        )
        for item in watchlist_items
    ]
    bullish_focus = [entry for entry in watchlist_entries if _is_bullish_signal(entry.latest_signal)]
    needs_attention = [entry for entry in watchlist_entries if _needs_attention_entry(entry)]

    rules = _load_alert_rules(tenant_id)
    active_alerts: list[AlertHit] = []
    for rule in rules:
        hit = _build_alert_hit(rule, _build_ticker_overview(rule.ticker, tenant_id, runs))
        if hit is not None:
            active_alerts.append(hit)

    portfolio = _build_portfolio_response(tenant_id)
    saved_searches = _load_saved_searches(tenant_id)
    saved_views = _load_saved_views(tenant_id)
    workspace_members = _load_workspace_members(tenant_id)
    all_automations = list_automation_rules(tenant_id)
    pinned_actions = [
        _build_pinned_run_entry(item, tenant_id)
        for item in _load_pinned_runs(tenant_id)
        if _is_pinned_action_active(item)
    ][:5]
    pending_reviews = _build_run_review_history_response(tenant_id, status="pending").items[:5]
    automations = [rule for rule in all_automations if rule.enabled][:5]
    saved_shortcuts: list[SavedShortcutItem] = []
    for search in saved_searches:
        if search.archived or not search.pinned:
            continue
        saved_shortcuts.append(SavedShortcutItem(
            kind="search",
            item_id=search.id,
            name=search.name,
            group=search.group,
            member_id=search.member_id,
            member_name=search.member_name,
            query=search.query,
            kinds=search.kinds,
        ))
    for view in saved_views:
        if view.archived or not view.pinned:
            continue
        saved_shortcuts.append(SavedShortcutItem(
            kind="view",
            item_id=view.id,
            name=view.name,
            group=view.group,
            member_id=view.member_id,
            member_name=view.member_name,
            url=view.url,
        ))
    saved_shortcuts = saved_shortcuts[:6]
    getting_started = _build_getting_started_checklist(
        runs=runs,
        watchlist_count=len(watchlist_items),
        portfolio_position_count=portfolio.summary.position_count,
        saved_search_count=len(saved_searches),
        saved_view_count=len(saved_views),
        automation_count=len(all_automations),
        member_count=len(workspace_members),
    )
    operational_runs = [
        _build_run_summary(run, tenant_id)
        for run in runs
        if run.status in {"failed", "cancelled"}
    ][:5]

    summary = DashboardSummary(
        generated_at=datetime.datetime.now().isoformat(),
        watchlist_count=len(watchlist_items),
        bullish_focus_count=len(bullish_focus),
        needs_attention_count=len(needs_attention),
        alert_hit_count=len(active_alerts),
        portfolio_position_count=portfolio.summary.position_count,
        pinned_action_count=len(pinned_actions),
        pending_review_count=len(pending_reviews),
        automation_count=len(automations),
        saved_shortcut_count=len(saved_shortcuts),
        recent_run_count=len(runs),
    )
    return DashboardResponse(
        summary=summary,
        visible_sections=prefs.visible_sections,
        section_order=prefs.section_order,
        bullish_focus=bullish_focus[:5],
        needs_attention=needs_attention[:5],
        active_alerts=active_alerts[:5],
        portfolio_focus=portfolio.positions[:5],
        pinned_actions=pinned_actions,
        pending_reviews=pending_reviews,
        automations=automations,
        saved_shortcuts=saved_shortcuts,
        operational_runs=operational_runs,
        getting_started=getting_started,
    )


def _bucketize_counts(values: dict[str, int]) -> list[AnalyticsBucket]:
    return [
        AnalyticsBucket(label=label, value=value)
        for label, value in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ]


def _safe_duration_seconds(started_at: str | None, completed_at: str | None) -> float | None:
    if not started_at or not completed_at:
        return None
    try:
        start = datetime.datetime.fromisoformat(started_at)
        end = datetime.datetime.fromisoformat(completed_at)
    except ValueError:
        return None
    duration = (end - start).total_seconds()
    return duration if duration >= 0 else None


def _build_workspace_analytics_response(tenant_id: str | None) -> WorkspaceAnalyticsResponse:
    runs = list_runs(tenant_id)
    status_counts: dict[str, int] = {}
    provider_counts: dict[str, int] = {}
    signal_counts: dict[str, int] = {}
    asset_type_counts: dict[str, int] = {}
    ticker_counts: dict[str, int] = {}
    daily_counts: dict[str, dict[str, int]] = {}
    durations: list[float] = []

    for run in runs:
        status = str(run.status or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        provider = str(run.config.get("llm_provider") or "unknown")
        provider_counts[provider] = provider_counts.get(provider, 0) + 1

        signal = str(run.signal or run.error or "No signal")
        signal_counts[signal] = signal_counts.get(signal, 0) + 1

        asset = str(run.asset_type or "unknown")
        asset_type_counts[asset] = asset_type_counts.get(asset, 0) + 1

        ticker = str(run.ticker or "unknown")
        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        day = str(run.created_at or "")[:10]
        if day:
            bucket = daily_counts.setdefault(day, {
                "total_runs": 0,
                "completed_runs": 0,
                "failed_runs": 0,
                "cancelled_runs": 0,
            })
            bucket["total_runs"] += 1
            if status == "completed":
                bucket["completed_runs"] += 1
            elif status == "failed":
                bucket["failed_runs"] += 1
            elif status == "cancelled":
                bucket["cancelled_runs"] += 1

        duration = _safe_duration_seconds(run.started_at, run.completed_at)
        if duration is not None:
            durations.append(duration)

    terminal_runs = sum(1 for run in runs if run.status in TERMINAL_RUN_STATUSES)
    completed_runs = status_counts.get("completed", 0)
    success_rate = round(completed_runs / terminal_runs, 4) if terminal_runs else 0.0
    avg_duration = round(statistics.mean(durations), 3) if durations else None

    summary = AnalyticsSummary(
        generated_at=_now_iso(),
        total_runs=len(runs),
        terminal_runs=terminal_runs,
        queued_runs=status_counts.get("queued", 0),
        running_runs=status_counts.get("running", 0) + status_counts.get("pending", 0) + status_counts.get("cancelling", 0),
        success_rate=success_rate,
        avg_duration_seconds=avg_duration,
        unique_ticker_count=len(ticker_counts),
    )
    daily_activity = [
        AnalyticsDailyActivity(date=day, **counts)
        for day, counts in sorted(daily_counts.items(), key=lambda item: item[0], reverse=True)[:14]
    ]
    return WorkspaceAnalyticsResponse(
        summary=summary,
        status_breakdown=_bucketize_counts(status_counts),
        provider_breakdown=_bucketize_counts(provider_counts),
        signal_breakdown=_bucketize_counts(signal_counts),
        asset_type_breakdown=_bucketize_counts(asset_type_counts),
        top_tickers=_bucketize_counts(ticker_counts)[:10],
        daily_activity=daily_activity,
    )


def _normalize_screener_scope(raw_scope: str | None) -> str:
    normalized = str(raw_scope or "all").strip().lower()
    return normalized if normalized in {"all", "watchlist", "portfolio", "pinned"} else "all"


def _normalize_screener_filter(raw_value: str | None) -> str:
    normalized = str(raw_value or "all").strip().lower()
    return normalized or "all"


def _normalize_notification_kind(raw_value: str | None) -> str:
    normalized = str(raw_value or "all").strip().lower()
    allowed = {"all", "run", "alert", "action", "comment", "review"}
    return normalized if normalized in allowed else "all"


def _normalize_notification_severity(raw_value: str | None) -> str:
    normalized = str(raw_value or "all").strip().lower()
    allowed = {"all", "info", "warning", "error"}
    return normalized if normalized in allowed else "all"


def _normalize_public_share_availability(raw_value: str | None) -> str:
    normalized = str(raw_value or "all").strip().lower()
    allowed = {"all", "active", "expired"}
    return normalized if normalized in allowed else "all"


def _build_workspace_screener_response(
    tenant_id: str | None,
    *,
    scope: str = "all",
    q: str | None = None,
    signal_filter: str | None = None,
    status_filter: str | None = None,
    asset_filter: str | None = None,
    provider_filter: str | None = None,
) -> WorkspaceScreenerResponse:
    resolved_scope = _normalize_screener_scope(scope)
    normalized_query = str(q or "").strip().lower()
    resolved_signal = _normalize_screener_filter(signal_filter)
    resolved_status = _normalize_screener_filter(status_filter)
    resolved_asset = _normalize_screener_filter(asset_filter)
    resolved_provider = _normalize_screener_filter(provider_filter)

    runs = list_runs(tenant_id)
    run_by_id = {run.run_id: run for run in runs}
    watchlist_entries = _build_watchlist_entries(tenant_id, runs)
    watchlist_set = {entry.ticker for entry in watchlist_entries}
    portfolio = _build_portfolio_response(tenant_id)
    portfolio_set = {position.ticker for position in portfolio.positions}
    alert_center = _build_alert_center_response(tenant_id, runs)
    alert_tickers = {hit.ticker for hit in alert_center.hits}

    pinned_entries = [_build_pinned_run_entry(item, tenant_id) for item in _load_pinned_runs(tenant_id)]
    pinned_by_ticker: dict[str, PinnedRun] = {}
    for item in pinned_entries:
        ticker = item.ticker
        if ticker and ticker not in pinned_by_ticker:
            pinned_by_ticker[ticker] = item
    pinned_set = set(pinned_by_ticker)

    all_tickers = {
        *{run.ticker for run in runs if run.ticker},
        *watchlist_set,
        *portfolio_set,
        *pinned_set,
    }

    if resolved_scope == "watchlist":
        candidate_tickers = watchlist_set
    elif resolved_scope == "portfolio":
        candidate_tickers = portfolio_set
    elif resolved_scope == "pinned":
        candidate_tickers = pinned_set
    else:
        candidate_tickers = all_tickers

    rows: list[ScreenerRow] = []
    for ticker in sorted(candidate_tickers):
        overview = _build_ticker_overview(ticker, tenant_id, runs)
        latest_run = run_by_id.get(overview.latest_run_id) if overview.latest_run_id else None
        pinned = pinned_by_ticker.get(ticker)
        annotation = _get_run_annotation(overview.latest_run_id, tenant_id) if overview.latest_run_id else None
        asset_type = latest_run.asset_type if latest_run is not None else _infer_asset_type(ticker)
        provider = str(latest_run.config.get("llm_provider")) if latest_run is not None and latest_run.config.get("llm_provider") else None
        research_depth = None
        if latest_run is not None:
            depth = latest_run.config.get("max_debate_rounds")
            research_depth = int(depth) if isinstance(depth, int) else None
        row = ScreenerRow(
            ticker=ticker,
            run_count=overview.run_count,
            latest_run_id=overview.latest_run_id,
            latest_signal=overview.latest_signal,
            latest_status=overview.latest_status,
            latest_date=overview.latest_date,
            latest_created_at=overview.latest_created_at,
            asset_type=asset_type,
            llm_provider=provider,
            research_depth=research_depth,
            on_watchlist=ticker in watchlist_set,
            in_portfolio=ticker in portfolio_set,
            is_pinned=ticker in pinned_set,
            has_alert_hit=ticker in alert_tickers,
            pinned_category=pinned.category if pinned else None,
            pinned_priority=pinned.priority if pinned else None,
            annotation_label=annotation.label if annotation else None,
            needs_attention=bool(
                (overview.latest_status and str(overview.latest_status).lower() in {"failed", "cancelled"})
                or _is_bearish_signal(overview.latest_signal)
                or ticker in alert_tickers
            ),
        )

        if normalized_query:
            haystack = " ".join(
                part for part in [
                    row.ticker,
                    row.latest_signal or "",
                    row.latest_status or "",
                    row.asset_type or "",
                    row.llm_provider or "",
                    row.pinned_category or "",
                    row.pinned_priority or "",
                    row.annotation_label or "",
                ] if part
            ).lower()
            if normalized_query not in haystack:
                continue

        if resolved_signal != "all":
            if resolved_signal == "bullish" and not _is_bullish_signal(row.latest_signal):
                continue
            if resolved_signal == "bearish" and not _is_bearish_signal(row.latest_signal):
                continue
            if resolved_signal == "unscored" and row.latest_signal:
                continue

        if resolved_status != "all" and str(row.latest_status or "").lower() != resolved_status:
            continue
        if resolved_asset != "all" and str(row.asset_type or "").lower() != resolved_asset:
            continue
        if resolved_provider != "all" and str(row.llm_provider or "").lower() != resolved_provider:
            continue

        rows.append(row)

    rows.sort(
        key=lambda row: (
            bool(row.has_alert_hit),
            bool(row.is_pinned),
            bool(row.on_watchlist),
            bool(row.in_portfolio),
            row.latest_created_at or "",
            row.ticker,
        ),
        reverse=True,
    )

    summary = ScreenerSummary(
        total_candidates=len(rows),
        bullish_count=sum(1 for row in rows if _is_bullish_signal(row.latest_signal)),
        bearish_count=sum(1 for row in rows if _is_bearish_signal(row.latest_signal)),
        alert_hit_count=sum(1 for row in rows if row.has_alert_hit),
        watchlist_count=sum(1 for row in rows if row.on_watchlist),
        portfolio_count=sum(1 for row in rows if row.in_portfolio),
        pinned_count=sum(1 for row in rows if row.is_pinned),
    )
    return WorkspaceScreenerResponse(
        scope=resolved_scope,
        query=normalized_query,
        signal_filter=resolved_signal,
        status_filter=resolved_status,
        asset_filter=resolved_asset,
        provider_filter=resolved_provider,
        summary=summary,
        rows=rows[:50],
    )


def _build_notification_center_response(
    tenant_id: str | None,
    *,
    unread_only: bool = False,
    member: str | None = None,
    kind: str | None = None,
    severity: str | None = None,
) -> NotificationCenterResponse:
    reads = _load_notification_reads(tenant_id)
    runs = list_runs(tenant_id)
    run_by_id = {run.run_id: run for run in runs}
    items: list[NotificationItem] = []
    seen: set[str] = set()
    today = datetime.datetime.now().date().isoformat()
    member_filter = member.strip() if member else None
    kind_filter = _normalize_notification_kind(kind)
    severity_filter = _normalize_notification_severity(severity)

    for run in runs:
        if run.status not in TERMINAL_RUN_STATUSES:
            continue
        created_at = run.completed_at or run.created_at
        if not created_at:
            continue
        notification_id = f"run:{run.run_id}:{run.status}"
        if notification_id in seen:
            continue
        seen.add(notification_id)
        severity = "info"
        title = f"{run.ticker} run completed"
        message = run.signal or f"{run.date} analysis finished."
        if run.status == "failed":
            severity = "error"
            title = f"{run.ticker} run failed"
            message = run.error or f"{run.date} analysis failed."
        elif run.status == "cancelled":
            severity = "warning"
            title = f"{run.ticker} run cancelled"
            message = run.error or f"{run.date} analysis was cancelled."
        items.append(NotificationItem(
            id=notification_id,
            kind="run",
            severity=severity,
            title=title,
            message=message,
            created_at=created_at,
            is_read=notification_id in reads,
            target_url=_build_share_url("/", tenant_id, run_id=run.run_id),
            ticker=run.ticker,
            run_id=run.run_id,
        ))

    alert_center = _build_alert_center_response(tenant_id, runs)
    rules_by_id = {rule.id: rule for rule in alert_center.rules}
    for hit in alert_center.hits:
        notification_id = f"alert:{hit.rule_id}:{hit.run_id}"
        if notification_id in seen:
            continue
        seen.add(notification_id)
        run = run_by_id.get(hit.run_id)
        rule = rules_by_id.get(hit.rule_id)
        created_at = (
            (run.completed_at or run.created_at) if run is not None
            else (rule.created_at if rule is not None else _now_iso())
        )
        items.append(NotificationItem(
            id=notification_id,
            kind="alert",
            severity="warning",
            title=f"Alert hit for {hit.ticker}",
            message=f"{hit.field}: expected {hit.expected_value}, actual {hit.actual_value}.",
            created_at=created_at,
            is_read=notification_id in reads,
            target_url=_build_share_url("/", tenant_id, run_id=hit.run_id),
            ticker=hit.ticker,
            run_id=hit.run_id,
        ))

    for raw_item in _load_pinned_runs(tenant_id):
        item = _build_pinned_run_entry(raw_item, tenant_id)
        if not item.due_date or item.action_status == "done":
            continue
        if item.snoozed_until and item.snoozed_until > today:
            continue
        if item.due_date > today:
            continue
        notification_id = f"pin-due:{item.run_id}:{item.due_date}"
        if notification_id in seen:
            continue
        seen.add(notification_id)
        overdue = item.due_date < today
        title = f"{item.ticker or item.run_id} action overdue" if overdue else f"{item.ticker or item.run_id} action due today"
        message = item.next_action or item.note or "Pinned action needs review."
        items.append(NotificationItem(
            id=notification_id,
            kind="action",
            severity="error" if overdue else "warning",
            title=title,
            message=message,
            created_at=f"{item.due_date}T00:00:00",
            is_read=notification_id in reads,
            target_url=_build_share_url("/", tenant_id, run_id=item.run_id),
            ticker=item.ticker,
            run_id=item.run_id,
            member=item.assignee,
        ))

    for comment in _load_run_comments(tenant_id):
        mentioned = _extract_comment_mentions(comment.content, tenant_id)
        if not mentioned:
            continue
        run = run_by_id.get(comment.run_id)
        for mentioned_member in mentioned:
            notification_id = f"comment:{comment.id}:{mentioned_member}"
            if notification_id in seen:
                continue
            seen.add(notification_id)
            ticker = run.ticker if run is not None else None
            items.append(NotificationItem(
                id=notification_id,
                kind="comment",
                severity="info",
                title=f"{comment.author} mentioned @{mentioned_member}",
                message=comment.content,
                created_at=comment.created_at,
                is_read=notification_id in reads,
                target_url=_build_share_url("/", tenant_id, run_id=comment.run_id),
                ticker=ticker,
                run_id=comment.run_id,
                member=mentioned_member,
            ))

    for review in _load_run_reviews(tenant_id):
        if review.status != "pending":
            continue
        notification_id = f"review:{review.run_id}:{review.reviewer}"
        if notification_id in seen:
            continue
        seen.add(notification_id)
        run = run_by_id.get(review.run_id)
        items.append(NotificationItem(
            id=notification_id,
            kind="review",
            severity="warning",
            title=f"Review requested for {run.ticker if run is not None else review.run_id}",
            message=review.note or "A saved run is waiting for your review.",
            created_at=review.updated_at,
            is_read=notification_id in reads,
            target_url=_build_share_url("/", tenant_id, run_id=review.run_id),
            ticker=run.ticker if run is not None else None,
            run_id=review.run_id,
            member=review.reviewer,
        ))

    items.sort(key=lambda item: item.created_at, reverse=True)
    unread_count = sum(1 for item in items if not item.is_read)
    visible_items = [
        item for item in items
        if (unread_only is False or not item.is_read)
        and (member_filter is None or str(item.member or "").strip().lower() == member_filter.lower())
        and (kind_filter == "all" or item.kind == kind_filter)
        and (severity_filter == "all" or item.severity == severity_filter)
    ]
    return NotificationCenterResponse(
        generated_at=_now_iso(),
        unread_count=unread_count,
        total_count=len(items),
        unread_only=unread_only,
        member_filter=member_filter,
        kind_filter=kind_filter,
        severity_filter=severity_filter,
        items=visible_items[:30],
    )


def _build_member_workspace_response(member: WorkspaceMember, tenant_id: str | None) -> MemberWorkspaceResponse:
    today = datetime.datetime.now().date().isoformat()
    assigned_actions = [
        _build_pinned_run_entry(item, tenant_id)
        for item in _load_pinned_runs(tenant_id)
        if str(item.assignee or "").strip().lower() == member.name.strip().lower()
    ]
    assigned_actions.sort(
        key=lambda item: (
            item.action_status == "done",
            item.due_date or "9999-12-31",
            item.created_at or "",
        )
    )

    member_notifications = _build_notification_center_response(tenant_id, member=member.name, unread_only=False)
    mention_notifications = [item for item in member_notifications.items if item.kind == "comment"]
    pending_reviews = [
        review for review in _load_run_reviews(tenant_id)
        if review.reviewer.strip().lower() == member.name.strip().lower()
        and review.status == "pending"
    ]
    pending_reviews.sort(key=lambda review: review.updated_at, reverse=True)
    recent_comments = [
        comment for comment in _load_run_comments(tenant_id)
        if comment.author.strip().lower() == member.name.strip().lower()
    ]
    recent_comments.sort(key=lambda comment: comment.created_at, reverse=True)

    summary = MemberWorkspaceSummary(
        assigned_action_count=len(assigned_actions),
        overdue_action_count=sum(
            1
            for item in assigned_actions
            if item.action_status != "done"
            and item.due_date is not None
            and item.due_date < today
            and not (item.snoozed_until and item.snoozed_until > today)
        ),
        pending_review_count=len(pending_reviews),
        mention_count=len(mention_notifications),
        unread_mention_count=sum(1 for item in mention_notifications if not item.is_read),
        recent_comment_count=len(recent_comments),
    )
    return MemberWorkspaceResponse(
        member=member,
        summary=summary,
        assigned_actions=assigned_actions[:10],
        pending_reviews=pending_reviews[:10],
        mention_notifications=mention_notifications[:10],
        recent_comments=recent_comments[:10],
    )


def _build_run_review_history_response(
    tenant_id: str | None,
    *,
    reviewer: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> RunReviewHistoryResponse:
    normalized_reviewer = reviewer.strip().lower() if reviewer else None
    normalized_status = (status or "all").strip().lower() or "all"
    normalized_query = (q or "").strip().lower()
    runs = list_runs(tenant_id)
    run_by_id = {run.run_id: run for run in runs}

    items: list[RunReviewHistoryRow] = []
    for review in _load_run_reviews(tenant_id):
        if normalized_reviewer and review.reviewer.strip().lower() != normalized_reviewer:
            continue
        if normalized_status != "all" and review.status != normalized_status:
            continue
        run = run_by_id.get(review.run_id)
        row = RunReviewHistoryRow(
            run_id=review.run_id,
            reviewer=review.reviewer,
            status=review.status,
            note=review.note,
            created_at=review.created_at,
            updated_at=review.updated_at,
            ticker=run.ticker if run is not None else None,
            date=run.date if run is not None else None,
            signal=run.signal if run is not None else None,
        )
        if normalized_query:
            haystack = " ".join(
                part for part in [
                    row.run_id,
                    row.reviewer,
                    row.status,
                    row.note or "",
                    row.ticker or "",
                    row.signal or "",
                ] if part
            ).lower()
            if normalized_query not in haystack:
                continue
        items.append(row)

    items.sort(key=lambda item: item.updated_at, reverse=True)
    summary = RunReviewHistorySummary(
        total_reviews=len(items),
        pending_count=sum(1 for item in items if item.status == "pending"),
        approved_count=sum(1 for item in items if item.status == "approved"),
        changes_requested_count=sum(1 for item in items if item.status == "changes_requested"),
    )
    return RunReviewHistoryResponse(
        reviewer_filter=reviewer,
        status_filter=normalized_status,
        query=normalized_query,
        summary=summary,
        items=items[:50],
    )


def _build_workspace_timeline_response(
    tenant_id: str | None,
    active_kinds: list[str] | None = None,
) -> WorkspaceTimelineResponse:
    kinds = active_kinds or []
    events: list[WorkspaceTimelineEvent] = []

    if not kinds or "run" in kinds:
        for run in list_runs(tenant_id):
            if not run.created_at:
                continue
            detail = run.signal or run.error or run.status
            events.append(WorkspaceTimelineEvent(
                kind="run",
                occurred_at=run.created_at,
                title=f"{run.ticker} analysis saved",
                detail=f"{run.date} · {detail}",
                ticker=run.ticker,
                run_id=run.run_id,
            ))

    if not kinds or "watchlist" in kinds:
        for item in _load_watchlist_items(tenant_id):
            created_at = item.get("created_at")
            if not isinstance(created_at, str) or not created_at:
                continue
            ticker = str(item["ticker"])
            events.append(WorkspaceTimelineEvent(
                kind="watchlist",
                occurred_at=created_at,
                title=f"{ticker} added to watchlist",
                detail="Saved for ongoing tracking.",
                ticker=ticker,
            ))

    if not kinds or "alert" in kinds:
        for rule in _load_alert_rules(tenant_id):
            if not rule.created_at:
                continue
            events.append(WorkspaceTimelineEvent(
                kind="alert",
                occurred_at=rule.created_at,
                title=f"Alert saved for {rule.ticker}",
                detail=f"{rule.field} = {rule.value}",
                ticker=rule.ticker,
            ))

    if not kinds or "portfolio" in kinds:
        for position in _load_portfolio_positions(tenant_id):
            created_at = position.get("created_at")
            if not isinstance(created_at, str) or not created_at:
                continue
            events.append(WorkspaceTimelineEvent(
                kind="portfolio",
                occurred_at=created_at,
                title=f"Position saved for {position['ticker']}",
                detail=f"qty {position['quantity']} @ {position['average_cost']}",
                ticker=str(position["ticker"]),
            ))

    if not kinds or "preset" in kinds:
        for preset in _load_presets(tenant_id):
            if not preset.created_at:
                continue
            events.append(WorkspaceTimelineEvent(
                kind="preset",
                occurred_at=preset.created_at,
                title=f"Preset saved: {preset.name}",
                detail=preset.analysis_request.ticker or "Saved analysis configuration",
                ticker=preset.analysis_request.ticker,
            ))

    if not kinds or "search" in kinds:
        for search in _load_saved_searches(tenant_id):
            if not search.created_at:
                continue
            events.append(WorkspaceTimelineEvent(
                kind="search",
                occurred_at=search.created_at,
                title=f"Saved search created: {search.name}",
                detail=search.query,
            ))

    if not kinds or "view" in kinds:
        for view in _load_saved_views(tenant_id):
            if not view.created_at:
                continue
            events.append(WorkspaceTimelineEvent(
                kind="view",
                occurred_at=view.created_at,
                title=f"Saved view created: {view.name}",
                detail=view.url,
            ))

    if not kinds or "member" in kinds:
        for member in _load_workspace_members(tenant_id):
            if not member.created_at:
                continue
            events.append(WorkspaceTimelineEvent(
                kind="member",
                occurred_at=member.created_at,
                title=f"Workspace member added: {member.name}",
                detail=member.role or "Workspace member",
            ))

    if not kinds or "share" in kinds:
        for share in _load_public_run_shares(tenant_id):
            events.append(WorkspaceTimelineEvent(
                kind="share",
                occurred_at=share.created_at,
                title=f"Public snapshot shared for {share.ticker}",
                detail=f"{share.status} · {share.share_id}",
                ticker=share.ticker,
                run_id=share.run_id,
            ))

    if not kinds or "note" in kinds:
        for note in _load_notes(tenant_id):
            events.append(WorkspaceTimelineEvent(
                kind="note",
                occurred_at=note.created_at,
                title=f"Note saved for {note.ticker or note.run_id or 'workspace'}",
                detail=note.content,
                ticker=note.ticker,
                run_id=note.run_id,
            ))

    if not kinds or "pin" in kinds:
        for pinned in _load_pinned_runs(tenant_id):
            if not pinned.created_at:
                continue
            detail = pinned.note or "Pinned for quick access."
            if pinned.category or pinned.priority:
                detail = " · ".join(
                    value for value in [pinned.category, pinned.priority, detail] if value
                )
            if pinned.next_action or pinned.action_status:
                detail = " · ".join(
                    value for value in [detail, pinned.next_action, pinned.action_status] if value
                )
            if pinned.assignee:
                detail = " · ".join(value for value in [detail, f"assignee {pinned.assignee}"] if value)
            events.append(WorkspaceTimelineEvent(
                kind="pin",
                occurred_at=pinned.created_at,
                title=f"Run pinned for {pinned.ticker or pinned.run_id}",
                detail=detail,
                ticker=pinned.ticker,
                run_id=pinned.run_id,
            ))

    if not kinds or "annotation" in kinds:
        for annotation in _load_run_annotations(tenant_id):
            run = get_run(annotation.run_id, tenant_id)
            title_target = run.ticker if run is not None else annotation.run_id
            events.append(WorkspaceTimelineEvent(
                kind="annotation",
                occurred_at=annotation.updated_at,
                title=f"Run annotated: {title_target}",
                detail=annotation.label if not annotation.summary else f"{annotation.label} · {annotation.summary}",
                ticker=run.ticker if run is not None else None,
                run_id=annotation.run_id,
            ))

    if not kinds or "comment" in kinds:
        for comment in _load_run_comments(tenant_id):
            events.append(WorkspaceTimelineEvent(
                kind="comment",
                occurred_at=comment.created_at,
                title=f"Comment from {comment.author}",
                detail=comment.content,
                run_id=comment.run_id,
            ))

    if not kinds or "review" in kinds:
        for review in _load_run_reviews(tenant_id):
            events.append(WorkspaceTimelineEvent(
                kind="review",
                occurred_at=review.updated_at,
                title=f"Review {review.status}: {review.run_id}",
                detail=review.note or f"Reviewer {review.reviewer}",
                run_id=review.run_id,
            ))

    events.sort(key=lambda event: event.occurred_at, reverse=True)
    return WorkspaceTimelineResponse(active_kinds=kinds, events=events[:20])


def _build_workspace_calendar_response(tenant_id: str | None) -> WorkspaceCalendarResponse:
    timeline = _build_workspace_timeline_response(tenant_id)
    by_date: dict[str, list[WorkspaceTimelineEvent]] = {}
    for event in timeline.events:
        day = event.occurred_at[:10]
        by_date.setdefault(day, []).append(event)

    days = [
        WorkspaceCalendarDay(date=day, events=events)
        for day, events in sorted(by_date.items(), key=lambda item: item[0], reverse=True)
    ]
    return WorkspaceCalendarResponse(days=days)


def _build_pinned_run_entry(entry: PinnedRun, tenant_id: str | None) -> PinnedRun:
    run = get_run(entry.run_id, tenant_id)
    if run is None:
        return entry
    return PinnedRun(
        run_id=entry.run_id,
        ticker=run.ticker,
        date=run.date,
        signal=run.signal,
        status=run.status,
        note=entry.note,
        category=entry.category,
        priority=entry.priority,
        next_action=entry.next_action,
        action_status=entry.action_status,
        assignee=entry.assignee,
        due_date=entry.due_date,
        snoozed_until=entry.snoozed_until,
        created_at=entry.created_at,
    )


def _build_action_board_response(tenant_id: str | None) -> ActionBoardResponse:
    grouped = {"todo": [], "doing": [], "done": []}
    for item in _load_pinned_runs(tenant_id):
        hydrated = _build_pinned_run_entry(item, tenant_id)
        status = hydrated.action_status or "todo"
        grouped.setdefault(status, []).append(hydrated)
    return ActionBoardResponse(
        todo=grouped["todo"],
        doing=grouped["doing"],
        done=grouped["done"],
    )


def _build_workspace_export_response(tenant_id: str | None) -> WorkspaceExport:
    runs = list_runs(tenant_id)
    run_summaries = [_build_run_summary(run, tenant_id) for run in runs]
    workspace_settings = _load_workspace_settings_model(tenant_id)
    dashboard_preferences = _load_dashboard_preferences(tenant_id)
    watchlist = _build_watchlist_entries(tenant_id, runs)
    alerts = _build_alert_center_response(tenant_id, runs)
    portfolio = _build_portfolio_response(tenant_id)
    workspace_members = _load_workspace_members(tenant_id)
    run_comments = _load_run_comments(tenant_id)
    run_reviews = _load_run_reviews(tenant_id)
    pinned_runs = [_build_pinned_run_entry(item, tenant_id) for item in _load_pinned_runs(tenant_id)]
    action_board = _build_action_board_response(tenant_id)
    timeline = _build_workspace_timeline_response(tenant_id)
    notes = _load_notes(tenant_id)
    presets = _load_presets(tenant_id)
    saved_searches = _load_saved_searches(tenant_id)
    saved_views = _load_saved_views(tenant_id)
    annotations = _load_run_annotations(tenant_id)

    summary = WorkspaceExportSummary(
        exported_at=datetime.datetime.now().isoformat(),
        tenant_id=tenant_id,
        run_count=len(run_summaries),
        watchlist_count=len(watchlist),
        alert_rule_count=len(alerts.rules),
        alert_hit_count=len(alerts.hits),
        portfolio_position_count=portfolio.summary.position_count,
        note_count=len(notes),
        preset_count=len(presets),
        saved_search_count=len(saved_searches),
        saved_view_count=len(saved_views),
        pinned_run_count=len(pinned_runs),
        annotation_count=len(annotations),
        member_count=len(workspace_members),
        comment_count=len(run_comments),
        review_count=len(run_reviews),
    )
    return WorkspaceExport(
        summary=summary,
        workspace_settings=workspace_settings,
        dashboard_preferences=dashboard_preferences,
        runs=run_summaries,
        watchlist=watchlist,
        alerts=alerts,
        portfolio=portfolio,
        workspace_members=workspace_members,
        run_comments=run_comments,
        run_reviews=run_reviews,
        pinned_runs=pinned_runs,
        action_board=action_board,
        timeline=timeline,
        notes=notes,
        presets=presets,
        saved_searches=saved_searches,
        saved_views=saved_views,
        annotations=annotations,
    )


def _truncate_export_text(value: str | None, limit: int = 120) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit - 3]}..."


def _build_workspace_export_markdown(workspace: WorkspaceExport) -> str:
    summary = workspace.summary
    lines = [
        "# TradingAgents Workspace Export",
        "",
        "## Snapshot",
        f"- Exported at: {summary.exported_at}",
        f"- Tenant: {summary.tenant_id or 'default'}",
        f"- Saved runs: {summary.run_count}",
        f"- Watchlist items: {summary.watchlist_count}",
        f"- Alert rules / active hits: {summary.alert_rule_count} / {summary.alert_hit_count}",
        f"- Portfolio positions: {summary.portfolio_position_count}",
        f"- Notes: {summary.note_count}",
        f"- Presets: {summary.preset_count}",
        f"- Saved searches / views: {summary.saved_search_count} / {summary.saved_view_count}",
        f"- Pinned runs / annotations: {summary.pinned_run_count} / {summary.annotation_count}",
        f"- Members / comments / reviews: {summary.member_count} / {summary.comment_count} / {summary.review_count}",
    ]

    lines.extend([
        "",
        "## Workspace Settings",
        f"- Default home view: {workspace.workspace_settings.default_home_view}",
        f"- Default saved view: {workspace.workspace_settings.default_saved_view_id or 'none'}",
        f"- Dashboard sections: {', '.join(workspace.dashboard_preferences.visible_sections or []) or 'default'}",
    ])

    if workspace.runs:
        lines.extend(["", "## Recent Runs"])
        for run in workspace.runs[:10]:
            detail = _truncate_export_text(run.signal or run.error or run.status, 140)
            lines.append(f"- {run.ticker} · {run.date} · {run.status} · {detail}")

    if workspace.watchlist:
        lines.extend(["", "## Watchlist"])
        for entry in workspace.watchlist[:10]:
            latest = entry.latest_signal or entry.latest_status or "No latest signal"
            lines.append(f"- {entry.ticker} · {entry.run_count} run(s) · {latest}")

    if workspace.alerts.rules or workspace.alerts.hits:
        lines.extend(["", "## Alerts"])
        for rule in workspace.alerts.rules[:10]:
            lines.append(f"- Rule: {rule.ticker} {rule.field} = {rule.value}")
        for hit in workspace.alerts.hits[:10]:
            lines.append(f"- Hit: {hit.ticker} {hit.field} = {hit.actual_value} ({hit.message})")

    if workspace.portfolio.positions:
        lines.extend(["", "## Portfolio"])
        lines.append(
            f"- Total cost basis: {workspace.portfolio.summary.total_cost_basis} across "
            f"{workspace.portfolio.summary.position_count} position(s)"
        )
        for position in workspace.portfolio.positions[:10]:
            latest = position.latest_signal or position.latest_status or "No latest signal"
            lines.append(
                f"- {position.ticker} · qty {position.quantity} · cost basis {position.cost_basis} · {latest}"
            )

    if workspace.pinned_runs:
        lines.extend(["", "## Pinned Actions"])
        lines.append(
            f"- Todo / Doing / Done: {len(workspace.action_board.todo)} / "
            f"{len(workspace.action_board.doing)} / {len(workspace.action_board.done)}"
        )
        for item in workspace.pinned_runs[:10]:
            detail = " · ".join(
                value
                for value in [
                    item.category,
                    item.priority,
                    item.action_status,
                    item.assignee,
                    item.next_action,
                    item.due_date,
                ]
                if value
            )
            lines.append(f"- {item.ticker or item.run_id} · {detail or 'Pinned'}")

    if workspace.notes:
        lines.extend(["", "## Notes"])
        for note in workspace.notes[:10]:
            scope = note.ticker or note.run_id or "workspace"
            lines.append(f"- {scope}: {_truncate_export_text(note.content, 140)}")

    if workspace.presets:
        lines.extend(["", "## Presets"])
        for preset in workspace.presets[:10]:
            lines.append(f"- {preset.name} · {preset.analysis_request.ticker or 'multi-ticker'}")

    if workspace.saved_searches:
        lines.extend(["", "## Saved Searches"])
        for item in workspace.saved_searches[:10]:
            lines.append(f"- {item.name}: {_truncate_export_text(item.query, 120)}")

    if workspace.saved_views:
        lines.extend(["", "## Saved Views"])
        for item in workspace.saved_views[:10]:
            lines.append(f"- {item.name}: {item.url}")

    if workspace.workspace_members:
        lines.extend(["", "## Workspace Members"])
        for item in workspace.workspace_members[:10]:
            lines.append(f"- {item.name}")

    if workspace.run_reviews:
        lines.extend(["", "## Run Reviews"])
        for item in workspace.run_reviews[:10]:
            detail = item.note or item.status
            lines.append(f"- {item.run_id} · {item.reviewer} · {item.status} · {_truncate_export_text(detail, 120)}")

    if workspace.run_comments:
        lines.extend(["", "## Run Comments"])
        for item in workspace.run_comments[:10]:
            lines.append(f"- {item.run_id} · {item.author}: {_truncate_export_text(item.content, 120)}")

    if workspace.annotations:
        lines.extend(["", "## Run Annotations"])
        for item in workspace.annotations[:10]:
            detail = item.summary or item.next_step or "Annotation saved"
            lines.append(f"- {item.run_id} · {item.label} · {_truncate_export_text(detail, 140)}")

    if workspace.timeline.events:
        lines.extend(["", "## Timeline Highlights"])
        for event in workspace.timeline.events[:10]:
            lines.append(f"- {event.occurred_at} · {event.kind} · {event.title}")

    return "\n".join(lines) + "\n"


def _build_workspace_search_response(
    tenant_id: str | None,
    query: str,
    kinds: list[str] | None = None,
) -> WorkspaceSearchResponse:
    normalized = query.strip()
    active_kinds = kinds or []
    if not normalized:
        return WorkspaceSearchResponse(query="", active_kinds=active_kinds, results=[])

    results: list[WorkspaceSearchResult] = []
    runs = list_runs(tenant_id)

    if not active_kinds or "run" in active_kinds:
        for run in runs:
            if _matches_query(normalized, run.ticker, run.date, run.signal, run.error, run.status):
                results.append(WorkspaceSearchResult(
                    kind="run",
                    entity_id=run.run_id,
                    title=f"{run.ticker} · {run.date}",
                    subtitle=run.status,
                    excerpt=run.signal or run.error or "Saved analysis run",
                    ticker=run.ticker,
                    run_id=run.run_id,
                ))

    if not active_kinds or "note" in active_kinds:
        for note in _load_notes(tenant_id):
            if _matches_query(normalized, note.content, *note.tags, note.ticker, note.run_id):
                results.append(WorkspaceSearchResult(
                    kind="note",
                    entity_id=note.id,
                    title=note.ticker or note.run_id or "Workspace Note",
                    subtitle=note.created_at,
                    excerpt=note.content,
                    ticker=note.ticker,
                    run_id=note.run_id,
                ))

    if not active_kinds or "watchlist" in active_kinds:
        for item in _load_watchlist_items(tenant_id):
            ticker = str(item["ticker"])
            if _matches_query(normalized, ticker):
                results.append(WorkspaceSearchResult(
                    kind="watchlist",
                    entity_id=str(item["id"]),
                    title=f"{ticker} in watchlist",
                    subtitle="Saved for ongoing tracking",
                    excerpt=ticker,
                    ticker=ticker,
                ))

    if not active_kinds or "portfolio" in active_kinds:
        for position in _load_portfolio_positions(tenant_id):
            ticker = str(position["ticker"])
            if _matches_query(normalized, ticker, position["quantity"], position["average_cost"]):
                results.append(WorkspaceSearchResult(
                    kind="portfolio",
                    entity_id=str(position["id"]),
                    title=f"{ticker} position",
                    subtitle=f"qty {position['quantity']} @ {position['average_cost']}",
                    excerpt=f"Saved holding for {ticker}",
                    ticker=ticker,
                ))

    if not active_kinds or "preset" in active_kinds:
        for preset in _load_presets(tenant_id):
            if _matches_query(
                normalized,
                preset.name,
                preset.analysis_request.ticker,
                preset.analysis_request.llm_provider,
                preset.analysis_request.market_profile,
            ):
                results.append(WorkspaceSearchResult(
                    kind="preset",
                    entity_id=preset.id,
                    title=preset.name,
                    subtitle=preset.analysis_request.ticker or "Saved analysis preset",
                    excerpt="Reusable analysis configuration",
                    ticker=preset.analysis_request.ticker,
                ))

    if not active_kinds or "search" in active_kinds:
        for search in _load_saved_searches(tenant_id):
            if _matches_query(normalized, search.name, search.query, search.group, search.member_name, *search.kinds):
                results.append(WorkspaceSearchResult(
                    kind="search",
                    entity_id=search.id,
                    title=search.name,
                    subtitle=search.group or "Saved workspace search",
                    excerpt=search.query,
                ))

    if not active_kinds or "view" in active_kinds:
        for view in _load_saved_views(tenant_id):
            if _matches_query(normalized, view.name, view.url, view.group, view.member_name, *view.visible_panels):
                results.append(WorkspaceSearchResult(
                    kind="view",
                    entity_id=view.id,
                    title=view.name,
                    subtitle=view.group or "Saved workspace view",
                    excerpt=view.url,
                ))

    if not active_kinds or "member" in active_kinds:
        for member in _load_workspace_members(tenant_id):
            if _matches_query(normalized, member.name, member.role):
                results.append(WorkspaceSearchResult(
                    kind="member",
                    entity_id=member.id,
                    title=member.name,
                    subtitle=member.role or "Workspace member",
                    excerpt="Workspace collaborator",
                ))

    if not active_kinds or "share" in active_kinds:
        for share in _load_public_run_shares(tenant_id):
            if _matches_query(normalized, share.share_id, share.ticker, share.status, share.signal):
                results.append(WorkspaceSearchResult(
                    kind="share",
                    entity_id=share.share_id,
                    title=f"{share.ticker} public snapshot",
                    subtitle=share.share_id,
                    excerpt=share.status,
                    ticker=share.ticker,
                    run_id=share.run_id,
                ))

    if not active_kinds or "alert" in active_kinds:
        for rule in _load_alert_rules(tenant_id):
            if _matches_query(normalized, rule.ticker, rule.field, rule.value):
                results.append(WorkspaceSearchResult(
                    kind="alert",
                    entity_id=rule.id,
                    title=f"{rule.ticker} alert",
                    subtitle=f"{rule.field} = {rule.value}",
                    excerpt="Saved alert rule",
                    ticker=rule.ticker,
                ))

    if not active_kinds or "comment" in active_kinds:
        for comment in _load_run_comments(tenant_id):
            run = get_run(comment.run_id, tenant_id)
            if _matches_query(normalized, comment.author, comment.content, comment.run_id, run.ticker if run else None):
                results.append(WorkspaceSearchResult(
                    kind="comment",
                    entity_id=comment.id,
                    title=f"Comment from {comment.author}",
                    subtitle=comment.run_id,
                    excerpt=comment.content,
                    ticker=run.ticker if run else None,
                    run_id=comment.run_id,
                ))

    if not active_kinds or "review" in active_kinds:
        for review in _load_run_reviews(tenant_id):
            run = get_run(review.run_id, tenant_id)
            if _matches_query(normalized, review.reviewer, review.status, review.note, review.run_id, run.ticker if run else None):
                results.append(WorkspaceSearchResult(
                    kind="review",
                    entity_id=review.run_id,
                    title=f"Review by {review.reviewer}",
                    subtitle=review.status,
                    excerpt=review.note or "Saved run review",
                    ticker=run.ticker if run else None,
                    run_id=review.run_id,
                ))

    return WorkspaceSearchResponse(query=normalized, active_kinds=active_kinds, results=results[:30])


def _build_share_url(path: str, tenant_id: str | None = None, **params: str) -> str:
    query: dict[str, str] = {}
    if tenant_id:
        query["tenant_id"] = tenant_id
    for key, value in params.items():
        if value:
            query[key] = value
    encoded = urlencode(query)
    return f"{path}?{encoded}" if encoded else path


def _build_public_run_share_snapshot(run, tenant_id: str | None, share_id: str, created_at: str) -> PublicRunShareSnapshot:
    return PublicRunShareSnapshot(
        share_id=share_id,
        tenant_id=tenant_id,
        run_id=run.run_id,
        ticker=run.ticker,
        date=run.date,
        asset_type=run.asset_type,
        status=run.status,
        created_at=created_at,
        signal=run.signal,
        error=run.error,
        config_summary=_run_config_summary(run),
        report_sections=dict(run.report_sections),
        current_report=run.current_report,
        final_report=run.final_report,
        view_count=0,
        last_viewed_at=None,
        expires_at=None,
        share_title=None,
        share_summary=None,
        annotation=_get_run_annotation(run.run_id, tenant_id),
        review=_get_run_review(run.run_id, tenant_id),
    )


def _build_public_run_share_html(snapshot: PublicRunShareSnapshot) -> str:
    title = snapshot.share_title or f"{snapshot.ticker} · {snapshot.date}"
    summary = snapshot.share_summary or "Public read-only TradingAgents snapshot"
    cards = [
        ("Status", snapshot.status),
        ("Signal", snapshot.signal or "n/a"),
        ("Asset", snapshot.asset_type),
        ("Shared", snapshot.created_at),
    ]
    card_html = "".join(
        f"<div class='share-card'><span class='share-card-label'>{html.escape(label)}</span><span class='share-card-value'>{html.escape(str(value or 'n/a'))}</span></div>"
        for label, value in cards
    )
    section_html = "".join(
        f"<section class='share-section'><h2>{html.escape(key.replace('_', ' ').title())}</h2><pre>{html.escape(str(content or ''))}</pre></section>"
        for key, content in snapshot.report_sections.items()
        if content
    )
    fallback_report = snapshot.final_report or snapshot.current_report or ""
    annotation_html = ""
    if snapshot.annotation is not None:
        annotation_html = (
            "<section class='share-section'>"
            "<h2>Annotation</h2>"
            f"<p><strong>{html.escape(snapshot.annotation.label)}</strong></p>"
            f"<p>{html.escape(snapshot.annotation.summary or snapshot.annotation.next_step or '')}</p>"
            "</section>"
        )
    review_html = ""
    if snapshot.review is not None:
        review_html = (
            "<section class='share-section'>"
            "<h2>Review</h2>"
            f"<p>{html.escape(snapshot.review.reviewer)} · {html.escape(snapshot.review.status)}</p>"
            f"<p>{html.escape(snapshot.review.note or '')}</p>"
            "</section>"
        )
    config_html = "".join(
        f"<li><strong>{html.escape(str(key))}:</strong> {html.escape(str(value))}</li>"
        for key, value in snapshot.config_summary.items()
        if value is not None and value != ""
    )
    full_report_html = (
        f"<section class='share-section'><h2>Full Report</h2><pre>{html.escape(snapshot.final_report)}</pre></section>"
        if snapshot.final_report else ""
    )
    sections = section_html or (
        f"<section class='share-section'><h2>Report</h2><pre>{html.escape(fallback_report or 'No report available.')}</pre></section>"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} · TradingAgents Share</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#0b1220; color:#e6edf3; margin:0; padding:2rem; }}
    main {{ max-width: 960px; margin: 0 auto; }}
    .hero {{ margin-bottom: 1.5rem; }}
    .hero h1 {{ margin: 0 0 0.5rem; font-size: 2rem; }}
    .hero p {{ margin: 0; color:#94a3b8; }}
    .share-grid {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap:0.75rem; margin:1.5rem 0; }}
    .share-card {{ background:#111827; border:1px solid #233044; border-radius:10px; padding:0.85rem 1rem; }}
    .share-card-label {{ display:block; font-size:0.75rem; color:#94a3b8; margin-bottom:0.35rem; text-transform:uppercase; }}
    .share-card-value {{ display:block; font-size:1rem; font-weight:600; }}
    .share-section {{ background:#111827; border:1px solid #233044; border-radius:10px; padding:1rem 1.1rem; margin-bottom:1rem; }}
    .share-section h2 {{ margin:0 0 0.75rem; font-size:1rem; color:#4fd1c5; }}
    .share-section pre {{ white-space:pre-wrap; word-break:break-word; margin:0; font-family: ui-monospace, SFMono-Regular, monospace; }}
    .share-section ul {{ margin:0; padding-left:1.2rem; }}
    a {{ color:#4fd1c5; }}
  </style>
</head>
<body>
  <main>
    <div class="hero">
      <h1>{html.escape(title)}</h1>
      <p>{html.escape(summary)}</p>
    </div>
    <div class="share-grid">{card_html}</div>
    <section class="share-section">
      <h2>Configuration Summary</h2>
      <ul>{config_html or '<li>No configuration summary available.</li>'}</ul>
    </section>
    {annotation_html}
    {review_html}
    {full_report_html}
    {sections}
  </main>
</body>
</html>"""


@router.get("/api/providers", response_model=list[ProviderInfo])
async def list_providers():
    """Return available LLM providers and their model catalogs."""
    providers = []
    for provider_key, modes in MODEL_OPTIONS.items():
        quick = [
            ProviderModel(label=label, value=value)
            for label, value in modes.get("quick", [])
        ]
        deep = [
            ProviderModel(label=label, value=value)
            for label, value in modes.get("deep", [])
        ]
        providers.append(ProviderInfo(
            provider=provider_key,
            display_name=_PROVIDER_DISPLAY_NAMES.get(provider_key, provider_key),
            quick_models=quick,
            deep_models=deep,
        ))
    return providers


@router.post("/api/runs", response_model=AnalysisResponse, status_code=201)
async def create_analysis_run(req: AnalysisRequest, request: Request):
    """Create and start a new analysis run."""
    loop = asyncio.get_running_loop()
    tenant_id = _request_tenant_id(request)
    result = create_run(req, loop, tenant_id)
    if isinstance(result, str):
        if result == "busy":
            raise HTTPException(
                status_code=409,
                detail="An analysis is already running. Please wait for it to complete.",
            )
        raise HTTPException(status_code=500, detail=result)
    return _analysis_response_from_run(result)


@router.post("/api/runs/batch", response_model=BatchAnalysisResponse, status_code=201)
async def create_batch_analysis_runs(payload: BatchAnalysisRequest, request: Request):
    """Create and queue multiple analysis runs from manual tickers or the watchlist."""
    tenant_id = _request_tenant_id(request)
    tickers = _resolve_batch_tickers(payload, tenant_id)
    if not tickers:
        raise HTTPException(status_code=400, detail="Provide at least one ticker or use the watchlist source.")

    loop = asyncio.get_running_loop()
    responses: list[AnalysisResponse] = []
    for ticker in tickers:
        req = AnalysisRequest(
            ticker=ticker,
            date=payload.date,
            asset_type=_infer_asset_type(ticker),
            analysts=payload.analysts,
            llm_provider=payload.llm_provider,
            deep_think_model=payload.deep_think_model,
            quick_think_model=payload.quick_think_model,
            research_depth=payload.research_depth,
            output_language=payload.output_language,
            market_profile=payload.market_profile,
            max_risk_discuss_rounds=payload.max_risk_discuss_rounds,
            max_recur_limit=payload.max_recur_limit,
            checkpoint_enabled=payload.checkpoint_enabled,
            benchmark_ticker=payload.benchmark_ticker,
            backend_url=payload.backend_url,
            temperature=payload.temperature,
            google_thinking_level=payload.google_thinking_level,
            openai_reasoning_effort=payload.openai_reasoning_effort,
            anthropic_effort=payload.anthropic_effort,
        )
        result = create_run(req, loop, tenant_id)
        if isinstance(result, str):
            raise HTTPException(status_code=500, detail=result)
        responses.append(_analysis_response_from_run(result))

    return BatchAnalysisResponse(
        source=payload.source,
        tickers=tickers,
        requested_count=len(tickers),
        created_count=len(responses),
        runs=responses,
    )


@router.get("/api/runs", response_model=list[RunSummary])
async def get_runs(
    request: Request,
    q: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    asset_type: str | None = None,
    archived: str = "active",
):
    """Return recent analysis runs, newest first."""
    tenant_id = _request_tenant_id(request)
    archived_run_ids = _load_archived_run_ids(tenant_id)
    runs = _filter_runs(
        list_runs(tenant_id),
        q=q,
        status=status,
        provider=provider,
        asset_type=asset_type,
        archived_scope=archived,
        archived_run_ids=archived_run_ids,
    )
    return [
        _build_run_summary(run, tenant_id)
        for run in runs
    ]


@router.get("/api/runs/export")
async def export_run_history_csv(
    request: Request,
    q: str | None = None,
    status: str | None = None,
    provider: str | None = None,
    asset_type: str | None = None,
    archived: str = "active",
):
    """Download the filtered run history as CSV."""
    tenant_id = _request_tenant_id(request)
    archived_run_ids = _load_archived_run_ids(tenant_id)
    runs = _filter_runs(
        list_runs(tenant_id),
        q=q,
        status=status,
        provider=provider,
        asset_type=asset_type,
        archived_scope=archived,
        archived_run_ids=archived_run_ids,
    )
    rows = [
        {
            "run_id": run.run_id,
            "ticker": run.ticker,
            "date": run.date,
            "status": run.status,
            "archived": run.run_id in archived_run_ids,
            "asset_type": run.asset_type,
            "llm_provider": run.config.get("llm_provider") or "",
            "created_at": run.created_at,
            "completed_at": run.completed_at,
            "queue_position": get_queue_position(run.run_id, tenant_id),
            "signal": run.signal,
            "error": run.error,
        }
        for run in runs
    ]
    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="run-history",
        fieldnames=["run_id", "ticker", "date", "status", "archived", "asset_type", "llm_provider", "created_at", "completed_at", "queue_position", "signal", "error"],
        rows=rows,
    )


@router.post("/api/runs/bulk", response_model=RunBulkActionResult)
async def bulk_update_runs(payload: RunBulkAction, request: Request):
    """Apply one bulk action to selected runs."""
    tenant_id = _request_tenant_id(request)
    archived_run_ids = _load_archived_run_ids(tenant_id)
    deleted = 0
    retried = 0
    archived_count = 0
    restored_count = 0
    skipped = 0

    for run_id in payload.ids:
        if payload.action == "delete":
            result = delete_run(run_id, tenant_id)
            if result is not None:
                deleted += 1
                archived_run_ids.discard(run_id)
            else:
                skipped += 1
            continue

        if payload.action == "retry":
            result = retry_run(run_id, tenant_id)
            if result is not None:
                retried += 1
            else:
                skipped += 1
            continue

        if payload.action == "archive":
            run = get_run(run_id, tenant_id)
            if run is None or run.status not in TERMINAL_RUN_STATUSES or run_id in archived_run_ids:
                skipped += 1
            else:
                archived_run_ids.add(run_id)
                archived_count += 1
            continue

        if payload.action == "restore":
            if run_id not in archived_run_ids:
                skipped += 1
            else:
                archived_run_ids.discard(run_id)
                restored_count += 1

    _save_archived_run_ids(tenant_id, archived_run_ids)
    return RunBulkActionResult(
        action=payload.action,
        deleted=deleted,
        retried=retried,
        archived=archived_count,
        restored=restored_count,
        skipped=skipped,
    )


@router.get("/api/watchlist", response_model=list[WatchlistEntry])
async def get_watchlist(request: Request):
    """Return saved tickers plus their latest known research summary."""
    tenant_id = _request_tenant_id(request)
    return _build_watchlist_entries(tenant_id)


@router.post("/api/watchlist/import", response_model=WorkspaceImportResult)
async def import_watchlist(payload: WorkspaceImportRequest, request: Request):
    """Import multiple watchlist tickers from pasted CSV/TSV/plaintext."""
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Import content must not be blank.")

    tenant_id = _request_tenant_id(request)
    parsed = parse_watchlist_import(content)
    items = _load_watchlist_items(tenant_id)
    existing_tickers = {str(item["ticker"]) for item in items}
    imported_count = 0
    skipped_count = parsed.skipped_count

    for ticker in parsed.tickers:
        if ticker in existing_tickers:
            skipped_count += 1
            continue
        items.append({
            "id": uuid.uuid4().hex[:12],
            "ticker": ticker,
            "created_at": _now_iso(),
        })
        existing_tickers.add(ticker)
        imported_count += 1

    if imported_count:
        _save_watchlist_items(tenant_id, items)

    return _build_workspace_import_result(
        imported_count=imported_count,
        skipped_count=skipped_count,
        errors=parsed.errors,
    )


@router.get("/api/alerts", response_model=AlertCenterResponse)
async def get_alert_center(request: Request):
    """Return saved alert rules and the ones currently matched by latest runs."""
    tenant_id = _request_tenant_id(request)
    return _build_alert_center_response(tenant_id)


@router.get("/api/portfolio", response_model=PortfolioResponse)
async def get_portfolio(request: Request):
    """Return tenant-scoped saved positions with latest known research context."""
    tenant_id = _request_tenant_id(request)
    return _build_portfolio_response(tenant_id)


@router.post("/api/portfolio/import", response_model=WorkspaceImportResult)
async def import_portfolio(payload: WorkspaceImportRequest, request: Request):
    """Import multiple portfolio positions from pasted CSV/TSV/plaintext."""
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Import content must not be blank.")

    tenant_id = _request_tenant_id(request)
    parsed = parse_portfolio_import(content)
    positions = _load_portfolio_positions(tenant_id)

    for row in parsed.positions:
        positions.append({
            "id": uuid.uuid4().hex[:12],
            "ticker": row.ticker,
            "quantity": row.quantity,
            "average_cost": row.average_cost,
            "created_at": _now_iso(),
        })

    if parsed.positions:
        _save_portfolio_positions(tenant_id, positions)

    return _build_workspace_import_result(
        imported_count=len(parsed.positions),
        skipped_count=parsed.skipped_count,
        errors=parsed.errors,
    )


@router.get("/api/briefing/daily", response_model=DailyBriefingResponse)
async def get_daily_briefing(request: Request):
    """Return a tenant-scoped daily briefing assembled from saved workspace data."""
    tenant_id = _request_tenant_id(request)
    return _build_daily_briefing_response(tenant_id)


@router.get("/api/dashboard", response_model=DashboardResponse)
async def get_workspace_dashboard(request: Request):
    """Return a persistent dashboard assembled from saved workspace data."""
    tenant_id = _request_tenant_id(request)
    return _build_dashboard_response(tenant_id)


@router.patch("/api/dashboard/preferences", response_model=DashboardPreferences)
async def update_dashboard_preferences(payload: DashboardPreferences, request: Request):
    """Persist dashboard widget visibility preferences."""
    tenant_id = _request_tenant_id(request)
    prefs = DashboardPreferences(
        visible_sections=payload.visible_sections or list(_DEFAULT_DASHBOARD_SECTIONS),
        section_order=payload.section_order or list(_DEFAULT_DASHBOARD_SECTIONS),
    )
    _save_dashboard_preferences(tenant_id, prefs)
    return prefs


@router.get("/api/analytics", response_model=WorkspaceAnalyticsResponse)
async def get_workspace_analytics(request: Request):
    """Return operational and usage analytics derived from saved runs."""
    tenant_id = _request_tenant_id(request)
    return _build_workspace_analytics_response(tenant_id)


@router.get("/api/analytics/export")
async def export_workspace_analytics_csv(request: Request):
    """Download workspace analytics as CSV."""
    tenant_id = _request_tenant_id(request)
    payload = _build_workspace_analytics_response(tenant_id)
    rows: list[dict[str, object]] = []

    rows.extend([
        {"section": "summary", "label": "generated_at", "value": payload.summary.generated_at},
        {"section": "summary", "label": "total_runs", "value": payload.summary.total_runs},
        {"section": "summary", "label": "terminal_runs", "value": payload.summary.terminal_runs},
        {"section": "summary", "label": "queued_runs", "value": payload.summary.queued_runs},
        {"section": "summary", "label": "running_runs", "value": payload.summary.running_runs},
        {"section": "summary", "label": "success_rate", "value": payload.summary.success_rate},
        {"section": "summary", "label": "avg_duration_seconds", "value": payload.summary.avg_duration_seconds},
        {"section": "summary", "label": "unique_ticker_count", "value": payload.summary.unique_ticker_count},
    ])

    for bucket in payload.status_breakdown:
        rows.append({"section": "status", "label": bucket.label, "value": bucket.value})
    for bucket in payload.provider_breakdown:
        rows.append({"section": "provider", "label": bucket.label, "value": bucket.value})
    for bucket in payload.signal_breakdown:
        rows.append({"section": "signal", "label": bucket.label, "value": bucket.value})
    for bucket in payload.asset_type_breakdown:
        rows.append({"section": "asset_type", "label": bucket.label, "value": bucket.value})
    for bucket in payload.top_tickers:
        rows.append({"section": "ticker", "label": bucket.label, "value": bucket.value})
    for item in payload.daily_activity:
        rows.append({"section": "daily_activity", "label": item.date, "value": item.total_runs})

    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="workspace-analytics",
        fieldnames=["section", "label", "value"],
        rows=rows,
    )


@router.get("/api/screener", response_model=WorkspaceScreenerResponse)
async def get_workspace_screener(
    request: Request,
    scope: str = "all",
    q: str | None = None,
    signal: str | None = None,
    status: str | None = None,
    asset_type: str | None = None,
    provider: str | None = None,
):
    """Return a filtered idea explorer built from saved workspace state."""
    tenant_id = _request_tenant_id(request)
    return _build_workspace_screener_response(
        tenant_id,
        scope=scope,
        q=q,
        signal_filter=signal,
        status_filter=status,
        asset_filter=asset_type,
        provider_filter=provider,
    )


@router.get("/api/screener/export")
async def export_workspace_screener_csv(
    request: Request,
    scope: str = "all",
    q: str | None = None,
    signal: str | None = None,
    status: str | None = None,
    asset_type: str | None = None,
    provider: str | None = None,
):
    """Download the current screener result set as CSV."""
    tenant_id = _request_tenant_id(request)
    payload = _build_workspace_screener_response(
        tenant_id,
        scope=scope,
        q=q,
        signal_filter=signal,
        status_filter=status,
        asset_filter=asset_type,
        provider_filter=provider,
    )
    rows = [
        {
            "ticker": row.ticker,
            "run_count": row.run_count,
            "latest_run_id": row.latest_run_id,
            "latest_signal": row.latest_signal,
            "latest_status": row.latest_status,
            "latest_date": row.latest_date,
            "latest_created_at": row.latest_created_at,
            "asset_type": row.asset_type,
            "llm_provider": row.llm_provider,
            "research_depth": row.research_depth,
            "on_watchlist": row.on_watchlist,
            "in_portfolio": row.in_portfolio,
            "is_pinned": row.is_pinned,
            "has_alert_hit": row.has_alert_hit,
            "pinned_category": row.pinned_category,
            "pinned_priority": row.pinned_priority,
            "annotation_label": row.annotation_label,
            "needs_attention": row.needs_attention,
        }
        for row in payload.rows
    ]
    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="workspace-screener",
        fieldnames=list(rows[0].keys()) if rows else [
            "ticker",
            "run_count",
            "latest_run_id",
            "latest_signal",
            "latest_status",
            "latest_date",
            "latest_created_at",
            "asset_type",
            "llm_provider",
            "research_depth",
            "on_watchlist",
            "in_portfolio",
            "is_pinned",
            "has_alert_hit",
            "pinned_category",
            "pinned_priority",
            "annotation_label",
            "needs_attention",
        ],
        rows=rows,
    )


@router.get("/api/notifications", response_model=NotificationCenterResponse)
async def get_notification_center(
    request: Request,
    unread_only: bool = False,
    member: str | None = None,
    kind: str | None = None,
    severity: str | None = None,
):
    """Return tenant-scoped in-app notifications derived from workspace activity."""
    tenant_id = _request_tenant_id(request)
    return _build_notification_center_response(
        tenant_id,
        unread_only=unread_only,
        member=member,
        kind=kind,
        severity=severity,
    )


@router.post("/api/notifications/read-all", response_model=NotificationReadResult)
async def mark_all_notifications_read(
    request: Request,
    member: str | None = None,
    kind: str | None = None,
    severity: str | None = None,
):
    """Mark all currently visible notifications as read."""
    tenant_id = _request_tenant_id(request)
    center = _build_notification_center_response(tenant_id, member=member, kind=kind, severity=severity)
    unread = [item.id for item in center.items if not item.is_read]
    reads = _load_notification_reads(tenant_id)
    read_at = _now_iso()
    for notification_id in unread:
        reads[notification_id] = read_at
    _save_notification_reads(tenant_id, reads)
    refreshed = _build_notification_center_response(tenant_id, member=member, kind=kind, severity=severity)
    return NotificationReadResult(updated=len(unread), unread_count=refreshed.unread_count)


@router.post("/api/notifications/{notification_id}/read", response_model=NotificationReadResult)
async def mark_notification_read(notification_id: str, request: Request):
    """Mark one notification as read."""
    tenant_id = _request_tenant_id(request)
    center = _build_notification_center_response(tenant_id)
    if not any(item.id == notification_id for item in center.items):
        raise HTTPException(status_code=404, detail="Notification not found")

    reads = _load_notification_reads(tenant_id)
    updated = 0 if notification_id in reads else 1
    reads[notification_id] = _now_iso()
    _save_notification_reads(tenant_id, reads)
    refreshed = _build_notification_center_response(tenant_id)
    return NotificationReadResult(updated=updated, unread_count=refreshed.unread_count)


@router.get("/api/notifications/export")
async def export_notification_center_csv(
    request: Request,
    unread_only: bool = False,
    member: str | None = None,
    kind: str | None = None,
    severity: str | None = None,
):
    """Download the current notification feed as CSV."""
    tenant_id = _request_tenant_id(request)
    payload = _build_notification_center_response(
        tenant_id,
        unread_only=unread_only,
        member=member,
        kind=kind,
        severity=severity,
    )
    rows = [
        {
            "id": item.id,
            "kind": item.kind,
            "severity": item.severity,
            "title": item.title,
            "message": item.message,
            "created_at": item.created_at,
            "is_read": item.is_read,
            "member": item.member,
            "ticker": item.ticker,
            "run_id": item.run_id,
            "target_url": item.target_url,
        }
        for item in payload.items
    ]
    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="notifications",
        fieldnames=["id", "kind", "severity", "title", "message", "created_at", "is_read", "member", "ticker", "run_id", "target_url"],
        rows=rows,
    )


@router.get("/api/automations", response_model=list[AutomationRule])
async def get_automations(request: Request):
    """Return saved scheduled automation rules."""
    tenant_id = _request_tenant_id(request)
    return list_automation_rules(tenant_id)


@router.post("/api/automations", response_model=AutomationRule, status_code=201)
async def add_automation(payload: AutomationRuleCreate, request: Request):
    """Create one scheduled automation rule."""
    tenant_id = _request_tenant_id(request)
    return create_automation_rule(payload, tenant_id)


@router.patch("/api/automations/{rule_id}", response_model=AutomationRule)
async def toggle_automation(rule_id: str, payload: AutomationRuleToggleUpdate, request: Request):
    """Enable or disable one automation rule."""
    tenant_id = _request_tenant_id(request)
    updated = update_automation_rule_enabled(rule_id, payload, tenant_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    return updated


@router.post("/api/automations/{rule_id}/run-now", response_model=AutomationRunResponse)
async def run_automation_now(rule_id: str, request: Request):
    """Queue one automation rule immediately."""
    tenant_id = _request_tenant_id(request)
    result = run_automation_rule_now(rule_id, tenant_id, start_worker=get_execution_mode() != "external_worker")
    if result is None:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    return result


@router.delete("/api/automations/{rule_id}", response_model=DeleteResult)
async def remove_automation(rule_id: str, request: Request):
    """Delete one automation rule."""
    tenant_id = _request_tenant_id(request)
    deleted = delete_automation_rule(rule_id, tenant_id)
    return DeleteResult(deleted=deleted)


@router.get("/api/workspace/export")
async def download_workspace_export(request: Request, format: str = "json"):
    """Download a tenant-scoped workspace snapshot as JSON or markdown."""
    tenant_id = _request_tenant_id(request)
    workspace = _build_workspace_export_response(tenant_id)
    normalized = format.strip().lower()
    safe_tenant = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-"
        for ch in (tenant_id or "default")
    ) or "default"
    timestamp = workspace.summary.exported_at[:19].replace(":", "-")

    if normalized == "json":
        filename = f"tradingagents-workspace-{safe_tenant}-{timestamp}.json"
        return Response(
            content=workspace.model_dump_json(indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if normalized in {"md", "markdown"}:
        filename = f"tradingagents-workspace-{safe_tenant}-{timestamp}.md"
        return Response(
            content=_build_workspace_export_markdown(workspace),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    raise HTTPException(status_code=400, detail="format must be json or markdown")


@router.post("/api/workspace/import", response_model=WorkspaceSnapshotImportResult)
async def import_workspace_snapshot(payload: WorkspaceSnapshotImportRequest, request: Request):
    """Restore saved workspace state from one exported JSON snapshot."""
    try:
        raw_snapshot = json.loads(payload.content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Import content must be valid JSON.") from exc
    if not isinstance(raw_snapshot, dict):
        raise HTTPException(status_code=400, detail="Import content must be a JSON object.")

    try:
        snapshot = WorkspaceExport.model_validate(raw_snapshot)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid workspace snapshot: {exc}") from exc

    tenant_id = _request_tenant_id(request)
    mode = payload.mode

    if "workspace_settings" in raw_snapshot:
        if mode == "replace":
            _save_workspace_settings_model(tenant_id, snapshot.workspace_settings)
        else:
            current = _load_workspace_settings_model(tenant_id)
            imported = raw_snapshot.get("workspace_settings", {})
            merged = WorkspaceSettings(
                default_home_view=snapshot.workspace_settings.default_home_view
                if "default_home_view" in imported
                else current.default_home_view,
                default_saved_view_id=snapshot.workspace_settings.default_saved_view_id
                if "default_saved_view_id" in imported
                else current.default_saved_view_id,
            )
            _save_workspace_settings_model(tenant_id, merged)

    if "dashboard_preferences" in raw_snapshot:
        if mode == "replace":
            _save_dashboard_preferences(tenant_id, snapshot.dashboard_preferences)
        else:
            _save_dashboard_preferences(tenant_id, snapshot.dashboard_preferences)

    if "watchlist" in raw_snapshot:
        imported = _watchlist_items_from_export(snapshot.watchlist)
        if mode == "replace":
            _save_watchlist_items(tenant_id, imported)
        else:
            merged = _merge_model_items(
                _load_watchlist_items(tenant_id),
                imported,
                lambda item: str(item["ticker"]).strip().upper(),
            )
            _save_watchlist_items(tenant_id, merged)

    if "alerts" in raw_snapshot:
        if mode == "replace":
            _save_alert_rules(tenant_id, snapshot.alerts.rules)
        else:
            merged = _merge_model_items(
                _load_alert_rules(tenant_id),
                snapshot.alerts.rules,
                lambda item: item.id,
            )
            _save_alert_rules(tenant_id, merged)

    if "portfolio" in raw_snapshot:
        imported = _portfolio_positions_from_export(snapshot.portfolio.positions)
        if mode == "replace":
            _save_portfolio_positions(tenant_id, imported)
        else:
            merged = _merge_model_items(
                _load_portfolio_positions(tenant_id),
                imported,
                lambda item: str(item["id"]),
            )
            _save_portfolio_positions(tenant_id, merged)

    if "workspace_members" in raw_snapshot:
        if mode == "replace":
            _save_workspace_members(tenant_id, snapshot.workspace_members)
        else:
            merged = _merge_model_items(
                _load_workspace_members(tenant_id),
                snapshot.workspace_members,
                lambda item: item.name.strip().lower(),
            )
            _save_workspace_members(tenant_id, merged)

    if "run_comments" in raw_snapshot:
        if mode == "replace":
            _save_run_comments(tenant_id, snapshot.run_comments)
        else:
            merged = _merge_model_items(
                _load_run_comments(tenant_id),
                snapshot.run_comments,
                lambda item: item.id,
            )
            _save_run_comments(tenant_id, merged)

    if "run_reviews" in raw_snapshot:
        if mode == "replace":
            _save_run_reviews(tenant_id, snapshot.run_reviews)
        else:
            merged = _merge_model_items(
                _load_run_reviews(tenant_id),
                snapshot.run_reviews,
                lambda item: item.run_id,
            )
            _save_run_reviews(tenant_id, merged)

    if "pinned_runs" in raw_snapshot:
        if mode == "replace":
            _save_pinned_runs(tenant_id, snapshot.pinned_runs)
        else:
            merged = _merge_model_items(
                _load_pinned_runs(tenant_id),
                snapshot.pinned_runs,
                lambda item: item.run_id,
            )
            _save_pinned_runs(tenant_id, merged)

    if "notes" in raw_snapshot:
        if mode == "replace":
            _save_notes(tenant_id, snapshot.notes)
        else:
            merged = _merge_model_items(
                _load_notes(tenant_id),
                snapshot.notes,
                lambda item: item.id,
            )
            _save_notes(tenant_id, merged)

    if "presets" in raw_snapshot:
        if mode == "replace":
            _save_presets(tenant_id, snapshot.presets)
        else:
            merged = _merge_model_items(
                _load_presets(tenant_id),
                snapshot.presets,
                lambda item: item.id,
            )
            _save_presets(tenant_id, merged)

    if "saved_searches" in raw_snapshot:
        if mode == "replace":
            _save_saved_searches(tenant_id, snapshot.saved_searches)
        else:
            merged = _merge_model_items(
                _load_saved_searches(tenant_id),
                snapshot.saved_searches,
                lambda item: item.id,
            )
            _save_saved_searches(tenant_id, merged)

    if "saved_views" in raw_snapshot:
        if mode == "replace":
            _save_saved_views(tenant_id, snapshot.saved_views)
        else:
            merged = _merge_model_items(
                _load_saved_views(tenant_id),
                snapshot.saved_views,
                lambda item: item.id,
            )
            _save_saved_views(tenant_id, merged)

    if "annotations" in raw_snapshot:
        if mode == "replace":
            _save_run_annotations(tenant_id, snapshot.annotations)
        else:
            merged = _merge_model_items(
                _load_run_annotations(tenant_id),
                snapshot.annotations,
                lambda item: item.run_id,
            )
            _save_run_annotations(tenant_id, merged)

    return _build_workspace_snapshot_import_result(
        mode=mode,
        watchlist_count=len(_load_watchlist_items(tenant_id)),
        alert_rule_count=len(_load_alert_rules(tenant_id)),
        portfolio_position_count=len(_load_portfolio_positions(tenant_id)),
        pinned_run_count=len(_load_pinned_runs(tenant_id)),
        note_count=len(_load_notes(tenant_id)),
        preset_count=len(_load_presets(tenant_id)),
        saved_search_count=len(_load_saved_searches(tenant_id)),
        saved_view_count=len(_load_saved_views(tenant_id)),
        annotation_count=len(_load_run_annotations(tenant_id)),
        member_count=len(_load_workspace_members(tenant_id)),
        comment_count=len(_load_run_comments(tenant_id)),
        review_count=len(_load_run_reviews(tenant_id)),
    )


@router.get("/api/search", response_model=WorkspaceSearchResponse)
async def get_workspace_search(request: Request, q: str, kinds: str | None = None):
    """Return cross-entity workspace search results."""
    tenant_id = _request_tenant_id(request)
    return _build_workspace_search_response(tenant_id, q, _normalize_search_kinds(kinds))


@router.get("/api/search/export")
async def export_workspace_search_csv(request: Request, q: str, kinds: str | None = None):
    """Download workspace search results as CSV."""
    tenant_id = _request_tenant_id(request)
    payload = _build_workspace_search_response(tenant_id, q, _normalize_search_kinds(kinds))
    rows = [
        {
            "kind": item.kind,
            "entity_id": item.entity_id,
            "title": item.title,
            "subtitle": item.subtitle,
            "excerpt": item.excerpt,
            "ticker": item.ticker,
            "run_id": item.run_id,
        }
        for item in payload.results
    ]
    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="workspace-search",
        fieldnames=["kind", "entity_id", "title", "subtitle", "excerpt", "ticker", "run_id"],
        rows=rows,
    )


@router.get("/api/searches", response_model=list[SavedSearch])
async def get_saved_searches(request: Request):
    """Return tenant-scoped saved workspace searches."""
    tenant_id = _request_tenant_id(request)
    return _load_saved_searches(tenant_id)


@router.post("/api/searches", response_model=SavedSearch, status_code=201)
async def add_saved_search(payload: SavedSearchCreate, request: Request):
    """Persist one saved workspace search."""
    tenant_id = _request_tenant_id(request)
    searches = _load_saved_searches(tenant_id)
    member = _get_workspace_member(payload.member_id, tenant_id) if payload.member_id else None
    if payload.member_id and member is None:
        raise HTTPException(status_code=400, detail="member_id must match a saved workspace member")
    search = SavedSearch(
        id=uuid.uuid4().hex[:12],
        name=payload.name,
        query=payload.query,
        kinds=payload.kinds,
        group=payload.group,
        pinned=payload.pinned,
        archived=payload.archived,
        member_id=member.id if member else None,
        member_name=member.name if member else None,
        created_at=_now_iso(),
    )
    searches.append(search)
    _save_saved_searches(tenant_id, searches)
    return search


@router.delete("/api/searches/{search_id}", response_model=DeleteResult)
async def delete_saved_search(search_id: str, request: Request):
    """Remove one saved workspace search."""
    tenant_id = _request_tenant_id(request)
    searches = _load_saved_searches(tenant_id)
    kept = [search for search in searches if search.id != search_id]
    deleted = 1 if len(kept) != len(searches) else 0
    if deleted:
        _save_saved_searches(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.patch("/api/searches/{search_id}", response_model=SavedSearch)
async def update_saved_search(search_id: str, payload: SavedSearchUpdate, request: Request):
    """Update one saved workspace search."""
    tenant_id = _request_tenant_id(request)
    searches = _load_saved_searches(tenant_id)
    updated: SavedSearch | None = None
    for item in searches:
        if item.id != search_id:
            continue
        if payload.name is not None:
            item.name = payload.name
        if payload.group is not None:
            item.group = payload.group
        if payload.pinned is not None:
            item.pinned = payload.pinned
        if payload.archived is not None:
            item.archived = payload.archived
        updated = item
        break
    if updated is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    _save_saved_searches(tenant_id, searches)
    return updated


@router.post("/api/searches/{search_id}/duplicate", response_model=SavedSearch, status_code=201)
async def duplicate_saved_search(search_id: str, request: Request):
    """Create one duplicated saved workspace search."""
    tenant_id = _request_tenant_id(request)
    searches = _load_saved_searches(tenant_id)
    source = next((item for item in searches if item.id == search_id), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Saved search not found")
    duplicate = SavedSearch(
        id=uuid.uuid4().hex[:12],
        name=_build_duplicate_name([item.name for item in searches], source.name),
        query=source.query,
        kinds=list(source.kinds),
        group=source.group,
        pinned=False,
        archived=False,
        member_id=source.member_id,
        member_name=source.member_name,
        created_at=_now_iso(),
    )
    searches.append(duplicate)
    _save_saved_searches(tenant_id, searches)
    return duplicate


@router.post("/api/searches/bulk", response_model=SavedItemBulkActionResult)
async def bulk_update_saved_searches(payload: SavedItemBulkAction, request: Request):
    """Apply one bulk lifecycle action to saved searches."""
    tenant_id = _request_tenant_id(request)
    searches = _load_saved_searches(tenant_id)
    if not payload.ids:
        return SavedItemBulkActionResult(action=payload.action, updated=0, deleted=0)

    updated = 0
    deleted = 0
    target_ids = set(payload.ids)
    if payload.action == "delete":
        kept = [item for item in searches if item.id not in target_ids]
        deleted = len(searches) - len(kept)
        if deleted:
            _save_saved_searches(tenant_id, kept)
        return SavedItemBulkActionResult(action=payload.action, updated=0, deleted=deleted)

    for item in searches:
        if item.id not in target_ids:
            continue
        item.archived = payload.action == "archive"
        updated += 1
    if updated:
        _save_saved_searches(tenant_id, searches)
    return SavedItemBulkActionResult(action=payload.action, updated=updated, deleted=0)


@router.get("/api/members", response_model=list[WorkspaceMember])
async def get_workspace_members(request: Request):
    """Return tenant-scoped lightweight workspace members."""
    tenant_id = _request_tenant_id(request)
    return _load_workspace_members(tenant_id)


@router.post("/api/members", response_model=WorkspaceMember, status_code=201)
async def add_workspace_member(payload: WorkspaceMemberCreate, request: Request):
    """Persist one workspace member for assignment workflows."""
    tenant_id = _request_tenant_id(request)
    members = _load_workspace_members(tenant_id)
    normalized = payload.name.strip().lower()
    if any(member.name.strip().lower() == normalized for member in members):
        raise HTTPException(status_code=409, detail="Workspace member already exists")
    member = WorkspaceMember(
        id=uuid.uuid4().hex[:12],
        name=payload.name,
        role=payload.role,
        created_at=_now_iso(),
    )
    members.append(member)
    _save_workspace_members(tenant_id, members)
    return member


@router.delete("/api/members/{member_id}", response_model=DeleteResult)
async def delete_workspace_member(member_id: str, request: Request):
    """Remove one workspace member and clear matching assignees from pinned actions."""
    tenant_id = _request_tenant_id(request)
    members = _load_workspace_members(tenant_id)
    kept = [member for member in members if member.id != member_id]
    deleted = 1 if len(kept) != len(members) else 0
    if deleted:
        removed_names = {member.name for member in members if member.id == member_id}
        _save_workspace_members(tenant_id, kept)
        if removed_names:
            pinned_runs = _load_pinned_runs(tenant_id)
            changed = False
            for item in pinned_runs:
                if item.assignee in removed_names:
                    item.assignee = None
                    changed = True
            if changed:
                _save_pinned_runs(tenant_id, pinned_runs)
    return DeleteResult(deleted=deleted)


@router.get("/api/members/{member_id}/workspace", response_model=MemberWorkspaceResponse)
async def get_member_workspace(member_id: str, request: Request):
    """Return one member-centric inbox/workspace view."""
    tenant_id = _request_tenant_id(request)
    member = _get_workspace_member(member_id, tenant_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Workspace member not found")
    return _build_member_workspace_response(member, tenant_id)


@router.get("/api/views", response_model=list[SavedView])
async def get_saved_views(request: Request):
    """Return tenant-scoped saved workspace views."""
    tenant_id = _request_tenant_id(request)
    return _load_saved_views(tenant_id)


@router.post("/api/views", response_model=SavedView, status_code=201)
async def add_saved_view(payload: SavedViewCreate, request: Request):
    """Persist one saved workspace view."""
    tenant_id = _request_tenant_id(request)
    views = _load_saved_views(tenant_id)
    member = _get_workspace_member(payload.member_id, tenant_id) if payload.member_id else None
    if payload.member_id and member is None:
        raise HTTPException(status_code=400, detail="member_id must match a saved workspace member")
    view = SavedView(
        id=uuid.uuid4().hex[:12],
        name=payload.name,
        url=payload.url,
        visible_panels=payload.visible_panels,
        group=payload.group,
        pinned=payload.pinned,
        archived=payload.archived,
        member_id=member.id if member else None,
        member_name=member.name if member else None,
        created_at=_now_iso(),
    )
    views.append(view)
    _save_saved_views(tenant_id, views)
    return view


@router.delete("/api/views/{view_id}", response_model=DeleteResult)
async def delete_saved_view(view_id: str, request: Request):
    """Remove one saved workspace view."""
    tenant_id = _request_tenant_id(request)
    views = _load_saved_views(tenant_id)
    kept = [view for view in views if view.id != view_id]
    deleted = 1 if len(kept) != len(views) else 0
    if deleted:
        _save_saved_views(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.patch("/api/views/{view_id}", response_model=SavedView)
async def update_saved_view(view_id: str, payload: SavedViewUpdate, request: Request):
    """Update one saved workspace view."""
    tenant_id = _request_tenant_id(request)
    views = _load_saved_views(tenant_id)
    updated: SavedView | None = None
    for item in views:
        if item.id != view_id:
            continue
        if payload.name is not None:
            item.name = payload.name
        if payload.group is not None:
            item.group = payload.group
        if payload.pinned is not None:
            item.pinned = payload.pinned
        if payload.archived is not None:
            item.archived = payload.archived
        updated = item
        break
    if updated is None:
        raise HTTPException(status_code=404, detail="Saved view not found")
    _save_saved_views(tenant_id, views)
    return updated


@router.post("/api/views/{view_id}/duplicate", response_model=SavedView, status_code=201)
async def duplicate_saved_view(view_id: str, request: Request):
    """Create one duplicated saved workspace view."""
    tenant_id = _request_tenant_id(request)
    views = _load_saved_views(tenant_id)
    source = next((item for item in views if item.id == view_id), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Saved view not found")
    duplicate = SavedView(
        id=uuid.uuid4().hex[:12],
        name=_build_duplicate_name([item.name for item in views], source.name),
        url=source.url,
        visible_panels=list(source.visible_panels),
        group=source.group,
        pinned=False,
        archived=False,
        member_id=source.member_id,
        member_name=source.member_name,
        created_at=_now_iso(),
    )
    views.append(duplicate)
    _save_saved_views(tenant_id, views)
    return duplicate


@router.post("/api/views/bulk", response_model=SavedItemBulkActionResult)
async def bulk_update_saved_views(payload: SavedItemBulkAction, request: Request):
    """Apply one bulk lifecycle action to saved views."""
    tenant_id = _request_tenant_id(request)
    views = _load_saved_views(tenant_id)
    if not payload.ids:
        return SavedItemBulkActionResult(action=payload.action, updated=0, deleted=0)

    updated = 0
    deleted = 0
    target_ids = set(payload.ids)
    if payload.action == "delete":
        kept = [item for item in views if item.id not in target_ids]
        deleted = len(views) - len(kept)
        if deleted:
            _save_saved_views(tenant_id, kept)
        return SavedItemBulkActionResult(action=payload.action, updated=0, deleted=deleted)

    for item in views:
        if item.id not in target_ids:
            continue
        item.archived = payload.action == "archive"
        updated += 1
    if updated:
        _save_saved_views(tenant_id, views)
    return SavedItemBulkActionResult(action=payload.action, updated=updated, deleted=0)


@router.get("/api/pinned-runs", response_model=list[PinnedRun])
async def get_pinned_runs(
    request: Request,
    category: str | None = None,
    action_status: str | None = None,
    assignee: str | None = None,
):
    """Return tenant-scoped pinned runs with current run metadata when available."""
    tenant_id = _request_tenant_id(request)
    items = _load_pinned_runs(tenant_id)
    if category:
        normalized = category.strip().lower()
        items = [item for item in items if item.category == normalized]
    if action_status:
        normalized = action_status.strip().lower()
        items = [item for item in items if item.action_status == normalized]
    if assignee:
        normalized = assignee.strip().lower()
        items = [item for item in items if str(item.assignee or "").strip().lower() == normalized]
    return [_build_pinned_run_entry(item, tenant_id) for item in items]


@router.get("/api/action-board", response_model=ActionBoardResponse)
async def get_action_board(request: Request):
    """Return pinned runs grouped by action status."""
    tenant_id = _request_tenant_id(request)
    return _build_action_board_response(tenant_id)


@router.post("/api/pinned-runs", response_model=PinnedRun, status_code=201)
async def add_pinned_run(payload: PinnedRunCreate, request: Request):
    """Pin one saved run for quick access."""
    tenant_id = _request_tenant_id(request)
    run = get_run(payload.run_id, tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if payload.assignee and payload.assignee not in _workspace_member_names(tenant_id):
        raise HTTPException(status_code=400, detail="Assignee must match a saved workspace member")

    pinned_runs = _load_pinned_runs(tenant_id)
    existing = next((item for item in pinned_runs if item.run_id == payload.run_id), None)
    if existing is None:
        existing = PinnedRun(
            run_id=payload.run_id,
            ticker=run.ticker,
            date=run.date,
            signal=run.signal,
            status=run.status,
            note=payload.note,
            category=payload.category,
            priority=payload.priority,
            next_action=payload.next_action,
            action_status=payload.action_status,
            assignee=payload.assignee,
            due_date=payload.due_date,
            snoozed_until=payload.snoozed_until,
            created_at=_now_iso(),
        )
        pinned_runs.append(existing)
    else:
        existing.note = payload.note
        existing.ticker = run.ticker
        existing.date = run.date
        existing.signal = run.signal
        existing.status = run.status
        existing.category = payload.category
        existing.priority = payload.priority
        existing.next_action = payload.next_action
        existing.action_status = payload.action_status
        existing.assignee = payload.assignee
        existing.due_date = payload.due_date
        existing.snoozed_until = payload.snoozed_until
    _save_pinned_runs(tenant_id, pinned_runs)
    return existing


@router.delete("/api/pinned-runs/{run_id}", response_model=DeleteResult)
async def delete_pinned_run(run_id: str, request: Request):
    """Remove one pinned run."""
    tenant_id = _request_tenant_id(request)
    pinned_runs = _load_pinned_runs(tenant_id)
    kept = [item for item in pinned_runs if item.run_id != run_id]
    deleted = 1 if len(kept) != len(pinned_runs) else 0
    if deleted:
        _save_pinned_runs(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.patch("/api/pinned-runs/{run_id}/status", response_model=PinnedRun)
async def update_pinned_run_status(run_id: str, payload: PinnedRunStatusUpdate, request: Request):
    """Update only the action status of a pinned run."""
    tenant_id = _request_tenant_id(request)
    pinned_runs = _load_pinned_runs(tenant_id)
    updated: PinnedRun | None = None
    for item in pinned_runs:
        if item.run_id != run_id:
            continue
        item.action_status = payload.action_status
        updated = item
        break
    if updated is None:
        raise HTTPException(status_code=404, detail="Pinned run not found")
    _save_pinned_runs(tenant_id, pinned_runs)
    return _build_pinned_run_entry(updated, tenant_id)


@router.patch("/api/pinned-runs/{run_id}/assignee", response_model=PinnedRun)
async def update_pinned_run_assignee(run_id: str, payload: PinnedRunAssigneeUpdate, request: Request):
    """Update only the assignee of a pinned run."""
    tenant_id = _request_tenant_id(request)
    if payload.assignee and payload.assignee not in _workspace_member_names(tenant_id):
        raise HTTPException(status_code=400, detail="Assignee must match a saved workspace member")

    pinned_runs = _load_pinned_runs(tenant_id)
    updated: PinnedRun | None = None
    for item in pinned_runs:
        if item.run_id != run_id:
            continue
        item.assignee = payload.assignee
        updated = item
        break
    if updated is None:
        raise HTTPException(status_code=404, detail="Pinned run not found")
    _save_pinned_runs(tenant_id, pinned_runs)
    return _build_pinned_run_entry(updated, tenant_id)


@router.get("/api/timeline", response_model=WorkspaceTimelineResponse)
async def get_workspace_timeline(request: Request, kinds: str | None = None):
    """Return a chronological workspace timeline built from saved tenant state."""
    tenant_id = _request_tenant_id(request)
    return _build_workspace_timeline_response(tenant_id, _normalize_timeline_kinds(kinds))


@router.get("/api/timeline/export")
async def export_workspace_timeline_csv(request: Request, kinds: str | None = None):
    """Download workspace timeline events as CSV."""
    tenant_id = _request_tenant_id(request)
    payload = _build_workspace_timeline_response(tenant_id, _normalize_timeline_kinds(kinds))
    rows = [
        {
            "kind": event.kind,
            "occurred_at": event.occurred_at,
            "title": event.title,
            "detail": event.detail,
            "ticker": event.ticker,
            "run_id": event.run_id,
        }
        for event in payload.events
    ]
    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="workspace-timeline",
        fieldnames=["kind", "occurred_at", "title", "detail", "ticker", "run_id"],
        rows=rows,
    )


@router.get("/api/calendar", response_model=WorkspaceCalendarResponse)
async def get_workspace_calendar(request: Request):
    """Return a date-grouped workspace calendar built from saved tenant events."""
    tenant_id = _request_tenant_id(request)
    return _build_workspace_calendar_response(tenant_id)


@router.get("/api/notes", response_model=list[Note])
async def get_notes(request: Request, ticker: str | None = None, run_id: str | None = None, q: str | None = None):
    """Return saved notes filtered to the current ticker or run when requested."""
    tenant_id = _request_tenant_id(request)
    notes = _load_notes(tenant_id)
    normalized_ticker = _normalize_ticker_symbol(ticker) if ticker else None

    if run_id:
        notes = [note for note in notes if note.run_id == run_id]
    elif normalized_ticker:
        notes = [note for note in notes if note.ticker == normalized_ticker]
    if q:
        notes = [note for note in notes if _note_matches_query(note, q)]
    return notes


@router.get("/api/runs/{run_id}/comments", response_model=list[RunComment])
async def get_run_comments(run_id: str, request: Request):
    """Return run-scoped collaboration comments."""
    tenant_id = _request_tenant_id(request)
    if get_run(run_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return [comment for comment in _load_run_comments(tenant_id) if comment.run_id == run_id]


@router.post("/api/runs/{run_id}/comments", response_model=RunComment, status_code=201)
async def add_run_comment(run_id: str, payload: RunCommentCreate, request: Request):
    """Persist one run-scoped collaboration comment."""
    tenant_id = _request_tenant_id(request)
    if get_run(run_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    member_names = _workspace_member_names(tenant_id)
    if not member_names:
        raise HTTPException(status_code=400, detail="Add a workspace member before posting comments")
    if payload.author not in member_names:
        raise HTTPException(status_code=400, detail="Author must match a saved workspace member")

    comments = _load_run_comments(tenant_id)
    comment = RunComment(
        id=uuid.uuid4().hex[:12],
        run_id=run_id,
        author=payload.author,
        content=payload.content,
        created_at=_now_iso(),
    )
    comments.append(comment)
    _save_run_comments(tenant_id, comments)
    return comment


@router.patch("/api/runs/{run_id}/comments/{comment_id}", response_model=RunComment)
async def update_run_comment(run_id: str, comment_id: str, payload: RunCommentResolveUpdate, request: Request):
    """Resolve or reopen one run-scoped collaboration comment."""
    tenant_id = _request_tenant_id(request)
    if get_run(run_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")

    member_names = _workspace_member_names(tenant_id)
    if payload.resolved:
        if not payload.resolved_by:
            raise HTTPException(status_code=400, detail="resolved_by is required when resolving a comment")
        if payload.resolved_by not in member_names:
            raise HTTPException(status_code=400, detail="resolved_by must match a saved workspace member")

    comments = _load_run_comments(tenant_id)
    updated: RunComment | None = None
    for comment in comments:
        if comment.run_id != run_id or comment.id != comment_id:
            continue
        comment.resolved = payload.resolved
        if payload.resolved:
            comment.resolved_by = payload.resolved_by
            comment.resolved_at = _now_iso()
        else:
            comment.resolved_by = None
            comment.resolved_at = None
        updated = comment
        break
    if updated is None:
        raise HTTPException(status_code=404, detail="Run comment not found")
    _save_run_comments(tenant_id, comments)
    return updated


@router.delete("/api/runs/{run_id}/comments/{comment_id}", response_model=DeleteResult)
async def delete_run_comment(run_id: str, comment_id: str, request: Request):
    """Remove one run-scoped collaboration comment."""
    tenant_id = _request_tenant_id(request)
    comments = _load_run_comments(tenant_id)
    kept = [comment for comment in comments if not (comment.run_id == run_id and comment.id == comment_id)]
    deleted = 1 if len(kept) != len(comments) else 0
    if deleted:
        _save_run_comments(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.post("/api/runs/{run_id}/review", response_model=RunReview, status_code=201)
async def save_run_review(run_id: str, payload: RunReviewCreate, request: Request):
    """Create or update one lightweight run review request/decision."""
    tenant_id = _request_tenant_id(request)
    if get_run(run_id, tenant_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if payload.reviewer not in _workspace_member_names(tenant_id):
        raise HTTPException(status_code=400, detail="Reviewer must match a saved workspace member")

    reviews = _load_run_reviews(tenant_id)
    existing = next((item for item in reviews if item.run_id == run_id), None)
    now = _now_iso()
    if existing is None:
        review = RunReview(
            run_id=run_id,
            reviewer=payload.reviewer,
            status=payload.status,
            note=payload.note,
            created_at=now,
            updated_at=now,
        )
        reviews.append(review)
    else:
        existing.reviewer = payload.reviewer
        existing.status = payload.status
        existing.note = payload.note
        existing.updated_at = now
        review = existing
    _save_run_reviews(tenant_id, reviews)
    return review


@router.delete("/api/runs/{run_id}/review", response_model=DeleteResult)
async def delete_run_review(run_id: str, request: Request):
    """Remove one saved run review."""
    tenant_id = _request_tenant_id(request)
    reviews = _load_run_reviews(tenant_id)
    kept = [item for item in reviews if item.run_id != run_id]
    deleted = 1 if len(kept) != len(reviews) else 0
    if deleted:
        _save_run_reviews(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.get("/api/reviews", response_model=RunReviewHistoryResponse)
async def get_run_review_history(
    request: Request,
    reviewer: str | None = None,
    status: str | None = None,
    q: str | None = None,
):
    """Return filtered review history across saved runs."""
    tenant_id = _request_tenant_id(request)
    return _build_run_review_history_response(tenant_id, reviewer=reviewer, status=status, q=q)


@router.get("/api/reviews/export")
async def export_run_review_history_csv(
    request: Request,
    reviewer: str | None = None,
    status: str | None = None,
    q: str | None = None,
):
    """Download filtered run review history as CSV."""
    tenant_id = _request_tenant_id(request)
    payload = _build_run_review_history_response(tenant_id, reviewer=reviewer, status=status, q=q)
    rows = [
        {
            "run_id": item.run_id,
            "reviewer": item.reviewer,
            "status": item.status,
            "note": item.note,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "ticker": item.ticker,
            "date": item.date,
            "signal": item.signal,
        }
        for item in payload.items
    ]
    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="review-history",
        fieldnames=["run_id", "reviewer", "status", "note", "created_at", "updated_at", "ticker", "date", "signal"],
        rows=rows,
    )


@router.get("/api/artifacts/library", response_model=list[ArtifactLibraryItem])
async def get_artifact_library(request: Request, q: str | None = None):
    """Return a workspace-wide library of downloadable run artifacts."""
    tenant_id = _request_tenant_id(request)
    return _build_artifact_library_items(tenant_id, q=q)


@router.get("/api/artifacts/library/export")
async def export_artifact_library_csv(request: Request, q: str | None = None):
    """Download the current artifact library as CSV."""
    tenant_id = _request_tenant_id(request)
    items = _build_artifact_library_items(tenant_id, q=q)
    rows = [
        {
            "run_id": item.run_id,
            "ticker": item.ticker,
            "date": item.date,
            "status": item.status,
            "created_at": item.created_at,
            "signal": item.signal,
            "error": item.error,
            "artifact_count": item.artifact_count,
            "report_download_url": item.report_download_url,
            "state_download_url": item.state_download_url,
        }
        for item in items
    ]
    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="artifact-library",
        fieldnames=["run_id", "ticker", "date", "status", "created_at", "signal", "error", "artifact_count", "report_download_url", "state_download_url"],
        rows=rows,
    )


@router.post("/api/notes", response_model=Note, status_code=201)
async def add_note(payload: NoteCreate, request: Request):
    """Persist one tenant-scoped note."""
    tenant_id = _request_tenant_id(request)
    notes = _load_notes(tenant_id)
    now = _now_iso()
    note = Note(
        id=uuid.uuid4().hex[:12],
        content=payload.content,
        tags=payload.tags,
        ticker=payload.ticker,
        run_id=payload.run_id,
        created_at=now,
        updated_at=now,
    )
    notes.append(note)
    _save_notes(tenant_id, notes)
    return note


@router.put("/api/notes/{note_id}", response_model=Note)
async def update_note(note_id: str, payload: NoteUpdate, request: Request):
    """Edit one saved note."""
    tenant_id = _request_tenant_id(request)
    notes = _load_notes(tenant_id)
    updated_note: Note | None = None
    new_notes: list[Note] = []

    for note in notes:
        if note.id != note_id:
            new_notes.append(note)
            continue
        updated_note = Note(
            id=note.id,
            content=payload.content,
            tags=payload.tags,
            ticker=note.ticker,
            run_id=note.run_id,
            created_at=note.created_at,
            updated_at=_now_iso(),
        )
        new_notes.append(updated_note)

    if updated_note is None:
        raise HTTPException(status_code=404, detail="Note not found")

    _save_notes(tenant_id, new_notes)
    return updated_note


@router.delete("/api/notes/{note_id}", response_model=DeleteResult)
async def delete_note(note_id: str, request: Request):
    """Remove a saved note."""
    tenant_id = _request_tenant_id(request)
    notes = _load_notes(tenant_id)
    kept = [note for note in notes if note.id != note_id]
    deleted = 1 if len(kept) != len(notes) else 0
    if deleted:
        _save_notes(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.get("/api/presets", response_model=list[AnalysisPreset])
async def get_presets(request: Request):
    """Return saved tenant-scoped analysis presets."""
    tenant_id = _request_tenant_id(request)
    return _load_presets(tenant_id)


@router.post("/api/presets", response_model=AnalysisPreset, status_code=201)
async def add_preset(payload: AnalysisPresetCreate, request: Request):
    """Persist one tenant-scoped analysis preset."""
    tenant_id = _request_tenant_id(request)
    presets = _load_presets(tenant_id)
    preset = AnalysisPreset(
        id=uuid.uuid4().hex[:12],
        name=payload.name,
        created_at=_now_iso(),
        analysis_request=payload.analysis_request,
    )
    presets.append(preset)
    _save_presets(tenant_id, presets)
    return preset


@router.patch("/api/presets/{preset_id}", response_model=AnalysisPreset)
async def update_preset(preset_id: str, payload: AnalysisPresetUpdate, request: Request):
    """Rename one saved analysis preset."""
    tenant_id = _request_tenant_id(request)
    presets = _load_presets(tenant_id)
    updated: AnalysisPreset | None = None
    for preset in presets:
        if preset.id != preset_id:
            continue
        preset.name = payload.name
        updated = preset
        break
    if updated is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    _save_presets(tenant_id, presets)
    return updated


@router.post("/api/presets/{preset_id}/duplicate", response_model=AnalysisPreset, status_code=201)
async def duplicate_preset(preset_id: str, request: Request):
    """Duplicate one saved analysis preset."""
    tenant_id = _request_tenant_id(request)
    presets = _load_presets(tenant_id)
    source = next((preset for preset in presets if preset.id == preset_id), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    duplicate = AnalysisPreset(
        id=uuid.uuid4().hex[:12],
        name=_build_duplicate_name([preset.name for preset in presets], source.name),
        created_at=_now_iso(),
        analysis_request=source.analysis_request,
    )
    presets.append(duplicate)
    _save_presets(tenant_id, presets)
    return duplicate


@router.delete("/api/presets/{preset_id}", response_model=DeleteResult)
async def delete_preset(preset_id: str, request: Request):
    """Remove a saved analysis preset."""
    tenant_id = _request_tenant_id(request)
    presets = _load_presets(tenant_id)
    kept = [preset for preset in presets if preset.id != preset_id]
    deleted = 1 if len(kept) != len(presets) else 0
    if deleted:
        _save_presets(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.get("/api/share/runs/{run_id}", response_model=ShareLink)
async def share_run_link(run_id: str, request: Request):
    """Return a relative link that re-opens one saved run."""
    tenant_id = _request_tenant_id(request)
    run = get_run(run_id, tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return ShareLink(
        label="Run Link",
        url=_build_share_url("/", tenant_id, run_id=run_id),
    )


@router.get("/api/share/tickers/{ticker}", response_model=ShareLink)
async def share_ticker_link(ticker: str, request: Request):
    """Return a relative link that re-opens one ticker home context."""
    tenant_id = _request_tenant_id(request)
    normalized = _normalize_ticker_symbol(ticker)
    return ShareLink(
        label="Ticker Link",
        url=_build_share_url("/", tenant_id, ticker=normalized),
    )


@router.get("/api/share/compare", response_model=ShareLink)
async def share_compare_link(left_run_id: str, right_run_id: str, request: Request):
    """Return a relative link that restores one compare view."""
    tenant_id = _request_tenant_id(request)
    return ShareLink(
        label="Compare Link",
        url=_build_share_url(
            "/",
            tenant_id,
            compare_left_run_id=left_run_id,
            compare_right_run_id=right_run_id,
        ),
    )


@router.get("/api/share/briefing/daily", response_model=ShareLink)
async def share_daily_briefing_link(request: Request):
    """Return a relative link that restores the daily briefing view."""
    tenant_id = _request_tenant_id(request)
    return ShareLink(
        label="Briefing Link",
        url=_build_share_url("/", tenant_id, view="briefing"),
    )


@router.post("/api/runs/{run_id}/public-share", response_model=PublicRunShareInfo, status_code=201)
async def create_public_run_share(run_id: str, request: Request):
    """Create or refresh a public read-only snapshot for one saved run."""
    tenant_id = _request_tenant_id(request)
    run = get_run(run_id, tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    shares = _load_public_run_shares(tenant_id)
    existing = next((item for item in shares if item.run_id == run_id), None)
    share_id = existing.share_id if existing is not None else uuid.uuid4().hex[:12]
    created_at = existing.created_at if existing is not None else _now_iso()
    snapshot = _build_public_run_share_snapshot(run, tenant_id, share_id, created_at)
    if existing is not None:
        snapshot.view_count = existing.view_count
        snapshot.last_viewed_at = existing.last_viewed_at
        snapshot.expires_at = existing.expires_at
        snapshot.share_title = existing.share_title
        snapshot.share_summary = existing.share_summary

    if existing is None:
        shares.append(snapshot)
    else:
        index = shares.index(existing)
        shares[index] = snapshot
    _save_public_run_shares(tenant_id, shares)
    return _build_public_share_info(snapshot)


@router.get("/api/public-shares", response_model=list[PublicRunShareListItem])
async def list_public_run_shares(
    request: Request,
    q: str | None = None,
    availability: str = "all",
):
    """Return the current tenant's public run snapshots."""
    tenant_id = _request_tenant_id(request)
    normalized_query = str(q or "").strip().lower()
    availability_filter = _normalize_public_share_availability(availability)
    items = [
        _build_public_share_list_item(item)
        for item in _load_public_run_shares(tenant_id)
        if (
            availability_filter == "all"
            or (availability_filter == "active" and not _is_public_share_expired(item))
            or (availability_filter == "expired" and _is_public_share_expired(item))
        )
        and (
            not normalized_query
            or _matches_query(
                normalized_query,
                item.share_id,
                item.ticker,
                item.run_id,
                item.status,
                item.signal,
                item.share_title,
                item.share_summary,
            )
        )
    ]
    items.sort(key=lambda item: item.created_at, reverse=True)
    return items


@router.get("/api/public-shares/export")
async def export_public_run_shares_csv(
    request: Request,
    q: str | None = None,
    availability: str = "all",
):
    """Download public share snapshots as CSV."""
    tenant_id = _request_tenant_id(request)
    items = await list_public_run_shares(request, q=q, availability=availability)
    rows = [
        {
            "share_id": item.share_id,
            "url": item.url,
            "created_at": item.created_at,
            "run_id": item.run_id,
            "ticker": item.ticker,
            "date": item.date,
            "status": item.status,
            "signal": item.signal,
            "view_count": item.view_count,
            "last_viewed_at": item.last_viewed_at,
            "expires_at": item.expires_at,
            "share_title": item.share_title,
            "share_summary": item.share_summary,
        }
        for item in items
    ]
    return _build_csv_download_response(
        tenant_id=tenant_id,
        prefix="public-shares",
        fieldnames=["share_id", "url", "created_at", "run_id", "ticker", "date", "status", "signal", "view_count", "last_viewed_at", "expires_at", "share_title", "share_summary"],
        rows=rows,
    )


@router.patch("/api/runs/{run_id}/public-share", response_model=PublicRunShareInfo)
async def update_public_run_share(run_id: str, payload: PublicRunShareUpdate, request: Request):
    """Set or clear one public share's expiry."""
    tenant_id = _request_tenant_id(request)
    shares = _load_public_run_shares(tenant_id)
    updated: PublicRunShareSnapshot | None = None
    for item in shares:
        if item.run_id != run_id:
            continue
        if payload.expires_in_days is None:
            item.expires_at = None
        else:
            expires_at = datetime.datetime.now() + datetime.timedelta(days=payload.expires_in_days)
            item.expires_at = expires_at.isoformat()
        if payload.share_title is not None:
            item.share_title = payload.share_title or None
        if payload.share_summary is not None:
            item.share_summary = payload.share_summary or None
        updated = item
        break
    if updated is None:
        raise HTTPException(status_code=404, detail="Public run share not found")
    _save_public_run_shares(tenant_id, shares)
    return _build_public_share_info(updated)


@router.delete("/api/runs/{run_id}/public-share", response_model=DeleteResult)
async def delete_public_run_share(run_id: str, request: Request):
    """Revoke one public read-only snapshot."""
    tenant_id = _request_tenant_id(request)
    shares = _load_public_run_shares(tenant_id)
    kept = [item for item in shares if item.run_id != run_id]
    deleted = 1 if len(kept) != len(shares) else 0
    if deleted:
        _save_public_run_shares(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.post("/api/portfolio/positions", response_model=PortfolioPosition, status_code=201)
async def add_portfolio_position(payload: PortfolioPositionCreate, request: Request):
    """Persist one tenant-scoped portfolio position."""
    tenant_id = _request_tenant_id(request)
    positions = _load_portfolio_positions(tenant_id)
    stored = {
        "id": uuid.uuid4().hex[:12],
        "ticker": payload.ticker,
        "quantity": float(payload.quantity),
        "average_cost": float(payload.average_cost),
        "created_at": _now_iso(),
    }
    positions.append(stored)
    _save_portfolio_positions(tenant_id, positions)
    return _build_portfolio_position(stored, tenant_id)


@router.delete("/api/portfolio/positions/{position_id}", response_model=DeleteResult)
async def delete_portfolio_position(position_id: str, request: Request):
    """Remove one saved portfolio position."""
    tenant_id = _request_tenant_id(request)
    positions = _load_portfolio_positions(tenant_id)
    kept = [position for position in positions if position["id"] != position_id]
    deleted = 1 if len(kept) != len(positions) else 0
    if deleted:
        _save_portfolio_positions(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.post("/api/alerts/rules", response_model=AlertRule, status_code=201)
async def add_alert_rule(payload: AlertRuleCreate, request: Request):
    """Persist one tenant-scoped alert rule."""
    tenant_id = _request_tenant_id(request)
    rules = _load_alert_rules(tenant_id)
    rule = AlertRule(
        id=uuid.uuid4().hex[:12],
        ticker=payload.ticker,
        field=payload.field,
        value=_normalize_alert_value(payload.field, payload.value),
        created_at=_now_iso(),
    )
    rules.append(rule)
    _save_alert_rules(tenant_id, rules)
    return rule


@router.delete("/api/alerts/rules/{rule_id}", response_model=DeleteResult)
async def delete_alert_rule(rule_id: str, request: Request):
    """Remove a saved alert rule."""
    tenant_id = _request_tenant_id(request)
    rules = _load_alert_rules(tenant_id)
    kept = [rule for rule in rules if rule.id != rule_id]
    deleted = 1 if len(kept) != len(rules) else 0
    if deleted:
        _save_alert_rules(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.post("/api/watchlist", response_model=WatchlistEntry, status_code=201)
async def add_watchlist_ticker(update: WatchlistUpdate, request: Request):
    """Persist one ticker in the current tenant's watchlist."""
    tenant_id = _request_tenant_id(request)
    items = _load_watchlist_items(tenant_id)
    if not any(str(item["ticker"]) == update.ticker for item in items):
        items.append({
            "id": uuid.uuid4().hex[:12],
            "ticker": update.ticker,
            "created_at": _now_iso(),
        })
        _save_watchlist_items(tenant_id, items)

    matched = next((item for item in items if str(item["ticker"]) == update.ticker), None)
    created_at = matched.get("created_at") if matched and isinstance(matched.get("created_at"), str) else None
    return _watchlist_entry_from_overview(
        _build_ticker_overview(update.ticker, tenant_id),
        created_at=created_at,
    )


@router.delete("/api/watchlist/{ticker}", response_model=DeleteResult)
async def delete_watchlist_ticker(ticker: str, request: Request):
    """Remove a ticker from the current tenant's watchlist."""
    tenant_id = _request_tenant_id(request)
    normalized = _normalize_ticker_symbol(ticker)
    items = _load_watchlist_items(tenant_id)
    kept = [item for item in items if str(item["ticker"]) != normalized]
    deleted = 1 if len(kept) != len(items) else 0
    if deleted:
        _save_watchlist_items(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.get("/api/tickers/{ticker}", response_model=TickerOverview)
async def get_ticker_overview(ticker: str, request: Request):
    """Return a ticker-centric summary built from the current tenant's run history."""
    tenant_id = _request_tenant_id(request)
    normalized = _normalize_ticker_symbol(ticker)
    return _build_ticker_overview(normalized, tenant_id)


@router.get("/api/runs/compare", response_model=RunComparison)
async def compare_runs(left_run_id: str, right_run_id: str, request: Request):
    """Return a side-by-side comparison of two saved runs."""
    tenant_id = _request_tenant_id(request)
    left_run = get_run(left_run_id, tenant_id)
    right_run = get_run(right_run_id, tenant_id)
    if left_run is None or right_run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    left = _build_compare_run(left_run)
    right = _build_compare_run(right_run)
    available_sections, differing_sections = _diff_sections(left, right)
    return RunComparison(
        left=left,
        right=right,
        available_sections=available_sections,
        differing_summary_fields=_diff_summary_fields(left, right),
        differing_sections=differing_sections,
    )


@router.post("/api/runs/{run_id}/chat", response_model=RunChatResponse)
async def chat_about_run(run_id: str, payload: RunChatRequest, request: Request):
    """Answer a follow-up question against one saved run."""
    tenant_id = _request_tenant_id(request)
    run = get_run(run_id, tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    settings = load_settings(path=get_web_settings_path(tenant_id))
    config = run.config or {}
    provider = str(config.get("llm_provider") or "openai")
    model = str(config.get("deep_think_llm") or config.get("quick_think_llm") or "")
    if not model:
        raise HTTPException(status_code=400, detail="Run has no configured chat model")

    prompt = _build_follow_up_prompt(run, payload)
    llm_kwargs = _get_provider_kwargs_from_config(config)
    with PROCESS_EXECUTION_LOCK:
        export_api_keys_to_env(settings, overwrite=True)
        client = create_llm_client(
            provider=provider,
            model=model,
            base_url=config.get("backend_url"),
            **llm_kwargs,
        )
        response = client.get_llm().invoke(prompt)

    answer = getattr(response, "content", str(response))
    return RunChatResponse(
        run_id=run_id,
        provider=provider,
        model=model,
        question=payload.question,
        answer=str(answer).strip(),
    )


@router.post("/api/runs/{run_id}/annotation", response_model=RunAnnotation, status_code=201)
async def save_run_annotation(run_id: str, payload: RunAnnotationCreate, request: Request):
    """Create or update one structured annotation for a saved run."""
    tenant_id = _request_tenant_id(request)
    run = get_run(run_id, tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    annotations = _load_run_annotations(tenant_id)
    existing = next((item for item in annotations if item.run_id == run_id), None)
    now = _now_iso()
    if existing is None:
        annotation = RunAnnotation(
            run_id=run_id,
            label=payload.label,
            summary=payload.summary,
            next_step=payload.next_step,
            created_at=now,
            updated_at=now,
        )
        annotations.append(annotation)
    else:
        existing.label = payload.label
        existing.summary = payload.summary
        existing.next_step = payload.next_step
        existing.updated_at = now
        annotation = existing
    _save_run_annotations(tenant_id, annotations)
    return annotation


@router.delete("/api/runs/{run_id}/annotation", response_model=DeleteResult)
async def delete_run_annotation(run_id: str, request: Request):
    """Remove one saved run annotation."""
    tenant_id = _request_tenant_id(request)
    annotations = _load_run_annotations(tenant_id)
    kept = [item for item in annotations if item.run_id != run_id]
    deleted = 1 if len(kept) != len(annotations) else 0
    if deleted:
        _save_run_annotations(tenant_id, kept)
    return DeleteResult(deleted=deleted)


@router.get("/api/runs/{run_id}", response_model=RunStatus)
async def get_run_status(run_id: str, request: Request):
    """Get the current status of an analysis run."""
    tenant_id = _request_tenant_id(request)
    run = get_run(run_id, tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatus(
        run_id=run.run_id,
        status=run.status,
        ticker=run.ticker,
        date=run.date,
        asset_type=run.asset_type,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        queue_position=get_queue_position(run.run_id, tenant_id),
        agents=dict(run.agents),
        report_sections=dict(run.report_sections),
        config_summary=_run_config_summary(run),
        current_report=run.current_report,
        final_report=run.final_report,
        signal=run.signal,
        error=run.error,
        annotation=_get_run_annotation(run.run_id, tenant_id),
        review=_get_run_review(run.run_id, tenant_id),
        public_share=_build_public_share_info(_get_public_run_share_for_run(run.run_id, tenant_id)),
    )


@router.post("/api/runs/{run_id}/cancel", response_model=RunStatus)
async def cancel_analysis_run(run_id: str, request: Request):
    """Request cancellation for an in-flight analysis run."""
    tenant_id = _request_tenant_id(request)
    run = cancel_run(run_id, tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatus(
        run_id=run.run_id,
        status=run.status,
        ticker=run.ticker,
        date=run.date,
        asset_type=run.asset_type,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        queue_position=get_queue_position(run.run_id, tenant_id),
        agents=dict(run.agents),
        report_sections=dict(run.report_sections),
        config_summary=_run_config_summary(run),
        current_report=run.current_report,
        final_report=run.final_report,
        signal=run.signal,
        error=run.error,
        annotation=_get_run_annotation(run.run_id, tenant_id),
        review=_get_run_review(run.run_id, tenant_id),
        public_share=_build_public_share_info(_get_public_run_share_for_run(run.run_id, tenant_id)),
    )


@router.delete("/api/runs/{run_id}", status_code=204)
async def delete_analysis_run(run_id: str, request: Request):
    """Delete a terminal run and its persisted artifacts."""
    tenant_id = _request_tenant_id(request)
    deleted = delete_run(run_id, tenant_id)
    if deleted is not None:
        archived_run_ids = _load_archived_run_ids(tenant_id)
        if run_id in archived_run_ids:
            archived_run_ids.discard(run_id)
            _save_archived_run_ids(tenant_id, archived_run_ids)
        return None

    existing = get_run(run_id, tenant_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Run is still active")
    raise HTTPException(status_code=404, detail="Run not found")


@router.post("/api/runs/{run_id}/retry", response_model=AnalysisResponse, status_code=201)
async def retry_analysis_run(run_id: str, request: Request):
    """Clone a terminal run into a new queued run."""
    tenant_id = _request_tenant_id(request)
    run = retry_run(run_id, tenant_id)
    if run is not None:
        return AnalysisResponse(
            run_id=run.run_id,
            status=run.status,
            ticker=run.ticker,
            date=run.date,
        )

    existing = get_run(run_id, tenant_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Run is still active")
    raise HTTPException(status_code=404, detail="Run not found")


@router.get("/api/runs/{run_id}/timeline", response_model=list[RunEvent])
async def get_run_timeline(run_id: str, request: Request):
    """Return the persisted event timeline for a run."""
    run = get_run(run_id, _request_tenant_id(request))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return list(run.event_history)


@router.get("/api/runs/{run_id}/events")
async def stream_run_events(run_id: str, request: Request):
    """SSE endpoint for streaming analysis progress."""
    tenant_id = _request_tenant_id(request)
    run = get_run(run_id, tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if get_execution_mode() == "external_worker":
        async def persisted_event_generator():
            emitted = 0
            while True:
                refreshed = get_run(run_id, tenant_id)
                if not refreshed:
                    break

                history = list(refreshed.event_history)
                for record in history[emitted:]:
                    yield {
                        "event": record.get("event", "message"),
                        "data": json.dumps(record.get("data", {})),
                    }
                emitted = len(history)

                if refreshed.status in TERMINAL_RUN_STATUSES and emitted >= len(history):
                    break
                await asyncio.sleep(1.0)

        return EventSourceResponse(persisted_event_generator())

    subscriber_id, queue = subscribe_run_events(run, tenant_id)

    async def event_generator():
        try:
            if run.status in TERMINAL_RUN_STATUSES:
                terminal_event = build_terminal_event(run)
                if terminal_event is not None:
                    yield {
                        "event": terminal_event["event"],
                        "data": json.dumps(terminal_event["data"]),
                    }
                    return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield {"comment": "keepalive"}
                    continue

                event_type = event.get("event", "message")
                data = event.get("data", {})
                yield {"event": event_type, "data": json.dumps(data)}

                if event_type in ("complete", "error", "cancelled"):
                    break
        except asyncio.CancelledError:
            pass
        finally:
            unsubscribe_run_events(run, subscriber_id, tenant_id)

    return EventSourceResponse(event_generator())


# ── Settings endpoints ─────────────────────────────────────────────────────

# Default empty API keys for all known providers.
_EMPTY_API_KEYS = dict.fromkeys(["openai", "anthropic", "google", "xai", "deepseek", "qwen", "qwen-cn", "glm", "glm-cn", "minimax", "minimax-cn", "openrouter", "mistral", "kimi", "groq", "nvidia", "openai_compatible", "ollama", "bedrock", "FRED_API_KEY", "AWS_DEFAULT_REGION", "AWS_PROFILE", "OLLAMA_BASE_URL"], "")


def _settings_to_response(settings: dict) -> SettingsResponse:
    """Convert raw settings dict to a SettingsResponse."""
    api_keys = settings.get("api_keys", {})
    # Fill in any missing providers with empty string
    full_keys = {**_EMPTY_API_KEYS, **api_keys}

    llm = settings.get("llm", {})
    analysis = settings.get("analysis", {})
    workspace = settings.get("workspace", {})
    data = settings.get("data", {})
    security = settings.get("security", {})
    integrations = settings.get("integrations", {})
    webhook = integrations.get("webhook", {}) if isinstance(integrations, dict) else {}
    dv = data.get("data_vendors", {})
    tv = data.get("tool_vendors", {})

    return SettingsResponse(
        api_keys=mask_api_keys(full_keys),
        llm=LLMSettings(
            provider=llm.get("provider", "openai"),
            quick_think_model=llm.get("quick_think_model", "gpt-5.4-mini"),
            deep_think_model=llm.get("deep_think_model", "gpt-5.5"),
            backend_url=llm.get("backend_url"),
            temperature=llm.get("temperature"),
            google_thinking_level=llm.get("google_thinking_level"),
            openai_reasoning_effort=llm.get("openai_reasoning_effort"),
            anthropic_effort=llm.get("anthropic_effort"),
        ),
        analysis=AnalysisSettings(
            output_language=analysis.get("output_language", "English"),
            market_profile=analysis.get("market_profile", "default"),
            research_depth=analysis.get("research_depth", analysis.get("max_debate_rounds", 1)),
            max_risk_discuss_rounds=analysis.get("max_risk_discuss_rounds", 1),
            max_recur_limit=analysis.get("max_recur_limit", 100),
            checkpoint_enabled=analysis.get("checkpoint_enabled", False),
            benchmark_ticker=analysis.get("benchmark_ticker"),
            memory_log_max_entries=analysis.get("memory_log_max_entries"),
        ),
        workspace=WorkspaceSettings(
            default_home_view=workspace.get("default_home_view", "auto"),
            default_saved_view_id=workspace.get("default_saved_view_id"),
        ),
        data=DataSettings(
            data_vendors=DataVendorSettings(**{
                k: v for k, v in dv.items() if k in DataVendorSettings.model_fields
            }) if dv else DataVendorSettings(),
            tool_vendors=ToolVendorSettings(**{
                k: v for k, v in tv.items() if k in ToolVendorSettings.model_fields
            }) if tv else ToolVendorSettings(),
            news_article_limit=data.get("news_article_limit", 20),
            global_news_article_limit=data.get("global_news_article_limit", 10),
            global_news_lookback_days=data.get("global_news_lookback_days", 7),
            global_news_queries=list(data.get("global_news_queries", [
                "Federal Reserve interest rates inflation",
                "S&P 500 earnings GDP economic outlook",
                "geopolitical risk trade war sanctions",
                "ECB Bank of England BOJ central bank policy",
                "oil commodities supply chain energy",
            ])),
        ),
        security=SecuritySettings(
            web_api_token="***" if security.get("web_api_token") else None,
        ),
        integrations=IntegrationsSettings(
            webhook={
                "enabled": bool(webhook.get("enabled", False)),
                "url": webhook.get("url"),
                "bearer_token": "***" if webhook.get("bearer_token") else None,
                "event_kinds": list(webhook.get("event_kinds", ["run", "alert", "action"])),
                "last_delivery_at": webhook.get("last_delivery_at"),
                "last_error": webhook.get("last_error"),
            }
        ),
    )


@router.get("/api/settings", response_model=SettingsResponse)
async def get_settings(request: Request):
    """Return current settings (API keys masked)."""
    tenant_id = _request_tenant_id(request)
    settings = load_settings(path=get_web_settings_path(tenant_id))
    return _settings_to_response(settings)


@router.put("/api/settings", response_model=SettingsResponse)
async def put_settings(update: SettingsUpdate, request: Request):
    """Update settings and persist to disk."""
    tenant_id = _request_tenant_id(request)
    settings_path = get_web_settings_path(tenant_id)
    existing = _load_settings_for_update(settings_path)

    # Merge API keys — "***" means "keep existing value"
    if update.api_keys is not None:
        existing_keys = existing.get("api_keys", {})
        for k, v in update.api_keys.items():
            if v == "***":
                continue  # masked — don't overwrite
            existing_keys[k] = v
        existing["api_keys"] = existing_keys

    # Merge LLM settings
    if update.llm is not None:
        llm = existing.get("llm", {})
        llm.update(update.llm.model_dump(exclude_none=True))
        existing["llm"] = llm

    # Merge analysis settings
    if update.analysis is not None:
        analysis = existing.get("analysis", {})
        analysis.update(update.analysis.model_dump(exclude_none=True))
        existing["analysis"] = analysis

    if update.workspace is not None:
        workspace = existing.get("workspace", {})
        workspace.update(update.workspace.model_dump(exclude_none=True))
        existing["workspace"] = workspace

    # Merge data settings
    if update.data is not None:
        data = existing.get("data", {})
        update_data = update.data.model_dump(exclude_none=True)
        if "data_vendors" in update_data and isinstance(update_data["data_vendors"], dict):
            existing_dv = data.get("data_vendors", {})
            existing_dv.update(update_data.pop("data_vendors"))
            data["data_vendors"] = existing_dv
        if "tool_vendors" in update_data and isinstance(update_data["tool_vendors"], dict):
            existing_tv = data.get("tool_vendors", {})
            existing_tv.update(update_data.pop("tool_vendors"))
            data["tool_vendors"] = existing_tv
        data.update(update_data)
        existing["data"] = data

    if update.security is not None:
        security = existing.get("security", {})
        for key, value in update.security.model_dump(exclude_none=True).items():
            if value == "***":
                continue
            security[key] = value
        existing["security"] = security

    if update.integrations is not None:
        integrations = existing.get("integrations", {})
        if not isinstance(integrations, dict):
            integrations = {}
        existing_webhook = integrations.get("webhook", {})
        if not isinstance(existing_webhook, dict):
            existing_webhook = {}
        webhook_update = update.integrations.webhook.model_dump(exclude_none=True)
        if webhook_update.get("bearer_token") == "***":
            webhook_update.pop("bearer_token", None)
        existing_webhook.update(webhook_update)
        integrations["webhook"] = existing_webhook
        existing["integrations"] = integrations

    save_settings(existing, path=settings_path)
    export_api_keys_to_env(existing, overwrite=True)
    return _settings_to_response(existing)


@router.get("/api/runs/{run_id}/artifacts", response_model=list[ArtifactInfo])
async def list_run_artifacts(run_id: str, request: Request):
    """List downloadable artifacts for a completed run."""
    run = get_run(run_id, _request_tenant_id(request))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return [
        ArtifactInfo(
            name=artifact.key,
            label=artifact.label,
            download_url=f"/api/runs/{run_id}/artifacts/download?name={artifact.key}",
        )
        for artifact in build_run_artifacts(
            report_path=run.report_path,
            state_log_path=run.state_log_path,
        )
    ]


@router.get("/api/runs/{run_id}/artifacts/download")
async def download_named_run_artifact(run_id: str, name: str, request: Request):
    """Download any named artifact for a run."""
    run = get_run(run_id, _request_tenant_id(request))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    artifact = resolve_run_artifact(
        report_path=run.report_path,
        state_log_path=run.state_log_path,
        key=name,
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not available")

    media_type = "application/json" if artifact.path.suffix == ".json" else "text/markdown"
    return FileResponse(artifact.path, media_type=media_type, filename=artifact.path.name)


@router.get("/api/runs/{run_id}/artifacts/content", response_model=ArtifactContent)
async def get_named_run_artifact_content(run_id: str, name: str, request: Request):
    """Return one artifact's text content for inline viewing."""
    run = get_run(run_id, _request_tenant_id(request))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    artifact = resolve_run_artifact(
        report_path=run.report_path,
        state_log_path=run.state_log_path,
        key=name,
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not available")

    return ArtifactContent(
        name=artifact.key,
        label=artifact.label,
        content=artifact.path.read_text(encoding="utf-8"),
    )


@router.get("/api/runs/{run_id}/report")
async def download_run_report(run_id: str, request: Request):
    """Download the saved markdown report for a completed run."""
    run = get_run(run_id, _request_tenant_id(request))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    artifact = resolve_run_artifact(
        report_path=run.report_path,
        state_log_path=run.state_log_path,
        key="complete-report",
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Report not available")

    filename = f"{run.ticker}_{run.date}_complete_report.md"
    return FileResponse(artifact.path, media_type="text/markdown", filename=filename)


@router.get("/api/runs/{run_id}/artifacts/full-state")
async def download_run_full_state(run_id: str, request: Request):
    """Download the saved full-state JSON for a completed run."""
    run = get_run(run_id, _request_tenant_id(request))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    artifact = resolve_run_artifact(
        report_path=run.report_path,
        state_log_path=run.state_log_path,
        key="full-state",
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Full state log not available")

    filename = f"{run.ticker}_{run.date}_full_state.json"
    return FileResponse(artifact.path, media_type="application/json", filename=filename)


# ── UI ────────────────────────────────────────────────────────────────────

@router.get("/service-worker.js")
async def get_service_worker():
    """Serve the PWA service worker from the app root so it can control the full UI scope."""
    path = Path(__file__).parent / "static" / "service-worker.js"
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@router.get("/shared/{share_id}", response_class=HTMLResponse)
async def get_public_run_share_page(share_id: str):
    """Serve one public read-only run snapshot without requiring API auth."""
    located = _find_public_run_share_location(share_id)
    if located is None:
        raise HTTPException(status_code=404, detail="Shared run not found")
    tenant_id, snapshot = located
    if _is_public_share_expired(snapshot):
        raise HTTPException(status_code=404, detail="Shared run not found")
    shares = _load_public_run_shares(tenant_id)
    for item in shares:
        if item.share_id != share_id:
            continue
        item.view_count += 1
        item.last_viewed_at = _now_iso()
        snapshot = item
        break
    _save_public_run_shares(tenant_id, shares)
    return HTMLResponse(content=_build_public_run_share_html(snapshot))


def _spa_index_path() -> Path:
    return Path(__file__).parent / "static" / "spa" / "index.html"


def _serve_spa_index() -> HTMLResponse:
    index_path = _spa_index_path()
    if not index_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Vue SPA assets are not built. Run `npm --prefix frontend run build`.",
        )
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@router.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the Vue SPA shell."""
    return _serve_spa_index()


@router.get("/{spa_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_spa_route(spa_path: str):
    """Serve the Vue SPA shell for client-side routes."""
    first_segment = spa_path.split("/", 1)[0]
    if first_segment in {"api", "static", "shared"} or spa_path == "service-worker.js":
        raise HTTPException(status_code=404, detail="Not found")
    return _serve_spa_index()
