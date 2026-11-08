"""Explain bounded SEC excerpt coverage without treating it as a quality score.

Only accepted, citation-ready Evidence records count. This module makes no
network or model calls and does not claim that a selected issuer represents a
sector. An accepted excerpt is not necessarily cited by the generated answer.
"""

from __future__ import annotations

from app.contracts.industry_sources import sec_filing_source


def filing_coverage(industry: str, section: str, evidence: list[dict]) -> dict:
    source = sec_filing_source(industry)
    if section not in source.topic_terms:
        raise ValueError("No filing evidence topic configured for this section")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Filing coverage requires accepted evidence records")

    represented: set[str] = set()
    expected_field = f"sec_10k_excerpt_{section.replace('-', '_')}"
    for record in evidence:
        if not isinstance(record, dict):
            raise ValueError("Malformed filing evidence record")
        symbol = record.get("symbol")
        if symbol not in source.peers:
            raise ValueError("Filing evidence contains an unapproved issuer")
        if record.get("field") != expected_field:
            raise ValueError("Filing evidence does not match the requested topic")
        represented.add(symbol)

    selected = list(source.peers)
    available = [symbol for symbol in selected if symbol in represented]
    missing = [symbol for symbol in selected if symbol not in represented]
    limitation = (
        f"Accepted SEC passages represent {len(available)} of {len(selected)} preselected U.S. issuers "
        f"for {section}. This is not industry-wide coverage, independent verification, or a count "
        "of claims actually supported by these excerpts."
    )
    return {
        "selected_issuers": selected,
        "represented_issuers": available,
        "missing_issuers": missing,
        "accepted_excerpts": len(evidence),
        "limitation": limitation,
    }
