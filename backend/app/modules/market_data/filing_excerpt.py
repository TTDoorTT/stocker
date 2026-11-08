"""Bounded SEC 10-K passage retrieval with deterministic topic ranking.

This is *not* a SEC section parser: Item headings are hints, not verified
boundaries. Issuer statements are untrusted source text, not instructions.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from app.contracts.industry_sources import sec_filing_source
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.sec import SecProvider

SEC_DOCUMENT = re.compile(
    r"^https://www\.sec\.gov/Archives/edgar/data/[1-9][0-9]*/[0-9]{18}/"
    r"[A-Za-z0-9_.-]{1,180}\.(?:htm|html|txt)$",
    re.IGNORECASE,
)

# These exact terms preserve compatibility with intelligence/filing_section.py.
TOPIC_TERMS = {
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
TOPICS = tuple(TOPIC_TERMS)
WORD_WEIGHTS = {
    "supply chain": 5,
    "high bandwidth memory": 5,
    "advanced packaging": 5,
    "artificial intelligence": 4,
    "competition": 4,
    "customer demand": 4,
    "risk factors": 3,
    "manufacturing": 3,
    "semiconductors": 3,
    "semiconductor": 3,
    "data centers": 3,
    "data center": 3,
    "accelerators": 3,
    "accelerator": 3,
}

TERMS = re.compile(
    r"\b(?:" + "|".join(re.escape(x) for x in sorted(WORD_WEIGHTS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
HEADING = re.compile(
    r"^item\s+(1a|1|7a|7)\s*[.\-:]?\s*"
    r"(business|risk\s+factors|management.{0,75}|quantitative.{0,75})?\s*$",
    re.IGNORECASE,
)
MAX_DOCUMENT_BYTES = 8_000_000
MAX_VISIBLE_CHARS = 2_400_000
MAX_DOCUMENTS = 5
MAX_PASSAGES_PER_TOPIC = 2
MAX_EXCERPT_CHARS = 360
MAX_CANDIDATES_PER_TOPIC = 2500
CACHE_SECONDS = 24 * 3600


class _VisibleText(HTMLParser):
    """Collect text blocks; exclude scripts/styles/headers and never execute markup."""

    BLOCKS = {"p", "div", "li", "br", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "section"}
    IGNORE = {"script", "style", "noscript", "head", "ix:header"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.parts: list[str] = []
        self.hidden: str | None = None
        self.hidden_depth = 0

    def _flush(self) -> None:
        body = " ".join(" ".join(self.parts).split())
        self.parts.clear()
        if body:
            self.blocks.append(body)

    def handle_starttag(self, tag: str, attrs) -> None:
        if self.hidden:
            if tag == self.hidden:
                self.hidden_depth += 1
            return
        if tag in self.IGNORE:
            self._flush()
            self.hidden = tag
            self.hidden_depth = 1
        elif tag in self.BLOCKS:
            self._flush()

    def handle_startendtag(self, tag: str, attrs) -> None:
        if not self.hidden and tag in self.BLOCKS:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if self.hidden:
            if tag == self.hidden:
                self.hidden_depth -= 1
                if self.hidden_depth == 0:
                    self.hidden = None
            return
        if tag in self.BLOCKS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def _blocks(document: str) -> list[tuple[str, str | None]]:
    """Attach a best-effort Item heading cue, never a verified SEC Item label."""
    if "<" in document[:300]:
        reader = _VisibleText()
        reader.feed(document[: MAX_VISIBLE_CHARS * 2])
        reader.close()
        reader._flush()
        blocks = reader.blocks
    else:
        blocks = re.split(r"\n\s*\n", document[:MAX_VISIBLE_CHARS])

    output: list[tuple[str, str | None]] = []
    hint: str | None = None
    total = 0
    for block in blocks:
        clean = " ".join(block.split())
        if not clean:
            continue
        total += len(clean)
        if total > MAX_VISIBLE_CHARS:
            break
        if len(clean) <= 110:
            heading = HEADING.fullmatch(clean)
            if heading:
                item = heading.group(1).upper()
                hint = f"Item {item} (unverified heading cue)"
                continue
        output.append((clean, hint))
    return output


# Detect likely sentence boundaries rather than clipping arbitrary characters.
_SENTENCE_GAP = re.compile(r'(?<=[.!?])\s+(?=[A-Z“"(])')
_ABBREVIATION = re.compile(
    r"(?:\b(?:U\.S|U\.K|e\.g|i\.e|Dr|Mr|Mrs|Ms|vs))\.$",
    re.IGNORECASE,
)
_SENTENCE_END = re.compile(r"""[.!?]["'\u201d)\]]*$""")


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Select sentence-shaped spans, rejecting unfinished trailing fragments."""
    spans: list[tuple[int, int]] = []
    start = 0

    for gap in _SENTENCE_GAP.finditer(text):
        if _ABBREVIATION.search(text[max(start, gap.start() - 14) : gap.start()]):
            continue

        end = gap.start()
        if _SENTENCE_END.search(text[start:end].rstrip()):
            spans.append((start, end))
            start = gap.end()

    if _SENTENCE_END.search(text[start:].rstrip()):
        spans.append((start, len(text)))

    return spans


def _excerpt(
    text: str,
    position: int,
    spans: list[tuple[int, int]] | None = None,
) -> str:
    """Prefer complete sentences within the existing excerpt limit.

    Skip overlong or incomplete spans instead of silently truncating
    qualifications. These remain heuristic, unverified source boundaries.
    """
    sentences = _sentence_spans(text) if spans is None else spans

    index = next(
        (i for i, (start, end) in enumerate(sentences) if start <= position < end),
        None,
    )

    if index is None:
        return ""

    left = right = index

    if sentences[right][1] - sentences[left][0] > MAX_EXCERPT_CHARS:
        return ""

    # Expand short sentences to retain enough context for quality screening.
    while sentences[right][1] - sentences[left][0] < 100 and right + 1 < len(sentences):
        if sentences[right + 1][1] - sentences[left][0] > MAX_EXCERPT_CHARS:
            break
        right += 1

    while sentences[right][1] - sentences[left][0] < 100 and left > 0:
        if sentences[right][1] - sentences[left - 1][0] > MAX_EXCERPT_CHARS:
            break
        left -= 1

    if sentences[right][1] - sentences[left][0] < 100:
        return ""

    # Include a following caveat when it fits without truncation.
    if right + 1 < len(sentences) and sentences[right + 1][1] - sentences[left][0] <= MAX_EXCERPT_CHARS:
        right += 1

    return text[sentences[left][0] : sentences[right][1]].strip()


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def _near_duplicate(left: str, right: str) -> bool:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= 0.78


def extract_passages(document: str, *, topic_terms: dict[str, tuple[str, ...]] | None = None) -> list[dict]:
    """Find balanced topic excerpts, not just the first three regex matches.

    Per-topic ranking and deduplication are deterministic. Some text can be
    reused across different topics when the filing supports both, because the
    existing evidence adapter selects by its exact matched_term contract.
    """
    topics = TOPIC_TERMS if topic_terms is None else topic_terms
    weights = (
        WORD_WEIGHTS
        if topic_terms is None
        else {term: WORD_WEIGHTS.get(term, 3) for values in topics.values() for term in values}
    )
    matcher = (
        TERMS
        if topic_terms is None
        else re.compile(
            r"\b(?:" + "|".join(re.escape(x) for x in sorted(weights, key=len, reverse=True)) + r")\b",
            re.IGNORECASE,
        )
    )
    candidates: dict[str, list[dict]] = defaultdict(list)
    position = 0
    for paragraph, heading in _blocks(document):
        matches = list(matcher.finditer(paragraph))
        if not matches:
            position += len(paragraph)
            continue
        spans = _sentence_spans(paragraph)
        for topic, allowed in topics.items():
            relevant = [m for m in matches if m.group(0).casefold() in allowed]
            if not relevant or len(candidates[topic]) >= MAX_CANDIDATES_PER_TOPIC:
                continue
            # Try the strongest keyword first; skip an overlong sentence
            # rather than cutting it and losing important source qualifiers.
            for best in sorted(
                relevant,
                key=lambda m: (-weights[m.group(0).casefold()], m.start()),
            ):
                excerpt = _excerpt(paragraph, best.start(), spans)
                if 100 <= len(excerpt) <= MAX_EXCERPT_CHARS:
                    break
            else:
                continue
            names = {m.group(0).casefold() for m in matcher.finditer(excerpt)}
            distinct = len(names.intersection(allowed))
            score = 10 + weights[best.group(0).casefold()] * 3 + min(distinct, 4) * 2
            if heading:
                score += 2
                if topic == "competition" and "1A" in heading:
                    score += 4
                if topic in {"technology", "supply-chain"} and "Item 1 " in heading:
                    score += 4
            candidates[topic].append(
                {
                    "matched_term": best.group(0),
                    "text": excerpt,
                    "topic": topic,
                    "section_hint": heading,
                    "relevance_score": score,
                    "_offset": position + best.start(),
                }
            )
        position += len(paragraph)

    selected: list[dict] = []
    for topic in TOPICS:
        ranked = sorted(candidates[topic], key=lambda p: (-p["relevance_score"], p["_offset"]))
        chosen: list[dict] = []
        for candidate in ranked:
            if any(_near_duplicate(candidate["text"], x["text"]) for x in chosen):
                continue
            chosen.append(candidate)
            if len(chosen) >= MAX_PASSAGES_PER_TOPIC:
                break
        for item in chosen:
            item.pop("_offset")
        selected.extend(chosen)
    return selected


def _fetch_document(sec: SecProvider, url: str) -> tuple[str, str, bool]:
    """Use existing SEC transport and shared pacing, with no redirects."""
    if not SEC_DOCUMENT.fullmatch(url) or urlsplit(url).query or urlsplit(url).fragment:
        raise DataUnavailable("SEC document URL was rejected by the filing allowlist")
    headers = sec.headers()
    http = sec.http
    cache_key = ("sec-primary-document", url)
    with http.lock:
        existing = http.cache.get(cache_key)
        if existing and existing[0] > time.monotonic():
            return existing[1], existing[2].isoformat(), True
        pause = 0.25 - (time.monotonic() - http.last.get("www.sec.gov", 0))
        if pause > 0:
            time.sleep(pause)
        http.last["www.sec.gov"] = time.monotonic()
        try:
            with http.client.stream("GET", url, headers=headers, follow_redirects=False) as response:
                if response.status_code != 200:
                    raise DataUnavailable(f"SEC document HTTP {response.status_code}")
                content_type = response.headers.get("content-type", "").lower()
                if content_type and not any(
                    label in content_type for label in ("text/html", "text/plain", "application/xhtml+xml")
                ):
                    raise DataUnavailable("SEC document was not returned as HTML/text")
                raw = bytearray()
                for chunk in response.iter_bytes():
                    if len(raw) + len(chunk) > MAX_DOCUMENT_BYTES:
                        raise DataUnavailable("SEC document exceeds bounded retrieval limit")
                    raw.extend(chunk)
        except httpx.HTTPError:
            raise DataUnavailable("SEC document unavailable or access denied") from None
        document = raw.decode("utf-8", errors="replace")
        fetched = datetime.now(UTC)
        http.cache[cache_key] = (time.monotonic() + CACHE_SECONDS, document, fetched)
        return document, fetched.isoformat(), False


def filing_excerpts(sec: SecProvider, snapshot: dict) -> dict:
    """Consume only 10-K URLs from validated SEC submissions metadata."""
    industry = snapshot.get("industry", "ai-computing")
    source = sec_filing_source(industry)
    result = {
        "industry": industry,
        "year": snapshot["year"],
        "mode": snapshot["mode"],
        "excerpts": [],
        "gaps": [],
        "coverage": (
            "Selected recent SEC 10-K documents; up to five issuers and two excerpts per topic per issuer. "
            "Relevance is heuristic; Item headings are unverified cues."
        ),
    }
    if snapshot["mode"] != "live":
        result["gaps"].append(
            "SEC filing text is unavailable in fixture mode; no fake excerpts are generated."
        )
        return result

    documents = []
    seen = set()
    for row in snapshot.get("filings", []):
        if row.get("form") != "10-K" or row.get("symbol") in seen:
            continue
        if not SEC_DOCUMENT.fullmatch(str(row.get("source_url", ""))):
            continue
        documents.append(row)
        seen.add(row["symbol"])
        if len(documents) >= MAX_DOCUMENTS:
            break
    if not documents:
        result["gaps"].append("No safely addressable recent 10-K primary documents were identified.")
        return result

    per_company: dict[str, dict[str, list[dict]]] = {}
    for item in documents:
        symbol = item["symbol"]
        per_company[symbol] = {topic: [] for topic in TOPICS}
        try:
            document, fetched, cached = _fetch_document(sec, item["source_url"])
            selected = extract_passages(
                document, topic_terms=source.topic_terms if source.slug != "ai-computing" else None
            )
            if not selected:
                result["gaps"].append(f"{symbol}: no usable matching passages in the bounded text.")
            for passage in selected:
                per_company[symbol][passage["topic"]].append(
                    {
                        "symbol": symbol,
                        "form": "10-K",
                        "filed": item["filed"],
                        "matched_term": passage["matched_term"],
                        "text": passage["text"],
                        "topic": passage["topic"],
                        "section_hint": passage["section_hint"],
                        "relevance_score": passage["relevance_score"],
                        "source_name": "SEC EDGAR primary filing",
                        "source_url": item["source_url"],
                        "fetched_at": fetched,
                        "cached": cached,
                    }
                )
        except DataUnavailable as exc:
            result["gaps"].append(f"{symbol}: {exc}")

    # Balance coverage across issuers. The section adapter can safely select
    # its own topic from the first 50 rows without one company dominating.
    for topic in TOPICS:
        for rank in range(MAX_PASSAGES_PER_TOPIC):
            for item in documents:
                matches = per_company[item["symbol"]][topic]
                if len(matches) > rank:
                    result["excerpts"].append(matches[rank])

    if source.slug == "semiconductor":
        result["gaps"].append(source.limitations)
    result["gaps"].extend(
        [
            "Item labels are heading-based guesses, NOT validated SEC Item boundaries.",
            "Passages are partial keyword-selected issuer statements, not independently established industry facts.",
            "Five selected U.S. issuers are not a complete industry census; financial frame year may differ from filing year.",
        ]
    )
    return result
