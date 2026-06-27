"""China news adapter tests."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.mark.unit
def test_china_stock_news_filters_by_window(monkeypatch):
    from tradingagents.dataflows import china_news

    news = pd.DataFrame(
        [
            {
                "新闻标题": "贵州茅台分红公告",
                "新闻内容": "公司披露年度分红方案。",
                "发布时间": "2026-06-26 09:17:00",
                "文章来源": "21世纪经济报道",
                "新闻链接": "https://example.com/a",
            },
            {
                "新闻标题": "较早新闻",
                "新闻内容": "窗口外数据。",
                "发布时间": "2026-05-01 09:17:00",
                "文章来源": "证券时报网",
                "新闻链接": "https://example.com/b",
            },
        ]
    )

    class FakeAK:
        @staticmethod
        def stock_news_em(symbol: str):
            assert symbol == "600519"
            return news

    monkeypatch.setattr(china_news, "_load_akshare", lambda: FakeAK)
    out = china_news.get_news_china("600519.SS", "2026-06-20", "2026-06-27")

    assert "## 600519.SS China Market News" in out
    assert "贵州茅台分红公告" in out
    assert "较早新闻" not in out


@pytest.mark.unit
def test_china_stock_news_skips_multi_stock_roundups(monkeypatch):
    from tradingagents.dataflows import china_news

    news = pd.DataFrame(
        [
            {
                "新闻标题": "103股获杠杆资金净买入超亿元",
                "新闻内容": "000657 中钨高新 300346 南大光电 688256 寒武纪 600519 贵州茅台 601318 中国平安",
                "发布时间": "2026-06-26 09:24:00",
                "文章来源": "证券时报网",
                "新闻链接": "https://example.com/roundup",
            },
            {
                "新闻标题": "贵州茅台实施年度分红",
                "新闻内容": "贵州茅台600519.SH 公布年度分红方案。",
                "发布时间": "2026-06-26 09:17:00",
                "文章来源": "21世纪经济报道",
                "新闻链接": "https://example.com/dividend",
            },
        ]
    )

    class FakeAK:
        @staticmethod
        def stock_news_em(symbol: str):
            return news

    monkeypatch.setattr(china_news, "_load_akshare", lambda: FakeAK)
    out = china_news.get_news_china("600519.SS", "2026-06-20", "2026-06-27")

    assert "贵州茅台实施年度分红" in out
    assert "103股获杠杆资金净买入超亿元" not in out


@pytest.mark.unit
def test_china_global_news_filters_by_window(monkeypatch):
    from tradingagents.dataflows import china_news

    news = pd.DataFrame(
        [
            {
                "title": "央行公开市场操作维持流动性充裕",
                "pubTime": "2026-06-25 08:00:00",
                "summary": "公开市场操作保持平稳。",
                "url": "https://example.com/macro",
            },
            {
                "title": "窗口外宏观新闻",
                "pubTime": "2026-05-01 08:00:00",
                "summary": "过早数据。",
                "url": "https://example.com/old",
            },
        ]
    )

    class FakeAK:
        @staticmethod
        def stock_news_main_cx():
            return news

    monkeypatch.setattr(china_news, "_load_akshare", lambda: FakeAK)
    out = china_news.get_global_news_china("2026-06-27", 7, 10)

    assert "## China Market Policy and Macro News" in out
    assert "央行公开市场操作维持流动性充裕" in out
    assert "窗口外宏观新闻" not in out


@pytest.mark.unit
def test_china_insider_placeholder_is_explicit():
    from tradingagents.dataflows.china_news import get_insider_transactions_china

    out = get_insider_transactions_china("600519.SS")
    assert "DATA_UNAVAILABLE" in out
    assert "shareholder pledge" in out
