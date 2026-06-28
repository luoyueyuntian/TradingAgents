"""China market profile defaults and runtime routing behavior."""

from __future__ import annotations

import pytest

import tradingagents.dataflows.config as config_module
from tradingagents.dataflows import interface
from tradingagents.dataflows.config import initialize_config


def _reset_config():
    initialize_config()


@pytest.mark.unit
def test_china_profile_vendor_defaults():
    from tradingagents.dataflows.market_profiles import get_profile_data_vendors

    vendors = get_profile_data_vendors("cn_a")
    assert vendors["news_data"] == "cn_news"
    assert vendors["macro_data"] == "cn_macro"
    assert vendors["prediction_markets"] == "cn_market_signals"


@pytest.mark.unit
def test_get_vendor_uses_china_profile_defaults():
    _reset_config()
    config_module.set_config({"market_profile": "cn_a"})

    assert interface.get_vendor("news_data", "get_news") == "cn_news"
    assert interface.get_vendor("macro_data", "get_macro_indicators") == "cn_macro"
    assert interface.get_vendor("prediction_markets", "get_prediction_markets") == "cn_market_signals"


@pytest.mark.unit
def test_tool_vendor_override_beats_china_profile_default():
    _reset_config()
    config_module.set_config(
        {
            "market_profile": "cn_a",
            "tool_vendors": {
                "get_macro_indicators": "fred",
            },
        }
    )

    assert interface.get_vendor("macro_data", "get_macro_indicators") == "fred"


@pytest.mark.unit
def test_default_sentinel_still_uses_china_profile_defaults():
    _reset_config()
    config_module.set_config(
        {
            "market_profile": "cn_a",
            "data_vendors": {
                "news_data": "default",
                "macro_data": "default",
                "prediction_markets": "default",
            },
        }
    )

    assert interface.get_vendor("news_data", "get_news") == "cn_news"
    assert interface.get_vendor("macro_data", "get_macro_indicators") == "cn_macro"
    assert interface.get_vendor("prediction_markets", "get_prediction_markets") == "cn_market_signals"
