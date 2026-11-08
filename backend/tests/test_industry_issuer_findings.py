"""No-network tests for reviewed claim issuer attribution."""

import pytest

from app.modules.intelligence.issuer_findings import issuer_findings

URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm"


def sample():
    evidence = [
        {"evidence_id": "ev-a", "symbol": "AMD", "source_url": URL},
        {"evidence_id": "ev-b", "symbol": "AVGO", "source_url": URL},
    ]
    claims = [
        {"text": "AMD describes a technical approach.", "evidence_ids": ["ev-a"]},
        {
            "text": "Separate disclosures describe packaging.",
            "evidence_ids": ["ev-a", "ev-b"],
        },
    ]
    review = {
        "status": "model_screened",
        "claims_reviewed": 2,
        "assessments": [
            {
                "claim_index": 0,
                "verdict": "supported",
                "supporting_evidence_ids": ["ev-a"],
            },
            {
                "claim_index": 1,
                "verdict": "supported",
                "supporting_evidence_ids": ["ev-a", "ev-b"],
            },
        ],
    }
    return evidence, claims, review


def test_attributes_claims_without_inventing_comparisons():
    results = issuer_findings(*sample())

    assert len(results) == 2
    assert results[0]["scope"] == "single_issuer"
    assert results[0]["issuers"] == ["AMD"]

    assert results[1]["scope"] == "multiple_issuers"
    assert results[1]["issuers"] == ["AMD", "AVGO"]
    assert results[1]["citations"][1]["evidence_id"] == "ev-b"


def test_legacy_reports_remain_compatible():
    evidence, claims, review = sample()

    assert issuer_findings(evidence, None, review) == []
    assert issuer_findings(evidence, claims, None) == []


@pytest.mark.parametrize(
    "fault",
    ["unknown_id", "changed_citation", "duplicate_index", "rejected", "bad_url"],
)
def test_invalid_attribution_rejected(fault):
    evidence, claims, review = sample()

    if fault == "unknown_id":
        claims[0]["evidence_ids"] = ["ev-unknown"]
    elif fault == "changed_citation":
        review["assessments"][0]["supporting_evidence_ids"] = ["ev-b"]
    elif fault == "duplicate_index":
        review["assessments"][1]["claim_index"] = 0
    elif fault == "rejected":
        review["assessments"][0]["verdict"] = "insufficient"
    elif fault == "bad_url":
        evidence[0]["source_url"] = "javascript:alert(1)"

    with pytest.raises(ValueError):
        issuer_findings(evidence, claims, review)


def test_duplicate_evidence_ids_rejected():
    evidence, claims, review = sample()
    evidence[1]["evidence_id"] = "ev-a"

    with pytest.raises(ValueError):
        issuer_findings(evidence, claims, review)
