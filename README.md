<p align="center">
  <img src="assets/TauricResearch.png" style="width: 60%; height: auto;">
</p>

<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2412.20138" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2412.20138-B31B1B?logo=arxiv"/></a>
  <a href="https://discord.com/invite/hk9PGKShPK" target="_blank"><img alt="Discord" src="https://img.shields.io/badge/Discord-TradingResearch-7289da?logo=discord&logoColor=white&color=7289da"/></a>
  <a href="./assets/wechat.png" target="_blank"><img alt="WeChat" src="https://img.shields.io/badge/WeChat-TauricResearch-brightgreen?logo=wechat&logoColor=white"/></a>
  <a href="https://x.com/TauricResearch" target="_blank"><img alt="X Follow" src="https://img.shields.io/badge/X-TauricResearch-white?logo=x&logoColor=white"/></a>
  <br>
  <a href="https://github.com/TauricResearch/" target="_blank"><img alt="Community" src="https://img.shields.io/badge/Join_GitHub_Community-TauricResearch-14C290?logo=discourse"/></a>
</div>

<div align="center">
  <!-- Keep these links. Translations will automatically update with the README. -->
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=de">Deutsch</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=es">Español</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=fr">français</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ja">日本語</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ko">한국어</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=pt">Português</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=ru">Русский</a> | 
  <a href="https://www.readme-i18n.com/TauricResearch/TradingAgents?lang=zh">中文</a>
</div>

---

# TradingAgents: Multi-Agents LLM Financial Trading Framework

## News
- [2026-06] **TradingAgents v0.3.0** released with a verified data-access contract, an expanded provider registry (NVIDIA, Kimi, Groq, Mistral, Bedrock, and any OpenAI-compatible endpoint), FRED and Polymarket data vendors, a current-generation model catalog, and a CI gate. See [CHANGELOG.md](CHANGELOG.md) for the full list.
- [2026-05] **TradingAgents v0.2.5** released with the grounded Sentiment Analyst, GPT-5.5 etc. model coverage, Qwen/GLM/MiniMax dual-region support, `TRADINGAGENTS_*` env-var configurability with API-key auto-detection, remote Ollama support, non-US alpha benchmarks, and ticker path-traversal hardening.
- [2026-04] **TradingAgents v0.2.4** released with structured-output agents (Research Manager, Trader, Portfolio Manager), LangGraph checkpoint resume, persistent decision log, DeepSeek/Qwen/GLM/Azure provider support, Docker, and a Windows UTF-8 encoding fix.
- [2026-03] **TradingAgents v0.2.3** released with multi-language support, GPT-5.4 family models, unified model catalog, backtesting date fidelity, and proxy support.
- [2026-03] **TradingAgents v0.2.2** released with GPT-5.4/Gemini 3.1/Claude 4.6 model coverage, five-tier rating scale, OpenAI Responses API, Anthropic effort control, and cross-platform stability.
- [2026-02] **TradingAgents v0.2.0** released with multi-provider LLM support (GPT-5.x, Gemini 3.x, Claude 4.x, Grok 4.x) and improved system architecture.
- [2026-01] **Trading-R1** [Technical Report](https://arxiv.org/abs/2509.11420) released, with [Terminal](https://github.com/TauricResearch/Trading-R1) expected to land soon.

<div align="center">
<a href="https://www.star-history.com/#TauricResearch/TradingAgents&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date" />
   <img alt="TradingAgents Star History" src="https://api.star-history.com/svg?repos=TauricResearch/TradingAgents&type=Date" style="width: 80%; height: auto;" />
 </picture>
</a>
</div>

> 🎉 **TradingAgents** officially released! We have received numerous inquiries about the work, and we would like to express our thanks for the enthusiasm in our community.
>
> So we decided to fully open-source the framework. Looking forward to building impactful projects with you!

<div align="center">

🚀 [TradingAgents](#tradingagents-framework) | 🖥️ [Web UI](#web-ui) | ⚡ [Installation](#installation-and-web-ui) | 📦 [Python Usage](#tradingagents-package) | 🤝 [Contributing](#contributing) | 📄 [Citation](#citation)

</div>

## TradingAgents Framework

TradingAgents is a multi-agent trading framework that mirrors the dynamics of real-world trading firms. By deploying specialized LLM-powered agents: from fundamental analysts, sentiment experts, and technical analysts, to trader, risk management team, the platform collaboratively evaluates market conditions and informs trading decisions. Moreover, these agents engage in dynamic discussions to pinpoint the optimal strategy.

The current application is delivered primarily as a FastAPI web workspace. It keeps the agent graph reusable as a Python package while adding a browser-based workflow for configuration, queued analyses, saved runs, watchlists, alerts, portfolios, collaboration notes, public read-only shares, and tenant-scoped runtime maintenance.

<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;">
</p>

> TradingAgents framework is designed for research purposes. Trading performance may vary based on many factors, including the chosen backbone language models, model temperature, trading periods, the quality of data, and other non-deterministic factors. [It is not intended as financial, investment, or trading advice.](https://tauric.ai/disclaimer/)

Our framework decomposes complex trading tasks into specialized roles.

### Analyst Team
- Fundamentals Analyst: Evaluates company financials and performance metrics, identifying intrinsic values and potential red flags.
- Sentiment Analyst: Aggregates news headlines, StockTwits, and Reddit chatter into a single sentiment read to gauge short-term market mood.
- News Analyst: Monitors global news and macroeconomic indicators, interpreting the impact of events on market conditions.
- Technical Analyst: Utilizes technical indicators (like MACD and RSI) to detect trading patterns and forecast price movements.

<p align="center">
  <img src="assets/analyst.png" width="100%" style="display: inline-block; margin: 0 2%;">
</p>

### Researcher Team
- Comprises both bullish and bearish researchers who critically assess the insights provided by the Analyst Team. Through structured debates, they balance potential gains against inherent risks.

<p align="center">
  <img src="assets/researcher.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Trader Agent
- Composes reports from the analysts and researchers to make informed trading decisions, determining the timing and magnitude of trades.

<p align="center">
  <img src="assets/trader.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

### Risk Management and Portfolio Manager
- Continuously evaluates portfolio risk by assessing market volatility, liquidity, and other risk factors. The risk management team evaluates and adjusts trading strategies, providing assessment reports to the Portfolio Manager for final decision.
- The Portfolio Manager approves/rejects the transaction proposal. If approved, the order will be sent to the simulated exchange and executed.

<p align="center">
  <img src="assets/risk.png" width="70%" style="display: inline-block; margin: 0 2%;">
</p>

## Installation and Web UI

### Installation

Clone TradingAgents:
```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

Create a virtual environment in any of your favorite environment managers:
```bash
conda create -n tradingagents python=3.12
conda activate tradingagents
```

Install the web application and core package:
```bash
pip install ".[web]"
```

For direct Python/package usage without the browser UI, the core package can be installed on its own:
```bash
pip install .
```

### Dependencies

TradingAgents keeps its dependency set minimal. All LLM calls go through HTTP APIs; the dependencies below handle data fetching, agent orchestration, and data processing.

#### Core Dependencies

| Package | Size | When it's used |
|---|---|---|
| **langchain-core** | — | **Always.** Provides the `@tool` decorator for data tools, `ChatPromptTemplate` for agent prompts, and `HumanMessage`/`AIMessage` for inter-agent communication. Used in 11 files across agents and tools. |
| **langchain-openai** | — | When `llm_provider` is `openai`, `deepseek`, `qwen`, `glm`, `minimax`, `mistral`, `kimi`, `groq`, `nvidia`, `openai_compatible`, or `openrouter`. Provides `ChatOpenAI` (and `AzureChatOpenAI` for Azure). |
| **langchain-anthropic** | — | When `llm_provider` is `anthropic`. Provides `ChatAnthropic`. |
| **langchain-google-genai** | — | When `llm_provider` is `google`. Provides `ChatGoogleGenerativeAI`. |
| **langgraph** | — | **Always.** The agent orchestration framework. Builds the `StateGraph` that connects analysts → researchers → trader → risk management → portfolio manager. |
| **langgraph-checkpoint-sqlite** | — | When `checkpoint_enabled: true`. Saves graph state to SQLite for crash recovery. |
| **yfinance** | ~9 MB | **Always** (default data vendor). Fetches OHLCV prices, fundamentals, balance sheets, cash flow, income statements, insider transactions, and news for US/global tickers. |
| **pandas** | ~70 MB | **Always.** DataFrame operations across all data vendor implementations (8 files). Used for data cleaning, date filtering, column mapping, and markdown table generation. |
| **stockstats** | <1 MB | **Always.** Computes technical indicators (RSI, MACD, Bollinger Bands, etc.) on top of OHLCV data from yfinance. |
| **requests** | <1 MB | When using FRED (macro data), Polymarket (prediction markets), or Alpha Vantage. Direct HTTP calls to these APIs. |

#### Optional Dependencies

Install with `pip install ".[extra]"`:

| Package | Install extra | When it's used |
|---|---|---|
| **akshare** | — | When `market_profile` is `cn_a` (China A-shares). Fetches China macro data (CPI, PPI, PMI), market signals (margin trading, northbound flow), and news from 东方财富/财联社. **Note:** akshare pulls in `py_mini_racer` (61 MB V8 JS engine) because some Chinese financial sites encrypt data with JavaScript. |
| **langchain-aws** | `pip install ".[bedrock]"` | When `llm_provider` is `bedrock`. Provides `ChatBedrockConverse` for AWS Bedrock Anthropic models. |
| **fastapi** | `pip install ".[web]"` | Always, for the web UI. Provides the HTTP API framework. |
| **uvicorn** | `pip install ".[web]"` | Always, for the web UI. ASGI server that runs the FastAPI app. |
| **sse-starlette** | `pip install ".[web]"` | Always, for the web UI. Server-Sent Events for streaming analysis progress to the browser. |

#### Dependency Footprint

A minimal install (US/global markets, no China data, no Bedrock, no web) pulls ~127 packages / ~455 MB, dominated by:
- `pandas` + `numpy`: 103 MB
- `langchain` ecosystem (core + provider): ~50 MB
- `yfinance` + transitive deps: ~30 MB

To skip the China market dependency (~90 MB savings):
```bash
pip install .  # akshare is a core dep today; planned to become optional
```

### Docker

The quickest way to run the Web UI is Docker:
```bash
docker compose up -d              # start web UI at http://localhost:8000
./deploy.sh                       # or use the deploy script (rebuild + restart)
```

Docker Compose publishes the web UI on `127.0.0.1:8000` by default. Before
binding it to a public interface or reverse proxy, set `TRADINGAGENTS_WEB_API_TOKEN`
and configure `TRADINGAGENTS_WEB_CORS_ORIGINS` for the browser origins you trust.

#### Frontend-only debugging with the Docker backend

After the Docker image is built and the backend container is running, you can
iterate on the local Vue frontend without rebuilding the image:

```bash
./deploy.sh
cd frontend
npm install
npm run dev:docker
```

Open `http://127.0.0.1:5173/static/spa/` (the root path redirects there). The
Vite dev server proxies `/api/*` requests to the Docker backend at
`http://127.0.0.1:8000`, so frontend edits hot-reload while the container keeps
serving the backend API and worker runtime. If your backend is published on a
different local port, override the proxy target:

```bash
TRADINGAGENTS_WEB_DEV_PROXY_TARGET=http://127.0.0.1:18000 npm run dev:docker
```

To split the API and worker into separate processes:
```bash
docker compose --profile external-worker up -d
./deploy.sh --external-worker
```

In this mode, the API only accepts and persists runs; the worker executes them asynchronously from the shared volume-backed queue state.
By default this split mode uses `TRADINGAGENTS_WEB_STATE_BACKEND=sqlite` with the database at `~/.tradingagents/web/state.db`.
Use `TRADINGAGENTS_WEB_STATE_DIR` or `TRADINGAGENTS_WEB_SQLITE_PATH` to relocate the shared state root or SQLite database path.

For local models with Ollama:
```bash
docker compose --profile ollama up -d
./deploy.sh --ollama
```

You can combine both profiles to run Ollama plus a separate API and worker:
```bash
docker compose --profile ollama --profile external-worker up -d
./deploy.sh --ollama --external-worker
```

Configuration is managed through the web UI (Settings gear icon) and persisted to `~/.tradingagents/settings.json` via a Docker volume.

### Required APIs

TradingAgents supports multiple LLM providers. Set the API key for your chosen provider:

```bash
export OPENAI_API_KEY=...          # OpenAI (GPT)
export GOOGLE_API_KEY=...          # Google (Gemini)
export ANTHROPIC_API_KEY=...       # Anthropic (Claude)
export XAI_API_KEY=...             # xAI (Grok)
export DEEPSEEK_API_KEY=...        # DeepSeek
export DASHSCOPE_API_KEY=...       # Qwen — International (dashscope-intl.aliyuncs.com)
export DASHSCOPE_CN_API_KEY=...    # Qwen — China (dashscope.aliyuncs.com)
export ZHIPU_API_KEY=...           # GLM via Z.AI (international)
export ZHIPU_CN_API_KEY=...        # GLM via BigModel (China, open.bigmodel.cn)
export MINIMAX_API_KEY=...         # MiniMax — Global (api.minimax.io)
export MINIMAX_CN_API_KEY=...      # MiniMax — China (api.minimaxi.com)
export OPENROUTER_API_KEY=...      # OpenRouter
export ALPHA_VANTAGE_API_KEY=...   # Alpha Vantage
```

For Azure OpenAI, copy `.env.enterprise.example` to `.env.enterprise` and fill in your credentials.

For AWS Bedrock, install the extra with `pip install ".[bedrock]"`, set `llm_provider: "bedrock"`, configure AWS credentials (environment variables, `~/.aws/credentials`, or an IAM role) and `AWS_DEFAULT_REGION`, and use a Bedrock model ID, e.g. `us.anthropic.claude-opus-4-8-v1:0`.

For local models, configure Ollama with `llm_provider: "ollama"`. The default endpoint is `http://localhost:11434/v1`; set `OLLAMA_BASE_URL` to point at a remote `ollama-serve`. Pull models with `ollama pull <name>`, and pick "Custom model ID" in the Web UI for any model not listed by default.

For any other OpenAI-compatible server (vLLM, LM Studio, llama.cpp, or a custom relay), use `llm_provider: "openai_compatible"` and set the endpoint via `backend_url` (or `TRADINGAGENTS_LLM_BACKEND_URL`), e.g. `http://localhost:8000/v1` for vLLM or `http://localhost:1234/v1` for LM Studio. The model is whatever your server serves. No key is needed for local servers; set `OPENAI_COMPATIBLE_API_KEY` when the endpoint requires one.

Alternatively, copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### Web UI

The Web UI is the primary product surface. It serves the browser workspace, REST API, static assets, PWA manifest, and Server-Sent Events stream from the same FastAPI app.

Start the web server after installing `.[web]`:
```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

The web API token is optional for local-only use, but strongly recommended
whenever the server is reachable from another machine:
```bash
export TRADINGAGENTS_WEB_API_TOKEN="choose-a-long-random-token"
export TRADINGAGENTS_WEB_CORS_ORIGINS="http://localhost:8000"
```

To run the API without executing analyses in-process, start it with:
```bash
TRADINGAGENTS_WEB_RUN_MODE=external_worker uvicorn web.app:app --host 0.0.0.0 --port 8000
python -m web.worker
```

Open http://localhost:8000 to access the interface. From there you can:
- Configure API keys and LLM provider (Settings gear icon)
- Select ticker, date, research depth, analysts, and one-off advanced run overrides
- Run analysis and watch real-time progress via SSE streaming
- View tabbed reports (Market, Sentiment, News, Fundamentals, Research, Trading, Decision)
- Inspect queue position, run history, configuration summaries, timelines, and saved artifacts for past runs
- Browse a reports library across saved runs so complete reports and full-state files are downloadable from one place
- Build a tenant-scoped watchlist and use Ticker Home to revisit the latest saved research for each symbol
- Paste CSV or TSV tables to import watchlist tickers and portfolio positions instead of adding them one by one
- Upload CSV, TSV, TXT, or JSON files straight into watchlist, portfolio, and workspace import flows instead of copying their contents by hand
- Queue a manual batch of tickers or run your whole watchlist with the current analysis settings
- Compare two saved runs side by side to inspect how signals, settings, and report sections changed
- Ask follow-up questions against a saved run to keep exploring the same analysis without starting over
- Create tenant-scoped alert rules and review which latest saved runs currently match them
- Track saved portfolio positions and see each holding alongside the latest research signal and cost basis summary
- Review a daily workspace briefing that rolls up alert hits, watchlist focus, portfolio context, and recent runs
- Review an in-app notification center for completed runs, active alert hits, and due pinned actions
- Filter the notification center by member, kind, severity, and unread state so the inbox stays usable as collaboration activity grows
- Export the currently filtered notification feed as CSV and mark only the filtered slice as read when triaging the inbox
- Optionally forward new workspace notifications to an external webhook for downstream automations or chatops
- Save daily or weekly automation rules that queue the watchlist or a manual basket with your current analysis settings
- Copy deep links for runs, tickers, compare views, and daily briefing so the UI can reopen the same workspace context
- Export the saved workspace as JSON or a markdown handoff summary for backup, sharing, or offline review
- Re-import an exported workspace JSON snapshot to restore saved watchlists, notes, views, pinned actions, and collaboration context
- Install the web workspace as a lightweight desktop/mobile app shell with cached static assets for basic offline reopening
- Prompt users to install the web workspace as an app shell directly from the header when the browser exposes an install event
- Use a command palette and keyboard shortcuts such as `Cmd/Ctrl+K` to jump across major workspace surfaces faster
- Export filtered screener candidates, workspace search results, and timeline events to CSV for spreadsheet analysis or handoff
- See a lightweight getting-started checklist on the dashboard so a new workspace knows the next best setup step
- Turn on browser desktop alerts so new unread run, alert, action, mention, and review notifications can surface outside the tab
- Create and manage public read-only run snapshots so one saved analysis can be shared outside the authenticated workspace
- See lightweight view counts and last-viewed timestamps on shared snapshots so public links feel more like real web shares than blind exports
- Filter shared snapshots by search and availability and export the current share directory as CSV
- Set optional expiry windows on public run snapshots so external links can be safely time-boxed
- Customize the title and summary of public run snapshots so shared pages read more like intentional landing pages than raw exports
- Filter recent runs by query, status, provider, and asset type, then export the narrowed history as CSV
- Select filtered recent runs for bulk retry or bulk delete when cleaning up saved analysis history
- Persist recent-run filters in saved views and shareable URLs so history slices reopen with the same status/provider/library context
- Open a persistent workspace dashboard that surfaces bullish focus, attention items, active alerts, pinned actions, portfolio context, and operational issues
- Review a dedicated workspace analytics panel for run success rates, provider mix, signal mix, top tickers, and daily activity
- Export workspace analytics as CSV for spreadsheet analysis or external reporting
- Use a workspace screener to filter saved ideas by scope, signal, status, asset type, provider, and current attention flags
- Save reusable analysis presets and re-apply them to the form with one click
- Rename or duplicate saved presets so common analysis setups can branch without starting from scratch
- Browse a workspace timeline that chronicles saved runs, watchlist additions, alert rules, positions, and presets
- See timeline activity for saved searches, saved views, workspace members, and public snapshot sharing as the workspace becomes more collaborative
- Filter timeline events by kind so workspace activity stays readable as the event stream grows
- Review the same workspace activity grouped by day in a lightweight calendar view
- Add structured annotations to important saved runs so their takeaway and next step remain visible in history and detail views
- Save scoped notes for the current ticker or run and revisit them as part of the workspace timeline
- Search, tag, and edit saved notes so your research annotations stay reusable instead of becoming a write-only log
- Browse note tags as clickable chips so recurring themes like risk, earnings, or macro can be reopened faster
- Switch the notes panel between current-context and all-workspace modes so notes can act as both inline annotations and a lightweight research library
- Persist notes mode and notes search inside saved views and shareable URLs so a note library slice can reopen with the same context
- Reopen recently viewed runs, tickers, and saved views from one lightweight local history panel
- Discuss a saved run with workspace members through a lightweight run-scoped comment thread
- Resolve or reopen run discussion comments so collaboration threads can double as lightweight work items
- Surface @member mentions and assignee-specific work inside the notification center, with optional webhook forwarding
- Open a member-centric workspace view to see assigned actions, mention notifications, and recent comments for one collaborator
- Set a current member in the header so notifications and the member workspace can open in a default “my inbox” context
- Persist member-scoped inbox, review, and screener filters inside deep links and saved views so collaboration context reopens cleanly
- Save member-aware searches and views so applying them restores the same collaboration context, not just the raw query or panel set
- Group and pin saved searches/views so frequently used workspace shortcuts stay organized as the product surface grows
- Rename or duplicate saved searches and saved views so workspace shortcuts can evolve without being rebuilt from scratch
- Archive or restore saved searches/views and filter active versus archived shortcuts as your workspace library grows
- Personalize the workspace dashboard by choosing which summary panes stay visible on the homepage
- Choose a default home surface so the app can open into dashboard, inbox, briefing, analytics, or other primary work areas
- Point the default home surface at a saved view so the app can reopen into a fully curated workspace layout
- Promote a saved view to the default home directly from the saved views list for faster homepage curation
- Browse saved views in either gallery or list form so reusable workspace layouts feel more like a visual library than a settings table
- Surface more than market status on the homepage, including pending reviews, enabled automations, and pinned shortcuts
- Assign a reviewer to a saved run and track lightweight review status directly inside the workspace
- Filter review history by reviewer, status, and note text so past review decisions stay inspectable
- Export filtered review history as CSV when you need a lightweight audit trail outside the app
- Search runs, notes, watchlist items, portfolio positions, presets, and alert rules from one unified workspace search box
- Search saved searches, saved views, workspace members, and public shares from the same workspace search surface too
- Search collaboration data too, including run comments and review records, from the same workspace search surface
- Filter search results by entity type and save your most-used searches as reusable workspace views
- Pin important saved runs with a note, category, priority, next action, action status, and optional due/snooze dates so they behave more like an actionable shortlist
- Open an action board that groups pinned items into todo, doing, and done columns for quick status updates
- Add lightweight workspace members and assign pinned actions so collaboration can happen without a full user system
- Label workspace members with lightweight roles such as analyst, reviewer, or lead so collaboration context is easier to scan
- Save full workspace views so a useful combination of ticker, compare state, briefing, or search context can be reopened in one click
- Configure benchmark ticker, memory-log rotation, global-news query sets, category vendor chains, and per-tool vendor overrides from the Settings dialog
- Switch between tenant namespaces and use Runtime Maintenance to inspect or clear tenant-scoped checkpoints and decision memory

### Markets and tickers

TradingAgents works with any market Yahoo Finance covers, using the exchange-suffixed ticker. Company identity and the alpha benchmark resolve automatically per market.

- US: `AAPL`, `SPY`
- Hong Kong: `0700.HK` · Tokyo: `7203.T` · London: `AZN.L`
- India: `RELIANCE.NS`, `.BO` · Canada: `.TO` · Australia: `.AX`
- China A-shares: Shanghai `.SS`, Shenzhen `.SZ` (e.g. `600519.SS` for Kweichow Moutai)
- Crypto: `BTC-USD`, `ETH-USD`

In the Web UI, enter the ticker in the Analysis Configuration panel. The workspace infers the asset type, stores completed runs, and lets you reopen the ticker through Ticker Home, history, saved views, dashboard widgets, and shareable deep links.

## TradingAgents Package

### Implementation Details

We built TradingAgents with LangGraph to ensure flexibility and modularity. The framework supports multiple LLM providers: OpenAI, Google, Anthropic, xAI, DeepSeek, Qwen (Alibaba DashScope, international and China endpoints), GLM (Zhipu), MiniMax (global + China), OpenRouter, Ollama for local models, and Azure OpenAI for enterprise.

### Python Usage

To use TradingAgents inside your code, you can import the `tradingagents` module and initialize a `TradingAgentsGraph()` object. The `.propagate()` function will return a decision. Here's a quick example:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())

# forward propagate
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

You can also adjust the default configuration to set your own choice of LLMs, debate rounds, etc.

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"        # e.g. openai, google, anthropic, deepseek, groq, ollama; openai_compatible covers any OpenAI-compatible endpoint (vLLM, LM Studio, llama.cpp, ...)
config["deep_think_llm"] = "gpt-5.5"     # Model for complex reasoning
config["quick_think_llm"] = "gpt-5.4-mini" # Model for quick tasks
config["max_debate_rounds"] = 2

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
print(decision)
```

See `tradingagents/default_config.py` for all configuration options.

### China A-Shares

TradingAgents can be switched into a mainland-China market profile for A-share
analysis:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["market_profile"] = "cn_a"

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("600519.SS", "2026-06-27")
print(decision)
```

In `cn_a` mode:

- `news_data` defaults to China-market company and macro news adapters
- `macro_data` defaults to China macro indicators such as `cpi`, `ppi`, `pmi`, `m2`, `social_financing`, and `lpr`
- `prediction_markets` is repurposed into China forward-looking market-structure signals such as `northbound flow`, `margin financing`, and broad `fund flow`
- overseas social sources like Reddit and StockTwits are intentionally deprioritized or disabled for the sentiment analyst

## Persistence and Recovery

TradingAgents persists two kinds of state across runs.

### Decision log

The decision log is always on. Each completed run appends its decision to a shared memory log. On the next run for the same ticker, TradingAgents fetches the realised return (raw and alpha vs SPY), generates a one-paragraph reflection, and injects the most recent same-ticker decisions plus recent cross-ticker lessons into the Portfolio Manager prompt, so each analysis carries forward what worked and what didn't.

For direct Python/package usage, the default path is `~/.tradingagents/memory/trading_memory.md` and you can override it with `TRADINGAGENTS_MEMORY_LOG_PATH`.

For the Web runtime, the memory log is tenant-scoped and shared across runs:
- default tenant: `~/.tradingagents/web/memory/trading_memory.md`
- named tenant: `~/.tradingagents/web/tenants/<TENANT_ID>/memory/trading_memory.md`

Use the Web UI's Runtime Maintenance panel to inspect or clear tenant-scoped memory entries.

### Checkpoint resume

Checkpoint resume is opt-in. When enabled, LangGraph saves state after each node so a crashed or interrupted run resumes from the last successful step instead of starting over. On a resume run you will see `Resuming from step N for <TICKER> on <date>` in the logs; on a new run you will see `Starting fresh`. Checkpoints are cleared automatically on successful completion.

For direct Python/package usage, per-ticker SQLite databases live at `~/.tradingagents/cache/checkpoints/<TICKER>.db` (override the base with `TRADINGAGENTS_CACHE_DIR`).

For the Web runtime, checkpoints are tenant-scoped and shared across runs for the same tenant:
- default tenant: `~/.tradingagents/web/cache/checkpoints/<TICKER>.db`
- named tenant: `~/.tradingagents/web/tenants/<TENANT_ID>/cache/checkpoints/<TICKER>.db`

Enable checkpoint resume from the Settings dialog or the Advanced Run Overrides panel. Use the Runtime Maintenance panel to inspect or clear tenant-scoped checkpoint files.

```python
config = DEFAULT_CONFIG.copy()
config["checkpoint_enabled"] = True
ta = TradingAgentsGraph(config=config)
_, decision = ta.propagate("NVDA", "2026-01-15")
```

## Reproducibility

TradingAgents is LLM-driven, so two runs of the same ticker and date can differ. This is expected for a research tool built on language models, not a defect. The variation comes from a few distinct sources, and it helps to separate them.

Language model sampling is non-deterministic. Even at a fixed temperature, providers do not guarantee byte-identical output across calls, and reasoning models (the default GPT-5.x family, and any thinking-mode model) vary the most because their internal reasoning is itself sampled.

Live data moves. News, StockTwits, and Reddit return different content as time passes, so a run today sees different inputs than a run last week even for the same historical trade date. Pin the analysis date to hold the price and indicator window fixed, but the social and news sources still reflect "now".

To reduce variation you can lower the sampling temperature. Set `temperature` in your config (or `TRADINGAGENTS_TEMPERATURE` in `.env`); lower values make models that honor it more repeatable. The current curated models are reasoning-first and largely ignore temperature, so for tighter reproducibility use a non-reasoning model, which you can set explicitly via the Custom model ID option.

```python
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["temperature"] = 0.0
# Reasoning models ignore temperature. For tighter reproducibility, set a
# non-reasoning deep/quick model explicitly (e.g. via the Custom model ID option).
```

What does not vary anymore: the analyzed company identity is resolved deterministically from the ticker before any agent runs, and the market analyst grounds exact price and indicator claims in a verified data snapshot. Earlier reports of "different companies" or fabricated price levels across runs are addressed by these two mechanisms.

Backtest results are not guaranteed to match any published figure. Returns depend on the model, the temperature, the date range, data quality, and the sampling above. Treat the framework as a research scaffold for studying multi-agent analysis, not as a strategy with a fixed, replicable return.

## Contributing

Contributions are welcome: bug fixes, documentation, and feature ideas; past contributions are credited per release in [`CHANGELOG.md`](CHANGELOG.md).

## Citation

Please reference our work if you find *TradingAgents* provides you with some help :)

```
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework}, 
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138}, 
}
```
