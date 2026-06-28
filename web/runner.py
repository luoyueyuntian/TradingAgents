"""Analysis execution bridge: background thread + asyncio.Queue for SSE."""

from __future__ import annotations

import asyncio
import datetime
import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.event_processor import (
    ANALYST_AGENT_NAMES,
    ANALYST_ORDER,
    ANALYST_REPORT_MAP,
    ChunkProcessor,
    build_agent_status_map,
    build_run_config,
)
from tradingagents.graph.trading_graph import TradingAgentsGraph

from .schemas import AnalysisRequest

logger = logging.getLogger(__name__)

# Conservative concurrency guard.  Config is now thread-local (ContextVar),
# but other shared state (LLM clients, data vendor caches) may not be.
# Safe to relax to a higher count once all shared state is audited.
_run_lock = threading.Semaphore(1)


@dataclass
class RunState:
    """In-memory state for a single analysis run."""

    run_id: str
    ticker: str
    date: str
    asset_type: str
    config: dict[str, Any]
    selected_analysts: list[str]
    status: str = "pending"
    agents: dict[str, str] = field(default_factory=dict)
    report_sections: dict[str, str | None] = field(default_factory=dict)
    current_report: str | None = None
    final_report: str | None = None
    final_state: dict | None = None
    signal: str | None = None
    error: str | None = None
    created_at: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    events: asyncio.Queue = field(default_factory=asyncio.Queue)
    _chunk_processor: ChunkProcessor | None = field(default=None, repr=False)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.datetime.now().isoformat()
        # Build agent status map and report sections from shared helpers
        self.agents = build_agent_status_map(self.selected_analysts)
        from tradingagents.graph.event_processor import build_report_sections
        self.report_sections = build_report_sections(self.selected_analysts)
        # Create chunk processor for this run
        self._chunk_processor = ChunkProcessor(self.selected_analysts)


# In-memory run storage
_runs: dict[str, RunState] = {}

# How long to keep completed runs before pruning (seconds).
_RUN_TTL = 3600  # 1 hour


def _prune_old_runs() -> None:
    """Remove completed runs older than _RUN_TTL to avoid unbounded memory growth."""
    now = datetime.datetime.now()
    stale = []
    for run_id, run in _runs.items():
        if run.status in ("completed", "failed") and run.completed_at:
            try:
                completed = datetime.datetime.fromisoformat(run.completed_at)
                if (now - completed).total_seconds() > _RUN_TTL:
                    stale.append(run_id)
            except (ValueError, TypeError):
                pass
    for run_id in stale:
        del _runs[run_id]


def get_run(run_id: str) -> RunState | None:
    return _runs.get(run_id)


def _put_event(run: RunState, event: dict, loop: asyncio.AbstractEventLoop):
    """Thread-safe event push to the run's asyncio.Queue."""
    try:
        if loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(run.events.put(event), loop)
    except RuntimeError:
        pass  # loop closed between check and call


def _emit_agent_status(run: RunState, agent: str, status: str, loop: asyncio.AbstractEventLoop):
    """Update agent status and emit SSE event."""
    if agent in run.agents:
        run.agents[agent] = status
        _put_event(run, {"event": "agent_status", "data": {"agent": agent, "status": status}}, loop)


def _emit_report(run: RunState, section: str, content: str, loop: asyncio.AbstractEventLoop):
    """Update report section and emit SSE event."""
    if section in run.report_sections:
        run.report_sections[section] = content
        _put_event(run, {"event": "report_update", "data": {"section": section, "content": content}}, loop)
        _update_current_report(run)


def _update_current_report(run: RunState):
    """Update the current_report summary from report_sections."""
    from tradingagents.graph.event_processor import build_current_report
    run.current_report = build_current_report(run.report_sections)


def _update_final_report(run: RunState):
    """Build the complete final report from all sections."""
    from tradingagents.graph.event_processor import build_final_report
    run.final_report = build_final_report(run.report_sections)


def _process_chunk(
    run: RunState,
    chunk: dict[str, Any],
    loop: asyncio.AbstractEventLoop,
):
    """Process a single streamed chunk using shared ChunkProcessor."""
    cp = run._chunk_processor

    # Extract messages and tool calls for progress events
    messages, tools = cp.get_messages_and_tools(chunk)
    for msg in messages:
        _put_event(run, {"event": "progress", "data": {"message": msg}}, loop)
    for tool_name in tools:
        _put_event(run, {"event": "progress", "data": {"tool_call": tool_name}}, loop)

    # Process chunk through shared state machine
    old_status = dict(run.agents)
    old_reports = dict(run.report_sections)

    cp.process_chunk(chunk)

    # Sync state from ChunkProcessor to RunState and emit SSE events
    for agent, status in cp.agent_status.items():
        if run.agents.get(agent) != status:
            _emit_agent_status(run, agent, status, loop)

    for section, content in cp.report_sections.items():
        if content and run.report_sections.get(section) != content:
            _emit_report(run, section, content, loop)

    run.current_report = cp.current_report


def _run_analysis_thread(run: RunState, loop: asyncio.AbstractEventLoop):
    """Execute the analysis in a background thread."""
    try:
        run.status = "running"
        run.started_at = datetime.datetime.now().isoformat()
        _put_event(run, {"event": "progress", "data": {"message": f"Starting analysis for {run.ticker} on {run.date}"}}, loop)

        graph = TradingAgentsGraph(
            run.selected_analysts,
            config=run.config,
            debug=False,
        )

        instrument_context = graph.resolve_instrument_context(run.ticker, run.asset_type)
        init_state = graph.propagator.create_initial_state(
            run.ticker,
            run.date,
            asset_type=run.asset_type,
            instrument_context=instrument_context,
        )
        args = graph.propagator.get_graph_args()

        trace = []
        for chunk in graph.graph.stream(init_state, **args):
            _process_chunk(run, chunk, loop)
            trace.append(chunk)

        # Merge final state
        final_state: dict[str, Any] = {}
        for chunk in trace:
            final_state.update(chunk)
        run.final_state = final_state

        # Extract signal
        run.signal = graph.process_signal(final_state.get("final_trade_decision", ""))

        # Build final report from final state
        for section in run.report_sections:
            if section in final_state and final_state[section]:
                run.report_sections[section] = final_state[section]
        _update_final_report(run)

        # Finalize: mark all agents completed
        run._chunk_processor.finalize()
        for agent in run.agents:
            run.agents[agent] = "completed"

        run.status = "completed"
        run.completed_at = datetime.datetime.now().isoformat()
        _put_event(run, {
            "event": "complete",
            "data": {
                "signal": run.signal,
                "report": run.final_report or "",
            },
        }, loop)

    except Exception as e:
        logger.exception("Analysis failed for run %s", run.run_id)
        run.status = "failed"
        run.error = str(e)
        run.completed_at = datetime.datetime.now().isoformat()
        _put_event(run, {"event": "error", "data": {"message": str(e)}}, loop)
    finally:
        _run_lock.release()


def create_run(req: AnalysisRequest, loop: asyncio.AbstractEventLoop) -> RunState | str:
    """Create a new analysis run and start it in a background thread.

    Returns the RunState on success, or an error string if the system is busy.
    """
    _prune_old_runs()

    if not _run_lock.acquire(blocking=False):
        return "busy"

    config = build_run_config({
        "llm_provider": req.llm_provider.lower() if req.llm_provider else None,
        "quick_think_llm": req.quick_think_model,
        "deep_think_llm": req.deep_think_model,
        "output_language": req.output_language,
        "backend_url": req.backend_url,
        "temperature": req.temperature,
        "max_debate_rounds": req.research_depth,
        "max_risk_discuss_rounds": req.research_depth,
        "google_thinking_level": req.google_thinking_level,
        "openai_reasoning_effort": req.openai_reasoning_effort,
        "anthropic_effort": req.anthropic_effort,
    })

    run_id = str(uuid.uuid4())
    run = RunState(
        run_id=run_id,
        ticker=req.ticker.upper(),
        date=req.date,
        asset_type=req.asset_type,
        config=config,
        selected_analysts=req.analysts,
    )
    _runs[run_id] = run

    thread = threading.Thread(
        target=_run_analysis_thread,
        args=(run, loop),
        daemon=True,
    )
    thread.start()
    return run
