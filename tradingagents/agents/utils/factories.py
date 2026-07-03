"""Shared agent factory functions to reduce boilerplate across agent families."""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
)

# ── Shared system preamble for tool-using analysts ─────────────────────────

_ANALYST_SYSTEM_PREAMBLE = (
    "You are a helpful AI assistant, collaborating with other assistants."
    " Use the provided tools to progress towards answering the question."
    " If you are unable to fully answer, that's OK; another assistant with different tools"
    " will help where you left off. Execute what you can to make progress."
    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
    " You have access to the following tools: {tool_names}."
    " Today's date is {current_date}; treat it as 'now' for all analysis and tool-call date ranges."
    " {instrument_context}\n"
    "{system_message}"
)


# ── Tool-using analyst factory ─────────────────────────────────────────────

def create_tool_analyst(
    llm: BaseChatModel,
    tools: list,
    system_message: str,
    report_key: str,
) -> Callable:
    """Create a tool-using analyst node.

    This replaces the duplicated boilerplate in market_analyst.py,
    fundamentals_analyst.py, and news_analyst.py.

    Args:
        llm: The language model to use.
        tools: List of tool functions to bind to the LLM.
        system_message: Domain-specific instructions for this analyst.
        report_key: State key for the output report (e.g., "market_report").
    """

    def analyst_node(state: dict[str, Any]) -> dict:
        current_date = state["trade_date"]
        instrument_context = get_instrument_context_from_state(state)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", _ANALYST_SYSTEM_PREAMBLE),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join(t.name for t in tools))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = result.content if len(result.tool_calls) == 0 else ""

        return {
            "messages": [result],
            report_key: report,
        }

    return analyst_node


# ── Research debate agent factory ──────────────────────────────────────────

def create_research_debate_agent(
    llm: BaseChatModel,
    prompt_builder: Callable[[dict[str, Any], str, str, str, str, str], str],
    owned_history_key: str,
    speaker_label: str,
) -> Callable:
    """Create a research debate node (Bull or Bear Researcher).

    Args:
        llm: The language model to use.
        prompt_builder: Function that builds the prompt string. Called as:
            prompt_builder(state, instrument_context, market_report,
                          sentiment_report, news_report, fundamentals_report)
        owned_history_key: Which history key this agent owns (e.g., "bull_history").
        speaker_label: Label prepended to arguments (e.g., "Bull Analyst").
    """

    def debate_node(state: dict[str, Any]) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        owned_history = investment_debate_state.get(owned_history_key, "")
        current_response = investment_debate_state.get("current_response", "")

        instrument_context = get_instrument_context_from_state(state)

        prompt = prompt_builder(
            state,
            instrument_context,
            state["market_report"],
            state["sentiment_report"],
            state["news_report"],
            state["fundamentals_report"],
        )

        response = llm.invoke(prompt)
        argument = f"{speaker_label}: {response.content}"

        new_state = {
            "history": history + "\n" + argument,
            owned_history_key: owned_history + "\n" + argument,
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }
        # Preserve the other speaker's history
        for key in ("bull_history", "bear_history"):
            if key != owned_history_key:
                new_state[key] = investment_debate_state.get(key, "")

        return {"investment_debate_state": new_state}

    return debate_node


# ── Risk debate agent factory ──────────────────────────────────────────────

def create_risk_debate_agent(
    llm: BaseChatModel,
    prompt_builder: Callable[[dict[str, Any], str, str, str, str, str, str], str],
    owned_history_key: str,
    speaker_label: str,
    current_response_key: str,
) -> Callable:
    """Create a risk debate node (Aggressive, Conservative, or Neutral Analyst).

    Args:
        llm: The language model to use.
        prompt_builder: Function that builds the prompt string. Called as:
            prompt_builder(state, instrument_context, market_report,
                          sentiment_report, news_report, fundamentals_report,
                          trader_decision)
        owned_history_key: Which history key this agent owns (e.g., "aggressive_history").
        speaker_label: Label prepended to arguments (e.g., "Aggressive Analyst").
        current_response_key: Key for this agent's current response
            (e.g., "current_aggressive_response").
    """

    def debate_node(state: dict[str, Any]) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        owned_history = risk_debate_state.get(owned_history_key, "")

        instrument_context = get_instrument_context_from_state(state)
        trader_decision = state["trader_investment_plan"]

        prompt = prompt_builder(
            state,
            instrument_context,
            state["market_report"],
            state["sentiment_report"],
            state["news_report"],
            state["fundamentals_report"],
            trader_decision,
        )

        response = llm.invoke(prompt)
        argument = f"{speaker_label}: {response.content}"

        new_state = {
            "history": history + "\n" + argument,
            owned_history_key: owned_history + "\n" + argument,
            "latest_speaker": speaker_label.split()[0],  # "Aggressive", "Conservative", "Neutral"
            current_response_key: argument,
            "count": risk_debate_state["count"] + 1,
        }
        # Preserve all history keys and current response keys
        for key in ("aggressive_history", "conservative_history", "neutral_history"):
            if key != owned_history_key:
                new_state[key] = risk_debate_state.get(key, "")
        for key in ("current_aggressive_response", "current_conservative_response", "current_neutral_response"):
            if key != current_response_key:
                new_state[key] = risk_debate_state.get(key, "")

        return {"risk_debate_state": new_state}

    return debate_node
