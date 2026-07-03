"""China-mode prompting and social-source behavior."""

from __future__ import annotations

import pytest

import tradingagents.dataflows.config as config_module
from tradingagents.dataflows.config import initialize_config


def _reset_config():
    initialize_config()


@pytest.mark.unit
def test_market_prompt_guidance_mentions_a_share_microstructure():
    _reset_config()
    config_module.set_config({"market_profile": "cn_a"})

    from tradingagents.agents.utils.agent_utils import get_market_specific_instruction

    text = get_market_specific_instruction("market")
    assert "T+1" in text
    assert "price limits" in text


@pytest.mark.unit
def test_news_prompt_guidance_mentions_policy_and_disclosure():
    _reset_config()
    config_module.set_config({"market_profile": "cn_a"})

    from tradingagents.agents.utils.agent_utils import get_market_specific_instruction

    text = get_market_specific_instruction("news")
    assert "policy" in text
    assert "disclosure" in text
    assert "northbound" in text


@pytest.mark.unit
def test_news_analyst_tool_guidance_switches_for_china_mode():
    _reset_config()
    config_module.set_config({"market_profile": "cn_a"})

    from tradingagents.agents.analysts.news_analyst import _build_news_tool_guidance

    text = _build_news_tool_guidance("company")
    assert "China macro" in text
    assert "northbound flow" in text
    assert "Fed rate cut" not in text


@pytest.mark.unit
def test_fundamentals_prompt_guidance_mentions_china_specific_risks():
    _reset_config()
    config_module.set_config({"market_profile": "cn_a"})

    from tradingagents.agents.utils.agent_utils import get_market_specific_instruction

    text = get_market_specific_instruction("fundamentals")
    assert "shareholder pledge" in text
    assert "government subsidy" in text
    assert "receivables" in text


@pytest.mark.unit
def test_stocktwits_disabled_in_china_mode():
    _reset_config()
    config_module.set_config({"market_profile": "cn_a"})

    from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages

    assert fetch_stocktwits_messages("600519.SS") == "<stocktwits disabled for cn_a market profile>"


@pytest.mark.unit
def test_reddit_disabled_in_china_mode():
    _reset_config()
    config_module.set_config({"market_profile": "cn_a"})

    from tradingagents.dataflows.reddit import fetch_reddit_posts

    assert fetch_reddit_posts("600519.SS") == "<reddit disabled for cn_a market profile>"


@pytest.mark.unit
def test_sentiment_message_includes_china_market_signals():
    from tradingagents.agents.analysts.sentiment_analyst import _build_system_message

    text = _build_system_message(
        ticker="600519.SS",
        start_date="2026-06-20",
        end_date="2026-06-27",
        news_block="news",
        stocktwits_block="<stocktwits disabled for cn_a market profile>",
        reddit_block="<reddit disabled for cn_a market profile>",
        market_signal_block="northbound flow data",
        china_mode=True,
    )

    assert "China market-structure signals" in text
    assert "northbound flow data" in text
    assert "overseas retail social platforms are secondary" in text
