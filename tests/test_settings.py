"""Tests for runtime settings export and config rebuilding."""

from __future__ import annotations

from types import SimpleNamespace

import tradingagents.default_config as default_config_module
import tradingagents.settings as settings_module


def test_build_default_config_reads_latest_settings(monkeypatch):
    fake_settings = {
        "llm": {
            "provider": "google",
            "quick_think_model": "gemini-3.5-flash",
            "deep_think_model": "gemini-3.1-pro-preview",
            "backend_url": "https://example.invalid/v1",
            "temperature": 0.2,
        },
        "analysis": {
            "output_language": "Chinese",
            "research_depth": 3,
            "max_risk_discuss_rounds": 2,
            "max_recur_limit": 150,
            "checkpoint_enabled": True,
            "market_profile": "cn_a",
            "benchmark_ticker": "QQQ",
            "memory_log_max_entries": 25,
        },
        "data": {
            "data_vendors": {
                "news_data": "cn_news",
                "macro_data": "cn_macro",
            },
            "tool_vendors": {
                "get_global_news": "alpha_vantage",
            },
            "news_article_limit": 12,
            "global_news_article_limit": 8,
            "global_news_lookback_days": 5,
            "global_news_queries": [
                "asia earnings outlook",
                "semiconductor export controls",
            ],
        },
    }
    fake_settings_module = SimpleNamespace(
        load_settings=lambda: fake_settings,
        export_api_keys_to_env=lambda **_: None,
    )
    monkeypatch.setattr(default_config_module, "_get_settings", lambda: fake_settings_module)

    config = default_config_module.build_default_config()

    assert config["llm_provider"] == "google"
    assert config["quick_think_llm"] == "gemini-3.5-flash"
    assert config["deep_think_llm"] == "gemini-3.1-pro-preview"
    assert config["backend_url"] == "https://example.invalid/v1"
    assert config["temperature"] == 0.2
    assert config["output_language"] == "Chinese"
    assert config["max_debate_rounds"] == 3
    assert config["max_risk_discuss_rounds"] == 2
    assert config["max_recur_limit"] == 150
    assert config["checkpoint_enabled"] is True
    assert config["market_profile"] == "cn_a"
    assert config["benchmark_ticker"] == "QQQ"
    assert config["memory_log_max_entries"] == 25
    assert config["data_vendors"]["news_data"] == "cn_news"
    assert config["data_vendors"]["macro_data"] == "cn_macro"
    assert config["tool_vendors"]["get_global_news"] == "alpha_vantage"
    assert config["news_article_limit"] == 12
    assert config["global_news_article_limit"] == 8
    assert config["global_news_lookback_days"] == 5
    assert config["global_news_queries"] == [
        "asia earnings outlook",
        "semiconductor export controls",
    ]


def test_export_api_keys_to_env_overwrites_current_process_when_requested(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "old-openai")
    monkeypatch.setenv("FRED_API_KEY", "old-fred")
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    settings = {
        "api_keys": {
            "openai": "new-openai",
            "FRED_API_KEY": "new-fred",
            "AWS_DEFAULT_REGION": "us-west-2",
            "OLLAMA_BASE_URL": "http://ollama.internal:11434/v1",
        }
    }

    settings_module.export_api_keys_to_env(settings, overwrite=True)

    assert settings_module.os.environ["OPENAI_API_KEY"] == "new-openai"
    assert settings_module.os.environ["FRED_API_KEY"] == "new-fred"
    assert settings_module.os.environ["AWS_DEFAULT_REGION"] == "us-west-2"
    assert (
        settings_module.os.environ["OLLAMA_BASE_URL"]
        == "http://ollama.internal:11434/v1"
    )
