"""Offline Phase 3D.3 claim-screening contract; no SEC/network/model access."""

from datetime import UTC, datetime

import pytest

from app.core.config import Settings
from app.modules.research import claim_review
from app.modules.research.claim_review import screen_filing_claims
from app.modules.research.service import summarize_captured_headlines

ID = "ev-test-issuer"
SOURCE = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm"
EXCERPT = (
    "The company relies on manufacturing partners and states that concentration "
    "among these partners could affect the availability of certain products."
)


def settings():
    return Settings(_env_file=None, llm_model="test-judge", data_mode="live")


def evidence():
    return [
        {
            "evidence_id": ID,
            "symbol": "NVDA",
            "field": "sec_10k_excerpt_supply_chain",
            "source_url": SOURCE,
            "value": "Unverified passage boundaries in NVDA SEC 10-K; matched topic 'manufacturing'; "
            "issuer text (untrusted): " + EXCERPT,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
    ]


def claim(text="The issuer discloses manufacturing partner concentration"):
    return {"text": text, "evidence_ids": [ID], "calculation_ids": [], "value": None}


def judge(monkeypatch, *, verdict="supported", ids=None, results=None):
    received = []

    class FakeModel:
        def __init__(self, configured):
            assert configured.llm_model == "test-judge"
            assert configured.llm_max_tokens <= 2048

        def complete(self, stage, context, schema, tools):
            assert stage == "claim_review"
            assert tools.definitions == []
            assert len(context["cited_issuer_excerpts"]) == 1
            assert context["cited_issuer_excerpts"][0]["issuer_excerpt"] == EXCERPT
            received.append(context)
            if results is not None:
                return results
            return {
                "assessments": [
                    {
                        "claim_index": 0,
                        "verdict": verdict,
                        "supporting_evidence_ids": [ID] if ids is None else ids,
                        "reason": "Source directly mentions these manufacturing partners.",
                    }
                ]
            }

    monkeypatch.setattr(claim_review, "ModelClient", FakeModel)
    return received


def test_supported_claim_is_marked_model_screened_not_verified(monkeypatch):
    calls = judge(monkeypatch)
    output = screen_filing_claims([claim()], evidence(), settings())
    assert output["status"] == "model_screened"
    assert "not independent verification" in output["limitations"]
    assert output["claims_reviewed"] == 1
    assert len(calls) == 1


@pytest.mark.parametrize("verdict", ["unsupported", "insufficient"])
def test_unsupported_or_inconclusive_claim_fails_closed(monkeypatch, verdict):
    judge(monkeypatch, verdict=verdict)
    with pytest.raises(ValueError, match="rejected"):
        screen_filing_claims([claim("The issuer dominates the market")], evidence(), settings())


def test_judge_cannot_substitute_or_omit_cited_evidence(monkeypatch):
    judge(monkeypatch, ids=["ev-invented"])
    with pytest.raises(ValueError, match="changed or omitted"):
        screen_filing_claims([claim()], evidence(), settings())


def test_missing_or_duplicate_judgments_rejected(monkeypatch):
    judge(monkeypatch, results={"assessments": []})
    with pytest.raises(ValueError):
        screen_filing_claims([claim()], evidence(), settings())
    duplicate = {
        "assessments": [
            {
                "claim_index": 0,
                "verdict": "supported",
                "supporting_evidence_ids": [ID],
                "reason": "Some supporting excerpt content.",
            },
            {
                "claim_index": 0,
                "verdict": "supported",
                "supporting_evidence_ids": [ID],
                "reason": "Some supporting excerpt content.",
            },
        ]
    }
    judge(monkeypatch, results=duplicate)
    with pytest.raises(ValueError, match="duplicate"):
        screen_filing_claims([claim(), claim("The issuer also notes partners")], evidence(), settings())


def test_unknown_claim_ids_rejected_before_model(monkeypatch):
    calls = judge(monkeypatch)
    bad = claim()
    bad["evidence_ids"] = ["ev-unknown"]
    with pytest.raises(ValueError, match="unknown evidence"):
        screen_filing_claims([bad], evidence(), settings())
    assert not calls


def test_malformed_or_non_filing_evidence_fails_closed(monkeypatch):
    calls = judge(monkeypatch)
    bad = evidence()
    bad[0]["field"] = "industry_rss_article"
    with pytest.raises(ValueError, match="non-filing"):
        screen_filing_claims([claim()], bad, settings())
    assert not calls


def test_summary_calls_reviewer_only_when_explicitly_enabled(monkeypatch):
    class FakeReportModel:
        def __init__(self, configured):
            pass

        def complete(self, stage, context, schema, tools):
            assert stage == "report"
            return {
                "stage": "report",
                "summary": "Limited issuer disclosure summary.",
                "executive_summary": "Limited issuer disclosure overview.",
                "claims": [claim()],
                "evidence_ids": [ID],
                "calculation_ids": [],
                "gaps": [],
            }

    from app.modules.research import service

    monkeypatch.setattr(service, "ModelClient", FakeReportModel)
    calls = judge(monkeypatch)
    payload = {"symbol": "US", "mode": "live", "evidence": evidence(), "news": [], "facts": [], "gaps": []}
    first = summarize_captured_headlines(payload, evidence(), [], settings(), bullets_only=True)
    assert "claim_review" not in first
    assert not calls
    checked = summarize_captured_headlines(
        payload, evidence(), [], settings(), bullets_only=True, review_filing=True
    )
    assert checked["claim_review"]["claims_reviewed"] == 1
    assert len(calls) == 1


def test_too_many_claims_rejected_before_model(monkeypatch):
    calls = judge(monkeypatch)
    with pytest.raises(ValueError, match="one to three"):
        screen_filing_claims([claim() for _ in range(4)], evidence(), settings())
    assert not calls


def test_inconclusive_regeneration_preserves_previous_saved_research(tmp_path, monkeypatch):
    from app.modules.intelligence import industry_research
    from app.modules.intelligence.industry_research import IndustryResearchService

    config = Settings(
        _env_file=None,
        data_mode="live",
        llm_model="test-judge",
        database_url=f"sqlite:///{tmp_path}/research.db",
    )
    response = {
        "answer": "Industry supply-chain (selected SEC filing excerpts)\n\n- Attributed issuer statement",
        "evidence": evidence(),
        "gaps": ["Selected issuer evidence only"],
        "mode": "live",
        "claim_review": {"status": "model_screened"},
    }

    def accepted(*args, **kwargs):
        assert kwargs["review_filing"] is True
        return response

    monkeypatch.setattr(industry_research, "capture_filing_section", lambda snap, sec: evidence())
    monkeypatch.setattr(industry_research, "summarize_captured_headlines", accepted)
    service = IndustryResearchService(
        config.database_url,
        lambda slug: {"slug": slug},
        lambda year: {},
        lambda: config,
        lambda year: {"mode": "live", "excerpts": [], "gaps": []},
    )
    old = service.generate("ai-computing", "supply-chain")
    assert old["saved"] is True

    def inconclusive(*args, **kwargs):
        raise ValueError("Claim review rejected unsupported or insufficiently supported research")

    monkeypatch.setattr(industry_research, "summarize_captured_headlines", inconclusive)
    with pytest.raises(ValueError, match="Claim review rejected"):
        service.generate("ai-computing", "supply-chain")
    after = service.saved("ai-computing", "supply-chain")
    assert after["result"] == old["result"]
    assert after["generated_at"] == old["generated_at"]
