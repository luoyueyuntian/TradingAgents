# CN A-Share Authoritative Data Design

## Goal

Adjust TradingAgents so mainland China A-share analysis uses China-market data
as the primary source for prices, technical-indicator inputs, and fundamentals,
while retaining `yfinance` as an explicit fallback when the China source is
missing, stale, or otherwise unusable.

## Scope

This design covers only the existing `cn_a` market profile for mainland China
A-shares.

In scope:

- Make `cn_a` prefer China-market data for OHLCV, technical-indicator inputs,
  and fundamentals.
- Keep the current high-level tool contracts unchanged so analysts, graph
  orchestration, and report assembly do not need interface changes.
- Preserve the current fallback behavior through the vendor router, with
  China-market vendors tried first and `yfinance` used only as a fallback.
- Add tests for routing, fallback, stale-data rejection, and backward
  compatibility for non-`cn_a` runs.
- Update configuration and documentation so users can see the new defaults.

Out of scope:

- Hong Kong equities, H-shares, US-listed ADRs, or other China-adjacent assets.
- Replacing the existing China news, macro, or market-signal adapters.
- Adding licensed commercial feeds.
- Reworking the graph, analyst tool signatures, or agent sequencing.

## User Intent

The desired behavior is:

- Mainland A-share runs should use China-authoritative or China-native market
  data whenever possible.
- If the China source fails or returns unusable data, the run should degrade
  gracefully by falling back to `yfinance` rather than failing outright.
- This behavior should apply only to `market_profile="cn_a"`.

## Current-State Constraints

The existing codebase already has the right architectural seams:

- `tradingagents/dataflows/interface.py` routes each abstract tool method to a
  configured vendor chain.
- `tradingagents/dataflows/market_profiles.py` can override vendor defaults for
  `cn_a`.
- The analyst-facing wrappers in `tradingagents/agents/utils/*.py` are stable
  and graph-facing; changing their signatures would create unnecessary churn.
- `route_to_vendor(...)` already supports ordered fallback across vendors and
  already distinguishes between explicit no-data outcomes and real errors.

The design should therefore stay inside the dataflow layer and configuration
layer instead of touching the graph or prompts unless a data-contract issue
forces it.

## Requirements

### 1. Market-Profile Coverage

The `cn_a` profile must expand beyond news, macro, and forward-looking market
signals to also cover:

- `core_stock_apis`
- `technical_indicators`
- `fundamental_data`

The default vendor chains in `cn_a` should become:

- `core_stock_apis`: `cn_stock,yfinance`
- `technical_indicators`: `cn_stock,yfinance`
- `fundamental_data`: `cn_fundamentals,yfinance`
- `news_data`: keep current China defaults
- `macro_data`: keep current China defaults
- `prediction_markets`: keep current China defaults

### 2. Stable High-Level Tool Contracts

These user-facing tools must keep their current signatures and output shape:

- `get_stock_data`
- `get_indicators`
- `get_fundamentals`
- `get_balance_sheet`
- `get_cashflow`
- `get_income_statement`

The rest of the system should not need to know whether the active vendor is
China-native or `yfinance`.

### 3. China-First OHLCV

A new China stock adapter should:

- Accept A-share symbols already normalized to `.SS` / `.SZ`.
- Convert them to the China-source symbol format internally.
- Return the same style of output as `get_YFin_data_online(...)`: header text
  plus CSV data.
- Apply date-window filtering and stale-data protection before returning data.
- Raise `NoMarketDataError` when the China source returns no rows, unusable
  rows, or stale rows so the router can fall back to `yfinance`.

### 4. China-First Technical Indicators

Technical indicators should continue to be computed locally rather than being
fetched from a separate remote indicator API.

The important behavior change is that, in `cn_a` mode, the underlying OHLCV
used for indicator calculation should come from the China-first stock adapter,
with fallback to `yfinance` only when necessary.

### 5. China-First Fundamentals

A new China fundamentals adapter should provide:

- a fundamentals overview
- balance sheet data
- cash flow data
- income statement data

The adapter must preserve the current output contracts:

- `get_fundamentals`: header plus `Label: value` lines
- statement methods: header plus CSV output

The adapter may omit fields that do not map cleanly from the China source, but
it must not fabricate values or emit misleading placeholders. If it cannot
produce any usable fields for a request, it should raise `NoMarketDataError`
and let the router fall back to `yfinance`.

### 6. Graceful Degradation

China-first behavior must not mean “always trust the first source.”

For both OHLCV and fundamentals:

- empty data should trigger fallback
- malformed or unusable data should trigger fallback
- stale OHLCV should trigger fallback
- unexpected vendor exceptions should be visible through the existing logging
  behavior and fallback rules

This design intentionally keeps the existing vendor-router semantics rather than
introducing custom fallback logic inside each adapter.

### 7. Backward Compatibility

Non-`cn_a` runs must preserve existing behavior.

This includes:

- default/global runs still using the current vendor defaults
- explicit user vendor overrides still taking precedence over profile defaults
- existing analyst tool wrappers and prompts remaining compatible with the new
  data providers

## Proposed Architecture

### A. New China Equity Helper Module

Add a small shared helper module for mainland-equity normalization and
dataframe cleanup, for example:

- `tradingagents/dataflows/china_equity_utils.py`

Responsibilities:

- normalize `.SS` / `.SZ` symbols into China-source request forms
- identify exchange and raw security code
- detect relevant date columns in returned data
- provide small shared utilities needed by both stock and fundamentals adapters

This avoids coupling the dataflow layer to `tradingagents/service/stock_catalog.py`,
whose `_normalize_cn_a_symbol(...)` helper lives in the service layer and is not
the right dependency direction for vendor code.

### B. New `cn_stock` Adapter

Add:

- `tradingagents/dataflows/cn_stock.py`

Responsibilities:

- load the China-market vendor
- fetch OHLCV for mainland A-shares
- normalize and filter the returned frame
- enforce stale-data checks
- render the same textual stock-data contract the current system expects

This adapter is the source of truth for China-first OHLCV and, indirectly, for
China-first technical indicators.

### C. New `cn_fundamentals` Adapter

Add:

- `tradingagents/dataflows/cn_fundamentals.py`

Responsibilities:

- fetch fundamentals overview data
- fetch balance sheet, cash flow, and income statement data
- map China-source fields into stable output labels
- render statement data into the same CSV-style contract used today

This adapter should keep the mapping logic internal so future upgrades from one
China source to another do not change the rest of the application.

### D. Routing-Layer Changes

Update:

- `tradingagents/dataflows/interface.py`
- `tradingagents/dataflows/market_profiles.py`

Changes:

- register `cn_stock` for `get_stock_data` and indicator-related OHLCV loading
- register `cn_fundamentals` for fundamentals and financial statements
- extend `cn_a` profile defaults so vendor chains are China-first

The router should continue to own ordered fallback behavior. The new adapters
should simply raise typed no-data errors when the China source is not usable.

### E. Configuration and Docs

Update:

- `tradingagents/default_config.py`
- `README.md`

The defaults and docs should clearly state that `cn_a` now prefers China-native
data for price and fundamentals and falls back to `yfinance` if necessary.

## Data-Contract Strategy

### OHLCV Contract

Preserve the current `get_stock_data` response style:

- human-readable header
- retrieval timestamp
- CSV body

This is the lowest-risk approach because the market analyst and downstream
formatting already consume this shape.

### Fundamentals Overview Contract

Preserve the current `get_fundamentals` style:

- header
- compact `Label: value` lines

The label set can be China-aware and smaller than the current `yfinance` field
set, as long as it emphasizes stable, decision-relevant fields such as:

- company name
- industry
- market cap if available
- revenue
- net profit
- gross margin / operating margin if available
- ROE / ROA if available
- debt and liquidity ratios if available
- book value and operating cash-flow signals where stably mapped

### Financial Statements Contract

Preserve the current statement style:

- header
- CSV serialization of the statement dataframe

This keeps the fundamentals analyst’s existing tool usage intact.

## Error Handling

### China Source Failure Rules

For `cn_a` price and fundamentals:

- vendor unavailable -> raise `VendorNotConfiguredError` or vendor exception as
  appropriate so the router can try the next vendor in chain
- no rows -> raise `NoMarketDataError`
- stale rows -> raise `NoMarketDataError`
- zero usable mapped fields -> raise `NoMarketDataError`

### No Silent Substitution

The adapters must not:

- quietly switch to another symbol
- quietly use a different market
- fabricate missing fields
- return stale OHLCV just because some rows exist

If the China source is not good enough for the requested call, the correct
behavior is to make that explicit and let the existing fallback chain continue.

## Testing Strategy

Tests should be written first and should verify behavior at the routing and
adapter level.

### 1. Profile Default Tests

Add tests proving that `cn_a` now defaults to:

- `cn_stock,yfinance` for `core_stock_apis`
- `cn_stock,yfinance` for `technical_indicators`
- `cn_fundamentals,yfinance` for `fundamental_data`

### 2. Routing Preference Tests

Add tests proving that:

- when the China adapter succeeds, the router returns its result
- `yfinance` is not called when the China adapter succeeds

### 3. Fallback Tests

Add tests proving that:

- empty China-source OHLCV falls back to `yfinance`
- stale China-source OHLCV falls back to `yfinance`
- empty China fundamentals fall back to `yfinance`
- China-source exceptions still allow in-chain fallback when configured

### 4. Non-China Compatibility Tests

Add tests proving that:

- non-`cn_a` profiles keep existing defaults
- explicit user tool/category overrides still beat profile defaults

### 5. Adapter Contract Tests

Add tests for:

- symbol normalization for `.SS` and `.SZ`
- window filtering behavior
- output format consistency
- no-data and stale-data handling
- statement rendering and fundamentals field mapping

## Implementation Slice

The first implementation slice should be:

1. add failing tests for `cn_a` vendor-chain defaults
2. add failing tests for China-first stock routing and fallback
3. implement `cn_stock`
4. add failing tests for China-first fundamentals routing and fallback
5. implement `cn_fundamentals`
6. update docs/config text

This order keeps the work incremental and preserves clear TDD checkpoints.

## File Plan

Expected new files:

- `tradingagents/dataflows/china_equity_utils.py`
- `tradingagents/dataflows/cn_stock.py`
- `tradingagents/dataflows/cn_fundamentals.py`
- one or more focused tests, likely:
  - `tests/test_cn_stock.py`
  - `tests/test_cn_fundamentals.py`

Expected modified files:

- `tradingagents/dataflows/interface.py`
- `tradingagents/dataflows/market_profiles.py`
- `tradingagents/default_config.py`
- `README.md`
- existing routing/profile tests such as:
  - `tests/test_china_market_profile.py`
  - `tests/test_vendor_routing.py`

## Acceptance Criteria

The work is complete when:

- `market_profile="cn_a"` makes mainland A-share price, indicator inputs, and
  fundamentals China-first by default
- `yfinance` is still available as the second vendor in the chain
- stale or unusable China-source OHLCV does not leak into the analysis
- existing non-China behavior is unchanged
- tests cover the new routing and fallback behavior

## Open Deliberate Trade-Offs

- The first pass optimizes for trustworthy routing and contract stability over
  exhaustive field coverage.
- The first pass intentionally limits scope to mainland A-shares and does not
  expand to Hong Kong.
- The first pass keeps `yfinance` fallback because operational continuity is
  more important than enforcing China-only purity when the primary source is
  temporarily unavailable.
