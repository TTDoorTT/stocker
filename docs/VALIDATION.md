# Validation

## Current local acceptance

```bash
docker compose config --quiet
make check
```

The earlier Stocker naming/AI-configuration acceptance recorded **172 backend / 26 frontend tests** and a production build (234 modules). Those are **historical counts, not the current RSS revision counts**. The current main code (commit `87001b7`) passed the configured CI checks: Python 3.11/3.13 backend tests, Ruff, Biome lint/format/imports, strict TypeScript, frontend tests/build and isolated fixture Docker persistence. RSS added four endpoints and corresponding OpenAPI snapshot updates, plus offline backend/frontend tests. This documentation-only update was not independently executed in a local Docker or browser environment.

Docker acceptance verified AI preferences, watchlist/positions, six-stage research, report and events survive container recreation unchanged on a separate fixture volume. Container checks verified 0700 directory/0600 credential-file permissions, redacted status and no synthetic secrets in backend logs. The exact Docker host alias resolves; this does not prove a particular Windows/WSL host model is reachable.

Real Chromium acceptance passed setup/skip/backend model test/save/Settings/reset, saved-key absence from reloaded DOM and browser storage, a 390px no-overflow assertion, and zero pageerrors. It used a synthetic loopback model responder. Screenshot perception could not run because `vision-analyze` lacked `NVIDIA_API_KEY`; visual appearance is unverified. The complete general native browser harness was not rerun for this revision because the live ports remain occupied. Commands are in [development](DEVELOPMENT.md).

## CI

The latest reviewed `main` commit [`87001b7`](https://github.com/TTDoorTT/stocker/commit/87001b707d1a33f010e4f16ee3942e64218dd9f8) **passed** [GitHub Actions run 42342083456](https://github.com/TTDoorTT/stocker/actions/runs/42342083456) on 2026-11-07, including the merged RSS feed/highlights persistence work. The earlier frontend-theme CI failure at `caba235` was corrected and [run 42333781423](https://github.com/TTDoorTT/stocker/actions/runs/42333781423) passed. The first RSS PR run failed, then the corrected RSS PR [run 42340763254](https://github.com/TTDoorTT/stocker/actions/runs/42340763254) passed. A future documentation commit requires its own CI result; no success is presumed in advance. The workflow covers Python 3.11/3.13, Node 22 checks and isolated Docker recreation/persistence.

## RSS-specific checks and limitations

New offline checks cover RSS English/CJK/date filtering, tracking-URL cleanup, SQLite refresh persistence, source-diverse headline/excerpt selection, no implicit model calls on feed reads, saved per-category highlights, stale detection and preservation of previously saved summaries when regeneration fails. Frontend checks cover saved-summary restoration without re-inference and failed-regeneration behavior. These are test/CI assertions, not evidence that all 88 configured feeds were reachable, that every publisher permits every reuse, or that a real external model generated trustworthy sector conclusions. Refreshing RSS performs live network calls, but opening the page does not require financial `DATA_MODE=live`.

## Acceptance limits

These fixture and synthetic-model checks establish application behavior, persistence and validation, not financial accuracy or broad model quality. Existing endpoint/model/key values and financial data mode are preserved. Real Strata inference and live financial providers were not rerun for this feature.

Previous live records cover limited SEC/Finnhub U.S. symbols, Yahoo daily history and Bank of Canada macro; a recorded AAPL run validated six stages and produced a sourced report while remaining overall incomplete. Detailed historical executions, failures, budgets and decisions are preserved in [the pre-cleanup snapshot](https://github.com/TTDoorTT/stocker/tree/7933922ca5e3b88fa43b345456e856f8cfc550ba/progress). Canadian fundamentals/current quotes, automatic FX conversion, licensed consensus and interim/TTM coverage remain unavailable or incomplete. Optional provider entitlements, TSXV live history and broader live-model quality remain unverified.
