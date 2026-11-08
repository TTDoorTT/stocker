"""Attribute screened SEC research claims to their cited issuers.

Issuer attribution does not establish factual verification,
relative performance, or an independent company comparison.
"""

from __future__ import annotations

from app.modules.intelligence.filing_section import SEC_DOCUMENT


def issuer_findings(evidence: list[dict], claims: object, review: object) -> list[dict]:
    """Build structured findings only from screened claims and accepted evidence."""
    if not isinstance(review, dict) or review.get("status") != "model_screened":
        return []
    if claims is None:
        return []

    assessments = review.get("assessments")
    if not isinstance(claims, list) or not isinstance(assessments, list):
        raise ValueError("Issuer findings require complete review metadata")
    if not claims or len(claims) != len(assessments) or review.get("claims_reviewed") != len(claims):
        raise ValueError("Issuer findings require one review per claim")

    sources: dict[str, dict] = {}
    for record in evidence:
        if not isinstance(record, dict):
            raise ValueError("Issuer findings received malformed evidence")

        evidence_id = record.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id or evidence_id in sources:
            raise ValueError("Issuer findings received invalid evidence IDs")

        if (
            not isinstance(record.get("symbol"), str)
            or not record["symbol"]
            or not isinstance(record.get("source_url"), str)
            or not SEC_DOCUMENT.fullmatch(record["source_url"])
        ):
            raise ValueError("Issuer findings require attributable SEC sources")

        sources[evidence_id] = record

    checks: dict[int, dict] = {}

    for item in assessments:
        if not isinstance(item, dict):
            raise ValueError("Issuer findings received malformed assessment")

        index = item.get("claim_index")
        if type(index) is not int or index < 0 or index >= len(claims) or index in checks:
            raise ValueError("Issuer findings received invalid claim indexes")

        if item.get("verdict") != "supported":
            raise ValueError("Issuer findings require supported claims")

        checks[index] = item

    output = []

    for index, claim in enumerate(claims):
        if not isinstance(claim, dict) or not isinstance(claim.get("text"), str) or not claim["text"].strip():
            raise ValueError("Issuer findings received malformed claims")

        ids = claim.get("evidence_ids")

        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids):
            raise ValueError("Issuer findings require evidence IDs")

        if len(ids) != len(set(ids)) or any(x not in sources for x in ids):
            raise ValueError("Issuer findings include unknown or duplicate citations")

        reviewed_ids = checks[index].get("supporting_evidence_ids")

        if (
            not isinstance(reviewed_ids, list)
            or len(reviewed_ids) != len(ids)
            or set(reviewed_ids) != set(ids)
        ):
            raise ValueError("Issuer findings disagree with screened citations")

        cited = [sources[x] for x in ids]
        issuers = list(dict.fromkeys(row["symbol"] for row in cited))

        output.append(
            {
                "claim_index": index,
                "text": claim["text"],
                "issuers": issuers,
                "scope": "single_issuer" if len(issuers) == 1 else "multiple_issuers",
                "citations": [
                    {
                        "evidence_id": evidence_id,
                        "symbol": row["symbol"],
                        "source_url": row["source_url"],
                    }
                    for evidence_id, row in zip(ids, cited, strict=True)
                ],
            }
        )

    return output
