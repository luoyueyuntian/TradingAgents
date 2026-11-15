from __future__ import annotations

from datetime import date

from tradingagents.service.stock_catalog import (
    StockCatalogItem,
    refresh_stock_catalog,
    search_stock_catalog,
)


def test_refresh_stock_catalog_filters_regular_company_stocks(tmp_path):
    cache_path = tmp_path / "stock-catalog.json"
    fetchers = {
        "us": lambda: [
            StockCatalogItem(market="us", symbol="AAPL", name="Apple Inc. Common Stock", exchange="NASDAQ"),
            StockCatalogItem(market="us", symbol="SPY", name="SPDR S&P 500 ETF Trust", exchange="NYSE Arca"),
        ],
        "hk": lambda: [
            StockCatalogItem(market="hk", symbol="0700.HK", name="腾讯控股", exchange="HKEX"),
            StockCatalogItem(market="hk", symbol="2800.HK", name="盈富基金", exchange="HKEX"),
        ],
        "cn_a": lambda: [
            StockCatalogItem(market="cn_a", symbol="600519.SS", name="贵州茅台", exchange="SSE"),
            StockCatalogItem(market="cn_a", symbol="510300.SS", name="沪深300ETF", exchange="SSE"),
        ],
    }

    snapshot = refresh_stock_catalog(
        cache_path=cache_path,
        fetchers=fetchers,
        force=True,
        today=date(2026, 6, 30),
    )

    assert snapshot.updated_on == "2026-06-30"
    assert snapshot.counts == {"us": 1, "hk": 1, "cn_a": 1}
    assert [item.symbol for item in snapshot.markets["us"]] == ["AAPL"]
    assert [item.symbol for item in snapshot.markets["hk"]] == ["0700.HK"]
    assert [item.symbol for item in snapshot.markets["cn_a"]] == ["600519.SS"]


def test_refresh_stock_catalog_keeps_company_names_containing_unit(tmp_path):
    cache_path = tmp_path / "stock-catalog.json"

    snapshot = refresh_stock_catalog(
        cache_path=cache_path,
        fetchers={
            "us": lambda: [
                StockCatalogItem("us", "UNH", "UnitedHealth Group Incorporated", "NYSE"),
                StockCatalogItem("us", "SPY", "SPDR S&P 500 ETF Trust", "NYSE Arca"),
            ],
            "hk": lambda: [],
            "cn_a": lambda: [],
        },
        force=True,
        today=date(2026, 6, 30),
    )

    assert [item.symbol for item in snapshot.markets["us"]] == ["UNH"]


def test_search_stock_catalog_can_skip_stale_refresh(tmp_path):
    cache_path = tmp_path / "stock-catalog.json"
    refresh_stock_catalog(
        cache_path=cache_path,
        fetchers={
            "us": lambda: [StockCatalogItem("us", "AAPL", "Apple Inc. Common Stock", "NASDAQ")],
            "hk": lambda: [],
            "cn_a": lambda: [],
        },
        force=True,
        today=date(2026, 6, 29),
    )

    def _fail_fetch():
        raise AssertionError("search should not refresh synchronously")

    results = search_stock_catalog(
        "us",
        query="apple",
        cache_path=cache_path,
        fetchers={"us": _fail_fetch, "hk": _fail_fetch, "cn_a": _fail_fetch},
        today=date(2026, 6, 30),
        refresh_if_stale=False,
    )

    assert [item.symbol for item in results] == ["AAPL"]


def test_search_stock_catalog_uses_same_day_cache_until_forced(tmp_path):
    cache_path = tmp_path / "stock-catalog.json"
    calls = {"us": 0, "hk": 0, "cn_a": 0}

    def make_fetcher(market: str, item: StockCatalogItem):
        def _fetch():
            calls[market] += 1
            return [item]

        return _fetch

    first_fetchers = {
        "us": make_fetcher("us", StockCatalogItem("us", "AAPL", "Apple Inc. Common Stock", "NASDAQ")),
        "hk": make_fetcher("hk", StockCatalogItem("hk", "0700.HK", "腾讯控股", "HKEX")),
        "cn_a": make_fetcher("cn_a", StockCatalogItem("cn_a", "600519.SS", "贵州茅台", "SSE")),
    }

    first = search_stock_catalog(
        "us",
        query="apple",
        cache_path=cache_path,
        fetchers=first_fetchers,
        today=date(2026, 6, 30),
    )
    second = search_stock_catalog(
        "hk",
        query="腾讯",
        cache_path=cache_path,
        fetchers={
            "us": make_fetcher("us", StockCatalogItem("us", "MSFT", "Microsoft Corporation", "NASDAQ")),
            "hk": make_fetcher("hk", StockCatalogItem("hk", "9988.HK", "阿里巴巴", "HKEX")),
            "cn_a": make_fetcher("cn_a", StockCatalogItem("cn_a", "000001.SZ", "平安银行", "SZSE")),
        },
        today=date(2026, 6, 30),
    )

    assert [item.symbol for item in first] == ["AAPL"]
    assert [item.symbol for item in second] == ["0700.HK"]
    assert calls == {"us": 1, "hk": 1, "cn_a": 1}

    refreshed = refresh_stock_catalog(
        cache_path=cache_path,
        fetchers={
            "us": make_fetcher("us", StockCatalogItem("us", "MSFT", "Microsoft Corporation", "NASDAQ")),
            "hk": make_fetcher("hk", StockCatalogItem("hk", "9988.HK", "阿里巴巴", "HKEX")),
            "cn_a": make_fetcher("cn_a", StockCatalogItem("cn_a", "000001.SZ", "平安银行", "SZSE")),
        },
        force=True,
        today=date(2026, 6, 30),
    )

    assert [item.symbol for item in refreshed.markets["us"]] == ["MSFT"]
    assert calls == {"us": 2, "hk": 2, "cn_a": 2}


def test_hk_catalog_uses_official_list_and_filters_non_main_board(monkeypatch):
    import pandas as pd
    import requests

    from tradingagents.service.stock_catalog import fetch_hk_company_stocks
    class Response:
        content = b'xlsx'
        def raise_for_status(self): pass
    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: Response())
    monkeypatch.setattr(pd, 'read_excel', lambda *args, **kwargs: pd.DataFrame([
        {'股份代號':'00700','股份名稱':'騰訊控股','分類':'股本','次分類':'股本證券(主板)'},
        {'股份代號':'09988','股份名稱':'阿里巴巴－Ｗ','分類':'股本','次分類':'股本證券(主板)'},
        {'股份代號':'02800','股份名稱':'盈富基金','分類':'交易所買賣產品','次分類':'基金'},
        {'股份代號':'08001','股份名稱':'創業板公司','分類':'股本','次分類':'股本證券(GEM)'},
    ]))
    assert [s.symbol for s in fetch_hk_company_stocks()] == ['0700.HK','9988.HK']


def test_empty_refresh_preserves_last_good_market(tmp_path):
    path = tmp_path/'catalog.json'
    fetchers = {'us':lambda:[StockCatalogItem('us','AAPL','Apple','US')], 'hk':lambda:[StockCatalogItem('hk','0700.HK','腾讯控股','HKEX')], 'cn_a':lambda:[]}
    refresh_stock_catalog(cache_path=path,fetchers=fetchers,force=True)
    fetchers['hk']=lambda:[]
    snapshot=refresh_stock_catalog(cache_path=path,fetchers=fetchers,force=True)
    assert snapshot.counts['hk']==1
    assert 'hk' in snapshot.errors


def test_incomplete_today_cache_retries_missing_market_after_backoff(tmp_path):
    import os
    import time

    from tradingagents.service.stock_catalog import stock_catalog_needs_refresh
    path=tmp_path/'catalog.json'
    fetchers={'us':lambda:[StockCatalogItem('us','AAPL','Apple','US')], 'hk':lambda:[], 'cn_a':lambda:[StockCatalogItem('cn_a','600519.SS','贵州茅台','SSE')]}
    refresh_stock_catalog(cache_path=path,fetchers=fetchers,force=True)
    assert not stock_catalog_needs_refresh(cache_path=path)
    os.utime(path,(time.time()-301,time.time()-301))
    assert stock_catalog_needs_refresh(cache_path=path)
    fetchers['hk']=lambda:[StockCatalogItem('hk','0700.HK','腾讯控股','HKEX')]
    fetchers['us']=lambda:(_ for _ in ()).throw(AssertionError('should keep successful market'))
    snapshot=refresh_stock_catalog(cache_path=path,fetchers=fetchers)
    assert snapshot.counts=={'us':1,'hk':1,'cn_a':1}
