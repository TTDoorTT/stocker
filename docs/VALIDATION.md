# Validation

## Current local acceptance

```bash
docker compose config --quiet
make check
```

The Stocker naming revision passes **172 backend / 26 frontend tests**, Ruff/Biome format/lint/import checks, strict TypeScript, boundary/API snapshot checks and production build (234 modules). One existing Starlette/httpx deprecation warning remains. Existing API routes/schemas are preserved; only AI settings routes and DTOs are added. Checks run in isolated credential-free fixture containers.

Docker acceptance verified AI preferences, watchlist/positions, six-stage research, report and events survive container recreation unchanged on a separate fixture volume. Container checks verified 0700 directory/0600 credential-file permissions, redacted status and no synthetic secrets in backend logs. The exact Docker host alias resolves; this does not prove a particular Windows/WSL host model is reachable.

Real Chromium acceptance passed setup/skip/backend model test/save/Settings/reset, saved-key absence from reloaded DOM and browser storage, a 390px no-overflow assertion, and zero pageerrors. It used a synthetic loopback model responder. Screenshot perception could not run because `vision-analyze` lacked `NVIDIA_API_KEY`; visual appearance is unverified. The complete general native browser harness was not rerun for this revision because the live ports remain occupied. Commands are in [development](DEVELOPMENT.md).

## CI

The naming revision is local until publication; its remote CI is unrun. The preceding AI configuration revision passed [GitHub Actions run 42308316004](https://github.com/TTDoorTT/stocker/actions/runs/42308316004). The configured workflow covers Python 3.11/3.13, Node 22 quality/tests/build and isolated Docker recreation/persistence. A previously verified main baseline passed [GitHub Actions run 42298783499](https://github.com/TTDoorTT/stocker/actions/runs/42298783499); that historical result does not establish current revision success.

## Acceptance limits

These fixture and synthetic-model checks establish application behavior, persistence and validation, not financial accuracy or broad model quality. Existing endpoint/model/key values and financial data mode are preserved. Real Strata inference and live financial providers were not rerun for this feature.

Previous live records cover limited SEC/Finnhub U.S. symbols, Yahoo daily history and Bank of Canada macro; a recorded AAPL run validated six stages and produced a sourced report while remaining overall incomplete. Detailed executions, failures, budgets and decisions are kept in [`progress/`](../progress/README.md) on `main`. Canadian fundamentals/current quotes, automatic FX conversion, licensed consensus and interim/TTM coverage remain unavailable or incomplete. Optional provider entitlements, TSXV live history and broader live-model quality remain unverified.
