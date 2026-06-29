"""Pydantic models for the TradingAgents web API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_DEFAULT_ANALYSTS = ["market", "social", "news", "fundamentals"]
_ALLOWED_ANALYSTS = set(_DEFAULT_ANALYSTS)
_ALLOWED_ASSET_TYPES = {"stock", "crypto"}


class AnalysisRequest(BaseModel):
    """Request body for creating an analysis run."""

    ticker: str = Field(..., min_length=1, max_length=32, description="Ticker symbol")
    date: str = Field(..., description="Analysis date (YYYY-MM-DD)")
    asset_type: str = Field(default="stock", description="Asset type: stock or crypto")
    analysts: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_ANALYSTS),
        min_length=1,
        description="Analyst types to include",
    )
    llm_provider: str = Field(default="openai", description="LLM provider name")
    deep_think_model: str | None = Field(default=None, description="Deep thinking model ID")
    quick_think_model: str | None = Field(default=None, description="Quick thinking model ID")
    research_depth: int = Field(default=1, ge=1, description="Research depth: 1/3/5")
    output_language: str = Field(default="English", description="Output language")
    backend_url: str | None = Field(default=None, description="Custom backend URL")
    temperature: float | None = Field(default=None, description="Sampling temperature")
    google_thinking_level: str | None = Field(default=None)
    openai_reasoning_effort: str | None = Field(default=None)
    anthropic_effort: str | None = Field(default=None)

    @field_validator("ticker", "llm_provider", "output_language")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("value must not be blank")
        return trimmed

    @field_validator(
        "deep_think_model",
        "quick_think_model",
        "backend_url",
        "google_thinking_level",
        "openai_reasoning_effort",
        "anthropic_effort",
        mode="before",
    )
    @classmethod
    def _blank_optional_strings_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value

    @field_validator("date")
    @classmethod
    def _validate_date(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("date must be in YYYY-MM-DD format") from exc
        return value

    @field_validator("asset_type", mode="before")
    @classmethod
    def _normalize_asset_type(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("asset_type")
    @classmethod
    def _validate_asset_type(cls, value: str) -> str:
        if value not in _ALLOWED_ASSET_TYPES:
            allowed = ", ".join(sorted(_ALLOWED_ASSET_TYPES))
            raise ValueError(f"asset_type must be one of: {allowed}")
        return value

    @field_validator("analysts")
    @classmethod
    def _validate_analysts(cls, value: list[str]) -> list[str]:
        normalized = [analyst.strip().lower() for analyst in value]
        invalid = [analyst for analyst in normalized if analyst not in _ALLOWED_ANALYSTS]
        if invalid:
            allowed = ", ".join(sorted(_ALLOWED_ANALYSTS))
            bad = ", ".join(invalid)
            raise ValueError(f"analysts must be chosen from: {allowed}. Invalid: {bad}")
        return normalized


class AnalysisResponse(BaseModel):
    """Response returned when a run is created."""

    run_id: str
    status: str
    ticker: str
    date: str


class RunStatus(BaseModel):
    """Full run status returned by GET /api/runs/{run_id}."""

    run_id: str
    status: str
    ticker: str
    date: str
    asset_type: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    queue_position: int | None = None
    agents: dict[str, str] = Field(default_factory=dict)
    report_sections: dict[str, str | None] = Field(default_factory=dict)
    config_summary: dict[str, object] = Field(default_factory=dict)
    current_report: str | None = None
    final_report: str | None = None
    signal: str | None = None
    error: str | None = None


class RunSummary(BaseModel):
    """Condensed run summary returned by GET /api/runs."""

    run_id: str
    status: str
    ticker: str
    date: str
    asset_type: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    queue_position: int | None = None
    signal: str | None = None
    error: str | None = None


class RunEvent(BaseModel):
    """Persisted timeline event for a run."""

    timestamp: str
    event: str
    data: dict[str, str | int | float | bool | None] | dict[str, object]


class ProviderModel(BaseModel):
    """A single model option for a provider."""

    label: str
    value: str


class ProviderInfo(BaseModel):
    """Provider information returned by GET /api/providers."""

    provider: str
    display_name: str
    quick_models: list[ProviderModel]
    deep_models: list[ProviderModel]


# ── Settings schemas ──────────────────────────────────────────────────────


class LLMSettings(BaseModel):
    provider: str = "openai"
    quick_think_model: str = "gpt-5.4-mini"
    deep_think_model: str = "gpt-5.5"
    backend_url: str | None = None
    temperature: float | None = None
    google_thinking_level: str | None = None
    openai_reasoning_effort: str | None = None
    anthropic_effort: str | None = None


class AnalysisSettings(BaseModel):
    output_language: str = "English"
    market_profile: str = "default"
    research_depth: int = 1
    max_risk_discuss_rounds: int = 1
    max_recur_limit: int = 100
    checkpoint_enabled: bool = False


class DataVendorSettings(BaseModel):
    core_stock_apis: str = "yfinance"
    technical_indicators: str = "yfinance"
    fundamental_data: str = "yfinance"
    news_data: str = "yfinance"
    macro_data: str = "fred"
    prediction_markets: str = "polymarket"


class DataSettings(BaseModel):
    data_vendors: DataVendorSettings = Field(default_factory=DataVendorSettings)
    news_article_limit: int = 20
    global_news_article_limit: int = 10
    global_news_lookback_days: int = 7


class SecuritySettings(BaseModel):
    web_api_token: str | None = None


class SettingsResponse(BaseModel):
    """Full settings returned by GET /api/settings."""

    api_keys: dict[str, str]
    llm: LLMSettings
    analysis: AnalysisSettings
    data: DataSettings
    security: SecuritySettings


class ArtifactInfo(BaseModel):
    name: str
    label: str
    download_url: str


class ArtifactContent(BaseModel):
    name: str
    label: str
    content: str


class SettingsUpdate(BaseModel):
    """Partial update accepted by PUT /api/settings."""

    api_keys: dict[str, str] | None = None
    llm: LLMSettings | None = None
    analysis: AnalysisSettings | None = None
    data: DataSettings | None = None
    security: SecuritySettings | None = None
