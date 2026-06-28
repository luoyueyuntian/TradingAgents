"""Pydantic models for the TradingAgents web API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Request body for creating an analysis run."""

    ticker: str = Field(..., min_length=1, max_length=32, description="Ticker symbol")
    date: str = Field(..., description="Analysis date (YYYY-MM-DD)")
    asset_type: str = Field(default="stock", description="Asset type: stock or crypto")
    analysts: list[str] = Field(
        default=["market", "social", "news", "fundamentals"],
        description="Analyst types to include",
    )
    llm_provider: str = Field(default="openai", description="LLM provider name")
    deep_think_model: str = Field(default="", description="Deep thinking model ID")
    quick_think_model: str = Field(default="", description="Quick thinking model ID")
    research_depth: int = Field(default=1, description="Research depth: 1/3/5")
    output_language: str = Field(default="English", description="Output language")
    backend_url: str | None = Field(default=None, description="Custom backend URL")
    temperature: float | None = Field(default=None, description="Sampling temperature")
    google_thinking_level: str | None = Field(default=None)
    openai_reasoning_effort: str | None = Field(default=None)
    anthropic_effort: str | None = Field(default=None)


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
    agents: dict[str, str] = Field(default_factory=dict)
    current_report: str | None = None
    final_report: str | None = None
    signal: str | None = None
    error: str | None = None


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


class SettingsResponse(BaseModel):
    """Full settings returned by GET /api/settings."""

    api_keys: dict[str, str]
    llm: LLMSettings
    analysis: AnalysisSettings
    data: DataSettings


class SettingsUpdate(BaseModel):
    """Partial update accepted by PUT /api/settings."""

    api_keys: dict[str, str] | None = None
    llm: LLMSettings | None = None
    analysis: AnalysisSettings | None = None
    data: DataSettings | None = None
