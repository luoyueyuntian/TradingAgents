"""Pydantic models for the TradingAgents web API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_DEFAULT_ANALYSTS = ["market", "social", "news", "fundamentals"]
_ALLOWED_ANALYSTS = set(_DEFAULT_ANALYSTS)
_ALLOWED_ASSET_TYPES = {"stock", "crypto"}
_DEFAULT_GLOBAL_NEWS_QUERIES = [
    "Federal Reserve interest rates inflation",
    "S&P 500 earnings GDP economic outlook",
    "geopolitical risk trade war sanctions",
    "ECB Bank of England BOJ central bank policy",
    "oil commodities supply chain energy",
]


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
    market_profile: str | None = Field(default=None, description="Market profile override")
    max_risk_discuss_rounds: int | None = Field(default=None, ge=1)
    max_recur_limit: int | None = Field(default=None, ge=1)
    checkpoint_enabled: bool | None = Field(default=None)
    benchmark_ticker: str | None = Field(default=None, description="Benchmark ticker override")
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
        "market_profile",
        "benchmark_ticker",
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


class BatchAnalysisRequest(BaseModel):
    """Request body for creating multiple queued analysis runs."""

    tickers: list[str] = Field(default_factory=list)
    source: str = Field(default="manual", description="manual or watchlist")
    date: str = Field(..., description="Analysis date (YYYY-MM-DD)")
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
    market_profile: str | None = Field(default=None, description="Market profile override")
    max_risk_discuss_rounds: int | None = Field(default=None, ge=1)
    max_recur_limit: int | None = Field(default=None, ge=1)
    checkpoint_enabled: bool | None = Field(default=None)
    benchmark_ticker: str | None = Field(default=None, description="Benchmark ticker override")
    backend_url: str | None = Field(default=None, description="Custom backend URL")
    temperature: float | None = Field(default=None, description="Sampling temperature")
    google_thinking_level: str | None = Field(default=None)
    openai_reasoning_effort: str | None = Field(default=None)
    anthropic_effort: str | None = Field(default=None)

    @field_validator("llm_provider", "output_language")
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
        "market_profile",
        "benchmark_ticker",
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

    @field_validator("source")
    @classmethod
    def _normalize_source(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"manual", "watchlist"}:
            raise ValueError("source must be manual or watchlist")
        return normalized

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

    @field_validator("tickers", mode="before")
    @classmethod
    def _normalize_tickers(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("tickers must be a list")
        tickers: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().upper()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            tickers.append(normalized)
        return tickers


class BatchAnalysisResponse(BaseModel):
    """Summary returned when a batch of runs is queued."""

    source: str
    tickers: list[str] = Field(default_factory=list)
    requested_count: int = 0
    created_count: int = 0
    runs: list[AnalysisResponse] = Field(default_factory=list)


class RunBulkAction(BaseModel):
    """Bulk lifecycle action for selected saved runs."""

    ids: list[str] = Field(default_factory=list)
    action: str = Field(..., min_length=1)

    @field_validator("ids", mode="before")
    @classmethod
    def _normalize_ids(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("ids must be a list")
        ids: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ids.append(normalized)
        return ids

    @field_validator("action")
    @classmethod
    def _normalize_action(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"delete", "retry", "archive", "restore"}:
            raise ValueError("action must be delete, retry, archive or restore")
        return normalized


class RunBulkActionResult(BaseModel):
    """Bulk run-management outcome."""

    action: str
    deleted: int = 0
    retried: int = 0
    archived: int = 0
    restored: int = 0
    skipped: int = 0


class AutomationAnalysisConfig(BaseModel):
    """Saved analysis configuration reused by scheduled automation rules."""

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
    market_profile: str | None = Field(default=None, description="Market profile override")
    max_risk_discuss_rounds: int | None = Field(default=None, ge=1)
    max_recur_limit: int | None = Field(default=None, ge=1)
    checkpoint_enabled: bool | None = Field(default=None)
    benchmark_ticker: str | None = Field(default=None, description="Benchmark ticker override")
    backend_url: str | None = Field(default=None, description="Custom backend URL")
    temperature: float | None = Field(default=None, description="Sampling temperature")
    google_thinking_level: str | None = Field(default=None)
    openai_reasoning_effort: str | None = Field(default=None)
    anthropic_effort: str | None = Field(default=None)

    @field_validator("llm_provider", "output_language")
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
        "market_profile",
        "benchmark_ticker",
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


class AutomationRule(BaseModel):
    """One saved scheduled automation rule."""

    id: str
    name: str
    enabled: bool = True
    source: str = "watchlist"
    tickers: list[str] = Field(default_factory=list)
    cadence: str = "daily"
    weekday: str | None = None
    time_of_day: str = "09:00"
    created_at: str
    updated_at: str
    last_triggered_at: str | None = None
    last_queued_count: int = 0
    next_run_at: str | None = None
    analysis_config: AutomationAnalysisConfig


class AutomationRuleCreate(BaseModel):
    """Payload for creating one scheduled automation rule."""

    name: str = Field(..., min_length=1)
    enabled: bool = True
    source: str = "watchlist"
    tickers: list[str] = Field(default_factory=list)
    cadence: str = "daily"
    weekday: str | None = None
    time_of_day: str = "09:00"
    analysis_config: AutomationAnalysisConfig

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name must not be blank")
        return trimmed

    @field_validator("source")
    @classmethod
    def _normalize_source(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"manual", "watchlist"}:
            raise ValueError("source must be manual or watchlist")
        return normalized

    @field_validator("cadence")
    @classmethod
    def _normalize_cadence(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"daily", "weekly"}:
            raise ValueError("cadence must be daily or weekly")
        return normalized

    @field_validator("weekday")
    @classmethod
    def _normalize_weekday(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        allowed = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
        if normalized not in allowed:
            raise ValueError("weekday must be one of mon, tue, wed, thu, fri, sat, sun")
        return normalized

    @field_validator("time_of_day")
    @classmethod
    def _validate_time_of_day(cls, value: str) -> str:
        trimmed = value.strip()
        try:
            datetime.strptime(trimmed, "%H:%M")
        except ValueError as exc:
            raise ValueError("time_of_day must be in HH:MM format") from exc
        return trimmed

    @field_validator("tickers", mode="before")
    @classmethod
    def _normalize_tickers(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("tickers must be a list")
        tickers: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().upper()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            tickers.append(normalized)
        return tickers


class AutomationRuleToggleUpdate(BaseModel):
    """Payload for enabling or disabling an automation rule."""

    enabled: bool


class AutomationRunResponse(BaseModel):
    """Summary returned when an automation rule queues runs."""

    rule_id: str
    source: str
    tickers: list[str] = Field(default_factory=list)
    created_count: int = 0
    runs: list[AnalysisResponse] = Field(default_factory=list)


class RunAnnotation(BaseModel):
    """Lightweight structured metadata attached to a saved run."""

    run_id: str
    label: str
    summary: str | None = None
    next_step: str | None = None
    created_at: str
    updated_at: str


class RunAnnotationCreate(BaseModel):
    """Payload for creating or updating one run annotation."""

    label: str = Field(..., min_length=1)
    summary: str | None = None
    next_step: str | None = None

    @field_validator("label")
    @classmethod
    def _strip_label(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("label must not be blank")
        return trimmed

    @field_validator("summary", "next_step")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class RunReview(BaseModel):
    """Lightweight review request and decision for a saved run."""

    run_id: str
    reviewer: str
    status: str
    note: str | None = None
    created_at: str
    updated_at: str

    @field_validator("status")
    @classmethod
    def _normalize_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"pending", "approved", "changes_requested"}
        if normalized not in allowed:
            raise ValueError("status must be one of pending, approved, changes_requested")
        return normalized


class RunReviewCreate(BaseModel):
    """Payload for creating or updating one run review."""

    reviewer: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    note: str | None = None

    @field_validator("reviewer")
    @classmethod
    def _strip_reviewer(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("reviewer must not be blank")
        return trimmed

    @field_validator("status")
    @classmethod
    def _normalize_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"pending", "approved", "changes_requested"}
        if normalized not in allowed:
            raise ValueError("status must be one of pending, approved, changes_requested")
        return normalized

    @field_validator("note")
    @classmethod
    def _strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class PublicRunShareInfo(BaseModel):
    """Lightweight public-share metadata attached to a saved run."""

    share_id: str
    url: str
    created_at: str
    view_count: int = 0
    last_viewed_at: str | None = None
    expires_at: str | None = None
    share_title: str | None = None
    share_summary: str | None = None


class PublicRunShareListItem(BaseModel):
    """One public share row shown in the workspace management UI."""

    share_id: str
    url: str
    created_at: str
    run_id: str
    ticker: str
    date: str
    status: str
    signal: str | None = None
    view_count: int = 0
    last_viewed_at: str | None = None
    expires_at: str | None = None
    share_title: str | None = None
    share_summary: str | None = None


class PublicRunShareUpdate(BaseModel):
    """Payload for changing one public share's expiry."""

    expires_in_days: int | None = None
    share_title: str | None = None
    share_summary: str | None = None


class PublicRunShareSnapshot(BaseModel):
    """A tenant-scoped read-only snapshot exposed through a public share URL."""

    share_id: str
    tenant_id: str | None = None
    run_id: str
    ticker: str
    date: str
    asset_type: str
    status: str
    created_at: str
    signal: str | None = None
    error: str | None = None
    config_summary: dict[str, object] = Field(default_factory=dict)
    report_sections: dict[str, str | None] = Field(default_factory=dict)
    current_report: str | None = None
    final_report: str | None = None
    view_count: int = 0
    last_viewed_at: str | None = None
    expires_at: str | None = None
    share_title: str | None = None
    share_summary: str | None = None
    annotation: RunAnnotation | None = None
    review: RunReview | None = None


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
    annotation: RunAnnotation | None = None
    review: RunReview | None = None
    public_share: PublicRunShareInfo | None = None


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
    llm_provider: str | None = None
    archived: bool = False
    signal: str | None = None
    error: str | None = None
    annotation: RunAnnotation | None = None
    review: RunReview | None = None


class TickerOverview(BaseModel):
    """Ticker-centric summary built from saved run history."""

    ticker: str
    run_count: int = 0
    latest_run_id: str | None = None
    latest_signal: str | None = None
    latest_status: str | None = None
    latest_date: str | None = None
    latest_created_at: str | None = None
    recent_runs: list[RunSummary] = Field(default_factory=list)


class WatchlistEntry(BaseModel):
    """Saved ticker entry plus its latest known research summary."""

    ticker: str
    run_count: int = 0
    created_at: str | None = None
    latest_run_id: str | None = None
    latest_signal: str | None = None
    latest_status: str | None = None
    latest_date: str | None = None
    latest_created_at: str | None = None


class WatchlistUpdate(BaseModel):
    """Payload for adding one ticker to the watchlist."""

    ticker: str = Field(..., min_length=1, max_length=32)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        trimmed = value.strip().upper()
        if not trimmed:
            raise ValueError("ticker must not be blank")
        return trimmed


class WorkspaceImportRequest(BaseModel):
    """Pasted CSV/TSV/plaintext content for workspace imports."""

    content: str = Field(..., description="Raw pasted import content")


class ImportRowError(BaseModel):
    """One row-level import validation error."""

    line_number: int = Field(..., ge=1)
    message: str = Field(..., min_length=1)
    raw_value: str | None = None


class WorkspaceImportResult(BaseModel):
    """Summary returned after a watchlist or portfolio import."""

    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[ImportRowError] = Field(default_factory=list)


class AlertRule(BaseModel):
    """Tenant-scoped alert rule evaluated against latest saved runs."""

    id: str
    ticker: str
    field: str
    value: str
    created_at: str | None = None


class AlertRuleCreate(BaseModel):
    """Payload for creating a new alert rule."""

    ticker: str = Field(..., min_length=1, max_length=32)
    field: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        trimmed = value.strip().upper()
        if not trimmed:
            raise ValueError("ticker must not be blank")
        return trimmed

    @field_validator("field")
    @classmethod
    def _normalize_field(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"signal", "status"}:
            raise ValueError("field must be signal or status")
        return normalized

    @field_validator("value")
    @classmethod
    def _strip_value(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("value must not be blank")
        return trimmed


class AlertHit(BaseModel):
    """One alert rule currently matched by the latest saved run."""

    rule_id: str
    ticker: str
    field: str
    expected_value: str
    actual_value: str
    run_id: str
    run_date: str
    message: str


class AlertCenterResponse(BaseModel):
    """Saved alert rules and currently active hits."""

    rules: list[AlertRule] = Field(default_factory=list)
    hits: list[AlertHit] = Field(default_factory=list)


class PortfolioPosition(BaseModel):
    """One tenant-scoped saved position with latest known research context."""

    id: str
    ticker: str
    quantity: float
    average_cost: float
    cost_basis: float
    created_at: str | None = None
    latest_signal: str | None = None
    latest_status: str | None = None
    latest_date: str | None = None


class PortfolioPositionCreate(BaseModel):
    """Payload for creating one portfolio position."""

    ticker: str = Field(..., min_length=1, max_length=32)
    quantity: float = Field(..., gt=0)
    average_cost: float = Field(..., ge=0)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        trimmed = value.strip().upper()
        if not trimmed:
            raise ValueError("ticker must not be blank")
        return trimmed


class PortfolioSummary(BaseModel):
    """Derived summary for the current tenant portfolio."""

    position_count: int = 0
    unique_ticker_count: int = 0
    total_cost_basis: float = 0.0
    signal_breakdown: dict[str, int] = Field(default_factory=dict)


class PortfolioResponse(BaseModel):
    """Portfolio positions plus a derived summary."""

    summary: PortfolioSummary
    positions: list[PortfolioPosition] = Field(default_factory=list)


class DailyBriefingSummary(BaseModel):
    """Top-line counts and headline for the current tenant briefing."""

    generated_at: str
    headline: str
    alert_hit_count: int = 0
    watchlist_count: int = 0
    portfolio_position_count: int = 0
    recent_run_count: int = 0


class DailyBriefingResponse(BaseModel):
    """Tenant-scoped daily briefing assembled from saved workspace data."""

    summary: DailyBriefingSummary
    alert_hits: list[AlertHit] = Field(default_factory=list)
    watchlist_focus: list[WatchlistEntry] = Field(default_factory=list)
    portfolio_focus: list[PortfolioPosition] = Field(default_factory=list)
    recent_runs: list[RunSummary] = Field(default_factory=list)


class DashboardSummary(BaseModel):
    """Workspace dashboard headline metrics."""

    generated_at: str
    watchlist_count: int = 0
    bullish_focus_count: int = 0
    needs_attention_count: int = 0
    alert_hit_count: int = 0
    portfolio_position_count: int = 0
    pinned_action_count: int = 0
    pending_review_count: int = 0
    automation_count: int = 0
    saved_shortcut_count: int = 0
    recent_run_count: int = 0


class GettingStartedChecklistItem(BaseModel):
    """One recommended next-step in the workspace onboarding checklist."""

    id: str
    title: str
    description: str
    completed: bool = False
    action_label: str | None = None
    target_panel: str | None = None


class GettingStartedChecklist(BaseModel):
    """Lightweight workspace onboarding progress."""

    completed_count: int = 0
    remaining_count: int = 0
    total_count: int = 0
    items: list[GettingStartedChecklistItem] = Field(default_factory=list)


class SavedShortcutItem(BaseModel):
    """One pinned reusable workspace shortcut for the dashboard."""

    kind: str
    item_id: str
    name: str
    group: str | None = None
    member_id: str | None = None
    member_name: str | None = None
    url: str | None = None
    query: str | None = None
    kinds: list[str] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    """Persistent workspace dashboard assembled from saved workspace data."""

    summary: DashboardSummary
    visible_sections: list[str] = Field(default_factory=list)
    section_order: list[str] = Field(default_factory=list)
    bullish_focus: list[WatchlistEntry] = Field(default_factory=list)
    needs_attention: list[WatchlistEntry] = Field(default_factory=list)
    active_alerts: list[AlertHit] = Field(default_factory=list)
    portfolio_focus: list[PortfolioPosition] = Field(default_factory=list)
    pinned_actions: list[PinnedRun] = Field(default_factory=list)
    pending_reviews: list[RunReviewHistoryRow] = Field(default_factory=list)
    automations: list[AutomationRule] = Field(default_factory=list)
    saved_shortcuts: list[SavedShortcutItem] = Field(default_factory=list)
    operational_runs: list[RunSummary] = Field(default_factory=list)
    getting_started: GettingStartedChecklist = Field(default_factory=GettingStartedChecklist)


class DashboardPreferences(BaseModel):
    """Visible widget preferences for the workspace dashboard."""

    visible_sections: list[str] = Field(default_factory=list)
    section_order: list[str] = Field(default_factory=list)

    @field_validator("visible_sections", mode="before")
    @classmethod
    def _normalize_visible_sections(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("visible_sections must be a list")
        allowed = {
            "bullish_focus",
            "needs_attention",
            "active_alerts",
            "portfolio_focus",
            "pinned_actions",
            "pending_reviews",
            "automations",
            "saved_shortcuts",
            "operational_runs",
        }
        sections: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().lower()
            if normalized not in allowed or normalized in seen:
                continue
            seen.add(normalized)
            sections.append(normalized)
        return sections

    @field_validator("section_order", mode="before")
    @classmethod
    def _normalize_section_order(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("section_order must be a list")
        allowed = {
            "bullish_focus",
            "needs_attention",
            "active_alerts",
            "portfolio_focus",
            "pinned_actions",
            "pending_reviews",
            "automations",
            "saved_shortcuts",
            "operational_runs",
        }
        sections: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().lower()
            if normalized not in allowed or normalized in seen:
                continue
            seen.add(normalized)
            sections.append(normalized)
        return sections


class AnalyticsSummary(BaseModel):
    """Top-line metrics for workspace usage and operational health."""

    generated_at: str
    total_runs: int = 0
    terminal_runs: int = 0
    queued_runs: int = 0
    running_runs: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float | None = None
    unique_ticker_count: int = 0


class AnalyticsBucket(BaseModel):
    """One labeled bucket used in analytics breakdowns."""

    label: str
    value: int


class AnalyticsDailyActivity(BaseModel):
    """One day of run activity used in trend views."""

    date: str
    total_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    cancelled_runs: int = 0


class WorkspaceAnalyticsResponse(BaseModel):
    """Operational and usage analytics derived from saved runs."""

    summary: AnalyticsSummary
    status_breakdown: list[AnalyticsBucket] = Field(default_factory=list)
    provider_breakdown: list[AnalyticsBucket] = Field(default_factory=list)
    signal_breakdown: list[AnalyticsBucket] = Field(default_factory=list)
    asset_type_breakdown: list[AnalyticsBucket] = Field(default_factory=list)
    top_tickers: list[AnalyticsBucket] = Field(default_factory=list)
    daily_activity: list[AnalyticsDailyActivity] = Field(default_factory=list)


class ScreenerRow(BaseModel):
    """One candidate row in the workspace screener."""

    ticker: str
    run_count: int = 0
    latest_run_id: str | None = None
    latest_signal: str | None = None
    latest_status: str | None = None
    latest_date: str | None = None
    latest_created_at: str | None = None
    asset_type: str | None = None
    llm_provider: str | None = None
    research_depth: int | None = None
    on_watchlist: bool = False
    in_portfolio: bool = False
    is_pinned: bool = False
    has_alert_hit: bool = False
    pinned_category: str | None = None
    pinned_priority: str | None = None
    annotation_label: str | None = None
    needs_attention: bool = False


class ScreenerSummary(BaseModel):
    """Top-line counts for the workspace screener."""

    total_candidates: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    alert_hit_count: int = 0
    watchlist_count: int = 0
    portfolio_count: int = 0
    pinned_count: int = 0


class WorkspaceScreenerResponse(BaseModel):
    """Filtered screener response built from saved workspace state."""

    scope: str
    query: str = ""
    signal_filter: str = "all"
    status_filter: str = "all"
    asset_filter: str = "all"
    provider_filter: str = "all"
    summary: ScreenerSummary
    rows: list[ScreenerRow] = Field(default_factory=list)


class PresetAnalysisRequest(BaseModel):
    """Saved analysis-form configuration for reuse."""

    ticker: str | None = None
    llm_provider: str | None = None
    quick_think_model: str | None = None
    deep_think_model: str | None = None
    research_depth: int | None = None
    output_language: str | None = None
    market_profile: str | None = None
    max_risk_discuss_rounds: int | None = None
    max_recur_limit: int | None = None
    checkpoint_enabled: bool | None = None
    benchmark_ticker: str | None = None
    temperature: float | None = None
    backend_url: str | None = None
    google_thinking_level: str | None = None
    openai_reasoning_effort: str | None = None
    anthropic_effort: str | None = None


class AnalysisPreset(BaseModel):
    """One tenant-scoped saved analysis preset."""

    id: str
    name: str
    created_at: str | None = None
    analysis_request: PresetAnalysisRequest


class Note(BaseModel):
    """One tenant-scoped note attached to a ticker or run."""

    id: str
    content: str
    tags: list[str] = Field(default_factory=list)
    ticker: str | None = None
    run_id: str | None = None
    created_at: str
    updated_at: str


class NoteCreate(BaseModel):
    """Payload for saving one note."""

    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    ticker: str | None = None
    run_id: str | None = None

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("content must not be blank")
        return trimmed

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip().upper()
        return trimmed or None

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("tags must be a list")
        tags: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            tags.append(normalized)
        return tags


class NoteUpdate(BaseModel):
    """Payload for editing an existing note."""

    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("content must not be blank")
        return trimmed

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("tags must be a list")
        tags: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            tags.append(normalized)
        return tags


class RunComment(BaseModel):
    """One run-scoped collaboration comment."""

    id: str
    run_id: str
    author: str
    content: str
    created_at: str
    resolved: bool = False
    resolved_by: str | None = None
    resolved_at: str | None = None


class RunCommentCreate(BaseModel):
    """Payload for creating one run-scoped comment."""

    author: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)

    @field_validator("author", "content")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("value must not be blank")
        return trimmed


class RunCommentResolveUpdate(BaseModel):
    """Payload for resolving or reopening one run comment."""

    resolved: bool
    resolved_by: str | None = None

    @field_validator("resolved_by")
    @classmethod
    def _strip_resolved_by(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class WorkspaceTimelineEvent(BaseModel):
    """One saved workspace event rendered in chronological order."""

    kind: str
    occurred_at: str
    title: str
    detail: str
    ticker: str | None = None
    run_id: str | None = None


class WorkspaceTimelineResponse(BaseModel):
    """Chronological workspace timeline assembled from saved tenant state."""

    active_kinds: list[str] = Field(default_factory=list)
    events: list[WorkspaceTimelineEvent] = Field(default_factory=list)


class WorkspaceCalendarDay(BaseModel):
    """One day bucket in the workspace calendar."""

    date: str
    events: list[WorkspaceTimelineEvent] = Field(default_factory=list)


class WorkspaceCalendarResponse(BaseModel):
    """Date-grouped workspace event calendar."""

    days: list[WorkspaceCalendarDay] = Field(default_factory=list)


class AnalysisPresetCreate(BaseModel):
    """Payload for saving one analysis preset."""

    name: str = Field(..., min_length=1)
    analysis_request: PresetAnalysisRequest

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name must not be blank")
        return trimmed


class AnalysisPresetUpdate(BaseModel):
    """Payload for renaming one analysis preset."""

    name: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name must not be blank")
        return trimmed


class ShareLink(BaseModel):
    """Relative shareable link that restores saved workspace context."""

    label: str
    url: str


class WorkspaceExportSummary(BaseModel):
    """Top-line counts for one exported workspace snapshot."""

    exported_at: str
    tenant_id: str | None = None
    run_count: int = 0
    watchlist_count: int = 0
    alert_rule_count: int = 0
    alert_hit_count: int = 0
    portfolio_position_count: int = 0
    note_count: int = 0
    preset_count: int = 0
    saved_search_count: int = 0
    saved_view_count: int = 0
    pinned_run_count: int = 0
    annotation_count: int = 0
    member_count: int = 0
    comment_count: int = 0
    review_count: int = 0


class WorkspaceSettings(BaseModel):
    default_home_view: str = "auto"
    default_saved_view_id: str | None = None

    @field_validator("default_home_view")
    @classmethod
    def _normalize_default_home_view(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {
            "auto",
            "dashboard",
            "member-workspace",
            "notifications",
            "briefing",
            "analytics",
            "screener",
            "automations",
            "reviews",
            "search",
            "saved-view",
        }
        if normalized not in allowed:
            raise ValueError("default_home_view must be one of auto, dashboard, member-workspace, notifications, briefing, analytics, screener, automations, reviews, search, saved-view")
        return normalized

    @field_validator("default_saved_view_id")
    @classmethod
    def _strip_default_saved_view_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class WorkspaceSearchResult(BaseModel):
    """One cross-entity workspace search result."""

    kind: str
    entity_id: str
    title: str
    subtitle: str
    excerpt: str
    ticker: str | None = None
    run_id: str | None = None


class WorkspaceSearchResponse(BaseModel):
    """Workspace-wide search response."""

    query: str
    active_kinds: list[str] = Field(default_factory=list)
    results: list[WorkspaceSearchResult] = Field(default_factory=list)


class SavedSearch(BaseModel):
    """One tenant-scoped reusable workspace search."""

    id: str
    name: str
    query: str
    kinds: list[str] = Field(default_factory=list)
    group: str | None = None
    pinned: bool = False
    archived: bool = False
    member_id: str | None = None
    member_name: str | None = None
    created_at: str | None = None


class SavedSearchCreate(BaseModel):
    """Payload for saving one workspace search."""

    name: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    kinds: list[str] = Field(default_factory=list)
    group: str | None = None
    pinned: bool = False
    archived: bool = False
    member_id: str | None = None

    @field_validator("name", "query")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("value must not be blank")
        return trimmed

    @field_validator("kinds", mode="before")
    @classmethod
    def _normalize_kinds(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("kinds must be a list")
        allowed = {"run", "note", "watchlist", "portfolio", "preset", "alert", "comment", "review"}
        kinds: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().lower()
            if normalized not in allowed or normalized in seen:
                continue
            seen.add(normalized)
            kinds.append(normalized)
        return kinds

    @field_validator("member_id")
    @classmethod
    def _strip_member_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("group")
    @classmethod
    def _strip_group(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class SavedSearchUpdate(BaseModel):
    """Payload for updating one saved workspace search."""

    name: str | None = None
    group: str | None = None
    pinned: bool | None = None
    archived: bool | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("group")
    @classmethod
    def _strip_group(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class SavedItemBulkAction(BaseModel):
    """Bulk lifecycle action for saved searches or views."""

    ids: list[str] = Field(default_factory=list)
    action: str = Field(..., min_length=1)

    @field_validator("ids", mode="before")
    @classmethod
    def _normalize_ids(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("ids must be a list")
        ids: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ids.append(normalized)
        return ids

    @field_validator("action")
    @classmethod
    def _normalize_action(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"archive", "restore", "delete"}
        if normalized not in allowed:
            raise ValueError("action must be one of archive, restore, delete")
        return normalized


class SavedItemBulkActionResult(BaseModel):
    """Bulk action outcome for saved searches or views."""

    action: str
    updated: int = 0
    deleted: int = 0


class SavedView(BaseModel):
    """One tenant-scoped saved workspace view."""

    id: str
    name: str
    url: str
    visible_panels: list[str] = Field(default_factory=list)
    group: str | None = None
    pinned: bool = False
    archived: bool = False
    member_id: str | None = None
    member_name: str | None = None
    created_at: str | None = None


class SavedViewCreate(BaseModel):
    """Payload for saving one workspace view."""

    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    visible_panels: list[str] = Field(default_factory=list)
    group: str | None = None
    pinned: bool = False
    archived: bool = False
    member_id: str | None = None

    @field_validator("name", "url")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("value must not be blank")
        return trimmed

    @field_validator("visible_panels", mode="before")
    @classmethod
    def _normalize_panels(cls, value) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("visible_panels must be a list")
        panels: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            panels.append(normalized)
        return panels

    @field_validator("member_id")
    @classmethod
    def _strip_member_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("group")
    @classmethod
    def _strip_group(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class SavedViewUpdate(BaseModel):
    """Payload for updating one saved workspace view."""

    name: str | None = None
    group: str | None = None
    pinned: bool | None = None
    archived: bool | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("group")
    @classmethod
    def _strip_group(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class WorkspaceMember(BaseModel):
    """One lightweight workspace collaborator available for assignment."""

    id: str
    name: str
    role: str | None = None
    created_at: str | None = None


class WorkspaceMemberCreate(BaseModel):
    """Payload for saving one workspace collaborator."""

    name: str = Field(..., min_length=1)
    role: str | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("name must not be blank")
        return trimmed

    @field_validator("role")
    @classmethod
    def _normalize_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        allowed = {"analyst", "reviewer", "operator", "lead", "observer"}
        if normalized not in allowed:
            raise ValueError("role must be one of analyst, reviewer, operator, lead, observer")
        return normalized


class PinnedRun(BaseModel):
    """One tenant-scoped pinned analysis run."""

    run_id: str
    ticker: str | None = None
    date: str | None = None
    signal: str | None = None
    status: str | None = None
    note: str | None = None
    category: str | None = None
    priority: str | None = None
    next_action: str | None = None
    action_status: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    snoozed_until: str | None = None
    created_at: str | None = None


class PinnedRunCreate(BaseModel):
    """Payload for pinning one saved run."""

    run_id: str = Field(..., min_length=1)
    note: str | None = None
    category: str | None = None
    priority: str | None = None
    next_action: str | None = None
    action_status: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    snoozed_until: str | None = None

    @field_validator("run_id")
    @classmethod
    def _strip_run_id(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("run_id must not be blank")
        return trimmed

    @field_validator("note", "next_action", "assignee")
    @classmethod
    def _strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

    @field_validator("category")
    @classmethod
    def _normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        allowed = {"high-conviction", "follow-up", "risk", "archive"}
        if not normalized:
            return None
        if normalized not in allowed:
            raise ValueError("category must be one of high-conviction, follow-up, risk, archive")
        return normalized

    @field_validator("priority")
    @classmethod
    def _normalize_priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        allowed = {"p1", "p2", "p3"}
        if not normalized:
            return None
        if normalized not in allowed:
            raise ValueError("priority must be one of p1, p2, p3")
        return normalized

    @field_validator("action_status")
    @classmethod
    def _normalize_action_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        allowed = {"todo", "doing", "done"}
        if not normalized:
            return None
        if normalized not in allowed:
            raise ValueError("action_status must be one of todo, doing, done")
        return normalized

    @field_validator("due_date", "snoozed_until")
    @classmethod
    def _validate_optional_date(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        datetime.strptime(trimmed, "%Y-%m-%d")
        return trimmed


class PinnedRunStatusUpdate(BaseModel):
    """Payload for changing only the action status of a pinned run."""

    action_status: str

    @field_validator("action_status")
    @classmethod
    def _normalize_action_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"todo", "doing", "done"}
        if normalized not in allowed:
            raise ValueError("action_status must be one of todo, doing, done")
        return normalized


class PinnedRunAssigneeUpdate(BaseModel):
    """Payload for changing only the assignee of a pinned run."""

    assignee: str | None = None

    @field_validator("assignee")
    @classmethod
    def _strip_assignee(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class ActionBoardResponse(BaseModel):
    """Pinned runs grouped into a simple action board."""

    todo: list[PinnedRun] = Field(default_factory=list)
    doing: list[PinnedRun] = Field(default_factory=list)
    done: list[PinnedRun] = Field(default_factory=list)


class NotificationItem(BaseModel):
    """One in-app notification derived from saved workspace activity."""

    id: str
    kind: str
    severity: str
    title: str
    message: str
    created_at: str
    is_read: bool = False
    target_url: str | None = None
    ticker: str | None = None
    run_id: str | None = None
    member: str | None = None


class NotificationCenterResponse(BaseModel):
    """Notification feed plus unread counts for the current tenant."""

    generated_at: str
    unread_count: int = 0
    total_count: int = 0
    unread_only: bool = False
    member_filter: str | None = None
    kind_filter: str = "all"
    severity_filter: str = "all"
    items: list[NotificationItem] = Field(default_factory=list)


class NotificationReadResult(BaseModel):
    """Result returned when notifications are marked as read."""

    updated: int = 0
    unread_count: int = 0


class MemberWorkspaceSummary(BaseModel):
    """Top-line collaboration counts for one workspace member."""

    assigned_action_count: int = 0
    overdue_action_count: int = 0
    pending_review_count: int = 0
    mention_count: int = 0
    unread_mention_count: int = 0
    recent_comment_count: int = 0


class MemberWorkspaceResponse(BaseModel):
    """Member-centric workspace inbox built from assignments, mentions, and comments."""

    member: WorkspaceMember
    summary: MemberWorkspaceSummary
    assigned_actions: list[PinnedRun] = Field(default_factory=list)
    pending_reviews: list[RunReview] = Field(default_factory=list)
    mention_notifications: list[NotificationItem] = Field(default_factory=list)
    recent_comments: list[RunComment] = Field(default_factory=list)


class RunReviewHistoryRow(BaseModel):
    """One review entry enriched with run metadata for history views."""

    run_id: str
    reviewer: str
    status: str
    note: str | None = None
    created_at: str
    updated_at: str
    ticker: str | None = None
    date: str | None = None
    signal: str | None = None


class RunReviewHistorySummary(BaseModel):
    """Top-line counts for review history."""

    total_reviews: int = 0
    pending_count: int = 0
    approved_count: int = 0
    changes_requested_count: int = 0


class RunReviewHistoryResponse(BaseModel):
    """Filtered review history for the current workspace."""

    reviewer_filter: str | None = None
    status_filter: str = "all"
    query: str = ""
    summary: RunReviewHistorySummary
    items: list[RunReviewHistoryRow] = Field(default_factory=list)


class WorkspaceExport(BaseModel):
    """A tenant-scoped workspace snapshot suitable for backup or handoff."""

    summary: WorkspaceExportSummary
    workspace_settings: WorkspaceSettings = Field(default_factory=WorkspaceSettings)
    dashboard_preferences: DashboardPreferences = Field(default_factory=DashboardPreferences)
    runs: list[RunSummary] = Field(default_factory=list)
    watchlist: list[WatchlistEntry] = Field(default_factory=list)
    alerts: AlertCenterResponse
    portfolio: PortfolioResponse
    workspace_members: list[WorkspaceMember] = Field(default_factory=list)
    run_comments: list[RunComment] = Field(default_factory=list)
    run_reviews: list[RunReview] = Field(default_factory=list)
    pinned_runs: list[PinnedRun] = Field(default_factory=list)
    action_board: ActionBoardResponse
    timeline: WorkspaceTimelineResponse
    notes: list[Note] = Field(default_factory=list)
    presets: list[AnalysisPreset] = Field(default_factory=list)
    saved_searches: list[SavedSearch] = Field(default_factory=list)
    saved_views: list[SavedView] = Field(default_factory=list)
    annotations: list[RunAnnotation] = Field(default_factory=list)


class WorkspaceSnapshotImportRequest(BaseModel):
    """A pasted JSON workspace snapshot plus import mode."""

    content: str = Field(..., description="Raw workspace snapshot JSON")
    mode: str = Field(default="replace", description="replace or merge")

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("content must not be blank")
        return trimmed

    @field_validator("mode")
    @classmethod
    def _normalize_mode(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"replace", "merge"}:
            raise ValueError("mode must be replace or merge")
        return normalized


class WorkspaceSnapshotImportResult(BaseModel):
    """Summary returned after restoring a workspace snapshot."""

    mode: str
    watchlist_count: int = 0
    alert_rule_count: int = 0
    portfolio_position_count: int = 0
    pinned_run_count: int = 0
    note_count: int = 0
    preset_count: int = 0
    saved_search_count: int = 0
    saved_view_count: int = 0
    annotation_count: int = 0
    member_count: int = 0
    comment_count: int = 0
    review_count: int = 0


class CompareRun(BaseModel):
    """Run payload shaped for side-by-side comparison."""

    run_id: str
    status: str
    ticker: str
    date: str
    asset_type: str
    created_at: str
    signal: str | None = None
    error: str | None = None
    config_summary: dict[str, object] = Field(default_factory=dict)
    report_sections: dict[str, str | None] = Field(default_factory=dict)


class RunComparison(BaseModel):
    """Side-by-side comparison of two saved runs."""

    left: CompareRun
    right: CompareRun
    available_sections: list[str] = Field(default_factory=list)
    differing_summary_fields: list[str] = Field(default_factory=list)
    differing_sections: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    """One follow-up chat turn."""

    role: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)

    @field_validator("role")
    @classmethod
    def _normalize_role(cls, value: str) -> str:
        role = value.strip().lower()
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        return role

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("content must not be blank")
        return trimmed


class RunChatRequest(BaseModel):
    """Follow-up question asked against a saved run."""

    question: str = Field(..., min_length=1)
    history: list[ChatMessage] = Field(default_factory=list)

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("question must not be blank")
        return trimmed


class RunChatResponse(BaseModel):
    """Answer returned for a follow-up question on a saved run."""

    run_id: str
    provider: str
    model: str
    question: str
    answer: str


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


class TenantInfo(BaseModel):
    """A discovered tenant option for the web runtime."""

    tenant_id: str | None = None
    label: str
    active: bool = False


class CheckpointInfo(BaseModel):
    """A checkpoint file discovered under the current tenant's run roots."""

    run_id: str | None = None
    ticker: str
    path: str
    size_bytes: int


class MemoryEntryInfo(BaseModel):
    """A parsed decision-memory entry discovered under a run root."""

    run_id: str | None = None
    date: str
    ticker: str
    rating: str
    pending: bool
    raw: str | None = None
    alpha: str | None = None
    holding: str | None = None
    decision: str
    reflection: str


class DeleteResult(BaseModel):
    """Count of files deleted by a maintenance action."""

    deleted: int


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
    benchmark_ticker: str | None = None
    memory_log_max_entries: int | None = None


class ToolVendorSettings(BaseModel):
    get_stock_data: str | None = None
    get_indicators: str | None = None
    get_fundamentals: str | None = None
    get_balance_sheet: str | None = None
    get_cashflow: str | None = None
    get_income_statement: str | None = None
    get_news: str | None = None
    get_global_news: str | None = None
    get_insider_transactions: str | None = None
    get_macro_indicators: str | None = None
    get_prediction_markets: str | None = None


class DataVendorSettings(BaseModel):
    core_stock_apis: str = "yfinance"
    technical_indicators: str = "yfinance"
    fundamental_data: str = "yfinance"
    news_data: str = "yfinance"
    macro_data: str = "fred"
    prediction_markets: str = "polymarket"


class DataSettings(BaseModel):
    data_vendors: DataVendorSettings = Field(default_factory=DataVendorSettings)
    tool_vendors: ToolVendorSettings = Field(default_factory=ToolVendorSettings)
    news_article_limit: int = 20
    global_news_article_limit: int = 10
    global_news_lookback_days: int = 7
    global_news_queries: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_GLOBAL_NEWS_QUERIES)
    )


class SecuritySettings(BaseModel):
    web_api_token: str | None = None


class WebhookSettings(BaseModel):
    enabled: bool = False
    url: str | None = None
    bearer_token: str | None = None
    event_kinds: list[str] = Field(default_factory=lambda: ["run", "alert", "action"])
    last_delivery_at: str | None = None
    last_error: str | None = None

    @field_validator("url", "bearer_token", mode="before")
    @classmethod
    def _blank_optional_text_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value

    @field_validator("event_kinds", mode="before")
    @classmethod
    def _normalize_event_kinds(cls, value) -> list[str]:
        if value is None:
            return ["run", "alert", "action"]
        if not isinstance(value, list):
            raise ValueError("event_kinds must be a list")
        allowed = {"run", "alert", "action", "comment", "review"}
        kinds: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip().lower()
            if normalized not in allowed or normalized in seen:
                continue
            seen.add(normalized)
            kinds.append(normalized)
        return kinds or ["run", "alert", "action"]


class IntegrationsSettings(BaseModel):
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)


class SettingsResponse(BaseModel):
    """Full settings returned by GET /api/settings."""

    api_keys: dict[str, str]
    llm: LLMSettings
    analysis: AnalysisSettings
    workspace: WorkspaceSettings
    data: DataSettings
    security: SecuritySettings
    integrations: IntegrationsSettings


class ArtifactInfo(BaseModel):
    name: str
    label: str
    download_url: str


class ArtifactLibraryItem(BaseModel):
    """One run plus its top-level downloadable artifacts in the shared library view."""

    run_id: str
    ticker: str
    date: str
    status: str
    created_at: str
    signal: str | None = None
    error: str | None = None
    artifact_count: int = 0
    report_download_url: str | None = None
    state_download_url: str | None = None


class ArtifactContent(BaseModel):
    name: str
    label: str
    content: str


class SettingsUpdate(BaseModel):
    """Partial update accepted by PUT /api/settings."""

    api_keys: dict[str, str] | None = None
    llm: LLMSettings | None = None
    analysis: AnalysisSettings | None = None
    workspace: WorkspaceSettings | None = None
    data: DataSettings | None = None
    security: SecuritySettings | None = None
    integrations: IntegrationsSettings | None = None
