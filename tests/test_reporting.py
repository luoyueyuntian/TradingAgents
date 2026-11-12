"""Report parity: the shared writer produces the report tree for the CLI and the
programmatic API alike (#1037)."""

from types import SimpleNamespace

import pytest

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.reporting import write_report_tree


def _state():
    return {
        "market_report": "MKT",
        "news_report": "NEWS",
        "investment_debate_state": {"judge_decision": "RM PLAN"},
        "trader_investment_plan": "TRADE",
        "risk_debate_state": {"judge_decision": "PM DECISION"},
    }


@pytest.mark.unit
def test_write_report_tree_creates_files(tmp_path):
    out = write_report_tree(_state(), "AAPL", tmp_path)
    assert out.name == "complete_report.md"
    assert (tmp_path / "1_analysts" / "market.md").read_text() == "MKT"
    assert (tmp_path / "1_analysts" / "news.md").read_text() == "NEWS"
    assert (tmp_path / "2_research" / "manager.md").read_text() == "RM PLAN"
    assert (tmp_path / "3_trading" / "trader.md").read_text() == "TRADE"
    assert (tmp_path / "5_portfolio" / "decision.md").read_text() == "PM DECISION"
    complete = out.read_text()
    assert "Trading Analysis Report: AAPL" in complete
    assert "MKT" in complete and "PM DECISION" in complete


@pytest.mark.unit
def test_save_reports_explicit_path(tmp_path):
    # Unbound: with an explicit save_path, the method doesn't touch self/config.
    out = TradingAgentsGraph.save_reports(None, _state(), "AAPL", save_path=tmp_path)
    assert (tmp_path / "complete_report.md").exists()
    assert out == tmp_path / "complete_report.md"


@pytest.mark.unit
def test_save_reports_defaults_under_results_dir(tmp_path):
    mock_self = SimpleNamespace(config={"results_dir": str(tmp_path)})
    out = TradingAgentsGraph.save_reports(mock_self, _state(), "AAPL")
    assert out.exists()
    assert out.parent.parent.name == "reports"  # results_dir/reports/AAPL_<stamp>/...
    assert out.parent.name.startswith("AAPL_")


@pytest.mark.unit
def test_log_state_persists_extended_process_fields(tmp_path):
    mock_self = SimpleNamespace(
        log_states_dict={},
        ticker="AAPL",
        config={"results_dir": str(tmp_path)},
        last_state_log_path=None,
    )
    state = {
        "company_of_interest": "AAPL",
        "asset_type": "stock",
        "trade_date": "2026-01-15",
        "instrument_context": "Resolved identity for AAPL",
        "past_context": "Past lessons for AAPL",
        "market_report": "MKT",
        "sentiment_report": "SENT",
        "news_report": "NEWS",
        "fundamentals_report": "FUND",
        "investment_debate_state": {
            "bull_history": "Bull",
            "bear_history": "Bear",
            "history": "Bull vs Bear",
            "current_response": "Bear",
            "judge_decision": "Hold",
            "count": 4,
        },
        "trader_investment_plan": "Trade plan",
        "risk_debate_state": {
            "aggressive_history": "Aggressive",
            "conservative_history": "Conservative",
            "neutral_history": "Neutral",
            "history": "Risk history",
            "latest_speaker": "Neutral",
            "current_aggressive_response": "Aggressive response",
            "current_conservative_response": "Conservative response",
            "current_neutral_response": "Neutral response",
            "judge_decision": "Buy",
            "count": 6,
        },
        "investment_plan": "Plan",
        "final_trade_decision": "Buy",
    }

    TradingAgentsGraph._log_state(mock_self, "2026-01-15", state)

    payload = __import__("json").loads(mock_self.last_state_log_path.read_text(encoding="utf-8"))
    assert payload["instrument_context"] == "Resolved identity for AAPL"
    assert payload["past_context"] == "Past lessons for AAPL"
    assert payload["investment_debate_state"]["count"] == 4
    assert payload["risk_debate_state"]["latest_speaker"] == "Neutral"
    assert payload["risk_debate_state"]["current_neutral_response"] == "Neutral response"
    assert payload["risk_debate_state"]["count"] == 6
