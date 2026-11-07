"""Offline contract, evidence, and persistence checks for industry research."""

from contextlib import closing
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.intelligence import industry_research
from app.modules.intelligence.industry_research import IndustryResearchService
from app.modules.research.errors import ModelError


def fixture_snapshot():
    timestamp = datetime.now(UTC).isoformat()
    return {
        "industry": "ai-computing",
        "mode": "live",
        "as_of": timestamp,
        "metrics": [
            {
                "key": "research_and_development",
                "label": "R&D expense",
                "source_url": "https://data.sec.gov/api/xbrl/frames/us-gaap/ResearchAndDevelopmentExpense/USD/CY2025.json",
                "source_name": "SEC EDGAR XBRL Frames",
                "fetched_at": timestamp,
                "cached": False,
                "rows": [
                    {
                        "symbol": "NVDA",
                        "start": "2025-01-01",
                        "end": "2025-12-31",
                        "value": 1000000,
                        "unit": "USD",
                    }
                ],
            }
        ],
        "filings": [
            {
                "symbol": "NVDA",
                "form": "10-K",
                "filed": "2026-04-01",
                "source_name": "SEC EDGAR submissions",
                "source_url": "https://www.sec.gov/Archives/edgar/data/1/000001/report.htm",
            }
        ],
        "news": [],
        "gaps": ["Selected peers are not a sector-wide census"],
    }


def make_service(tmp_path, monkeypatch, fail=False):
    settings = Settings(
        _env_file=None,
        data_mode="live",
        llm_model="local-test-model",
        database_url=f"sqlite:///{tmp_path}/research.db",
    )

    def catalog(slug):
        return {"slug": slug} if slug in {"ai-computing", "energy"} else _missing(slug)

    calls = []

    def summarize(payload, evidence, gaps, config, **kwargs):
        calls.append((evidence, kwargs))
        if fail:
            raise ModelError("Test model unavailable")
        return {
            "answer": "Industry highlights (headlines only)\n\n- Source-backed overview (ev-example)",
            "evidence": evidence,
            "gaps": gaps,
            "mode": "live",
        }

    monkeypatch.setattr(industry_research, "summarize_captured_headlines", summarize)
    service = IndustryResearchService(
        settings.database_url, catalog, lambda _: fixture_snapshot(), lambda: settings
    )
    return service, settings, calls


def _missing(slug):
    raise KeyError(slug)


def test_saved_is_read_only_and_section_validation(tmp_path, monkeypatch):
    service, _, calls = make_service(tmp_path, monkeypatch)
    assert service.saved("ai-computing", "overview")["saved"] is False
    assert service.saved("energy", "technology")["saved"] is False
    assert calls == []
    with pytest.raises(KeyError):
        service.saved("unknown", "overview")
    with pytest.raises(ValueError, match="Unknown industry section"):
        service.saved("ai-computing", "bad")
    with pytest.raises(ValueError, match="currently available only"):
        service.generate("energy", "overview")
    assert calls == []


def test_generate_persists_snapshot_and_survives_restart(tmp_path, monkeypatch):
    service, settings, calls = make_service(tmp_path, monkeypatch)
    generated = service.generate("ai-computing", "overview")
    assert generated["saved"]
    assert generated["model_id"] == "local-test-model"
    assert not generated["stale"]
    assert "captured evidence only" in generated["result"]["answer"]
    assert len(generated["result"]["evidence"]) == 2
    assert all(item["evidence_id"].startswith("ev-") for item in generated["result"]["evidence"])
    assert "Do not claim to have read filing bodies" in calls[0][1]["task"]

    restarted = IndustryResearchService(
        settings.database_url,
        service.catalog,
        lambda _: (_ for _ in ()).throw(AssertionError("SEC fetch")),
        lambda: settings,
    )
    assert restarted.saved("ai-computing", "overview")["result"]["answer"] == generated["result"]["answer"]
    assert len(calls) == 1  # No additional AI call on read
    with closing(restarted.repository.connect()) as db:
        row = db.execute("SELECT source_snapshot_json FROM industry_research_sections").fetchone()
    assert '"metrics"' in row[0] and '"filings"' in row[0]


def test_failed_regeneration_never_overwrites_previous(tmp_path, monkeypatch):
    service, _, _ = make_service(tmp_path, monkeypatch)
    service.generate("ai-computing", "overview")
    original = service.saved("ai-computing", "overview")
    monkeypatch.setattr(
        industry_research,
        "summarize_captured_headlines",
        lambda *args, **kwargs: (_ for _ in ()).throw(ModelError("offline")),
    )
    with pytest.raises(ModelError):
        service.generate("ai-computing", "overview")
    assert service.saved("ai-computing", "overview")["generated_at"] == original["generated_at"]
    assert service.saved("ai-computing", "overview")["result"] == original["result"]


def test_rss_changes_mark_saved_overview_stale(tmp_path, monkeypatch):
    service, _, _ = make_service(tmp_path, monkeypatch)
    service.generate("ai-computing", "overview")
    with closing(service.repository.connect()) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS rss_articles (
            category TEXT, canonical_url TEXT, headline TEXT, summary TEXT, published_at TEXT, source_url TEXT
        )""")
        db.execute(
            "INSERT INTO rss_articles VALUES (?, ?, ?, ?, ?, ?)",
            (
                "ai",
                "https://example.org/article",
                "New headline",
                "New excerpt",
                datetime.now(UTC).isoformat(),
                "https://example.org/article",
            ),
        )
    assert service.saved("ai-computing", "overview")["stale"]


def test_api_allows_saved_without_model_and_blocks_fixture_generation(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/app.db")
    monkeypatch.setattr(
        industry_research,
        "summarize_captured_headlines",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM invoked on GET")),
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/industries").status_code == 200
        assert client.get("/api/industries/ai-computing").status_code == 200
        r = client.get("/api/industries/ai-computing/sections/overview")
        assert r.status_code == 200 and r.json()["saved"] is False
        assert client.get("/api/industries/unknown/sections/overview").status_code == 404
        assert client.get("/api/industries/ai-computing/sections/invalid").status_code == 422
        assert client.post("/api/industries/ai-computing/sections/overview/generate").status_code == 503
        assert client.post("/api/industries/ai-computing/sections/technology/generate").status_code == 422


def test_unsupported_citation_is_rejected_and_not_persisted(tmp_path, monkeypatch):
    from app.modules.research.agents.client import ModelClient
    from app.modules.research.service import summarize_captured_headlines as actual_summary

    service, _, _ = make_service(tmp_path, monkeypatch)
    monkeypatch.setattr(industry_research, "summarize_captured_headlines", actual_summary)

    def uncited_model(self, stage, context, schema, tools):
        return {
            "stage": "report",
            "summary": "No validated source supports this claim.",
            "executive_summary": "The result needs evidence.",
            "claims": [
                {
                    "text": "A fabricated unsupported claim.",
                    "evidence_ids": ["ev-not-in-captured-evidence"],
                    "calculation_ids": [],
                    "value": None,
                    "unit": None,
                    "reference_id": None,
                }
            ],
            "evidence_ids": ["ev-not-in-captured-evidence"],
            "calculation_ids": [],
            "gaps": [],
        }

    monkeypatch.setattr(ModelClient, "complete", uncited_model)
    with pytest.raises(ValueError, match="Unknown evidence IDs"):
        service.generate("ai-computing", "overview")
    assert service.saved("ai-computing", "overview")["saved"] is False
