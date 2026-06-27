# China Market Adaptation Design

## Goal

Adapt TradingAgents so it can analyze China A-share equities with China-appropriate market data, macro context, and analyst inputs rather than the current US-centric defaults.

## Scope

This design covers the first complete China mainland market adaptation for the existing multi-agent workflow.

In scope:

- Introduce a China market profile that switches the system from US-centric defaults to mainland-China semantics.
- Add China-capable data vendors to the existing vendor-routing layer.
- Replace unsupported or low-signal overseas inputs for China mainland analysis.
- Update analyst prompts and tool descriptions so the agents reason about A-share context rather than US-market context.
- Add tests for routing, configuration, symbol handling, and China-specific analyst/tool behavior.

Out of scope for the first pass:

- A full production-grade commercial sentiment feed.
- Brokerage execution integration.
- Hong Kong market deep integration beyond optional future extension points.
- A complete backtest engine overhaul for China-specific disclosure timing.

## Current-State Constraints

The existing system already has a clean vendor-routing layer and analyst tool wrappers:

- `tradingagents/dataflows/interface.py` routes tool calls by category and method.
- Agent-facing tool wrappers in `tradingagents/agents/utils/*.py` call `route_to_vendor(...)`.
- The graph composition, research debate, trading, and risk-management layers are data-source-agnostic as long as the tool contracts return reasonable text reports.

This means the lowest-risk architecture is to preserve tool signatures and graph orchestration while changing configuration, vendor mappings, data providers, and analyst semantics.

## Requirements

### 1. China Market Profile

Add an explicit market profile for China mainland analysis.

The profile should:

- Select China-appropriate default vendors.
- Enable China-specific forward-looking signals.
- Disable unsupported overseas sentiment/prediction sources by default.
- Provide prompt hints so analysts know they are evaluating A-shares.

Recommended profile key:

- `market_profile = "cn_a"`

### 2. Unified Internal Market Interfaces

Preserve the current high-level tool contracts:

- `get_stock_data`
- `get_indicators`
- `get_fundamentals`
- `get_balance_sheet`
- `get_cashflow`
- `get_income_statement`
- `get_news`
- `get_global_news`
- `get_insider_transactions`
- `get_macro_indicators`
- `get_prediction_markets` or its China-safe replacement

The graph and analyst layers should not need to know which vendor serves the data.

### 3. China-Capable Vendor Layer

Extend the dataflow routing layer with China-capable providers.

Recommended first-pass vendor roles:

- `akshare` for broad China market coverage and quick integration.
- `tushare` as an optional higher-stability or future primary vendor.
- `cn_macro` for China macroeconomic indicators assembled from China official sources or a single adapter layer.
- `cn_market_signals` for northbound/southbound flow, margin financing, and other market-structure signals.

The first implementation should prefer one practical vendor path that can run in open-source contexts while leaving room for stronger production vendors later.

### 4. China-Relevant Information Inputs

The system should stop treating these as default information channels for A-shares:

- Reddit
- StockTwits
- Polymarket
- FRED aliases as the main macro vocabulary

The system should prioritize these instead:

- A-share OHLCV and index data
- China company fundamentals and statements
- China equity announcements and disclosure-driven events
- China macro series such as CPI, PPI, PMI, M2, social financing, LPR, policy rates, industrial production, retail sales, and exports
- Forward-looking market structure signals such as northbound flow, margin financing balance, and sector fund flow

### 5. Analyst-Layer Semantic Rewrite

The analyst prompts must be China-aware.

Changes needed:

- The news analyst should discuss policy, liquidity, industrial policy, macro demand, regulation, and disclosure events in China context.
- The sentiment analyst should not imply Reddit or StockTwits are always available. In the first pass it may consume news, announcements, and China market-structure signals.
- The fundamentals analyst should emphasize China-specific risk markers such as shareholder pledge, government subsidy dependence, receivables quality, inventory quality, goodwill, related-party transactions, and cash-flow quality.
- The market analyst should reason with China-specific microstructure such as price limits, T+1 equity trading, midday break, suspensions, and exchange-specific benchmarks.

### 6. Verification

The work is complete only when:

- China market profile can be configured and used.
- Core stock, fundamental, news/macro, and forward-signal calls succeed through the routing layer for China profile defaults.
- Analyst prompts no longer hard-code US-only semantics for China mode.
- Tests verify the China routing and behavior.

## Proposed Architecture

### A. Configuration Layer

Extend `DEFAULT_CONFIG` with:

- `market_profile`
- China vendor defaults under `data_vendors`
- China-specific optional settings such as forward-signal toggles or sentiment-source toggles

The defaults should remain backwards-compatible for existing users unless they opt into China mode.

### B. Vendor Adapters

Add new dataflow modules under `tradingagents/dataflows/` for China data.

Recommended files:

- `china_profile.py` or equivalent helpers for China-specific configuration behavior
- `akshare_stock.py`
- `china_macro.py`
- `china_market_signals.py`
- optional future `tushare_*` modules

If a function is not yet available from a China source, it should degrade gracefully with an explicit placeholder rather than silently fabricating US-style substitutes.

### C. Routing Layer

Update `tradingagents/dataflows/interface.py` so each abstract method can map to China vendors where appropriate.

For the first pass:

- `core_stock_apis`: add `akshare`
- `technical_indicators`: add `akshare` or compute from China OHLCV if needed
- `fundamental_data`: add `akshare`
- `news_data`: add China-compatible news/announcement adapters
- `macro_data`: add `cn_macro`
- `prediction_markets`: keep the interface but allow China mode to route to `cn_market_signals`

### D. Agent Tool Semantics

Keep the user-facing tool names stable to minimize graph churn, but revise their descriptions so they do not advertise US-only sources in China mode.

If necessary, retain `get_prediction_markets` as a compatibility name while changing its China-mode implementation to return forward-looking market structure signals rather than literal prediction-market odds.

### E. Analyst Prompting

Prompts should derive explanatory context from the market profile.

Recommended behavior:

- Build a small market-context helper that returns profile-specific prompt guidance.
- Inject that helper output into analyst prompts so China semantics are centralized rather than copied across files.

## Data Source Strategy

### First-Pass Open-Source Strategy

Use:

- `AKShare` for core A-share market and fundamental coverage
- existing open-source-compatible China macro adapters
- a China market-signals adapter for northbound and margin data

This approach maximizes accessibility and speed of integration.

### Future Production Strategy

Allow migration to:

- `Tushare Pro` for stronger operational stability
- official or licensed disclosure/event feeds
- licensed sentiment providers

The internal interfaces should remain stable so vendor upgrades do not force agent-layer rewrites.

## Error Handling

China mode should favor explicit degradation over silent substitution.

Examples:

- If social sentiment is disabled in China mode, return a clear placeholder that the sentiment analyst can interpret.
- If a China macro alias is unknown, return an instructive message similar to the current FRED behavior.
- If a company has no supported disclosure/event feed in the first pass, say so directly rather than falling back to irrelevant overseas news.

## Testing Strategy

Tests should cover:

- default config for `market_profile="cn_a"`
- vendor routing for China-capable methods
- backward compatibility for non-China defaults
- profile-aware prompt behavior
- placeholder/degradation behavior for unsupported sentiment sources
- China benchmark and symbol logic where modified

## Implementation Phasing

### Phase 1: Functional China Mode

- Add `market_profile`
- Add China vendor adapters
- Route core market/fundamental/macro/news/signal methods
- Update prompts and tool docs
- Add tests

### Phase 2: Higher-Fidelity China Inputs

- Expand announcement/disclosure coverage
- Improve sentiment with licensed or more stable domestic sources
- Add richer market-structure signals

### Phase 3: Research-Grade Timing and Backtest Safety

- Tighten disclosure-date handling
- Add more rigorous China-specific historical availability controls

## Recommended First Implementation Slice

Start with a complete but pragmatic A-share path:

- `market_profile="cn_a"`
- `AKShare` for price, indicators, fundamentals, and market/news-compatible coverage where possible
- China macro adapter for mainland macro indicators
- China forward-signals adapter replacing Polymarket semantics in China mode
- Prompt rewrites for market, sentiment, news, and fundamentals analysts

This slice is large enough to make the product genuinely usable for China mainland research without requiring a fully commercial data stack in the first merge.
