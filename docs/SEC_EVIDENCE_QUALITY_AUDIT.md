# Industry Research Phase 3D.1 — SEC evidence review

## Scope

This phase adds an **offline human-review audit**. It makes no network requests and does not invoke a model. It does **not** modify the SEC excerpt extractor, research validation, saved research, or API contracts.

Input: a response captured from `GET /api/industries/{slug}/filing-excerpts?year=2025` (for any configured SEC pilot: `ai-computing`, `semiconductor`, or `power-grid`) with `mode=live` and **Phase 3C `topic` fields**. Output: an immutable `manifest.json` and an editable `review.csv`. The input response is captured by the operator; fixture or unclassified data is rejected.

The review manifest contains publicly disclosed issuer excerpts but should be stored **outside the Git repository** to avoid oversized diffs and accidental publication of the review process. No representative SEC excerpts are fabricated by this package. Tests use obviously synthetic text only.

## What the review establishes

For every selected sample, the reviewer independently assesses:

| Column | Options | Meaning |
| --- | --- | --- |
| `source_match` | `unreviewed`, `exact`, `partial`, `mismatch`, `unavailable` | Does the normalized passage occur in the *original* SEC filing? Exact means an exact whitespace-normalized substring match, not semantic support. |
| `topic_relevance` | `unreviewed`, `high`, `medium`, `low`, `none` | How relevant is the excerpt to the assigned Technology/Supply Chain/Competition topic? |
| `context_integrity` | `unreviewed`, `intact`, `truncated`, `misleading` | Does the excerpt preserve qualifiers, negations, time, and scope? |
| `decision` | `unreviewed`, `usable`, `needs_context`, `reject` | Can it be used as evidence in qualitative research, or does it need more context? |
| `reviewer` | free text | Required for a complete review. |
| `notes` | free text | Required when rejecting; recommended for all other decisions. |

A row may be labeled `usable` **only** if source match is `exact`, relevance is `high` or `medium`, and context is `intact`. An auditor may still reject a technically matching quote. Any `reject` must have explanatory notes.

The `verify-local` command can compare one selected excerpt with **the locally saved original filing HTML/text**, stripping scripts and normalizing whitespace. It never accesses the network, never edits the review, and **does not verify the truth of issuer disclosures or whether an AI-generated claim follows from them**. A no-match result can also arise from differences in HTML rendering, character encoding or normalization and should be investigated manually.

## Limitations and next steps

- The audit is a *sample*, not a statistically representative guarantee of the SEC corpus or general model output.
- The latest saved industry AI analysis is separate from this audit. It may remain misleading even when its cited source text matches the filing.
- An issuer's disclosure expresses the issuer's position; it is not independent verification of an industry-wide fact.
- `section_hint` from Phase 3C is a **heuristic**, not a validated Item boundary.
- The script cannot prove that a locally saved file came from the indicated SEC URL; the reviewer must confirm the download origin.
- Phase 3D.2 can use this human-labeled dataset to propose deterministic quality gates and to measure false-positive/false-negative rates; it should not automatically train on or trust unlabeled data.
- Phase 3D.3 should assess **claim-to-passage entailment**, not just source-ID existence, and preserve earlier saved research on validation failures.

## Regression commands

```bash
python3 -m compileall -q backend/app/modules/intelligence/evidence_audit.py scripts/industry_evidence_audit.py

docker compose exec -T backend env -i \
  PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp \
  DATA_MODE=fixtures DATABASE_URL=sqlite:////tmp/stocker-3d1-tests.db \
  pytest -q tests/test_industry_evidence_audit.py tests/test_industry_filing_research.py tests/test_sec_filing_excerpts.py tests/test_boundaries.py

# Run full suites before merging.
```
