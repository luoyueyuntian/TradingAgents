from __future__ import annotations

from fastapi.testclient import TestClient

from web import routes as web_routes
from web.app import app


def test_stock_markets_route_lists_supported_markets():
    client = TestClient(app)

    response = client.get("/api/stocks/markets")

    assert response.status_code == 200
    payload = response.json()
    assert [item["value"] for item in payload] == ["us", "hk", "cn_a"]


def test_stocks_route_searches_selected_market(monkeypatch):
    client = TestClient(app)
    captured: dict[str, object] = {}

    def fake_search_stock_catalog(market: str, query: str = "", limit: int = 100, refresh_if_stale: bool = True):
        captured.update({
            "market": market,
            "query": query,
            "limit": limit,
            "refresh_if_stale": refresh_if_stale,
        })
        return [
            web_routes.StockCatalogItem(
                market="hk",
                symbol="0700.HK",
                name="腾讯控股",
                exchange="HKEX",
            )
        ]

    monkeypatch.setattr(web_routes, "search_stock_catalog", fake_search_stock_catalog)
    monkeypatch.setattr(web_routes, "stock_catalog_needs_refresh", lambda: False)

    response = client.get("/api/stocks", params={"market": "hk", "q": "腾讯", "limit": 25})

    assert response.status_code == 200
    assert captured == {"market": "hk", "query": "腾讯", "limit": 25, "refresh_if_stale": False}
    assert response.json() == [
        {
            "market": "hk",
            "symbol": "0700.HK",
            "name": "腾讯控股",
            "exchange": "HKEX",
            "label": "0700.HK · 腾讯控股 · HKEX",
        }
    ]


def test_stock_refresh_route_forces_refresh(monkeypatch):
    client = TestClient(app)
    captured: dict[str, object] = {}

    class FakeSnapshot:
        updated_on = "2026-06-30"
        counts = {"us": 2, "hk": 1, "cn_a": 1}
        errors = {}
        refreshed = True

    def fake_refresh_stock_catalog(force: bool = False):
        captured["force"] = force
        return FakeSnapshot()

    monkeypatch.setattr(web_routes, "refresh_stock_catalog", fake_refresh_stock_catalog)

    response = client.post("/api/stocks/refresh", json={"force": True})

    assert response.status_code == 200
    assert captured == {"force": True}
    assert response.json() == {
        "updated_on": "2026-06-30",
        "refreshed": True,
        "counts": {"us": 2, "hk": 1, "cn_a": 1},
        "errors": {},
    }
