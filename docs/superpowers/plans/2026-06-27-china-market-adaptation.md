# China Market Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a usable `cn_a` market mode so TradingAgents can analyze China A-share equities with China-appropriate data routing, macro context, forward-looking signals, and analyst semantics.

**Architecture:** Preserve the existing graph and tool interfaces, then introduce a China market profile plus vendor adapters under `tradingagents/dataflows/`. Route China mode through those adapters while keeping existing US/default behavior backwards-compatible. Centralize China prompt semantics in helper utilities so analyst files stay small and consistent.

**Tech Stack:** Python 3.10+, LangGraph, LangChain tools, pandas, requests, optional AKShare-backed adapters, pytest, unittest.mock.

---

### Task 1: Add `cn_a` profile plumbing and configuration defaults

**Files:**
- Modify: `tradingagents/default_config.py`
- Modify: `tradingagents/dataflows/config.py`
- Create: `tradingagents/dataflows/market_profiles.py`
- Test: `tests/test_dataflows_config.py`
- Test: `tests/test_env_overrides.py`

- [ ] **Step 1: Write the failing profile tests**

```python
def test_default_config_exposes_market_profile():
    from tradingagents.default_config import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["market_profile"] == "default"


def test_set_config_can_switch_to_cn_a_profile():
    from tradingagents.dataflows.config import get_config, set_config

    set_config({"market_profile": "cn_a"})
    assert get_config()["market_profile"] == "cn_a"
```

- [ ] **Step 2: Run the targeted tests to confirm failure**

Run: `pytest tests/test_dataflows_config.py -q`
Expected: failure because `market_profile` is not yet defined.

- [ ] **Step 3: Add `market_profile` and environment override support**

Key code to add in `tradingagents/default_config.py`:

```python
_ENV_OVERRIDES = {
    ...
    "TRADINGAGENTS_MARKET_PROFILE": "market_profile",
}
...
"market_profile": "default",
```

Key helper to add in `tradingagents/dataflows/market_profiles.py`:

```python
from tradingagents.dataflows.config import get_config


def get_market_profile() -> str:
    return str(get_config().get("market_profile", "default")).strip().lower() or "default"


def is_china_a_profile(profile: str | None = None) -> bool:
    value = (profile or get_market_profile()).strip().lower()
    return value == "cn_a"
```

- [ ] **Step 4: Re-run tests to verify config support passes**

Run: `pytest tests/test_dataflows_config.py tests/test_env_overrides.py -q`
Expected: PASS for the new config/profile coverage.

- [ ] **Step 5: Commit**

```bash
git add tradingagents/default_config.py tradingagents/dataflows/config.py tradingagents/dataflows/market_profiles.py tests/test_dataflows_config.py tests/test_env_overrides.py
git commit -m "feat: add China market profile config"
```

### Task 2: Add China vendor adapters for macro and forward-looking market signals

**Files:**
- Create: `tradingagents/dataflows/china_macro.py`
- Create: `tradingagents/dataflows/china_market_signals.py`
- Modify: `tradingagents/dataflows/interface.py`
- Modify: `tradingagents/agents/utils/macro_data_tools.py`
- Modify: `tradingagents/agents/utils/prediction_markets_tools.py`
- Test: `tests/test_vendor_routing.py`
- Create: `tests/test_china_macro.py`
- Create: `tests/test_china_market_signals.py`

- [ ] **Step 1: Write failing routing and adapter tests**

```python
def test_cn_macro_vendor_is_available_for_macro_data():
    from tradingagents.dataflows import interface
    assert "cn_macro" in interface.VENDOR_METHODS["get_macro_indicators"]


def test_cn_market_signals_vendor_is_available_for_forward_signals():
    from tradingagents.dataflows import interface
    assert "cn_market_signals" in interface.VENDOR_METHODS["get_prediction_markets"]
```

- [ ] **Step 2: Run the new and existing routing tests**

Run: `pytest tests/test_vendor_routing.py -q`
Expected: failure because the China vendors are not registered.

- [ ] **Step 3: Implement China macro adapter with China aliases**

Core shape for `tradingagents/dataflows/china_macro.py`:

```python
CHINA_MACRO_ALIASES = {
    "cpi": "cpi_yearly",
    "ppi": "ppi_yearly",
    "pmi": "pmi_yearly",
    "m2": "m2_yearly",
    "social_financing": "social_financing_flow",
    "lpr_1y": "lpr_1y",
    "lpr_5y": "lpr_5y",
}


def get_china_macro_data(indicator: str, curr_date: str, look_back_days: int | None = None) -> str:
    ...
```

Implementation requirements:
- lazy-import AKShare or a helper loader inside the function body
- return formatted markdown, not raw dataframes
- degrade with an explicit message when the alias is unknown or the vendor is unavailable

- [ ] **Step 4: Implement China forward-looking market-signal adapter**

Core shape for `tradingagents/dataflows/china_market_signals.py`:

```python
def get_china_market_signals(topic: str, limit: int | None = None) -> str:
    ...
```

Implementation requirements:
- keep the compatibility contract of `get_prediction_markets(...)`
- interpret China-mode topics such as northbound flow, margin financing, sector flow, or policy-sensitive liquidity signals
- return explicit markdown explaining what the signal means to the news analyst

- [ ] **Step 5: Register the vendors in `interface.py`**

Add imports and mappings similar to:

```python
from .china_macro import get_china_macro_data
from .china_market_signals import get_china_market_signals
...
VENDOR_LIST = [
    "yfinance",
    "fred",
    "polymarket",
    "alpha_vantage",
    "cn_macro",
    "cn_market_signals",
]
...
"get_macro_indicators": {
    "fred": get_fred_macro_data,
    "cn_macro": get_china_macro_data,
},
"get_prediction_markets": {
    "polymarket": get_polymarket_prediction_markets,
    "cn_market_signals": get_china_market_signals,
},
```

- [ ] **Step 6: Update tool docstrings to avoid US-only wording**

Adjust `macro_data_tools.py` and `prediction_markets_tools.py` so their descriptions mention profile-dependent vendors rather than only FRED or Polymarket.

- [ ] **Step 7: Re-run tests**

Run: `pytest tests/test_vendor_routing.py tests/test_china_macro.py tests/test_china_market_signals.py -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add tradingagents/dataflows/china_macro.py tradingagents/dataflows/china_market_signals.py tradingagents/dataflows/interface.py tradingagents/agents/utils/macro_data_tools.py tradingagents/agents/utils/prediction_markets_tools.py tests/test_vendor_routing.py tests/test_china_macro.py tests/test_china_market_signals.py
git commit -m "feat: add China macro and forward-signal vendors"
```

### Task 3: Add China A-share data routing defaults and China-aware report context

**Files:**
- Create: `tradingagents/dataflows/china_profile.py`
- Modify: `tradingagents/dataflows/interface.py`
- Modify: `tradingagents/agents/utils/agent_utils.py`
- Modify: `tradingagents/default_config.py`
- Test: `tests/test_instrument_identity.py`
- Create: `tests/test_china_market_profile.py`

- [ ] **Step 1: Write failing profile-behavior tests**

```python
def test_china_profile_uses_china_macro_and_forward_signal_defaults():
    from tradingagents.dataflows.china_profile import get_profile_data_vendors

    vendors = get_profile_data_vendors("cn_a")
    assert vendors["macro_data"] == "cn_macro"
    assert vendors["prediction_markets"] == "cn_market_signals"
```

- [ ] **Step 2: Run tests to verify missing helper behavior**

Run: `pytest tests/test_china_market_profile.py -q`
Expected: failure because the profile helper does not exist.

- [ ] **Step 3: Implement China profile defaults**

Core shape for `tradingagents/dataflows/china_profile.py`:

```python
CHINA_A_VENDOR_DEFAULTS = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
    "macro_data": "cn_macro",
    "prediction_markets": "cn_market_signals",
}


def get_profile_data_vendors(profile: str) -> dict[str, str]:
    ...
```

- [ ] **Step 4: Merge profile defaults into runtime vendor selection**

Update `interface.get_vendor(...)` so `cn_a` can override vendor defaults for categories not explicitly pinned by the user, while preserving the current "explicit chain wins" behavior.

- [ ] **Step 5: Add centralized China market context helper**

Add helper(s) in `agent_utils.py` similar to:

```python
def get_market_semantics_instruction() -> str:
    ...


def is_china_a_analysis(state: Mapping[str, Any] | None = None) -> bool:
    ...
```

Behavior:
- mention A-share microstructure and China-specific reasoning cues only in `cn_a` mode
- keep default/US behavior unchanged

- [ ] **Step 6: Re-run tests**

Run: `pytest tests/test_dataflows_config.py tests/test_instrument_identity.py tests/test_china_market_profile.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add tradingagents/dataflows/china_profile.py tradingagents/dataflows/interface.py tradingagents/agents/utils/agent_utils.py tradingagents/default_config.py tests/test_china_market_profile.py tests/test_instrument_identity.py
git commit -m "feat: add China profile runtime defaults"
```

### Task 4: Rewrite analyst prompts for China semantics and disable overseas sentiment assumptions

**Files:**
- Modify: `tradingagents/agents/analysts/market_analyst.py`
- Modify: `tradingagents/agents/analysts/news_analyst.py`
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Modify: `tradingagents/agents/analysts/sentiment_analyst.py`
- Modify: `tradingagents/dataflows/stocktwits.py`
- Modify: `tradingagents/dataflows/reddit.py`
- Create: `tests/test_china_prompting.py`
- Modify: `tests/test_i18n_coverage.py`

- [ ] **Step 1: Write failing prompt tests**

```python
def test_news_analyst_china_mode_mentions_china_macro_and_policy():
    ...


def test_sentiment_analyst_china_mode_does_not_require_reddit_or_stocktwits():
    ...
```

- [ ] **Step 2: Run prompt tests to confirm failure**

Run: `pytest tests/test_china_prompting.py -q`
Expected: failure because the prompts still advertise US-centric sources.

- [ ] **Step 3: Inject centralized China semantics into analyst prompts**

Required changes:
- `market_analyst.py`: mention price limits, T+1, midday break, suspensions when `cn_a`
- `news_analyst.py`: mention policy, liquidity, industrial policy, disclosure events, and China macro tools
- `fundamentals_analyst.py`: mention shareholder pledge, subsidies, receivables, goodwill, related-party transactions, and cash-flow quality
- `sentiment_analyst.py`: in `cn_a` mode, treat news plus China market signals as primary sentiment inputs and explicitly frame overseas social sources as unavailable/non-primary

- [ ] **Step 4: Make social-source placeholders explicit in China mode**

Add clear returned placeholders such as:

```python
return "<stocktwits disabled for cn_a market profile>"
return "<reddit disabled for cn_a market profile>"
```

The sentiment analyst should treat these as expected data limits, not network failures.

- [ ] **Step 5: Re-run analyst and prompt tests**

Run: `pytest tests/test_china_prompting.py tests/test_i18n_coverage.py tests/test_analyst_execution.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tradingagents/agents/analysts/market_analyst.py tradingagents/agents/analysts/news_analyst.py tradingagents/agents/analysts/fundamentals_analyst.py tradingagents/agents/analysts/sentiment_analyst.py tradingagents/dataflows/stocktwits.py tradingagents/dataflows/reddit.py tests/test_china_prompting.py tests/test_i18n_coverage.py
git commit -m "feat: add China-aware analyst semantics"
```

### Task 5: Verify end-to-end compatibility and document China usage

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_market_toolnode.py`
- Test: `tests/test_memory_log.py`
- Test: `tests/test_vendor_routing.py`
- Test: `tests/test_china_macro.py`
- Test: `tests/test_china_market_signals.py`
- Test: `tests/test_china_prompting.py`

- [ ] **Step 1: Add README usage for `cn_a` mode**

Document:
- `market_profile="cn_a"`
- ticker examples such as `600519.SS`
- China macro / forward-signal behavior
- overseas social-source disablement in China mode

- [ ] **Step 2: Run focused verification suite**

Run:

```bash
pytest \
  tests/test_dataflows_config.py \
  tests/test_vendor_routing.py \
  tests/test_memory_log.py \
  tests/test_market_toolnode.py \
  tests/test_china_macro.py \
  tests/test_china_market_signals.py \
  tests/test_china_market_profile.py \
  tests/test_china_prompting.py -q
```

Expected: PASS

- [ ] **Step 3: Run lint-style smoke checks for touched files**

Run:

```bash
python -m compileall tradingagents tests
```

Expected: no syntax errors

- [ ] **Step 4: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: document China A-share adaptation"
```
