"""FastAPI API endpoints for TradingAgents web."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from sse_starlette.sse import EventSourceResponse

from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
from tradingagents.service.artifact_store import build_run_artifacts, resolve_run_artifact
from .auth import get_auth_scope
from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import (
    export_api_keys_to_env,
    load_settings,
    mask_api_keys,
    save_settings,
)

from .runner import (
    TERMINAL_RUN_STATUSES,
    build_terminal_event,
    cancel_run,
    create_run,
    delete_run,
    get_execution_mode,
    get_run,
    get_queue_position,
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
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSettings,
    ArtifactContent,
    ArtifactInfo,
    DataSettings,
    DataVendorSettings,
    LLMSettings,
    ProviderInfo,
    ProviderModel,
    RunEvent,
    RunSummary,
    RunStatus,
    SecuritySettings,
    SettingsResponse,
    SettingsUpdate,
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


def _request_tenant_id(request: Request) -> str | None:
    return request.headers.get("X-TradingAgents-Tenant") or request.query_params.get("tenant_id") or None


@router.get("/api/system/status")
async def get_system_status(request: Request):
    """Return a compact operational snapshot for the current Web runtime."""
    tenant_id = _request_tenant_id(request)
    return {
        "execution_mode": get_execution_mode(),
        "tenant_id": get_tenant_id(tenant_id),
        "auth_scope": get_auth_scope(tenant_id),
        "state_backend": get_state_backend(),
        "state_location": get_state_location(tenant_id),
        **get_service_status(tenant_id),
    }


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
        "temperature": config.get("temperature"),
        "backend_url": config.get("backend_url"),
        "data_vendors": dict(config.get("data_vendors", {})),
        "news_article_limit": config.get("news_article_limit"),
        "global_news_article_limit": config.get("global_news_article_limit"),
        "global_news_lookback_days": config.get("global_news_lookback_days"),
    }


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
    return AnalysisResponse(
        run_id=result.run_id,
        status=result.status,
        ticker=result.ticker,
        date=result.date,
    )


@router.get("/api/runs", response_model=list[RunSummary])
async def get_runs(request: Request):
    """Return recent analysis runs, newest first."""
    tenant_id = _request_tenant_id(request)
    return [
        RunSummary(
            run_id=run.run_id,
            status=run.status,
            ticker=run.ticker,
            date=run.date,
            asset_type=run.asset_type,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            queue_position=get_queue_position(run.run_id, tenant_id),
            signal=run.signal,
            error=run.error,
        )
        for run in list_runs(tenant_id)
    ]


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
    )


@router.delete("/api/runs/{run_id}", status_code=204)
async def delete_analysis_run(run_id: str, request: Request):
    """Delete a terminal run and its persisted artifacts."""
    tenant_id = _request_tenant_id(request)
    deleted = delete_run(run_id, tenant_id)
    if deleted is not None:
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
_EMPTY_API_KEYS = {k: "" for k in [
    "openai", "anthropic", "google", "xai", "deepseek",
    "qwen", "qwen-cn", "glm", "glm-cn", "minimax", "minimax-cn",
    "openrouter", "mistral", "kimi", "groq", "nvidia",
    "openai_compatible", "ollama", "bedrock",
    "FRED_API_KEY", "AWS_DEFAULT_REGION", "AWS_PROFILE", "OLLAMA_BASE_URL",
]}


def _settings_to_response(settings: dict) -> SettingsResponse:
    """Convert raw settings dict to a SettingsResponse."""
    api_keys = settings.get("api_keys", {})
    # Fill in any missing providers with empty string
    full_keys = {**_EMPTY_API_KEYS, **api_keys}

    llm = settings.get("llm", {})
    analysis = settings.get("analysis", {})
    data = settings.get("data", {})
    security = settings.get("security", {})
    dv = data.get("data_vendors", {})

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
        ),
        data=DataSettings(
            data_vendors=DataVendorSettings(**{
                k: v for k, v in dv.items() if k in DataVendorSettings.model_fields
            }) if dv else DataVendorSettings(),
            news_article_limit=data.get("news_article_limit", 20),
            global_news_article_limit=data.get("global_news_article_limit", 10),
            global_news_lookback_days=data.get("global_news_lookback_days", 7),
        ),
        security=SecuritySettings(
            web_api_token="***" if security.get("web_api_token") else None,
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
    existing = load_settings(path=settings_path)

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

    # Merge data settings
    if update.data is not None:
        data = existing.get("data", {})
        update_data = update.data.model_dump(exclude_none=True)
        if "data_vendors" in update_data and isinstance(update_data["data_vendors"], dict):
            existing_dv = data.get("data_vendors", {})
            existing_dv.update(update_data.pop("data_vendors"))
            data["data_vendors"] = existing_dv
        data.update(update_data)
        existing["data"] = data

    if update.security is not None:
        security = existing.get("security", {})
        for key, value in update.security.model_dump(exclude_none=True).items():
            if value == "***":
                continue
            security[key] = value
        existing["security"] = security

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

@router.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the web UI."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
