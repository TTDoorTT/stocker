"""Bounded second-pass claim screening for sourced industry filing notes.

The reviewer may be the *same* model as the author: its judgments are not
independent verification or proof of semantic entailment. Reject unknown IDs,
missing assessments, unsupported claims and inconclusive review outputs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings
from app.modules.research.agents.client import ModelClient
from app.modules.research.errors import ModelError

MAX_CLAIMS = 3
MAX_EVIDENCE = 9
# Keep consistent with Claim.text max_length in research/schemas.py.
MAX_CLAIM_CHARS = 2000


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Assessment(_Strict):
    claim_index: int = Field(ge=0, le=MAX_CLAIMS - 1)
    verdict: Literal["supported", "unsupported", "insufficient"]
    supporting_evidence_ids: list[str] = Field(min_length=1, max_length=MAX_EVIDENCE)
    reason: str = Field(min_length=8, max_length=400)


class _Review(_Strict):
    assessments: list[_Assessment] = Field(min_length=1, max_length=MAX_CLAIMS)


class _NoTools:
    """No extra data retrieval or tool execution during review."""

    definitions: list[dict] = []

    @staticmethod
    def call(name: str, args: dict):
        raise ModelError("Claim review may not invoke tools")


def screen_filing_claims(claims: list[dict], evidence: list[dict], settings: Settings) -> dict:
    """Fail closed unless every short claim is accepted against cited excerpts.

    The upstream report schema/citation validator must run first. The judge
    cannot invent source IDs, change claims, or overrule the author's citations.
    """
    if not isinstance(claims, list) or not 1 <= len(claims) <= MAX_CLAIMS:
        raise ValueError("Filing review requires one to three validated claims")
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= MAX_EVIDENCE:
        raise ValueError("Filing review requires bounded captured evidence")
    by_id = {}
    for record in evidence:
        if not isinstance(record, dict) or not isinstance(record.get("evidence_id"), str):
            raise ValueError("Filing review received invalid evidence")
        if record["evidence_id"] in by_id:
            raise ValueError("Filing review received duplicate evidence IDs")
        if not isinstance(record.get("field"), str) or not record["field"].startswith("sec_10k_excerpt_"):
            raise ValueError("Filing review received non-filing evidence")
        by_id[record["evidence_id"]] = record

    request_claims = []
    used_ids: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise ValueError("Filing review received malformed claim")
        body = claim.get("text")
        ids = claim.get("evidence_ids")
        if not isinstance(body, str) or not 1 <= len(body) <= MAX_CLAIM_CHARS:
            raise ValueError("Filing review claim length exceeds bounded limit")
        if not isinstance(ids, list) or not ids or len(ids) > MAX_EVIDENCE:
            raise ValueError("Filing review requires source citations for each claim")
        if any(not isinstance(item, str) for item in ids) or len(ids) != len(set(ids)):
            raise ValueError("Filing review received invalid or duplicate citation IDs")
        if set(ids) - by_id.keys():
            raise ValueError("Filing review claim cites unknown evidence")
        if claim.get("value") is not None or claim.get("calculation_ids"):
            raise ValueError("Filing review accepts qualitative claims only")
        used_ids.update(ids)
        request_claims.append({"claim_index": index, "text": body, "evidence_ids": ids})

    records = []
    for evidence_id in sorted(used_ids):
        row = by_id[evidence_id]
        value = row.get("value")
        if not isinstance(value, str) or "issuer text (untrusted): " not in value:
            raise ValueError("Filing review cannot isolate original captured issuer text")
        excerpt = value.split("issuer text (untrusted): ", 1)[1]
        if not excerpt.strip() or len(excerpt) > 500:
            raise ValueError("Filing review received missing or oversized issuer excerpt")
        records.append(
            {
                "evidence_id": evidence_id,
                "symbol": row.get("symbol"),
                "source_url": row.get("source_url"),
                "issuer_excerpt": excerpt,
            }
        )

    # Reviewer uses the same configured endpoint but a smaller single-response
    # output budget. This is additional cost and can fail if the model is offline.
    review_settings = settings.model_copy(update={"llm_max_tokens": min(settings.llm_max_tokens, 2048)})
    raw = ModelClient(review_settings).complete(
        "claim_review",
        {"claims": request_claims, "cited_issuer_excerpts": records},
        _Review.model_json_schema(),
        _NoTools(),
    )
    output = _Review.model_validate(raw)
    if len(output.assessments) != len(request_claims):
        raise ValueError("Claim reviewer omitted one or more claims")
    seen: set[int] = set()
    for item in output.assessments:
        if item.claim_index in seen or item.claim_index >= len(request_claims):
            raise ValueError("Claim reviewer returned duplicate or invalid indices")
        seen.add(item.claim_index)
        expected = set(request_claims[item.claim_index]["evidence_ids"])
        if set(item.supporting_evidence_ids) != expected or len(item.supporting_evidence_ids) != len(
            expected
        ):
            raise ValueError("Claim reviewer changed or omitted cited evidence IDs")
        if item.verdict != "supported":
            raise ValueError("Claim review rejected unsupported or insufficiently supported research")
    if seen != set(range(len(request_claims))):
        raise ValueError("Claim reviewer did not cover every claim")

    return {
        "status": "model_screened",
        "method": "same_configured_model_second_pass",
        "model_id": settings.llm_model,
        "claims_reviewed": len(request_claims),
        "limitations": (
            "Second-pass model judgment is not independent verification or proof of support. "
            "Original SEC excerpts may omit context."
        ),
        "assessments": [item.model_dump() for item in output.assessments],
    }
