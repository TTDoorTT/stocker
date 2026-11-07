"""Offline acceptance checks for the SEC industry evidence pilot."""

from datetime import UTC, datetime

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.market_data.industry_sec import SECIndustryEvidence, _filing_rows, _frame_rows
from app.modules.market_data.providers.http import ProviderHTTP
from app.modules.market_data.service import DataService


def test_no_network_and_no_fabricated_sec_data_in_fixture_mode(tmp_path):
    settings = Settings(
        _env_file=None,
        data_mode="fixtures",
        sec_user_agent="",
        database_url=f"sqlite:///{tmp_path}/fixture.db",
    )
    result = SECIndustryEvidence(DataService(settings).sec, settings).snapshot(2025)
    assert result["companies"] == []
    assert result["metrics"] == []
    assert result["filings"] == []
    assert any("fixture" in gap.lower() for gap in result["gaps"])


def test_frame_filters_nonpeers_missing_period_and_invalid_values():
    valid = {
        "cik": 1045810,
        "entityName": "NVIDIA",
        "start": "2025-01-01",
        "end": "2025-12-31",
        "val": 1_000_000_000,
    }
    payload = {
        "data": [
            valid,
            dict(valid, cik=99),
            dict(valid, val=float("nan")),
            dict(valid, start="2025-10-01"),
            dict(valid, val=True),
        ]
    }
    rows = _frame_rows(payload, "NetIncomeLoss", 2025, {1045810: "NVDA"})
    assert len(rows) == 1
    assert rows[0]["value"] == 1_000_000_000
    assert rows[0]["start"] == "2025-01-01"


def test_submission_parser_blocks_malicious_filing_paths():
    payload = {
        "filings": {
            "recent": {
                "form": ["10-K", "10-Q", "8-K"],
                "accessionNumber": ["0001045810-26-000001"] * 3,
                "primaryDocument": ["report.htm", "../bad.html", "ok.htm"],
                "filingDate": ["2026-04-01"] * 3,
            }
        }
    }
    result = _filing_rows(payload, "NVDA", 1045810)
    assert len(result) == 2
    assert all(".." not in item["source_url"] for item in result)


def test_industry_snapshot_uses_existing_sec_transport_without_llm(tmp_path):
    requests = []
    peer_data = [
        ("NVDA", 1045810),
        ("AMD", 2488),
        ("INTC", 50863),
        ("AVGO", 1730168),
        ("MU", 723125),
    ]

    def handler(request):
        requests.append(str(request.url))
        assert request.headers["user-agent"] == "Stocker QA qa@example.org"
        path = request.url.path
        if path.endswith("company_tickers.json"):
            return httpx.Response(
                200,
                json={
                    str(i): {"ticker": ticker, "title": ticker, "cik_str": cik}
                    for i, (ticker, cik) in enumerate(peer_data)
                },
            )
        if "/api/xbrl/frames/" in path:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "cik": 1045810,
                            "entityName": "NVIDIA",
                            "start": "2025-01-01",
                            "end": "2025-12-31",
                            "val": 1_200_000_000,
                        }
                    ]
                },
            )
        if path.startswith("/submissions/CIK"):
            return httpx.Response(
                200,
                json={
                    "filings": {
                        "recent": {
                            "form": ["10-K"],
                            "accessionNumber": ["0001045810-26-000001"],
                            "primaryDocument": ["report.htm"],
                            "filingDate": ["2026-04-01"],
                        }
                    }
                },
            )
        return httpx.Response(404)

    settings = Settings(
        _env_file=None,
        data_mode="live",
        sec_user_agent="Stocker QA qa@example.org",
        database_url=f"sqlite:///{tmp_path}/live.db",
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    data = DataService(settings, ProviderHTTP(client))
    service = SECIndustryEvidence(data.sec, settings)
    first = service.snapshot(2025)
    second = service.snapshot(2025)

    assert len(first["companies"]) == 5
    assert len(first["metrics"]) == 2
    assert first["metrics"][0]["rows"][0]["symbol"] == "NVDA"
    assert first["metrics"][0]["rows"][0]["value"] == 1_200_000_000
    assert len(first["filings"]) == 5
    assert all(item["source_url"].startswith("https://www.sec.gov/Archives/") for item in first["filings"])
    assert all(metric["cached"] for metric in second["metrics"])
    assert len(requests) == 8  # one ticker map, two frames, five submissions, once only
    assert any("no comparable frame" in gap.lower() for gap in first["gaps"])
    assert first["as_of"] <= datetime.now(UTC).isoformat()


def test_route_validates_year_and_returns_no_synthetic_data(tmp_path):
    settings = Settings(
        _env_file=None,
        data_mode="fixtures",
        database_url=f"sqlite:///{tmp_path}/api.db",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/industries/ai-computing/evidence?year=2025")
        assert response.status_code == 200
        body = response.json()
        assert body["metrics"] == []
        assert body["news"] == []
        assert response.json()["industry"] == "ai-computing"
        assert client.get("/api/industries/ai-computing/evidence?year=2000").status_code == 422
        assert client.get("/api/industries/ai-computing/evidence?year=2099").status_code == 422
