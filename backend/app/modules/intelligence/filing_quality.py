"""Conservative deterministic screening of SEC excerpt inputs for industry research.

Screening is NOT semantic entailment verification. It does not fetch URLs, invoke
models, or establish that a filing passage proves a generated claim.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

WORDS = re.compile(r"[a-z]+(?:'[a-z]+)?", re.IGNORECASE)
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "by",
        "can",
        "do",
        "for",
        "from",
        "has",
        "have",
        "in",
        "into",
        "is",
        "it",
        "its",
        "may",
        "of",
        "on",
        "or",
        "our",
        "that",
        "the",
        "their",
        "there",
        "these",
        "this",
        "those",
        "to",
        "was",
        "were",
        "we",
        "which",
        "will",
        "with",
        "would",
    }
)
# Examples of obviously instruction-like text appearing within untrusted inputs.
# This is a limited additional safeguard, not a complete prompt-injection defense.
INSTRUCTION = re.compile(
    r"\b(?:ignore (?:all )?(?:previous|prior) instructions|"
    r"reveal (?:your |the )?(?:system|developer) prompt|"
    r"you are (?:now )?(?:chatgpt|an ai assistant)|"
    r"assistant (?:must|should) disregard)\b",
    re.IGNORECASE,
)
MIN_WORDS = 14
MIN_CONTENT_WORDS = 7
MIN_UNIQUE_RATIO = 0.40
MAX_INPUTS = 50
MAX_SELECTED = 9
NEAR_DUPLICATE_JACCARD = 0.83


@dataclass(frozen=True)
class QualityResult:
    """Machine checks only, never a factual quality or truth score."""

    selected: list[dict]
    rejection_counts: dict[str, int]
    considered: int


def _words(text: str) -> list[str]:
    return [w.casefold() for w in WORDS.findall(text)]


def _has_term(text: str, term: str) -> bool:
    # Whole phrases, not a substring inside an unrelated word.
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.IGNORECASE))


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 1.0


def _check(row: dict, section: str, allowed_terms: frozenset[str]) -> str | None:
    body = row.get("text")
    term = row.get("matched_term")
    if not isinstance(body, str) or not isinstance(term, str):
        return "malformed_excerpt"
    body = " ".join(body.split())
    term = term.strip().casefold()
    if not 100 <= len(body) <= 400:
        return "length_outside_contract"
    if row.get("topic") is not None and row.get("topic") != section:
        return "topic_conflict"
    if term not in allowed_terms or not _has_term(body, term):
        return "topic_not_in_text"
    if INSTRUCTION.search(body):
        return "instruction_like_text"
    words = _words(body)
    if len(words) < MIN_WORDS:
        return "insufficient_context"
    content = [word for word in words if word not in STOPWORDS]
    if len(set(content)) < MIN_CONTENT_WORDS:
        return "low_information"
    if len(set(words)) / len(words) < MIN_UNIQUE_RATIO:
        return "repetitive_text"
    return None


def select_quality_excerpts(
    excerpts: object,
    section: str,
    allowed_terms: frozenset[str],
    *,
    limit: int = MAX_SELECTED,
) -> QualityResult:
    """Select bounded, topic-consistent, non-duplicative excerpts across issuers.

    Original order from the retrieval adapter is meaningful for relevance and
    issuer balancing. Within each issuer we preserve that order; each pass
    chooses one excerpt per issuer before accepting a second from that issuer.

    This check does not independently validate SEC URLs or filing metadata;
    those are still validated by capture_filing_section before constructing
    Evidence records.
    """
    if not isinstance(excerpts, list):
        return QualityResult([], {"malformed_response": 1}, 0)
    if not 1 <= limit <= MAX_SELECTED:
        raise ValueError("Quality excerpt selection limit is out of bounds")

    reasons: Counter[str] = Counter()
    eligible: dict[str, list[tuple[dict, set[str]]]] = {}
    issuer_order: list[str] = []
    considered = 0
    for row in excerpts[:MAX_INPUTS]:
        considered += 1
        if not isinstance(row, dict):
            reasons["malformed_excerpt"] += 1
            continue
        reason = _check(row, section, allowed_terms)
        if reason:
            reasons[reason] += 1
            continue
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            reasons["malformed_issuer"] += 1
            continue
        if symbol not in eligible:
            issuer_order.append(symbol)
            eligible[symbol] = []
        eligible[symbol].append((row, set(_words(str(row["text"])))))

    selected: list[dict] = []
    selected_tokens: dict[str, list[set[str]]] = {}
    for index in range(MAX_INPUTS):
        any_candidate = False
        for symbol in issuer_order:
            group = eligible[symbol]
            if index >= len(group):
                continue
            any_candidate = True
            row, tokens = group[index]
            # Compare only within the same issuer: different issuers may make
            # genuinely distinct disclosures using similar legal wording.
            previous = selected_tokens.setdefault(symbol, [])
            if any(_jaccard(tokens, old) >= NEAR_DUPLICATE_JACCARD for old in previous):
                reasons["near_duplicate"] += 1
                continue
            selected.append(row)
            previous.append(tokens)
            if len(selected) == limit:
                return QualityResult(selected, dict(sorted(reasons.items())), considered)
        if not any_candidate:
            break
    return QualityResult(selected, dict(sorted(reasons.items())), considered)
