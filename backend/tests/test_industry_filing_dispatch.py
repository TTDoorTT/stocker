"""Fail-closed dispatch tests for SEC-backed industry research."""

import pytest

from app.modules.intelligence.filing_dispatch import prepare_filing_generation
from app.modules.market_data.errors import DataUnavailable


def test_ai_computing_uses_legacy_positional_contract():
    calls = []

    def capture(year):
        calls.append(("capture", year))
        return {"mode": "live", "excerpts": []}

    def evidence(snapshot, section):
        calls.append(("evidence", section))
        return [{"evidence_id": "ev-test"}]

    def gaps(section, snapshot):
        calls.append(("gaps", section))
        return ["Limited issuer evidence"]

    def task(section):
        calls.append(("task", section))
        return "Cited source note"

    result = prepare_filing_generation("ai-computing", "technology", 2025, capture, evidence, gaps, task)
    assert result.evidence == [{"evidence_id": "ev-test"}]
    assert result.gaps == ["Limited issuer evidence"]
    assert result.task == "Cited source note"
    assert calls == [
        ("capture", 2025),
        ("evidence", "technology"),
        ("gaps", "technology"),
        ("task", "technology"),
    ]


def test_semiconductor_requires_explicit_identity_and_keyword_routing():
    calls = []

    def capture(year, *, industry):
        calls.append(("capture", year, industry))
        return {"industry": industry, "mode": "live"}

    def evidence(snapshot, section, *, industry):
        calls.append(("evidence", section, industry))
        return [{"evidence_id": "ev-semi"}]

    def gaps(section, snapshot, *, industry):
        calls.append(("gaps", section, industry))
        return []

    def task(section, *, industry):
        calls.append(("task", section, industry))
        return "Semiconductor source note"

    result = prepare_filing_generation("semiconductor", "supply-chain", 2025, capture, evidence, gaps, task)
    assert result.snapshot["industry"] == "semiconductor"
    assert result.evidence[0]["evidence_id"] == "ev-semi"
    assert calls == [
        ("capture", 2025, "semiconductor"),
        ("evidence", "supply-chain", "semiconductor"),
        ("gaps", "supply-chain", "semiconductor"),
        ("task", "supply-chain", "semiconductor"),
    ]


@pytest.mark.parametrize("slug", ["semiconductor", "ai-computing"])
def test_mismatched_snapshot_is_rejected_before_evidence_adapter(slug):
    calls = []

    def capture(year, **kwargs):
        return {"industry": "different-industry", "mode": "live"}

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Evidence adapter must not run")

    with pytest.raises(DataUnavailable, match="industry mismatch"):
        prepare_filing_generation(slug, "technology", 2025, capture, forbidden, forbidden, forbidden)
    assert calls == []


def test_unknown_sector_is_rejected_before_capture():
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Provider must not run")

    with pytest.raises(ValueError, match="No integrated SEC filing source profile"):
        prepare_filing_generation(
            "not-enabled", "technology", 2025, forbidden, forbidden, forbidden, forbidden
        )
    assert calls == []


def test_new_profile_cannot_omit_industry_identity():
    calls = []

    def capture(year, *, industry):
        return {"mode": "live"}

    def forbidden(*args, **kwargs):
        calls.append(True)

    with pytest.raises(DataUnavailable, match="industry mismatch"):
        prepare_filing_generation(
            "semiconductor", "competition", 2025, capture, forbidden, forbidden, forbidden
        )
    assert not calls
