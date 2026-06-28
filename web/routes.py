"""FastAPI API endpoints for TradingAgents web."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
from tradingagents.settings import (
    load_settings,
    mask_api_keys,
    save_settings,
)

from .runner import create_run, get_run
from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisSettings,
    DataSettings,
    DataVendorSettings,
    LLMSettings,
    ProviderInfo,
    ProviderModel,
    RunStatus,
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
    result = create_run(req, loop)
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


@router.get("/api/runs/{run_id}", response_model=RunStatus)
async def get_run_status(run_id: str):
    """Get the current status of an analysis run."""
    run = get_run(run_id)
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
        agents=dict(run.agents),
        current_report=run.current_report,
        final_report=run.final_report,
        signal=run.signal,
        error=run.error,
    )


@router.get("/api/runs/{run_id}/events")
async def stream_run_events(run_id: str, request: Request):
    """SSE endpoint for streaming analysis progress."""
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(run.events.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield {"comment": "keepalive"}
                    continue

                event_type = event.get("event", "message")
                data = event.get("data", {})
                yield {"event": event_type, "data": json.dumps(data)}

                if event_type in ("complete", "error"):
                    break
        except asyncio.CancelledError:
            pass

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
    )


@router.get("/api/settings", response_model=SettingsResponse)
async def get_settings():
    """Return current settings (API keys masked)."""
    settings = load_settings()
    return _settings_to_response(settings)


@router.put("/api/settings", response_model=SettingsResponse)
async def put_settings(update: SettingsUpdate):
    """Update settings and persist to disk."""
    existing = load_settings()

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

    save_settings(existing)
    return _settings_to_response(existing)


# ── UI ────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the web UI."""
    from pathlib import Path

    template_path = Path(__file__).parent / "templates" / "index.html"
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))
