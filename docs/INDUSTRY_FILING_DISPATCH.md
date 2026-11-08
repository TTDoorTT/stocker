# Phase 4C — SEC filing dispatch refactor

This narrow, internal refactor moves industry-specific source call conventions out of `IndustryResearchService.generate` and into `intelligence/filing_dispatch.py`.

- Only explicitly integrated SEC industry source profiles are permitted; unknown slugs fail before retrieval.
- AI Computing retains its historical positional `capture(year)` and adapter signatures for legacy tests and integrations, and may have missing `industry` in historical snapshots.
- Semiconductor and future explicitly configured SEC profiles require `industry=slug` during capture and adaptation, and a snapshot with a matching `industry` identity. Mismatched identities fail before evidence construction or model calls.
- No new API endpoints, database migrations, permission changes, LLM parameters, source lists, or frontend changes.
- Existing claim-to-evidence screening, quality screening, source ID persistence and failure-preserving writes remain unchanged.

## Acceptance

Run `test_industry_filing_dispatch.py`, existing AI Computing and Semiconductor regression tests, the full backend and frontend suites, Ruff/Biome, and Docker CI. In particular, check the end-to-end source identity boundary and fail-closed behavior for unsupported sectors. Passing tests is not independent verification of the AI's conclusions.
