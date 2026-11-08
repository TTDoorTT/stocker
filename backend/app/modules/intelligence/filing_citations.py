"""Report which accepted SEC passages are cited by model-screened claims.

A model-reviewed citation is not independent proof that a claim is true.
This reads only previously captured Evidence and claim-review metadata. It
never fetches SEC filings, calls an LLM, or infers sector-wide coverage.
"""

from __future__ import annotations


def cited_filing_coverage(coverage: dict, evidence: list[dict], review: object) -> dict | None:
    """Count distinct cited evidence IDs and their issuers; None when not measured.

    Older reports and mocked generation calls may omit detailed reviewer
    assessments. In those cases do not invent cited-issuer measurements.
    Malformed *present* assessments fail closed before report persistence.
    """
    if not isinstance(review, dict) or review.get("status") != "model_screened":
        return None
    assessments = review.get("assessments")
    if assessments is None:
        return None
    if not isinstance(assessments, list) or not assessments:
        raise ValueError("Claim citation coverage requires reviewer assessments")
    if review.get("claims_reviewed") != len(assessments):
        raise ValueError("Claim citation coverage received inconsistent claim counts")

    selected = coverage.get("selected_issuers")
    represented = coverage.get("represented_issuers")
    if not isinstance(selected, list) or not isinstance(represented, list):
        raise ValueError("Claim citation coverage requires accepted issuer coverage")
    if not all(isinstance(symbol, str) for symbol in selected + represented):
        raise ValueError("Claim citation coverage received malformed issuer names")
    if len(selected) != len(set(selected)) or len(represented) != len(set(represented)):
        raise ValueError("Claim citation coverage received duplicate issuers")
    if not set(represented).issubset(set(selected)):
        raise ValueError("Claim citation coverage received inconsistent issuer coverage")

    by_id: dict[str, str] = {}
    for record in evidence:
        if not isinstance(record, dict):
            raise ValueError("Claim citation coverage received malformed evidence")
        evidence_id, symbol = record.get("evidence_id"), record.get("symbol")
        if (
            not isinstance(evidence_id, str)
            or not evidence_id
            or evidence_id in by_id
            or symbol not in represented
        ):
            raise ValueError("Claim citation coverage received invalid or duplicate evidence IDs")
        by_id[evidence_id] = symbol
    if not by_id:
        raise ValueError("Claim citation coverage requires accepted filing excerpts")

    cited: set[str] = set()
    seen_indexes: set[int] = set()
    for assessment in assessments:
        if not isinstance(assessment, dict):
            raise ValueError("Claim citation coverage received malformed reviewer output")
        index = assessment.get("claim_index")
        if type(index) is not int or index < 0 or index >= len(assessments) or index in seen_indexes:
            raise ValueError("Claim citation coverage received duplicate or invalid claim indices")
        seen_indexes.add(index)
        if assessment.get("verdict") != "supported":
            raise ValueError("Claim citation coverage requires accepted claim reviews")
        ids = assessment.get("supporting_evidence_ids")
        if not isinstance(ids, list) or not ids or any(not isinstance(item, str) for item in ids):
            raise ValueError("Claim citation coverage received invalid supporting evidence IDs")
        if len(ids) != len(set(ids)):
            raise ValueError("Claim citation coverage received invalid supporting evidence IDs")
        if any(not isinstance(item, str) or item not in by_id for item in ids):
            raise ValueError("Claim citation coverage cites unknown evidence")
        cited.update(ids)
    if seen_indexes != set(range(len(assessments))):
        raise ValueError("Claim citation coverage is missing a claim assessment")

    cited_symbols = {by_id[item] for item in cited}
    return {
        "cited_issuers": [symbol for symbol in selected if symbol in cited_symbols],
        "uncited_represented_issuers": [symbol for symbol in represented if symbol not in cited_symbols],
        "cited_excerpts": len(cited),
        "model_screened_claims": len(assessments),
        "citation_limitation": (
            "Issuer counts reflect citations in model-screened claims, not independent "
            "verification, completeness of the SEC filing, or industry-wide representation."
        ),
    }
