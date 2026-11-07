"""Read-only earnings endpoint contract, fixture and Canadian availability rules."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_earnings_fixture_endpoint_and_symbol_validation(tmp_path):
    settings = Settings(
        _env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/earnings.db"
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/stocks/AAPL/earnings")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL" and data["mode"] == "fixtures"
        assert data["upcoming"]["date_status"] == "estimated"
        assert data["history"] and data["sources"][0]["fixture"] is True
        assert "SYNTHETIC" in " ".join(data["gaps"])
        assert client.get("/api/stocks/AAPL/earnings?market=CA").status_code == 422
        assert client.get("/api/stocks/TSX:RY/earnings").status_code == 422
        assert client.get("/api/stocks/RY.TO/earnings").status_code == 503


def test_canadian_live_is_explicitly_unavailable_without_provider_calls(tmp_path):
    settings = Settings(_env_file=None, data_mode="live", database_url=f"sqlite:///{tmp_path}/earnings-ca.db")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/stocks/RY.TO/earnings?market=CA")
        assert response.status_code == 200
        data = response.json()
        assert data["market"] == "CA" and data["currency"] == "CAD"
        assert data["history"] == [] and data["upcoming"] is None
        assert data["gaps"]


def test_live_missing_finnhub_key_reports_gap_not_synthetic_results(tmp_path):
    settings = Settings(
        _env_file=None,
        data_mode="live",
        finnhub_api_key="",
        database_url=f"sqlite:///{tmp_path}/earnings-no-key.db",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/stocks/AAPL/earnings")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "live" and data["sources"] == []
        assert not data["history"] and data["upcoming"] is None
        assert "FINNHUB_API_KEY" in " ".join(data["gaps"])
