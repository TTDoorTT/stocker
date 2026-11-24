"""Offline SEC evidence audit regression tests, with no requests or model calls."""

import csv
import json
from datetime import UTC, datetime

import pytest

from app.modules.intelligence.evidence_audit import (
    create_audit,
    select_candidates,
    summarize_audit,
    verify_excerpt_in_document,
    verify_local_source,
)

URL = "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm"


def excerpt(topic="technology", symbol="NVDA", extra=""):
    return {
        "symbol": symbol,
        "topic": topic,
        "form": "10-K",
        "matched_term": "artificial intelligence" if topic == "technology" else "manufacturing",
        "source_url": URL,
        "filed": "2026-03-01",
        "fetched_at": datetime.now(UTC).isoformat(),
        "relevance_score": 35,
        "section_hint": "Item 1 (unverified heading cue)",
        "text": (
            f"The illustrative issuer filing describes {topic} in an operational context. "
            "This passage is synthetic test material rather than an actual SEC filing. "
            "The full document may contain additional qualifiers and counterevidence. " + extra
        ),
    }


def payload(*records, mode="live"):
    return {
        "industry": "ai-computing",
        "mode": mode,
        "excerpts": list(records),
        "gaps": ["Synthetic audit input; not a real SEC filing"],
    }


def _edit_csv(path, callback):
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        columns = reader.fieldnames
    callback(rows)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_sampling_balances_topics_and_issuers_deterministically():
    rows = [
        excerpt(topic, symbol, str(i))
        for topic in ("technology", "supply-chain", "competition")
        for symbol in ("NVDA", "AMD", "MU")
        for i in range(2)
    ]
    first, coverage = select_candidates(payload(*rows), limit=12)
    second, _ = select_candidates(payload(*reversed(rows)), limit=12)
    assert [r["sample_id"] for r in first] == [r["sample_id"] for r in second]
    assert len(first) == 12
    assert len(coverage["topic_counts"]) == 3
    assert len(coverage["issuer_counts"]) == 3
    assert max(coverage["issuer_counts"].values()) <= 5
    assert len({r["sample_id"] for r in first}) == 12


def test_prepare_requires_live_phase3c_excerpts_and_never_overwrites(tmp_path):
    with pytest.raises(ValueError, match="live"):
        create_audit(payload(excerpt(), mode="fixtures"), tmp_path / "fixtures")
    old = {**excerpt()}
    old.pop("topic")
    with pytest.raises(ValueError, match="Phase 3C"):
        create_audit(payload(old), tmp_path / "old")
    with pytest.raises(ValueError, match="No usable"):
        create_audit(payload(excerpt(extra="x", symbol="N0")), tmp_path / "invalid")
    result = create_audit(payload(excerpt()), tmp_path / "valid")
    assert result["selected"] == 1
    with pytest.raises(FileExistsError, match="already exists"):
        create_audit(payload(excerpt()), tmp_path / "valid")


def test_manifest_source_tampering_detected_even_when_sample_id_stays(tmp_path):
    directory = tmp_path / "audit"
    create_audit(payload(excerpt()), directory)
    _edit_csv(directory / "review.csv", lambda rows: rows[0].update(excerpt_text="Changed disclosure"))
    with pytest.raises(ValueError, match="Source evidence changed"):
        summarize_audit(directory)


def test_review_quality_requires_consistent_fields_and_human_labels(tmp_path):
    directory = tmp_path / "audit"
    create_audit(payload(excerpt()), directory)
    assert summarize_audit(directory)["audit_status"] == "incomplete"
    with pytest.raises(ValueError, match="Review incomplete"):
        summarize_audit(directory, strict=True)

    def valid_review(rows):
        rows[0].update(
            reviewer="Reviewer 1",
            source_match="exact",
            topic_relevance="medium",
            context_integrity="intact",
            decision="usable",
            notes="The phrase appears in source, topic matches, relevant qualifiers retained.",
        )

    _edit_csv(directory / "review.csv", valid_review)
    assert summarize_audit(directory, strict=True)["audit_status"] == "reviewed_usable_sample"

    def bad_review(rows):
        rows[0]["source_match"] = "mismatch"

    _edit_csv(directory / "review.csv", bad_review)
    with pytest.raises(ValueError, match="conflicts"):
        summarize_audit(directory)


def test_reject_requires_notes_and_is_reported_as_quality_issue(tmp_path):
    directory = tmp_path / "audit"
    create_audit(payload(excerpt()), directory)

    def reject(rows):
        rows[0].update(
            reviewer="Reviewer 1",
            source_match="mismatch",
            topic_relevance="none",
            context_integrity="misleading",
            decision="reject",
        )

    _edit_csv(directory / "review.csv", reject)
    with pytest.raises(ValueError, match="requires reviewer notes"):
        summarize_audit(directory)
    _edit_csv(directory / "review.csv", lambda rows: rows[0].update(notes="Excerpt not found"))
    report = summarize_audit(directory, strict=True)
    assert report["reviewed_count"] == 1
    assert report["rejected_sample_ids"]
    assert report["flagged_sample_ids"]
    assert report["audit_status"] == "reviewed_with_quality_findings"


def test_offline_html_verification_ignores_script_instructions(tmp_path):
    body = excerpt()["text"]
    html = f"<script>{body}</script><p>Different source text</p>"
    assert not verify_excerpt_in_document(body, html)
    assert verify_excerpt_in_document(body, f"<p>{body}</p>")
    directory = tmp_path / "audit"
    create_audit(payload(excerpt()), directory)
    sample = json.loads((directory / "manifest.json").read_text())["records"][0]
    file = tmp_path / "source.htm"
    file.write_text(f"<p>{body}</p>")
    result = verify_local_source(directory, sample["sample_id"], file)
    assert result["normalized_exact_substring"]
    with pytest.raises(ValueError, match="not found"):
        verify_local_source(directory, "nonexistent", file)


def test_rejects_foreign_sec_hosts_and_csv_formula_cells(tmp_path):
    malicious_url = {**excerpt(), "source_url": "https://sec.gov.evil.example/Archives/report.htm"}
    selected, coverage = select_candidates(payload(excerpt(), malicious_url))
    assert len(selected) == 1 and coverage["invalid_excerpts"] == 1
    untrusted_prefix = {**excerpt(), "text": '=HYPERLINK("evil") ' + excerpt()["text"]}
    directory = tmp_path / "audit"
    create_audit(payload(untrusted_prefix), directory)
    with (directory / "review.csv").open(newline="") as file:
        row = next(csv.DictReader(file))
    assert row["excerpt_text"].startswith("'=HYPERLINK")
    assert summarize_audit(directory)["sample_count"] == 1


def test_accepts_all_configured_sec_pilots_and_rejects_unconfigured_industries():
    for slug in ("ai-computing", "semiconductor", "power-grid"):
        data = {**payload(excerpt()), "industry": slug}
        selected, _ = select_candidates(data, limit=5)
        assert len(selected) == 1
    with pytest.raises(ValueError, match="Unsupported SEC audit industry"):
        select_candidates({**payload(excerpt()), "industry": "humanoid"})
