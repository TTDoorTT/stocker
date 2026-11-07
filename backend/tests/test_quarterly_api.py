"""Fixture-only quarterly REST contract checks; no SEC or model calls."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_fixture_quarterly_endpoint_returns_validated_synthetic_data(tmp_path):
    settings = Settings(_env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/q.db")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/stocks/AAPL/financial-trends")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL" and data["frequency"] == "quarterly"
        assert data["mode"] == "fixtures" and data["currency"] == "USD"
        assert all(p["source"]["fixture"] for p in data["periods"])
        assert data["ttm"]["revenue"]["status"] == "available"
        assert data["ttm"]["diluted_eps"]["status"] == "unavailable"
        assert data["gaps"]
        assert client.get("/api/stocks/AAPL/financial-trends?market=CA").status_code == 422
        assert client.get("/api/stocks/TSX:RY/financial-trends").status_code == 422
        assert client.get("/api/stocks/RY.TO/financial-trends").status_code == 503


def test_canadian_live_returns_gaps_without_issuer_or_sec_requests(tmp_path):
    settings = Settings(
        _env_file=None,
        data_mode="live",
        sec_user_agent="",
        database_url=f"sqlite:///{tmp_path}/q-ca.db",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/stocks/RY.TO/financial-trends?market=CA")
        assert response.status_code == 200
        data = response.json()
        assert data["market"] == "CA" and data["currency"] == "CAD"
        assert data["periods"] == [] and data["sources"] == []
        assert data["gaps"]
        assert data["ttm"]["revenue"]["status"] == "unavailable"
