"""Offline acceptance for the second, explicitly scoped SEC filing industry."""

from datetime import UTC, datetime

import httpx
import pytest

from app.contracts.industry_sources import SEC_FILING_SOURCES, sec_filing_source, validate_filing_sources
from app.core.config import Settings
from app.modules.intelligence import industry_research
from app.modules.intelligence.filing_section import capture_filing_section, filing_gaps, filing_task
from app.modules.intelligence.industries import IndustryCatalog
from app.modules.intelligence.industry_profiles import generation_pipeline
from app.modules.intelligence.industry_research import IndustryResearchService
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.filing_excerpt import extract_passages
from app.modules.market_data.industry_sec import SECIndustryEvidence
from app.modules.market_data.providers.http import ProviderHTTP
from app.modules.market_data.service import DataService
from app.modules.research.errors import ModelError

SEC_URL = "https://www.sec.gov/Archives/edgar/data/6951/000000695126000001/report.htm"


def example(term: str, symbol: str = "AMAT", topic: str = "technology") -> dict:
    return {
        "symbol": symbol,
        "form": "10-K",
        "filed": "2026-02-18",
        "matched_term": term,
        "topic": topic,
        "text": (
            f"The issuer discusses {term} within its semiconductor operations, including technical "
            "requirements for equipment validation, production workflows, operational uncertainties "
            "and manufacturing processes described in the selected annual filing."
        ),
        "source_name": "SEC EDGAR primary filing",
        "source_url": SEC_URL,
        "fetched_at": datetime.now(UTC).isoformat(),
        "cached": False,
    }


def snapshot(*rows: dict) -> dict:
    return {
        "industry": "semiconductor",
        "year": 2025,
        "mode": "live",
        "excerpts": list(rows),
        "gaps": ["Sampled selected U.S. issuers only"],
    }


def test_profile_permissions_and_issuer_universe():
    validate_filing_sources()
    assert len(SEC_FILING_SOURCES) == 3
    semiconductor = sec_filing_source("semiconductor")
    assert semiconductor.peers == ("NVDA", "INTC", "MU", "AMAT", "LRCX")
    catalog = IndustryCatalog()
    assert len(catalog.industries()) == 20
    sem = catalog.industry("semiconductor")
    assert sem["ai_sections"] == ["technology", "supply-chain", "competition"]
    assert sem["research_status"] == "limited_pilot"
    assert catalog.industry("ai-computing")["ai_sections"] == [
        "overview",
        "technology",
        "supply-chain",
        "competition",
    ]
    assert catalog.industry("hbm")["ai_sections"] == []
    assert generation_pipeline("semiconductor", "overview") is None
    assert generation_pipeline("semiconductor", "outlook") is None
    assert generation_pipeline("semiconductor", "technology") == "sec_filing_review"
    with pytest.raises(ValueError, match="No integrated"):
        sec_filing_source("unknown")


def test_semiconductor_extraction_has_sector_specific_topics():
    document = """
    The company describes lithography process technology and wafer deposition tools
    for semiconductor production, together with process control requirements and
    equipment installation milestones documented by its product teams.

    Manufacturing depends upon wafer fabrication capacity and specialized equipment
    components. The disclosure discusses upstream production schedules, suppliers,
    operating constraints and order fulfillment under changing demand conditions.

    Competitive conditions and customer concentration are described as strategic
    risks, with changes in pricing, qualification, and design wins influencing the
    commercial environment faced by the reporting issuer.
    """
    topics = sec_filing_source("semiconductor").topic_terms
    selected = extract_passages(document, topic_terms=topics)
    assert {row["topic"] for row in selected} == {"technology", "supply-chain", "competition"}
    assert any(row["matched_term"] in {"lithography", "deposition", "wafer"} for row in selected)
    # The original AI Computing extractor retains the original default topic definitions.
    original = extract_passages(document)
    assert all(row["matched_term"] not in {"lithography", "wafer", "deposition"} for row in original)


def test_filing_adapter_keeps_industries_separate():
    evidence = capture_filing_section(
        snapshot(example("lithography")), "technology", industry="semiconductor"
    )
    assert len(evidence) == 1
    assert evidence[0]["symbol"] == "AMAT"
    assert "lithography" in evidence[0]["value"]
    assert (
        "international"
        in " ".join(
            filing_gaps("technology", snapshot(example("lithography")), industry="semiconductor")
        ).lower()
    )
    assert "Global semiconductor" in filing_task("technology", industry="semiconductor")
    with pytest.raises(DataUnavailable, match="industry mismatch"):
        capture_filing_section(snapshot(example("lithography")), "technology", industry="ai-computing")
    with pytest.raises(DataUnavailable, match="No attributable"):
        capture_filing_section(
            snapshot(example("lithography", symbol="AMD")), "technology", industry="semiconductor"
        )


def test_fixture_mode_has_no_fake_semiconductor_evidence(tmp_path):
    settings = Settings(_env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/f.db")
    data = DataService(settings)
    snap = data.sec_industry_snapshot(2025, industry="semiconductor")
    excerpts = data.sec_filing_excerpts(2025, industry="semiconductor")
    assert snap["industry"] == "semiconductor"
    assert snap["companies"] == snap["filings"] == snap["metrics"] == []
    assert excerpts["excerpts"] == []
    assert excerpts["mode"] == "fixtures"


def test_sector_sec_snapshot_queries_only_configured_issuers(tmp_path):
    issuers = sec_filing_source("semiconductor").peers
    all_issuers = issuers + ("AMD",)
    ciks = {ticker: 8000 + i for i, ticker in enumerate(all_issuers)}
    requests = []

    def handler(request):
        requests.append(str(request.url))
        assert request.headers["user-agent"] == "Stocker test test@example.org"
        if request.url.path.endswith("company_tickers.json"):
            return httpx.Response(
                200,
                json={
                    str(i): {"ticker": ticker, "title": ticker, "cik_str": cik}
                    for i, (ticker, cik) in enumerate(ciks.items())
                },
            )
        if request.url.path.startswith("/submissions/CIK"):
            return httpx.Response(
                200,
                json={
                    "filings": {
                        "recent": {
                            "form": ["10-K"],
                            "accessionNumber": ["0000008000-26-000001"],
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
        sec_user_agent="Stocker test test@example.org",
        database_url=f"sqlite:///{tmp_path}/live.db",
    )
    data = DataService(settings, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler))))
    result = SECIndustryEvidence(data.sec, settings).snapshot(2025, industry="semiconductor")
    assert result["industry"] == "semiconductor"
    assert result["metrics"] == []  # No sector-wide financial frame comparison is invented.
    assert {row["symbol"] for row in result["filings"]} == set(issuers)
    assert "AMD" not in {row["symbol"] for row in result["companies"]}
    assert not any("/api/xbrl/frames/" in url for url in requests)
    assert len(requests) == 6  # one issuer index + five submissions


def test_generation_and_failed_regeneration_preserve_saved_result(tmp_path, monkeypatch):
    settings = Settings(
        _env_file=None,
        data_mode="live",
        llm_model="local-test-model",
        database_url=f"sqlite:///{tmp_path}/research.db",
    )
    captures = []
    calls = []

    def fetch(year, *, industry):
        captures.append((year, industry))
        return snapshot(example("lithography"))

    def summarize(payload, evidence, gaps, configured, **kwargs):
        calls.append(kwargs)
        return {
            "answer": "Industry highlights (headlines only)\n\n- Selected issuer disclosure",
            "evidence": evidence,
            "gaps": gaps,
            "mode": "live",
            "claim_review": {"status": "model_screened"},
        }

    monkeypatch.setattr(industry_research, "summarize_captured_headlines", summarize)
    service = IndustryResearchService(
        settings.database_url,
        IndustryCatalog().industry,
        lambda _: (_ for _ in ()).throw(AssertionError("AI overview source used")),
        lambda: settings,
        fetch,
    )
    assert service.saved("semiconductor", "technology")["saved"] is False
    assert captures == calls == []
    saved = service.generate("semiconductor", "technology")
    assert saved["saved"] and saved["result"]["claim_review"]["status"] == "model_screened"
    assert captures[0][1] == "semiconductor"
    assert calls[0]["review_filing"] is True
    assert "Global semiconductor" in calls[0]["task"]
    with pytest.raises(ValueError, match="currently available"):
        service.generate("semiconductor", "overview")

    def offline(*args, **kwargs):
        raise ModelError("Offline local model")

    monkeypatch.setattr(industry_research, "summarize_captured_headlines", offline)
    with pytest.raises(ModelError, match="Offline"):
        service.generate("semiconductor", "technology")
    prior = service.saved("semiconductor", "technology")
    assert prior["result"] == saved["result"]
    assert prior["generated_at"] == saved["generated_at"]
