# AI Computing — SEC evidence pilot

Phase 1 extends `Industry research` with a read-only, on-demand official-source preview. `GET /api/industries/ai-computing/evidence?year=YYYY` returns US-GAAP XBRL Frames for `ResearchAndDevelopmentExpense` and `NetIncomeLoss`, up to three recent 10-K / 10-Q / 8-K filing metadata records for each selected peer, and previously cached RSS headlines from `ai` and `semi`.

Selected tickers **NVDA, AMD, INTC, AVGO, MU** are illustrative publicly listed businesses relevant to AI computing; they are *not* validated exhaustive peers or a measure of industry coverage. Ticker-to-CIK mapping is verified on each cache miss using SEC's original mapping. Source URLs and frame periods accompany the results. There is no LLM call, new dependency, independent SEC HTTP client, new Docker service, or database migration.

## Reliability rules

- SEC access requires a genuine configured `SEC_USER_AGENT`, and only `https://www.sec.gov` and `https://data.sec.gov` are contacted through Stocker's existing fixed-host transport. Requests use the existing conservative pacing, retries and cache.
- SEC Frame results omit companies with inconsistent or unavailable fiscal-period tagging. Missing peers are recorded in `gaps`, not converted to zero or inferred.
- The calendar frame `CY2025` does **not** necessarily mean a company's fiscal-year 2025, nor does frame inclusion imply the value was available on a historical trading date. Stocker surfaces exact `start` and `end` per observed row. For backtesting, further as-of filing checks are needed.
- Filing metadata are the most recent returned records, filtered by form, **not filing text search**, and are never converted into assertions about contract awards, customer relationships, or production capacities.
- RSS records are retained as headlines linking to publishers. They cannot establish market shares, technical supply-chain facts, or financial figures.
- Do not pass this response to an LLM and label its output "verified industry research" without implementing validation, citation binding, and a run-specific evidence snapshot.

## Suggested future stages

1. Add additional official datasets selectively based on the industry: BLS for labor/inflation, EIA inventory for energy, Treasury financing indicators.
2. Store immutable industry-evidence snapshots and model-generated sections in SQLite, with source provenance and stale indicators.
3. Add independently generated sections: overview, technology, supply chain, competitive landscape, outlook. Only cite facts actually retrieved; missing sector data must remain explicit.
4. Bridge vetted company identifiers to the existing six-stage company research engine.

Reference: SEC EDGAR public API docs and [Stocker's provider policy](DATA_PROVIDERS.md). The idea of using XBRL Frames and filing metadata was informed by [global-stock-data](https://github.com/simonlin1212/global-stock-data), which is Apache 2.0 licensed; this Stocker pilot is a fresh implementation using its existing SEC provider rather than copied code.
