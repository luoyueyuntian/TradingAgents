from tradingagents.agents.utils.agent_utils import get_language_instruction
from tradingagents.agents.utils.factories import create_risk_debate_agent


def _build_neutral_prompt(state, instrument_context, market_report, sentiment_report, news_report, fundamentals_report, trader_decision):
    risk_debate_state = state["risk_debate_state"]
    history = risk_debate_state.get("history", "")
    current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
    current_conservative_response = risk_debate_state.get("current_conservative_response", "")

    return f"""As the Neutral Risk Analyst, your role is to provide a balanced perspective, weighing both the potential benefits and risks of the trader's decision or plan. You prioritize a well-rounded approach, evaluating the upsides and downsides while factoring in broader market trends, potential economic shifts, and diversification strategies.Here is the trader's decision:

{trader_decision}

Your task is to challenge both the Aggressive and Conservative Analysts, pointing out where each perspective may be overly optimistic or overly cautious. Use insights from the following data sources to support a moderate, sustainable strategy to adjust the trader's decision:

{instrument_context}
Market Research Report: {market_report}
Social Media Sentiment Report: {sentiment_report}
Latest World Affairs Report: {news_report}
Company Fundamentals Report: {fundamentals_report}
Here is the current conversation history: {history} Here is the last response from the aggressive analyst: {current_aggressive_response} Here is the last response from the conservative analyst: {current_conservative_response}. If there are no responses from the other viewpoints yet, present your own argument based on the available data.

Engage actively by analyzing both sides critically, addressing weaknesses in the aggressive and conservative arguments to advocate for a more balanced approach. Challenge each of their points to illustrate why a moderate risk strategy might offer the best of both worlds, providing growth potential while safeguarding against extreme volatility. Focus on debating rather than simply presenting data, aiming to show that a balanced view can lead to the most reliable outcomes. Output conversationally as if you are speaking without any special formatting.""" + get_language_instruction()


def create_neutral_debator(llm):
    return create_risk_debate_agent(
        llm=llm,
        prompt_builder=_build_neutral_prompt,
        owned_history_key="neutral_history",
        speaker_label="Neutral Analyst",
        current_response_key="current_neutral_response",
    )
