# Phase 5C.1 — Industry Research Synthesis

## Objective

Make SEC-backed research more useful without weakening its
source-verification requirements.

## Changes

- Encourage specific technical and operational distinctions.
- Compare issuers only when separate cited passages support both sides.
- Avoid combining unrelated disclosures merely to increase citation counts.
- Prefer concise claims with necessary, relevant citations.
- Explicitly acknowledge when comparative evidence is insufficient.
- Preserve source attribution and anti-hallucination constraints.

## Unchanged

- SEC filing retrieval and sentence-aware passage extraction.
- Industry issuer profiles and capability permissions.
- Research output schemas and claim-count limits.
- Second-pass claim screening.
- Saved research and SQLite schema.
- Frontend and API endpoints.
- Local model configuration and token budgets.

## Acceptance

Compare a new Technology report against the Phase 5A baseline.

Check whether it contains more useful, specific observations,
whether each comparison is supported by the cited excerpts,
and whether any unsupported conclusions are introduced.

A model-screened report is not independently verified.
Do not merge based only on automated test success.
