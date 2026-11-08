# Phase 4B — Semiconductor filing-backed research pilot

## Scope

The existing industry template slug `semiconductor` gains **explicit on-demand** Technology, Supply Chain and Competition generation. `overview` and `outlook` stay guided-only; all remaining industry profiles keep existing capabilities.

## Data

- SEC company-ticker mapping, SEC submissions 10-K metadata, and bounded primary-document text, through the existing allowlisted SEC transport.
- Illustrative five-issuer U.S. 10-K universe: **NVDA, INTC, MU, AMAT, LRCX**. Company roles are examples for research, not a validated supply-chain topology or an industry census.
- SEC source configuration and topic terminology live in `app/contracts/industry_sources.py`, shared by Market Data and Intelligence. Neither module imports another module's private providers.
- Semiconductor filing collection does **not** request XBRL Frames; there is no semiconductor quantitative Overview or peer-comparison engine in this increment.
- International foundries, foreign SEC 20-F issuers, Canadian-only companies, upstream chemistry, and specialized materials are not covered.

## Process

1. A user explicitly requests generation in the `semiconductor` workspace.
2. The backend capability registry permits only the three supported sections.
3. Market Data retrieves the selected issuers' recent 10-K filing documents and selects sector-specific topic passages. The SEC user-agent, URL allowlist, rate limiting, caching, document-size limits, and no-redirect policy are preserved.
4. The existing Intelligence filing adapter checks sector identity, approved issuers, filing metadata, source URLs and topic relevance; rejects low-information and duplicated content.
5. Generation uses the existing validated report schema, cited claims and fail-closed second-pass claim reviewer, and saves only after success.
6. GET of a saved note remains SQLite-only. Failed regeneration preserves the last successful saved note.

## Safety and provenance

- A citation identifies captured issuer text; it does not prove claim correctness or validate SEC Item boundaries.
- Topic ranking is heuristic, not a complete text extraction; unavailable data yields an explicit gap, never a model-only summary.
- Selected U.S. issuers cannot establish the *global* semiconductor supply chain, customer contracts, market share, production capacity, or foundry relationships.
- No new external hosts, runtime user-specified tickers, prompts, scraping APIs, database schema migrations or browser write operations.

## Validation

Run `backend/tests/test_semiconductor_industry.py`, existing SEC excerpt/ranking, industry quality/review/workspace, architecture tests, full backend + frontend CI, then test a live SEC generation with a valid SEC User-Agent and working model. Check cited passages directly in SEC documents before treating any conclusion as reliable.
