"""Reviewed SEC filing source universes for narrow industry research pilots.

A listed ticker is an illustrative issuer, not proof of value-chain role or
comprehensive industry coverage. Only the configured SEC 10-K pipeline may use
these universes; Canadian-only issuers and SEC 20-F filers are not implied.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SECFilingSource:
    slug: str
    label: str
    peers: tuple[str, ...]
    topic_terms: dict[str, tuple[str, ...]]
    limitations: str


AI_TOPICS = {
    "technology": (
        "artificial intelligence",
        "semiconductors",
        "semiconductor",
        "accelerators",
        "accelerator",
        "advanced packaging",
        "high bandwidth memory",
        "data centers",
        "data center",
    ),
    "supply-chain": ("supply chain", "manufacturing", "advanced packaging", "customer demand"),
    "competition": ("competition", "risk factors", "customer demand"),
}

SEMICONDUCTOR_TOPICS = {
    "technology": (
        "semiconductor",
        "semiconductors",
        "lithography",
        "wafer",
        "etch",
        "deposition",
        "process technology",
        "advanced packaging",
        "memory",
        "foundry",
    ),
    "supply-chain": (
        "supply chain",
        "manufacturing",
        "wafer",
        "foundry",
        "fabrication",
        "advanced packaging",
        "equipment",
        "customer demand",
        "capacity",
    ),
    "competition": (
        "competition",
        "competitive",
        "competitors",
        "customer concentration",
        "customer demand",
        "risk factors",
    ),
}

SEC_FILING_SOURCES: dict[str, SECFilingSource] = {
    "ai-computing": SECFilingSource(
        slug="ai-computing",
        label="AI Computing infrastructure",
        peers=("NVDA", "AMD", "INTC", "AVGO", "MU"),
        topic_terms=AI_TOPICS,
        limitations="Selected U.S. issuers only; not a census of AI infrastructure.",
    ),
    "semiconductor": SECFilingSource(
        slug="semiconductor",
        label="Global semiconductor supply chains",
        peers=("NVDA", "INTC", "MU", "AMAT", "LRCX"),
        topic_terms=SEMICONDUCTOR_TOPICS,
        limitations=(
            "Only selected U.S. SEC 10-K issuers; international foundries and non-U.S. "
            "manufacturing supply chains are not covered by this pilot."
        ),
    ),
}


def sec_filing_source(slug: str) -> SECFilingSource:
    try:
        return SEC_FILING_SOURCES[slug]
    except KeyError:
        raise ValueError("No integrated SEC filing source profile for this industry") from None


def validate_filing_sources() -> None:
    for slug, source in SEC_FILING_SOURCES.items():
        if source.slug != slug or len(source.peers) != 5 or len(set(source.peers)) != 5:
            raise ValueError("Invalid SEC industry issuer universe")
        if any(not ticker.isupper() or not ticker.isalnum() for ticker in source.peers):
            raise ValueError("Invalid SEC industry ticker")
        if set(source.topic_terms) != {"technology", "supply-chain", "competition"}:
            raise ValueError("Unimplemented SEC industry research topic")
        for terms in source.topic_terms.values():
            if not terms or len(set(terms)) != len(terms):
                raise ValueError("Empty or duplicate SEC topic terms")
            if any(term != term.lower() or len(term) < 3 for term in terms):
                raise ValueError("Invalid SEC topic term")


validate_filing_sources()
