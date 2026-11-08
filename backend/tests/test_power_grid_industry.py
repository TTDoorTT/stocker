"""Phase 4D: grid research is an explicit SEC pilot, never inferred from a template."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.contracts.industry_sources import sec_filing_source, validate_filing_sources
from app.core.config import Settings
from app.main import create_app
from app.modules.intelligence.filing_dispatch import prepare_filing_generation
from app.modules.intelligence.filing_section import capture_filing_section
from app.modules.intelligence.industries import IndustryCatalog
from app.modules.intelligence.industry_profiles import generation_pipeline
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.filing_excerpt import extract_passages
from app.modules.market_data.service import DataService

URL = "https://www.sec.gov/Archives/edgar/data/1996810/000199681026000015/gev-20251231.htm"


def sample():
    return {
        "industry": "power-grid",
        "mode": "live",
        "excerpts": [
            {
                "symbol": "GEV",
                "form": "10-K",
                "filed": "2026-01-29",
                "matched_term": "substation",
                "topic": "technology",
                "text": (
                    "The company discusses substation equipment for transmission networks "
                    "and describes engineering requirements, customer installations, "
                    "operating limitations and commissioning processes for electrical systems."
                ),
                "source_url": URL,
                "fetched_at": datetime.now(UTC).isoformat(),
            }
        ],
        "gaps": [],
    }


def test_explicit_profile_and_capabilities():
    validate_filing_sources()
    source = sec_filing_source("power-grid")
    assert source.peers == ("GEV", "ETN", "HUBB", "PWR", "NEE")
    grid = IndustryCatalog().industry("power-grid")
    assert grid["ai_sections"] == ["technology", "supply-chain", "competition"]
    assert generation_pipeline("power-grid", "overview") is None
    assert generation_pipeline("power-grid", "outlook") is None
    assert IndustryCatalog().industry("ai-computing")["ai_sections"][0] == "overview"


def test_grid_terms_are_distinct_and_evidence_keeps_identity():
    text = (
        "Grid modernization includes substation controls and transmission automation "
        "for electrical infrastructure. The issuer describes electrical system design, "
        "engineering verification, maintenance schedules and the operating limitations "
        "of transmission facilities."
    )
    passages = extract_passages(text, topic_terms=sec_filing_source("power-grid").topic_terms)
    assert any(p["topic"] == "technology" for p in passages)
    assert any(p["matched_term"] in {"grid modernization", "substation", "transmission"} for p in passages)
    evidence = capture_filing_section(sample(), "technology", industry="power-grid")
    assert len(evidence) == 1
    assert evidence[0]["symbol"] == "GEV"
    assert evidence[0]["source_url"] == URL
    with pytest.raises(DataUnavailable, match="industry mismatch"):
        capture_filing_section(sample(), "technology", industry="semiconductor")


def test_dispatch_preserves_explicit_sector_routing():
    calls = []

    def capture(year, *, industry):
        calls.append((year, industry))
        return sample()

    prepared = prepare_filing_generation(
        "power-grid",
        "technology",
        2025,
        capture,
        lambda snap, section, *, industry: capture_filing_section(snap, section, industry=industry),
        lambda section, snap, *, industry: [],
        lambda section, *, industry: "Limited issuer-disclosure note",
    )
    assert calls == [(2025, "power-grid")]
    assert prepared.snapshot["industry"] == "power-grid"
    assert prepared.evidence[0]["symbol"] == "GEV"


def test_fixture_mode_never_fabricates_grid_evidence(tmp_path):
    settings = Settings(
        _env_file=None,
        data_mode="fixtures",
        database_url=f"sqlite:///{tmp_path}/grid.db",
    )
    data = DataService(settings)
    result = data.sec_industry_snapshot(2025, industry="power-grid")
    assert result["mode"] == "fixtures"
    assert result["companies"] == result["metrics"] == result["filings"] == []
    assert data.sec_filing_excerpts(2025, industry="power-grid")["excerpts"] == []
    with TestClient(create_app(settings)) as client:
        public = client.get("/api/industries/power-grid")
        assert public.status_code == 200
        assert public.json()["ai_sections"] == ["technology", "supply-chain", "competition"]
        assert client.post("/api/industries/power-grid/sections/technology/generate").status_code == 503
