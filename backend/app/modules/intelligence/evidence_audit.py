"""Offline, human-reviewed SEC filing excerpt audit; no network, LLM, or writes to app DB.

A citation/source match does NOT establish that an issuer's passage supports an
AI-generated claim. The reviewer records source fidelity and contextual quality.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

from app.contracts.industry_sources import SEC_FILING_SOURCES

TOPICS = ("technology", "supply-chain", "competition")
SEC_DOCUMENT = re.compile(
    r"^https://www\.sec\.gov/Archives/edgar/data/[1-9][0-9]*/[0-9]{18}/"
    r"[A-Za-z0-9_.-]{1,180}\.(?:htm|html|txt)$",
    re.IGNORECASE,
)
IMMUTABLE = (
    "sample_id",
    "symbol",
    "topic",
    "matched_term",
    "source_url",
    "filed",
    "fetched_at",
    "relevance_score",
    "section_hint",
    "text_sha256",
    "excerpt_text",
)
REVIEW = ("reviewer", "source_match", "topic_relevance", "context_integrity", "decision", "notes")
FIELDS = IMMUTABLE + REVIEW
CHOICES = {
    "source_match": {"unreviewed", "exact", "partial", "mismatch", "unavailable"},
    "topic_relevance": {"unreviewed", "high", "medium", "low", "none"},
    "context_integrity": {"unreviewed", "intact", "truncated", "misleading"},
    "decision": {"unreviewed", "usable", "needs_context", "reject"},
}
MAX_SOURCE_SIZE = 8_000_000


def _hash(value: object) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _safe_cell(text: object) -> str:
    """Prevent CSV formula execution in Excel/Sheets, including whitespace prefixes."""
    value = str(text)
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def _valid_date(raw: object) -> bool:
    try:
        date.fromisoformat(str(raw))
        return True
    except (ValueError, TypeError):
        return False


def _valid_timestamp(raw: object) -> bool:
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except (TypeError, ValueError):
        return False


def _record(row: object) -> dict | None:
    if not isinstance(row, dict) or row.get("form") != "10-K":
        return None
    symbol = row.get("symbol")
    topic = row.get("topic")
    term = row.get("matched_term")
    url = row.get("source_url")
    body = row.get("text")
    if not (
        isinstance(symbol, str)
        and re.fullmatch(r"[A-Z]{1,8}", symbol)
        and topic in TOPICS
        and isinstance(term, str)
        and term.strip()
        and isinstance(url, str)
        and SEC_DOCUMENT.fullmatch(url)
        and isinstance(body, str)
        and 100 <= len(body) <= 400
        and _valid_date(row.get("filed"))
        and _valid_timestamp(row.get("fetched_at"))
    ):
        return None
    score = row.get("relevance_score")
    if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float))):
        return None
    section_hint = row.get("section_hint")
    if section_hint is not None and not isinstance(section_hint, str):
        return None
    identity = [symbol, topic, url, str(row["filed"]), term, body]
    return {
        "sample_id": "sec-" + _hash(identity)[:18],
        "symbol": symbol,
        "topic": topic,
        "matched_term": term,
        "source_url": url,
        "filed": str(row["filed"]),
        "fetched_at": str(row["fetched_at"]),
        "relevance_score": "" if score is None else str(score),
        "section_hint": "" if section_hint is None else section_hint,
        "text_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "excerpt_text": body,
    }


def select_candidates(payload: object, limit: int = 24) -> tuple[list[dict], dict]:
    """Deterministic topic/issuer round-robin; only genuine live Phase 3C rows."""
    if not isinstance(payload, dict) or payload.get("mode") != "live":
        raise ValueError("A live SEC filing-excerpts API response is required (not fixture data)")
    industry = payload.get("industry")
    if industry not in SEC_FILING_SOURCES:
        supported = ", ".join(sorted(SEC_FILING_SOURCES))
        raise ValueError(f"Unsupported SEC audit industry; configured pilots: {supported}")
    raw = payload.get("excerpts")
    if not isinstance(raw, list):
        raise ValueError("Expected an 'excerpts' list")
    if not 1 <= limit <= 60:
        raise ValueError("Sample limit must be from 1 to 60")
    if raw and not any(isinstance(r, dict) and "topic" in r for r in raw):
        raise ValueError("Phase 3C topic metadata not found: update/restart the extractor first")
    seen: set[str] = set()
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    invalid = 0
    for entry in raw:
        record = _record(entry)
        if record is None:
            invalid += 1
            continue
        if record["sample_id"] in seen:
            continue
        seen.add(record["sample_id"])
        buckets[(record["topic"], record["symbol"])].append(record)

    def rank(record: dict) -> tuple[float, str]:
        try:
            score = float(record["relevance_score"])
        except ValueError:
            score = 0
        return (-score, record["sample_id"])

    for bucket in buckets.values():
        bucket.sort(key=rank)
    symbols = sorted({symbol for _, symbol in buckets})
    groups = [(topic, symbol) for topic in TOPICS for symbol in symbols]
    selected: list[dict] = []
    issuer_counts: Counter = Counter()
    issuer_cap = max(2, (limit + max(len(symbols), 1) - 1) // max(len(symbols), 1) + 1)
    while len(selected) < limit:
        advanced = False
        for group in groups:
            if len(selected) >= limit:
                break
            if issuer_counts[group[1]] >= issuer_cap or not buckets[group]:
                continue
            record = buckets[group].pop(0)
            selected.append(record)
            issuer_counts[group[1]] += 1
            advanced = True
        if not advanced:
            break
    return selected, {
        "raw_excerpts": len(raw),
        "valid_unique_excerpts": len(seen),
        "invalid_excerpts": invalid,
        "selected": len(selected),
        "topic_counts": dict(sorted(Counter(row["topic"] for row in selected).items())),
        "issuer_counts": dict(sorted(issuer_counts.items())),
        "coverage_gaps": [str(g) for g in payload.get("gaps", []) if isinstance(g, str)][:100],
    }


def create_audit(payload: dict, directory: Path, limit: int = 24) -> dict:
    """Write immutable baseline and editable CSV; refuse to overwrite an audit."""
    records, coverage = select_candidates(payload, limit)
    if not records:
        raise ValueError("No usable passages to audit; check SEC access and the extracted topics")
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path, review_path = directory / "manifest.json", directory / "review.csv"
    if manifest_path.exists() or review_path.exists():
        raise FileExistsError("Audit already exists; use a new output folder to preserve earlier reviews")
    manifest = {
        "format_version": 1,
        "industry": payload["industry"],
        "purpose": "Manual SEC excerpt/source/context quality audit; not automated claim validation",
        "input_sha256": _hash(payload),
        "coverage": coverage,
        "records": records,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with review_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        writer.writeheader()
        for record in records:
            cells = {field: _safe_cell(record[field]) for field in IMMUTABLE}
            cells.update({field: "" if field in {"reviewer", "notes"} else "unreviewed" for field in REVIEW})
            writer.writerow(cells)
    return coverage


def summarize_audit(directory: Path, *, strict: bool = False) -> dict:
    """Reject changed evidence and invalid labels; never infer human judgments."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1:
        raise ValueError("Unsupported audit manifest version")
    expected = {r["sample_id"]: r for r in manifest["records"]}
    if len(expected) != len(manifest["records"]):
        raise ValueError("Duplicate sample IDs in manifest")
    with (directory / "review.csv").open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if set(reader.fieldnames or []) != set(FIELDS):
            raise ValueError("Review CSV columns do not match the expected audit format")
        rows = list(reader)
    if len(rows) != len(expected) or {r["sample_id"] for r in rows} != set(expected):
        raise ValueError("Review rows do not match original selected samples")
    for row in rows:
        original = expected[row["sample_id"]]
        for field in IMMUTABLE:
            if row[field] != _safe_cell(original[field]):
                raise ValueError(f"Source evidence changed for {row['sample_id']}: {field}")
        for field, allowed in CHOICES.items():
            if row[field] not in allowed:
                raise ValueError(f"Invalid {field} for {row['sample_id']}: {row[field]}")
        if row["decision"] == "usable" and (
            row["source_match"] != "exact"
            or row["topic_relevance"] not in {"high", "medium"}
            or row["context_integrity"] != "intact"
        ):
            raise ValueError(f"'usable' conflicts with recorded quality checks: {row['sample_id']}")
        if row["decision"] == "reject" and not row["notes"].strip():
            raise ValueError(f"Rejected evidence requires reviewer notes: {row['sample_id']}")
    complete = [
        r for r in rows if all(r[field] != "unreviewed" for field in CHOICES) and r["reviewer"].strip()
    ]
    unresolved = len(rows) - len(complete)
    result = {
        "sample_count": len(rows),
        "reviewed_count": len(complete),
        "unreviewed_count": unresolved,
        "decision_counts": dict(sorted(Counter(r["decision"] for r in rows).items())),
        "source_match_counts": dict(sorted(Counter(r["source_match"] for r in rows).items())),
        "topic_counts": manifest["coverage"].get("topic_counts", {}),
        "issuer_counts": manifest["coverage"].get("issuer_counts", {}),
        "rejected_sample_ids": [r["sample_id"] for r in rows if r["decision"] == "reject"],
        "flagged_sample_ids": [
            r["sample_id"]
            for r in rows
            if r["source_match"] == "mismatch" or r["context_integrity"] == "misleading"
        ],
        "audit_status": (
            "incomplete"
            if unresolved
            else "reviewed_with_quality_findings"
            if any(r["decision"] != "usable" for r in rows)
            else "reviewed_usable_sample"
        ),
    }
    if strict and unresolved:
        raise ValueError(f"Review incomplete: {unresolved} row(s) have unanswered criteria or no reviewer")
    return result


class _VisibleText(HTMLParser):
    IGNORE = {"script", "style", "noscript", "head", "ix:header"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.IGNORE and self.hidden is None:
            self.hidden = tag
        elif not self.hidden and tag in {"p", "div", "br", "li", "tr", "td", "h1", "h2"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == self.hidden:
            self.hidden = None
        if not self.hidden and tag in {"p", "div", "li", "tr", "td", "h1", "h2"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self.hidden is None:
            self.parts.append(data)


def verify_excerpt_in_document(excerpt: str, source: str) -> bool:
    """Whitespace-normalized exact substring check; NOT semantic entailment."""
    if "<" in source[:300]:
        parser = _VisibleText()
        parser.feed(source)
        parser.close()
        visible = " ".join(parser.parts)
    else:
        visible = source

    def normalize(value: str) -> str:
        return " ".join(value.split()).casefold()

    return normalize(excerpt) in normalize(visible)


def verify_local_source(directory: Path, sample_id: str, source_file: Path) -> dict:
    """Inspect previously saved SEC document bytes, never fetch remotely."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    row = next((r for r in manifest["records"] if r["sample_id"] == sample_id), None)
    if row is None:
        raise ValueError("Sample ID not found in audit manifest")
    if source_file.stat().st_size > MAX_SOURCE_SIZE:
        raise ValueError("Local SEC source exceeds 8 MB inspection limit")
    body = source_file.read_text(encoding="utf-8", errors="replace")
    return {
        "sample_id": sample_id,
        "source_url": row["source_url"],
        "normalized_exact_substring": verify_excerpt_in_document(row["excerpt_text"], body),
        "note": "Matching excerpt text does not establish full context or support any generated AI claim.",
    }
