"""Offline coverage diagnostics: selected issuers are not a sector census."""

import pytest

from app.modules.intelligence.filing_coverage import filing_coverage


def record(symbol: str, section: str = "technology") -> dict:
    return {
        "symbol": symbol,
        "field": f"sec_10k_excerpt_{section.replace('-', '_')}",
        "evidence_id": f"ev-{symbol}",
    }


@pytest.mark.parametrize(
    "industry,issuers",
    [
        ("ai-computing", ["NVDA", "AMD", "INTC", "AVGO", "MU"]),
        ("semiconductor", ["NVDA", "INTC", "MU", "AMAT", "LRCX"]),
        ("power-grid", ["GEV", "ETN", "HUBB", "PWR", "NEE"]),
    ],
)
def test_accepted_issuer_coverage_is_bounded(industry, issuers):
    result = filing_coverage(industry, "technology", [record(issuers[2]), record(issuers[0])])
    assert result["selected_issuers"] == issuers
    assert result["represented_issuers"] == [issuers[0], issuers[2]]
    assert result["missing_issuers"] == [issuers[1], issuers[3], issuers[4]]
    assert result["accepted_excerpts"] == 2
    assert "2 of 5" in result["limitation"]
    assert "not industry-wide" in result["limitation"]


def test_repeated_passages_count_once_per_issuer_but_each_as_an_excerpt():
    data = filing_coverage("semiconductor", "supply-chain", [record("AMAT", "supply-chain")] * 2)
    assert data["represented_issuers"] == ["AMAT"]
    assert data["accepted_excerpts"] == 2


@pytest.mark.parametrize("industry", ["semiconductor", "power-grid", "ai-computing"])
def test_cross_industry_or_mistopic_evidence_fails_closed(industry):
    with pytest.raises(ValueError, match="unapproved issuer"):
        filing_coverage(industry, "technology", [record("ZZZZ")])
    valid = filing_coverage(
        industry,
        "technology",
        [record({"semiconductor": "MU", "power-grid": "GEV", "ai-computing": "AMD"}[industry])],
    )
    assert valid["accepted_excerpts"] == 1
    with pytest.raises(ValueError, match="requested topic"):
        filing_coverage(industry, "supply-chain", [record(valid["represented_issuers"][0])])


def test_empty_and_nonfiler_inputs_do_not_claim_coverage():
    with pytest.raises(ValueError, match="accepted evidence"):
        filing_coverage("ai-computing", "technology", [])
    with pytest.raises(ValueError, match="Malformed"):
        filing_coverage("ai-computing", "technology", [None])
    with pytest.raises(ValueError, match="No filing evidence topic"):
        filing_coverage("ai-computing", "outlook", [record("NVDA")])
    with pytest.raises(ValueError, match="No integrated"):
        filing_coverage("invalid", "technology", [record("NVDA")])
