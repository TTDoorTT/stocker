# Phase 4F — Citations used by model-screened industry claims

## Problem

Phase 4E reports how many of the selected SEC issuers contributed **accepted** passages. Not every accepted passage is necessarily cited by a generated claim. A note can use a small subset of otherwise accepted evidence.

## New measurement

- After the existing report schema validation and model-based claim review succeed, reuse the claim review's `supporting_evidence_ids` to count **distinct actually cited** accepted excerpts and issuers.
- No network, SEC or LLM calls are added. Existing evidence IDs, prompts, validation, and saved reports are unchanged.
- `filing_coverage` adds optional `cited_issuers`, `uncited_represented_issuers`, `cited_excerpts`, `model_screened_claims`, and `citation_limitation`.
- Old results without these fields still render. Test stubs lacking detailed review metadata do not fabricate metrics.
- Reviewer outputs with assessments pointing at unknown IDs or unapproved issuers are rejected before save. Failed generation does not overwrite an earlier successful report.
- The UI distinguishes accepted-issuer coverage from cited-issuer coverage. This is **not** a factual correctness score, proof of semantic support, or an industry census. The reviewing model may be the same model as the generating model.

## Architecture

- `intelligence/filing_citations.py`: pure aggregation of already validated accepted Evidence and review metadata.
- `intelligence/industry_research.py`: enriches `filing_coverage` only after the existing model call; persists in the existing SQLite `result_json` column.
- `frontend`: optional display; no new endpoints or database schema migrations.

## Acceptance

- Coverage counts never exceed accepted evidence or selected issuers.
- Repeated citations count once; citations from the same issuer count that issuer once.
- Unknown or duplicate evidence IDs, malformed claim indexes and rejected verdicts fail closed.
- Old saved reports render with no additional requests or model calls.
- The full backend and frontend suites pass; use live model generation to confirm a report with detailed claim-review assessments displays cited counts.
