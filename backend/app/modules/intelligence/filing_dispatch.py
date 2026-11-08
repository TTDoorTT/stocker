"""Profile-driven dispatch for validated SEC filing research evidence.

Only the original AI Computing source has a legacy positional capture contract.
New SEC industry profiles use explicit identity keyword arguments. Never infer
new industry capabilities from a template or ticker list.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.contracts.industry_sources import sec_filing_source
from app.modules.market_data.errors import DataUnavailable


@dataclass(frozen=True)
class FilingGenerationInputs:
    snapshot: dict
    evidence: list[dict]
    gaps: list[str]
    task: str


def prepare_filing_generation(
    slug: str,
    section: str,
    year: int,
    capture: Callable,
    build_evidence: Callable,
    build_gaps: Callable,
    build_task: Callable,
) -> FilingGenerationInputs:
    """Capture evidence using the integrated industry's approved SEC profile.

    The injected adapters deliberately preserve existing test seams. New source
    profiles use an explicit industry parameter and must return matching identity.
    The historical AI Computing test contract permits a missing identity field.
    """
    sec_filing_source(slug)  # Explicitly configured issuer/topic universe only.
    legacy = slug == "ai-computing"

    if legacy:
        snapshot = capture(year)
    else:
        snapshot = capture(year, industry=slug)
    if not isinstance(snapshot, dict):
        raise DataUnavailable("SEC filing source returned malformed industry evidence")
    identity = snapshot.get("industry")
    if identity != slug and not (legacy and identity is None):
        raise DataUnavailable("SEC filing source industry mismatch")

    if legacy:
        evidence = build_evidence(snapshot, section)
        gaps = build_gaps(section, snapshot)
        task = build_task(section)
    else:
        evidence = build_evidence(snapshot, section, industry=slug)
        gaps = build_gaps(section, snapshot, industry=slug)
        task = build_task(section, industry=slug)
    return FilingGenerationInputs(snapshot, evidence, gaps, task)
