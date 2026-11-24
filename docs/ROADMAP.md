# Future work

The modular application, fixture checks, Docker persistence, CI, RSS category news with saved optional highlights, and persistent light/dark UI form the current baseline. The following are separate improvements, subject to source rights and explicit scope:

- Expand interim/TTM facts, balance-sheet detail, issuer/listing identity checks, peer comparisons and licensed consensus coverage.
- Improve live-model latency/reliability and independently repeat sourced multi-stage acceptance across more symbols; compare model strategies using identical evidence and human review.
- Add permitted Canadian quotes/fundamentals and verify TSXV history; introduce explicit dated FX conversion only with defined accounting semantics.
- Explore Bull/Bear debate, screening, backtesting, cross-model comparisons and report share cards.
- Extend simple positions into transaction accounting and portfolio risk checks.
- Consider event calendars, reminders, alerts, document/PDF research, historical replay and advanced chart drawing.
- Improve RSS source-health observability, publisher attribution/rights review, and manual highlight regeneration controls without silently increasing model calls.

Chinese A-share-specific trading sentiment remains outside the product scope.

## Stock research expansion (completed)

All five scoped stock research phases have been implemented behind strict contracts, deterministic finance modules, and offline fixture tests:

1. Interactive OHLCV price charts (`/api/stocks/{ticker}/candles`).
2. Quarterly financial trends and deterministic TTM (`/api/stocks/{ticker}/financial-trends`).
3. Earnings preview and historical review (`/api/stocks/{ticker}/earnings`).
4. Historical earnings event studies (`/api/stocks/{ticker}/events`, `/api/stocks/{ticker}/event-study`).
5. Earnings markers on price charts.

Quarterly/TTM observations and dated vendor earnings records are also captured as additive, provenance-labeled evidence during six-stage company research runs while preserving GAAP vs. non-GAAP separation and explicit consensus gaps.

See [Stock Research Providers](STOCK_RESEARCH_PROVIDERS.md).

## Next priorities

- Run live-provider and live-model end-to-end verification across SEC, Finnhub, Yahoo, and configured LLM endpoints; calibrate SEC excerpt quality gates and claim entailment with human-reviewed samples ([SEC evidence audit](SEC_EVIDENCE_QUALITY_AUDIT.md)).
- Expand SEC-backed industry pilots beyond `ai-computing`, `semiconductor`, and `power-grid` where verified issuer universes and regression tests exist, and evaluate `overview`/`outlook` evidence sources.
- Improve RSS source-health observability across the 88 configured feeds.
- Add permitted Canadian quotes/fundamentals and evolve simple positions into transaction accounting.
