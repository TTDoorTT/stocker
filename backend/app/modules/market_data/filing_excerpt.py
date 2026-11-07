"""Bounded SEC filing text retrieval for the AI Computing evidence pilot.

Only server-derived, allowlisted SEC 10-K primary documents are retrieved.
A match is a literal text excerpt, NOT a validated accounting/sector claim.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx

from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.sec import SecProvider

SEC_DOCUMENT = re.compile(
    r"^https://www\.sec\.gov/Archives/edgar/data/[1-9][0-9]*/[0-9]{18}/"
    r"[A-Za-z0-9_.-]{1,180}\.(?:htm|html|txt)$",
    re.IGNORECASE,
)
TERMS = re.compile(
    r"\b(?:supply chain|manufacturing|data centers?|artificial intelligence|"
    r"semiconductors?|advanced packaging|high bandwidth memory|"
    r"customer demand|competition|risk factors|accelerators?)\b",
    re.IGNORECASE,
)
MAX_DOCUMENT_BYTES = 8_000_000
MAX_DOCUMENTS = 3
MAX_EXCERPTS_PER_DOCUMENT = 3
MAX_EXCERPT_CHARS = 360
CACHE_SECONDS = 24 * 3600


class _VisibleText(HTMLParser):
    """Flatten readable HTML text without parsing or executing source markup."""

    BLOCKS = {"p", "div", "li", "br", "tr", "td", "th", "h1", "h2", "h3", "h4", "section"}
    IGNORE = {"script", "style", "noscript", "ix:header", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs):
        if self.hidden:
            self.hidden += 1
        elif tag in self.IGNORE:
            self.hidden = 1
        elif tag in self.BLOCKS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str):
        if self.hidden:
            self.hidden -= 1
        elif tag in self.BLOCKS:
            self.parts.append(" ")

    def handle_data(self, data: str):
        if not self.hidden:
            self.parts.append(data)


def extract_passages(document: str) -> list[dict]:
    """Return a few short literal matches; don't pretend to identify SEC Items."""
    parser = _VisibleText()
    parser.feed(document)
    parser.close()
    normalized = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    # Huge filings are deliberately not fully indexed by this pilot.
    normalized = normalized[:1_200_000]
    found: list[dict] = []
    seen: set[str] = set()
    for match in TERMS.finditer(normalized):
        start = max(0, match.start() - 125)
        end = min(len(normalized), start + MAX_EXCERPT_CHARS)
        excerpt = normalized[start:end].strip()
        if len(excerpt) < 100:
            continue
        signature = excerpt[:95].casefold()
        if signature in seen:
            continue
        seen.add(signature)
        found.append({"matched_term": match.group(0), "text": excerpt})
        if len(found) >= MAX_EXCERPTS_PER_DOCUMENT:
            break
    return found


def _fetch_document(sec: SecProvider, url: str) -> tuple[str, str, bool]:
    if not SEC_DOCUMENT.fullmatch(url) or urlsplit(url).query or urlsplit(url).fragment:
        raise DataUnavailable("SEC document URL was rejected by the filing allowlist")
    headers = sec.headers()
    http = sec.http
    cache_key = ("sec-primary-document", url)
    with http.lock:
        existing = http.cache.get(cache_key)
        if existing and existing[0] > time.monotonic():
            return existing[1], existing[2].isoformat(), True
        # Serialize with existing ProviderHTTP SEC calls and share its pacing.
        pause = 0.25 - (time.monotonic() - http.last.get("www.sec.gov", 0))
        if pause > 0:
            time.sleep(pause)
        http.last["www.sec.gov"] = time.monotonic()
        try:
            with http.client.stream("GET", url, headers=headers) as response:
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
    """Consume only filing URLs already derived from the SEC submissions API."""
    result = {
        "industry": "ai-computing",
        "year": snapshot["year"],
        "mode": snapshot["mode"],
        "excerpts": [],
        "gaps": [],
        "coverage": "Selected recent SEC 10-K primary documents; not full-text research or industry coverage.",
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
    for item in documents:
        try:
            document, fetched, cached = _fetch_document(sec, item["source_url"])
            matches = extract_passages(document)
            if not matches:
                result["gaps"].append(f"{item['symbol']}: no usable matching passages in the bounded text.")
            for passage in matches:
                result["excerpts"].append(
                    {
                        "symbol": item["symbol"],
                        "form": "10-K",
                        "filed": item["filed"],
                        "matched_term": passage["matched_term"],
                        "text": passage["text"],
                        "source_name": "SEC EDGAR primary filing",
                        "source_url": item["source_url"],
                        "fetched_at": fetched,
                        "cached": cached,
                    }
                )
        except DataUnavailable as exc:
            result["gaps"].append(f"{item['symbol']}: {exc}")
    result["gaps"].append(
        "Excerpts are literal keyword matches, not verified SEC Item boundaries or evidence of industry-wide trends."
    )
    result["gaps"].append(
        "Documents are limited to a few selected, recent 10-K filings and may differ from the requested financial frame year."
    )
    return result
