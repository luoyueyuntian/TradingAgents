# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradingAgents is a multi-agent LLM financial trading analysis framework (v0.3.0). It simulates a trading firm with specialized AI agents that collaborate to evaluate markets and produce trading decisions. It does **not** execute real trades.

## Common Commands

```bash
# Install (editable with dev tools)
pip install -e ".[dev]"

# Run tests
pytest -q                          # all tests
pytest -q -m unit                  # unit tests only
pytest -q -m smoke                 # smoke tests
pytest tests/test_signal_processing.py  # single test file

# Lint
ruff check .
python -m pyright --level warning --pythonpath "$(python -c 'import sys; print(sys.executable)')"
cd frontend && npm run check

# Run web server
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000

# Docker
docker compose run --rm tradingagents
docker compose --profile ollama run --rm tradingagents-ollama  # local Ollama
```

## Architecture

### Agent Pipeline (5 stages)

1. **Analyst Team** — 4 specialists analyze a ticker independently: Market (technical), Sentiment (social/news), News (macro events), Fundamentals (financials)
2. **Research Team** — Bull and Bear researchers debate analyst outputs; Research Manager judges
3. **Trader** — translates research into a concrete transaction proposal
4. **Risk Management** — Aggressive, Conservative, Neutral debators evaluate risk
5. **Portfolio Manager** — final 5-tier rating (Buy/Overweight/Hold/Underweight/Sell)

### Core Execution

- `TradingAgentsGraph` (`tradingagents/graph/trading_graph.py`) is the main orchestrator
- `propagate(ticker, date, asset_type)` runs the full pipeline and returns `(final_state, decision)`
- Internally uses LangGraph `StateGraph` with conditional edges for debate loops
- `Propagator` creates initial state, `GraphSetup` builds the graph, `ConditionalLogic` routes decisions

### Key Packages

- **`tradingagents/graph/`** — LangGraph orchestration (trading_graph, setup, propagation, reflection, signal_processing, checkpointer)
- **`tradingagents/agents/`** — Agent factories (analysts/, researchers/, risk_mgmt/, trader/, managers/) and shared utilities (schemas, states, tools, memory)
- **`tradingagents/dataflows/`** — Data vendor abstraction layer with fallback chains. `interface.py` routes tool calls to vendors (yfinance, alpha_vantage, fred, polymarket, china_*). `config.py` holds thread-local runtime config (via `ContextVar`). `market_profiles.py` handles US vs China A-share defaults.
- **`tradingagents/llm_clients/`** — Multi-provider LLM abstraction. `factory.py` routes to provider clients (openai, anthropic, google, azure, bedrock). `model_catalog.py` has curated model lists. `capabilities.py` tracks per-model API features.
- **`web/`** — FastAPI web interface. `runner.py` bridges sync graph streaming to async SSE via background threads. `routes.py` defines API endpoints.

### Configuration System

`tradingagents/default_config.py` defines `DEFAULT_CONFIG` dict. Environment variables prefixed with `TRADINGAGENTS_` override config keys automatically (e.g., `TRADINGAGENTS_LLM_PROVIDER` overrides `llm_provider`). The `_ENV_OVERRIDES` mapping in that file controls which env vars are recognized.

### Data Vendor Routing

`tradingagents/dataflows/interface.py` maps each tool method to a vendor implementation. The `data_vendors` config dict controls category-level defaults (e.g., `"core_stock_apis": "yfinance"`). `tool_vendors` allows per-tool overrides. Comma-separated chains enable fallback (e.g., `"yfinance,alpha_vantage"`).

### Persistence

- **Memory log**: `~/.tradingagents/memory/trading_memory.md` — stores past decisions and reflections for same-ticker context
- **Checkpoints**: SQLite at `~/.tradingagents/cache/checkpoints/<TICKER>.db` for crash recovery (opt-in via `--checkpoint`)
- **Reports**: markdown report trees written by `tradingagents/reporting.py`

## Testing

Tests are in `tests/` (flat, no subdirectories). The `conftest.py` provides:
- `_dummy_api_keys` (autouse): sets placeholder API key env vars so tests don't hang
- `_isolate_config` (autouse): resets context-local dataflows config between tests via `initialize_config()`
- `mock_llm_client`: patches `create_llm_client` for unit tests

Test markers: `unit`, `integration`, `smoke`.

## Code Style

- Ruff: line-length 100, target Python 3.10, rules `E W F I B UP C4 SIM` (ignore E501)
- isort: `combine-as-imports = true`
- `__init__.py` files may have intentional re-exports (F401 suppressed)

## Important Constraints

- `tradingagents/dataflows/config.py` uses a `ContextVar` for thread-local config — each thread/async context gets its own isolated config. The web layer keeps a conservative `Semaphore(1)` guard for now.
- `tradingagents/graph/event_processor.py` contains shared constants and the `ChunkProcessor` class used by the web layer for streaming chunk processing.
- `.env` files are auto-loaded on `import tradingagents` via python-dotenv.
