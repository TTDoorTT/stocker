"""Phase 4A contract tests: backend and UI must not advertise phantom pipelines."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.intelligence.industries import IndustryCatalog
from app.modules.intelligence.industry_profiles import (
    ALL_SECTIONS,
    generation_pipeline,
    public_capabilities,
    validate_profiles,
)


def test_all_industry_templates_have_truthful_generation_capabilities():
    catalog = IndustryCatalog()
    rows = catalog.industries()
    assert len(rows) == 20
    assert len({row["slug"] for row in rows}) == 20
    assert all(row["research_coverage"] for row in rows)
    for row in rows:
        allowed = [s for s in ALL_SECTIONS if generation_pipeline(row["slug"], s)]
        assert row["ai_sections"] == allowed
        assert row["research_status"] == ("limited_pilot" if allowed else "guided_only")
        assert catalog.industry(row["slug"]) == row
    assert sum(bool(row["ai_sections"]) for row in rows) == 2


def test_only_integrated_profiles_have_generation_pipelines():
    expected = {
        "overview": "sec_rss_overview",
        "technology": "sec_filing_review",
        "supply-chain": "sec_filing_review",
        "competition": "sec_filing_review",
    }
    assert {s: generation_pipeline("ai-computing", s) for s in expected} == expected
    assert generation_pipeline("ai-computing", "outlook") is None
    assert public_capabilities("semiconductor")["ai_sections"] == [
        "technology",
        "supply-chain",
        "competition",
    ]
    for slug in ("ai-application", "power-grid", "../evil", ""):
        assert public_capabilities(slug)["ai_sections"] == []
        assert all(generation_pipeline(slug, s) is None for s in ALL_SECTIONS)


def test_research_registry_rejects_invalid_templates():
    with pytest.raises(ValueError, match="unique"):
        validate_profiles([{"slug": "ai-computing"}, {"slug": "ai-computing"}])
    with pytest.raises(ValueError, match="no industry template"):
        validate_profiles([{"slug": "semiconductor"}])


def test_read_routes_expose_capabilities_without_model_or_sec(tmp_path, monkeypatch):
    settings = Settings(
        _env_file=None,
        data_mode="fixtures",
        database_url=f"sqlite:///{tmp_path}/phase4a.db",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/industries")
        assert response.status_code == 200
        assert len(response.json()) == 20
        ai = client.get("/api/industries/ai-computing")
        assert ai.status_code == 200
        assert ai.json()["ai_sections"] == ["overview", "technology", "supply-chain", "competition"]
        assert client.get("/api/industries/semiconductor").json()["ai_sections"] == [
            "technology",
            "supply-chain",
            "competition",
        ]
        assert client.post("/api/industries/semiconductor/sections/technology/generate").status_code == 503
        assert client.post("/api/industries/ai-computing/sections/technology/generate").status_code == 503
