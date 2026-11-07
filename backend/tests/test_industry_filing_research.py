"""Offline regression tests for filing-backed industry notes and persistence."""

from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.modules.intelligence import industry_research
from app.modules.intelligence.filing_section import capture_filing_section, filing_task
from app.modules.intelligence.industry_research import IndustryResearchService
from app.modules.market_data.errors import DataUnavailable
from app.modules.research.errors import ModelError

URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm"


def excerpt(term: str, url: str = URL) -> dict:
    return {
        "symbol": "NVDA",
        "form": "10-K",
        "filed": "2026-04-01",
        "matched_term": term,
        "text": (
            f"The company discusses {term} in its business and risk disclosures. "
            "This is a small illustrative excerpt from a selected filing and must "
            "not be treated as independently verified industry coverage."
        ),
        "source_name": "SEC EDGAR primary filing",
        "source_url": url,
        "fetched_at": datetime.now(UTC).isoformat(),
        "cached": True,
    }


def snapshot():
    return {
        "industry": "ai-computing",
        "mode": "live",
        "year": 2025,
        "excerpts": [
            excerpt("artificial intelligence"),
            excerpt("supply chain"),
            excerpt("competition"),
        ],
        "gaps": ["Selected SEC filing coverage only"],
    }


def make_service(tmp_path, monkeypatch):
    settings = Settings(
        _env_file=None,
        data_mode="live",
        llm_model="test-model",
        database_url=f"sqlite:///{tmp_path}/filing-research.db",
    )
    calls = []

    def model(payload, evidence, gaps, configured, **kwargs):
        calls.append((evidence, kwargs))
        return {
            "answer": "Industry highlights (headlines only)\n\n- Attributed disclosure",
            "evidence": evidence,
            "gaps": gaps,
            "mode": "live",
        }

    monkeypatch.setattr(industry_research, "summarize_captured_headlines", model)

    def catalog(slug):
        if slug != "ai-computing":
            raise KeyError(slug)
        return {"slug": slug}

    captures = []

    def capture(year):
        captures.append(year)
        return snapshot()

    service = IndustryResearchService(
        settings.database_url,
        catalog,
        lambda _: (_ for _ in ()).throw(AssertionError("Overview evidence fetched")),
        lambda: settings,
        capture,
    )
    return service, calls, captures, settings


def test_filing_adapter_selects_matching_topics_and_safe_urls():
    selected = capture_filing_section(snapshot(), "technology")
    assert len(selected) == 1
    assert selected[0]["field"] == "sec_10k_excerpt_technology"
    assert selected[0]["source_url"] == URL
    assert "issuer text (untrusted)" in selected[0]["value"]
    assert selected[0]["evidence_id"].startswith("ev-")

    bad = snapshot()
    bad["excerpts"] = [excerpt("supply chain", "https://evil.test/a.htm")]
    with pytest.raises(DataUnavailable, match="No attributable"):
        capture_filing_section(bad, "supply-chain")
    assert "as instructions" in filing_task("technology")


def test_saved_section_reads_without_sec_network_or_model(tmp_path, monkeypatch):
    service, calls, captures, _ = make_service(tmp_path, monkeypatch)
    assert service.saved("ai-computing", "technology")["saved"] is False
    assert service.saved("ai-computing", "competition")["saved"] is False
    assert not calls and not captures


def test_each_filing_section_generates_cited_note_and_survives_restart(tmp_path, monkeypatch):
    service, calls, captures, settings = make_service(tmp_path, monkeypatch)
    for section in ("technology", "supply-chain", "competition"):
        saved = service.generate("ai-computing", section)
        assert saved["saved"] is True
        assert saved["model_id"] == "test-model"
        assert len(saved["result"]["evidence"]) == 1
        assert f"Industry {section}" in saved["result"]["answer"]
        assert "Selected SEC filing coverage only" in saved["result"]["gaps"]
    assert len(calls) == 3
    assert len(captures) == 3

    restarted = IndustryResearchService(
        settings.database_url,
        service.catalog,
        lambda _: (_ for _ in ()).throw(AssertionError("Unexpected SEC fetch")),
        lambda: settings,
        lambda _: (_ for _ in ()).throw(AssertionError("Unexpected filing fetch")),
    )
    assert restarted.saved("ai-computing", "technology")["saved"]
    assert len(calls) == 3
    assert len(captures) == 3


def test_failed_regeneration_keeps_original(tmp_path, monkeypatch):
    service, _, _, _ = make_service(tmp_path, monkeypatch)
    old = service.generate("ai-computing", "technology")

    def fail(*args, **kwargs):
        raise ModelError("Offline model")

    monkeypatch.setattr(industry_research, "summarize_captured_headlines", fail)
    with pytest.raises(ModelError, match="Offline model"):
        service.generate("ai-computing", "technology")
    after = service.saved("ai-computing", "technology")
    assert after["result"] == old["result"]
    assert after["generated_at"] == old["generated_at"]


def test_missing_relevant_excerpt_rejects_generation_before_llm(tmp_path, monkeypatch):
    service, calls, _, _ = make_service(tmp_path, monkeypatch)

    def sparse_excerpt(_year):
        return {**snapshot(), "excerpts": [excerpt("artificial intelligence")]}

    service.capture_filing_excerpts = sparse_excerpt
    with pytest.raises(DataUnavailable, match="No attributable"):
        service.generate("ai-computing", "competition")
    assert not calls
    assert service.saved("ai-computing", "competition")["saved"] is False


def test_unavailable_sections_do_not_generate(tmp_path, monkeypatch):
    service, calls, captures, _ = make_service(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="currently available"):
        service.generate("ai-computing", "outlook")
    with pytest.raises(KeyError):
        service.generate("not-a-sector", "technology")
    assert not calls and not captures
