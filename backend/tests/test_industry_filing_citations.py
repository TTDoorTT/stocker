"""Offline Phase 4F: accepted SEC evidence versus actually cited evidence."""

import pytest

from app.modules.intelligence.filing_citations import cited_filing_coverage


def sample():
    coverage = {
        "selected_issuers": ["NVDA", "AMD", "INTC", "AVGO", "MU"],
        "represented_issuers": ["NVDA", "AMD", "MU"],
        "missing_issuers": ["INTC", "AVGO"],
        "accepted_excerpts": 4,
        "limitation": "Issuer sample only",
    }
    evidence = [
        {"evidence_id": "ev-n1", "symbol": "NVDA"},
        {"evidence_id": "ev-n2", "symbol": "NVDA"},
        {"evidence_id": "ev-a1", "symbol": "AMD"},
        {"evidence_id": "ev-m1", "symbol": "MU"},
    ]
    review = {
        "status": "model_screened",
        "claims_reviewed": 2,
        "assessments": [
            {"claim_index": 0, "verdict": "supported", "supporting_evidence_ids": ["ev-n1"]},
            {"claim_index": 1, "verdict": "supported", "supporting_evidence_ids": ["ev-n1", "ev-m1"]},
        ],
    }
    return coverage, evidence, review


def test_unique_cited_excerpts_and_issuer_order_are_not_accepted_counts():
    coverage, evidence, review = sample()
    result = cited_filing_coverage(coverage, evidence, review)
    assert result["cited_issuers"] == ["NVDA", "MU"]
    assert result["uncited_represented_issuers"] == ["AMD"]
    assert result["cited_excerpts"] == 2
    assert result["model_screened_claims"] == 2
    assert "not independent" in result["citation_limitation"]
    assert coverage["accepted_excerpts"] == 4


def test_absent_legacy_review_or_summary_only_stub_is_not_measured():
    coverage, evidence, review = sample()
    assert cited_filing_coverage(coverage, evidence, None) is None
    assert cited_filing_coverage(coverage, evidence, {}) is None
    assert cited_filing_coverage(coverage, evidence, {"status": "model_screened"}) is None


@pytest.mark.parametrize("fault", ["unknown", "duplicate", "unsupported", "missing", "count"])
def test_bad_reviewer_metadata_fails_before_persistence(fault):
    coverage, evidence, review = sample()
    if fault == "unknown":
        review["assessments"][0]["supporting_evidence_ids"] = ["ev-unknown"]
    elif fault == "duplicate":
        review["assessments"][1]["claim_index"] = 0
    elif fault == "unsupported":
        review["assessments"][1]["verdict"] = "unsupported"
    elif fault == "missing":
        review["assessments"] = []
        review["claims_reviewed"] = 0
    elif fault == "count":
        review["claims_reviewed"] = 3
    with pytest.raises(ValueError):
        cited_filing_coverage(coverage, evidence, review)


def test_cross_issuer_and_duplicate_ids_are_not_silently_counted():
    coverage, evidence, review = sample()
    evidence[0]["symbol"] = "ZZZZ"
    with pytest.raises(ValueError):
        cited_filing_coverage(coverage, evidence, review)
    coverage, evidence, review = sample()
    evidence[1]["evidence_id"] = "ev-n1"
    with pytest.raises(ValueError):
        cited_filing_coverage(coverage, evidence, review)


def test_no_cited_passages_from_missing_issuer():
    coverage, evidence, review = sample()
    review["assessments"][1]["supporting_evidence_ids"] = ["ev-a1"]
    result = cited_filing_coverage(coverage, evidence, review)
    assert result["cited_issuers"] == ["NVDA", "AMD"]
    assert result["uncited_represented_issuers"] == ["MU"]
