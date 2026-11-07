"""Offline SEC primary-document excerpt contract, no external network."""

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.market_data.filing_excerpt import (
    MAX_DOCUMENT_BYTES,
    extract_passages,
    filing_excerpts,
)
from app.modules.market_data.providers.http import ProviderHTTP
from app.modules.market_data.service import DataService

URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm"


def snapshot(mode="live", link=URL):
    return {
        "year": 2025,
        "mode": mode,
        "filings": [
            {"symbol": "NVDA", "form": "10-K", "filed": "2026-04-01", "source_url": link},
        ],
    }


def test_html_extraction_ignores_scripts_and_returns_bounded_literal_matches():
    html = (
        "<html><head><script>supply chain SECRET IN SCRIPT</script></head><body>"
        "<h2>Business discussion</h2><p>The semiconductor manufacturing supply chain "
        "depends on outsourced manufacturing partners and long-term planning. "
        "Supply chain conditions can affect operations and end users.</p></body></html>"
    )
    passages = extract_passages(html)
    assert passages
    assert all("SECRET IN SCRIPT" not in p["text"] for p in passages)
    assert all(len(p["text"]) <= 360 for p in passages)
    assert "manufacturing" in passages[0]["text"]


def test_filing_fetch_reuses_sec_transport_and_cache_without_ai(tmp_path):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        assert request.headers["user-agent"] == "Stocker QA qa@example.org"
        assert str(request.url) == URL
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            text="<p>The semiconductor manufacturing supply chain depends on trusted partners "
            "to provide specialized production capacity for customer deployments.</p>",
        )

    settings = Settings(
        _env_file=None,
        data_mode="live",
        sec_user_agent="Stocker QA qa@example.org",
        database_url=f"sqlite:///{tmp_path}/file.db",
    )
    provider = ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler)))
    data = DataService(settings, provider)
    first = filing_excerpts(data.sec, snapshot())
    second = filing_excerpts(data.sec, snapshot())
    assert len(calls) == 1
    assert first["excerpts"] and first["excerpts"][0]["source_url"] == URL
    assert first["excerpts"][0]["cached"] is False
    assert second["excerpts"][0]["cached"] is True


def test_fixture_blocks_network_and_foreign_urls(tmp_path):
    def forbidden(request):
        raise AssertionError("Unexpected network request")

    settings = Settings(
        _env_file=None,
        data_mode="fixtures",
        database_url=f"sqlite:///{tmp_path}/fixed.db",
    )
    data = DataService(settings, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(forbidden))))
    fixture = filing_excerpts(data.sec, snapshot(mode="fixtures"))
    assert fixture["excerpts"] == []
    assert "fixture" in fixture["gaps"][0].lower()

    live = Settings(
        _env_file=None,
        data_mode="live",
        sec_user_agent="Stocker QA qa@example.org",
        database_url=f"sqlite:///{tmp_path}/live.db",
    )
    data = DataService(live, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(forbidden))))
    rejected = filing_excerpts(data.sec, snapshot(link="https://example.org/untrusted.html"))
    assert rejected["excerpts"] == []
    assert any("safely addressable" in gap for gap in rejected["gaps"])


def test_size_cap_failure_is_reported_without_fake_excerpts(tmp_path):
    def handler(request):
        return httpx.Response(200, content=b"a" * (MAX_DOCUMENT_BYTES + 1))

    settings = Settings(
        _env_file=None,
        data_mode="live",
        sec_user_agent="Stocker QA qa@example.org",
        database_url=f"sqlite:///{tmp_path}/size.db",
    )
    data = DataService(settings, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler))))
    result = filing_excerpts(data.sec, snapshot())
    assert result["excerpts"] == []
    assert any("bounded retrieval limit" in gap for gap in result["gaps"])


def test_fixture_endpoint_does_not_invoke_model(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/api.db")
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/industries/ai-computing/filing-excerpts?year=2025")
        assert response.status_code == 200
        assert response.json()["excerpts"] == []
        assert client.get("/api/industries/ai-computing/filing-excerpts?year=1999").status_code == 422
