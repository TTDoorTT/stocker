"""Industry AI-generation capabilities: one explicit, fail-closed backend registry.

Only profiles with a fully integrated source pipeline may enable generation.
A guided template or a representative company symbol is not authorization to
run the AI Computing pilot for another industry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ALL_SECTIONS = ("overview", "technology", "supply-chain", "competition", "outlook")
Pipeline = Literal["sec_rss_overview", "sec_filing_review"]


@dataclass(frozen=True)
class IndustryResearchProfile:
    slug: str
    source_profile: str
    pipelines: tuple[tuple[str, Pipeline], ...]
    coverage: str


# This is a capability registry, NOT a generic SEC peer-provider implementation.
# The named source profile must be implemented and verified separately before
# a new industry is enabled. All other industries stay guided-only.
_PROFILES = {
    "ai-computing": IndustryResearchProfile(
        slug="ai-computing",
        source_profile="ai-computing-sec-pilot",
        pipelines=(
            ("overview", "sec_rss_overview"),
            ("technology", "sec_filing_review"),
            ("supply-chain", "sec_filing_review"),
            ("competition", "sec_filing_review"),
        ),
        coverage=(
            "Limited AI Computing pilot: SEC/RSS overview and SEC filing-backed technology, "
            "supply-chain and competition notes. Outlook is guided-only. Selected U.S. "
            "issuers do not represent the entire industry."
        ),
    )
}

GUIDED_COVERAGE = (
    "Guided research only. Automated industry generation is disabled until a "
    "sector-specific evidence provider, validation rules and regression tests exist."
)


def validate_profiles(templates: list[dict]) -> None:
    """Refuse misconfigured deployments rather than silently enabling bad research."""
    slugs = [row.get("slug") for row in templates]
    if len(slugs) != len(set(slugs)) or any(not isinstance(s, str) for s in slugs):
        raise ValueError("Industry templates must have unique string slugs")
    if not set(_PROFILES).issubset(slugs):
        raise ValueError("Configured research profile has no industry template")
    for slug, profile in _PROFILES.items():
        if profile.slug != slug or profile.source_profile != "ai-computing-sec-pilot":
            raise ValueError("Unknown research source integration; generation disabled")
        configured = [section for section, _ in profile.pipelines]
        if len(configured) != len(set(configured)) or any(s not in ALL_SECTIONS for s in configured):
            raise ValueError("Invalid or duplicate research section capability")
        expected = {
            "overview": "sec_rss_overview",
            "technology": "sec_filing_review",
            "supply-chain": "sec_filing_review",
            "competition": "sec_filing_review",
        }
        if dict(profile.pipelines) != expected:
            raise ValueError("Research profile does not match implemented source pipelines")


def generation_pipeline(slug: str, section: str) -> Pipeline | None:
    """Return a backend-supported pipeline, not a UI hint or speculative plan."""
    profile = _PROFILES.get(slug)
    if profile is None or profile.source_profile != "ai-computing-sec-pilot":
        return None
    return dict(profile.pipelines).get(section)


def public_capabilities(slug: str) -> dict:
    """Expose conservative capability flags with each existing industry template."""
    profile = _PROFILES.get(slug)
    if profile is None:
        return {
            "research_status": "guided_only",
            "ai_sections": [],
            "research_coverage": GUIDED_COVERAGE,
        }
    return {
        "research_status": "limited_pilot",
        "ai_sections": [section for section in ALL_SECTIONS if generation_pipeline(slug, section)],
        "research_coverage": profile.coverage,
    }
