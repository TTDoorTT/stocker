"""Read-only event/date and event-study endpoints, with no live network requests."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_fixture_event_date_endpoint_and_post_date_study(tmp_path):
    settings = Settings(_env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/e.db")
    with TestClient(create_app(settings)) as client:
        events = client.get("/api/stocks/AAPL/events")
        assert events.status_code == 200, events.text
        data = events.json()
        assert data["mode"] == "fixtures" and len(data["events"]) == 10
        assert all(row["date_precision"] == "date_only" for row in data["events"])
        assert all(row["source"]["fixture"] for row in data["events"])

        study = client.get("/api/stocks/AAPL/event-study")
        assert study.status_code == 200, study.text
        result = study.json()
        assert result["mode"] == "fixtures" and result["benchmark_symbol"] == "SPY"
        assert result["return_method"] == "compounded_close_to_close_excess"
        assert result["eligible_event_count"] >= 8
        assert len(result["summary"]) == 3
        assert all(item["eligible_n"] >= 8 for item in result["summary"])
        assert all(source["fixture"] for source in result["sources"])
        assert "SYNTHETIC" in " ".join(result["gaps"])
        assert client.get("/api/stocks/AAPL/event-study?market=CA").status_code == 422
        assert client.get("/api/stocks/TSX:RY/events").status_code == 422


def test_live_without_key_and_canadian_ticker_never_fabricate_events(tmp_path):
    settings = Settings(
        _env_file=None,
        data_mode="live",
        finnhub_api_key="",
        database_url=f"sqlite:///{tmp_path}/e-live.db",
    )
    with TestClient(create_app(settings)) as client:
        for path in ("events", "event-study"):
            us = client.get(f"/api/stocks/AAPL/{path}")
            assert us.status_code == 200, us.text
            value = us.json()
            assert value["mode"] == "live" and value["gaps"]
            if path == "events":
                assert value["events"] == []
            else:
                assert value["summary"] is None and value["eligible_event_count"] == 0
            ca = client.get(f"/api/stocks/RY.TO/{path}")
            assert ca.status_code == 200
            assert ca.json()["market"] == "CA" and ca.json()["currency"] == "CAD"
            assert ca.json()["gaps"]


def test_fixture_unsupported_ticker_is_not_live_fallback(tmp_path):
    settings = Settings(_env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/e-fx.db")
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/stocks/RY.TO/events").status_code == 503
        assert client.get("/api/stocks/RY.TO/event-study").status_code == 503
