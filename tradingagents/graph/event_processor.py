"""Shared constants and logic for processing streamed graph chunks.

Used by both the CLI (cli/main.py) and the web layer (web/runner.py) to
interpret the delta chunks emitted by ``graph.stream()``.
"""

from __future__ import annotations

from typing import Any

from tradingagents.default_config import DEFAULT_CONFIG

# ── Analyst identity constants ──────────────────────────────────────────────

ANALYST_ORDER: list[str] = ["market", "social", "news", "fundamentals"]

ANALYST_AGENT_NAMES: dict[str, str] = {
    "market": "Market Analyst",
    "social": "Sentiment Analyst",
    "news": "News Analyst",
    "fundamentals": "Fundamentals Analyst",
}

ANALYST_REPORT_MAP: dict[str, str] = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
}

# Fixed teams that always run (not user-selectable)
FIXED_AGENTS: dict[str, list[str]] = {
    "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
    "Trading Team": ["Trader"],
    "Risk Management": ["Aggressive Analyst", "Neutral Analyst", "Conservative Analyst"],
    "Portfolio Management": ["Portfolio Manager"],
}

# Report section mapping: section -> (analyst_key for filtering, finalizing_agent)
# analyst_key: which analyst selection controls this section (None = always included)
# finalizing_agent: which agent must be "completed" for this report to count as done
REPORT_SECTIONS: dict[str, tuple[str | None, str]] = {
    "market_report": ("market", "Market Analyst"),
    "sentiment_report": ("social", "Sentiment Analyst"),
    "news_report": ("news", "News Analyst"),
    "fundamentals_report": ("fundamentals", "Fundamentals Analyst"),
    "investment_plan": (None, "Research Manager"),
    "trader_investment_plan": (None, "Trader"),
    "final_trade_decision": (None, "Portfolio Manager"),
}

SECTION_TITLES: dict[str, str] = {
    "market_report": "Market Analysis",
    "sentiment_report": "Social Sentiment",
    "news_report": "News Analysis",
    "fundamentals_report": "Fundamentals Analysis",
    "investment_plan": "Research Team Decision",
    "trader_investment_plan": "Trading Team Plan",
    "final_trade_decision": "Portfolio Management Decision",
}

ANALYST_REPORT_SECTIONS = ["market_report", "sentiment_report", "news_report", "fundamentals_report"]


# ── Agent status helpers ────────────────────────────────────────────────────

def compute_analyst_statuses(
    selected_analysts: list[str],
    report_sections: dict[str, str | None],
) -> dict[str, str]:
    """Derive analyst statuses from accumulated report state.

    Returns a dict of agent_name -> status for the analyst team only.
    Logic:
    - Analysts with reports = completed
    - First analyst without report = in_progress
    - Remaining analysts without reports = pending
    """
    statuses: dict[str, str] = {}
    found_active = False
    for analyst_key in ANALYST_ORDER:
        if analyst_key not in selected_analysts:
            continue
        agent_name = ANALYST_AGENT_NAMES[analyst_key]
        report_key = ANALYST_REPORT_MAP[analyst_key]
        has_report = bool(report_sections.get(report_key))
        if has_report:
            statuses[agent_name] = "completed"
        elif not found_active:
            statuses[agent_name] = "in_progress"
            found_active = True
        else:
            statuses[agent_name] = "pending"
    return statuses


def build_agent_status_map(selected_analysts: list[str]) -> dict[str, str]:
    """Build the initial agent status map with all agents set to 'pending'."""
    agents: dict[str, str] = {}
    for analyst_key in selected_analysts:
        name = ANALYST_AGENT_NAMES.get(analyst_key)
        if name:
            agents[name] = "pending"
    for team_agents in FIXED_AGENTS.values():
        for agent in team_agents:
            agents[agent] = "pending"
    return agents


def build_report_sections(selected_analysts: list[str]) -> dict[str, str | None]:
    """Build the initial report sections dict for selected analysts."""
    sections: dict[str, str | None] = {}
    for section, (analyst_key, _) in REPORT_SECTIONS.items():
        if analyst_key is None or analyst_key in selected_analysts:
            sections[section] = None
    return sections


# ── Report helpers ──────────────────────────────────────────────────────────

def build_current_report(report_sections: dict[str, str | None]) -> str | None:
    """Build the most recently updated section summary for display."""
    for section in reversed(list(report_sections.keys())):
        content = report_sections[section]
        if content:
            return f"### {SECTION_TITLES.get(section, section)}\n{content}"
    return None


def build_final_report(report_sections: dict[str, str | None]) -> str | None:
    """Build the complete final report from all sections."""
    parts: list[str] = []
    if any(report_sections.get(s) for s in ANALYST_REPORT_SECTIONS):
        parts.append("## Analyst Team Reports")
        for s in ANALYST_REPORT_SECTIONS:
            if report_sections.get(s):
                title = s.replace("_", " ").title()
                parts.append(f"### {title}\n{report_sections[s]}")
    if report_sections.get("investment_plan"):
        parts.append("## Research Team Decision")
        parts.append(report_sections["investment_plan"])
    if report_sections.get("trader_investment_plan"):
        parts.append("## Trading Team Plan")
        parts.append(report_sections["trader_investment_plan"])
    if report_sections.get("final_trade_decision"):
        parts.append("## Portfolio Management Decision")
        parts.append(report_sections["final_trade_decision"])
    return "\n\n".join(parts) if parts else None


# ── Config builder ─────────────────────────────────────────────────────────

def build_run_config(overrides: dict[str, Any]) -> dict[str, Any]:
    """Build a run config by overlaying *overrides* onto DEFAULT_CONFIG.

    This is the shared config-assembly logic used by both the CLI and the web
    layer.  Callers pass only the keys they want to override; missing keys
    fall through to DEFAULT_CONFIG defaults.
    """
    config = DEFAULT_CONFIG.copy()
    for key, value in overrides.items():
        if value is not None and key in config:
            config[key] = value
    return config


# ── Chunk processing (state-machine logic) ──────────────────────────────────

class ChunkProcessor:
    """Processes streamed graph chunks and tracks agent/report state.

    Subclass or wrap this to emit events (CLI prints, SSE events, etc.).
    Call ``process_chunk(chunk)`` for each chunk from ``graph.stream()``.
    """

    def __init__(self, selected_analysts: list[str]) -> None:
        self.selected_analysts = [a.lower() for a in selected_analysts]
        self.agent_status = build_agent_status_map(self.selected_analysts)
        self.report_sections = build_report_sections(self.selected_analysts)
        self.current_report: str | None = None
        self.final_report: str | None = None
        self._processed_msg_ids: set[str] = set()

    def process_chunk(self, chunk: dict[str, Any]) -> None:
        """Process a single streamed chunk and update internal state."""
        self._process_reports(chunk)
        self._update_analyst_statuses()
        self._process_investment_debate(chunk)
        self._process_trader(chunk)
        self._process_risk_debate(chunk)
        self.current_report = build_current_report(self.report_sections)

    def get_messages_and_tools(self, chunk: dict[str, Any]) -> tuple[list[str], list[str]]:
        """Extract message texts and tool-call names from a chunk.

        Returns (messages, tool_names). Deduplicates by message id.
        """
        messages: list[str] = []
        tools: list[str] = []
        for message in chunk.get("messages", []):
            msg_id = getattr(message, "id", None)
            if msg_id is not None:
                if msg_id in self._processed_msg_ids:
                    continue
                self._processed_msg_ids.add(msg_id)
            content = getattr(message, "content", None)
            if content and str(content).strip():
                messages.append(str(content)[:200])
            if hasattr(message, "tool_calls") and message.tool_calls:
                for tc in message.tool_calls:
                    name = tc.get("name", tc.name) if isinstance(tc, dict) else getattr(tc, "name", "")
                    if name:
                        tools.append(name)
        return messages, tools

    def finalize(self) -> str | None:
        """Build the final report and mark all agents completed."""
        # Update report sections from final state if available
        self.final_report = build_final_report(self.report_sections)
        for agent in self.agent_status:
            self.agent_status[agent] = "completed"
        return self.final_report

    # ── Internal ────────────────────────────────────────────────────────

    def _process_reports(self, chunk: dict[str, Any]) -> None:
        """Capture analyst report content from chunk."""
        for analyst_key in ANALYST_ORDER:
            if analyst_key not in self.selected_analysts:
                continue
            report_key = ANALYST_REPORT_MAP[analyst_key]
            if chunk.get(report_key):
                self.report_sections[report_key] = chunk[report_key]

    def _update_analyst_statuses(self) -> None:
        """Update analyst team statuses from accumulated report state."""
        statuses = compute_analyst_statuses(self.selected_analysts, self.report_sections)
        self.agent_status.update(statuses)
        # When all analysts complete, kick off research team
        if (
            not any(s == "in_progress" for s in statuses.values())
            and self.selected_analysts
            and self.agent_status.get("Bull Researcher") == "pending"
        ):
            self.agent_status["Bull Researcher"] = "in_progress"

    def _process_investment_debate(self, chunk: dict[str, Any]) -> None:
        """Process research team debate state from chunk."""
        if not chunk.get("investment_debate_state"):
            return
        debate = chunk["investment_debate_state"]
        bull = debate.get("bull_history", "").strip()
        bear = debate.get("bear_history", "").strip()
        judge = debate.get("judge_decision", "").strip()

        if bull or bear:
            for agent in ["Bull Researcher", "Bear Researcher", "Research Manager"]:
                if self.agent_status.get(agent) == "pending":
                    self.agent_status[agent] = "in_progress"
        if bull:
            self.report_sections["investment_plan"] = f"### Bull Researcher Analysis\n{bull}"
        if bear:
            self.report_sections["investment_plan"] = f"### Bear Researcher Analysis\n{bear}"
        if judge:
            self.report_sections["investment_plan"] = f"### Research Manager Decision\n{judge}"
            for agent in ["Bull Researcher", "Bear Researcher", "Research Manager"]:
                self.agent_status[agent] = "completed"
            self.agent_status["Trader"] = "in_progress"

    def _process_trader(self, chunk: dict[str, Any]) -> None:
        """Process trader output from chunk."""
        if not chunk.get("trader_investment_plan"):
            return
        self.report_sections["trader_investment_plan"] = chunk["trader_investment_plan"]
        if self.agent_status.get("Trader") != "completed":
            self.agent_status["Trader"] = "completed"
            self.agent_status["Aggressive Analyst"] = "in_progress"

    def _process_risk_debate(self, chunk: dict[str, Any]) -> None:
        """Process risk management debate state from chunk."""
        if not chunk.get("risk_debate_state"):
            return
        risk = chunk["risk_debate_state"]
        for key, agent in [
            ("aggressive_history", "Aggressive Analyst"),
            ("conservative_history", "Conservative Analyst"),
            ("neutral_history", "Neutral Analyst"),
        ]:
            hist = risk.get(key, "").strip()
            if hist and self.agent_status.get(agent) != "completed":
                self.agent_status[agent] = "in_progress"
                self.report_sections["final_trade_decision"] = f"### {agent} Analysis\n{hist}"

        judge = risk.get("judge_decision", "").strip()
        if judge and self.agent_status.get("Portfolio Manager") != "completed":
            self.agent_status["Portfolio Manager"] = "in_progress"
            self.report_sections["final_trade_decision"] = f"### Portfolio Manager Decision\n{judge}"
            for agent in ["Aggressive Analyst", "Conservative Analyst", "Neutral Analyst", "Portfolio Manager"]:
                self.agent_status[agent] = "completed"
