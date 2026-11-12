"""Report parity: the shared writer produces the report tree for the CLI and the
programmatic API alike (#1037)."""

import re
from types import SimpleNamespace

import pytest

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.reporting import write_report_tree


def _state():
    return {
        "market_report": "MKT",
        "news_report": "NEWS",
        "investment_debate_state": {"bull_history": "BULL"},
        "investment_plan": "RM PLAN",
        "trader_investment_plan": "TRADE",
        "risk_debate_state": {"neutral_history": "NEUTRAL"},
        "final_trade_decision": "PM DECISION",
    }


SETTINGS = {"version": "0.5.2", "llm_provider": "openai", "deep_think_llm": "gpt-6-sol",
            "quick_think_llm": "gpt-6-luna", "analysts": ["market", "news"], "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 2, "data_vendors": {"core_stock_apis": "yfinance"}}


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
    graph = SimpleNamespace(run_settings=lambda: SETTINGS)
    out = TradingAgentsGraph.save_reports(graph, _state(), "AAPL", save_path=tmp_path)
    assert (tmp_path / "complete_report.md").exists()
    assert out == tmp_path / "complete_report.md"


@pytest.mark.unit
@pytest.mark.parametrize("empty_value", [None, ""])
def test_save_reports_replaces_previous_run_sections(tmp_path, empty_value):
    graph = SimpleNamespace(run_settings=lambda: SETTINGS)
    first = dict(_state(), trade_date="2026-09-22")
    TradingAgentsGraph.save_reports(graph, first, "AAPL", save_path=tmp_path)
    (tmp_path / "notes.md").write_text("User notes", encoding="utf-8")
    (tmp_path / "1_analysts" / "notes.md").write_text("Analyst notes", encoding="utf-8")

    second = {
        "trade_date": "2026-09-23",
        "market_report": "NEW MARKET",
        "news_report": empty_value,
        "investment_debate_state": {"bull_history": empty_value},
    }
    out = TradingAgentsGraph.save_reports(graph, second, "AAPL", save_path=tmp_path)

    assert (tmp_path / "1_analysts" / "market.md").read_text() == "NEW MARKET"
    for filename in (
        "1_analysts/news.md", "2_research/bull.md", "2_research/manager.md",
        "3_trading/trader.md", "4_risk/neutral.md", "5_portfolio/decision.md",
    ):
        assert not (tmp_path / filename).exists()
    assert (tmp_path / "notes.md").read_text() == "User notes"
    assert (tmp_path / "1_analysts" / "notes.md").read_text() == "Analyst notes"
    assert "NEW MARKET" in out.read_text(encoding="utf-8")
    assert "NEWS" not in out.read_text(encoding="utf-8")
    assert "NEWS" not in (tmp_path / "complete_report.html").read_text(encoding="utf-8")


@pytest.mark.unit
def test_empty_report_removes_previous_sections_and_disabled_html(tmp_path):
    write_report_tree(_state(), "AAPL", tmp_path)
    out = write_report_tree({}, "AAPL", tmp_path, html=False)

    assert list(tmp_path.rglob("*.md")) == [out]
    assert not (tmp_path / "complete_report.html").exists()
    assert "Trading Analysis Report: AAPL" in out.read_text()


@pytest.mark.unit
def test_save_reports_defaults_under_results_dir(tmp_path):
    graph = object.__new__(TradingAgentsGraph)
    graph.config = {"results_dir": str(tmp_path)}
    graph.run_settings = lambda: SETTINGS
    out = graph.save_reports(_state(), "AAPL")
    assert out.exists()
    assert out.parent.parent.name == "reports"  # results_dir/reports/AAPL_<stamp>/...
    assert out.parent.name.startswith("AAPL_")



@pytest.mark.unit
def test_the_report_names_the_analysis_date_and_what_produced_it(tmp_path):
    state = dict(_state(), trade_date="2026-09-23")

    header = write_report_tree(state, "NVDA", tmp_path, settings=SETTINGS).read_text().split("## ")[0]

    assert "Analysis date: 2026-09-23" in header
    assert "TradingAgents 0.5.2" in header
    assert "openai, deep gpt-6-sol, quick gpt-6-luna" in header
    assert "Analysts: market, news" in header
    assert "research debate rounds 1, risk debate rounds 2" in header
    assert "core_stock_apis yfinance" in header


@pytest.mark.unit
def test_run_settings_record_the_run_without_endpoints_or_paths():
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    graph = object.__new__(TradingAgentsGraph)
    graph.selected_analysts = ("market", "news")
    graph.config = {"llm_provider": "openai", "deep_think_llm": "gpt-6-sol", "quick_think_llm": "gpt-6-luna",
                    "max_debate_rounds": 1, "max_risk_discuss_rounds": 1, "output_language": "English",
                    "data_vendors": {"core_stock_apis": "yfinance"}, "tool_vendors": {},
                    "backend_url": "https://user:secret@relay.example/v1", "results_dir": "/home/me/results"}

    settings = graph.run_settings()

    assert settings["analysts"] == ["market", "news"]
    assert settings["deep_think_llm"] == "gpt-6-sol"
    assert "secret" not in str(settings) and "/home/me" not in str(settings)


@pytest.mark.unit
def test_a_partial_settings_dict_still_writes_the_report(tmp_path):
    out = write_report_tree(_state(), "AAPL", tmp_path, settings={"llm_provider": "openai"})
    assert "openai" in out.read_text()


@pytest.mark.unit
def test_run_settings_name_the_version_of_the_running_code():
    import tradingagents
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    graph = object.__new__(TradingAgentsGraph)
    graph.selected_analysts, graph.config = ("market",), {}
    assert graph.run_settings()["version"] == tradingagents.__version__


@pytest.mark.unit
@pytest.mark.parametrize("decision, rating", [
    ("**Rating**: Overweight\n\nAdd on weakness.", "Overweight"),
    ("Add on weakness.", "REVIEW"),           # no readable rating is said, not left out
])
def test_the_report_header_names_the_rating(tmp_path, decision, rating):
    state = dict(_state(), final_trade_decision=decision)

    header = write_report_tree(state, "NVDA", tmp_path, settings=SETTINGS).read_text().split("## ")[0]

    assert f"- Rating: {rating}" in header


@pytest.mark.unit
def test_the_header_names_the_analysts_as_users_select_them(tmp_path):
    settings = {**SETTINGS, "analysts": ["market", "social", "news"]}

    write_report_tree(_state(), "NVDA", tmp_path, settings=settings, html=True)

    markdown = (tmp_path / "complete_report.md").read_text(encoding="utf-8")
    assert "market, sentiment, news" in markdown and "social" not in markdown
    page = (tmp_path / "complete_report.html").read_text(encoding="utf-8")
    fields = re.findall(r'<span class="field">([^<]*)</span>', page)
    assert {"market", "sentiment", "news"} <= set(fields) and "social" not in page


@pytest.mark.unit
def test_log_state_persists_extended_process_fields(tmp_path):
    mock_self = SimpleNamespace(
        log_states_dict={},
        ticker="AAPL",
        config={"results_dir": str(tmp_path)},
        selected_analysts=("market",),
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
