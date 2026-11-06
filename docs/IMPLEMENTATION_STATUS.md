**Historical record — reconciled 2026-11-06.** The initial implementation and Docker/modular baseline are complete. Current owners are `app/modules/{market_data,research,portfolio,intelligence}`, `app/contracts`, `app/core/database.py` and frontend `src/features/*`. Main `93d0ee4` passed remote CI run 42298783499; local branding checks pass 150 backend / 21 frontend tests. See [current validation](VALIDATION.md). Original phase objectives, paths, failures and counts below are preserved as historical evidence. Later recorded AAPL live-budget acceptance produced six validated stages/report with incomplete evidence coverage; it was not independently repeated during cleanup.

**Superseding status:** baseline Implemented, Verified locally and Verified on CI. Canadian data remains Partial coverage; broader data/features are Deferred. Live results are recorded prior acceptance, not independently verified by this cleanup. Earlier blocked credentials and pending-CI statements below describe their original checkpoints.

---

# Phase acceptance and remaining work

This is an implementation, not another plan. All files stay under the selected project root. The original specification is preserved and reference clones are ignored. See PROGRESS.md for actual command results, failures, fixes and the exact resume step.

| Phase | Implemented files / demonstrated behavior | Verification / remaining acceptance |
|---|---|---|
|0 References | REFERENCE_AUDIT.md, DATA_PROVIDERS.md, ARCHITECTURE.md, DECISIONS.md, root setup/ignore/agent docs; both pinned reference clones studied | All requested paths located; no AGPL code copied. Completed. |
|1 Foundation | backend/app/main.py, core/config.py, db/repository.py; frontend Vite/React routes and typed client | Health, local startup, SQLite schema/lifecycle, frontend build and real browser API requests pass. Completed. |
|2 Data | app/data/http.py and service.py, models/market.py, finance/metrics.py, fixtures/market.json | Mocked SEC/Finnhub/Alpha, fiscal/currency checks, null missing data, deterministic formulas, original cache timestamps, malformed-provider and concurrency tests pass. Genuine live SEC contact/provider credentials absent; live financial retrieval unverified. |
|3 Agents | agents/client.py, tools.py, six prompts; models/research.py, orchestrator/engine.py and validation.py | Six roles on all three fixture symbols; corrupt math rejected/corrected, references checked, retry/revisit bounds, stale-risk correction, events/report persisted. Live model/usage acceptance blocked by missing configuration. |
|4 Workspace | frontend pages Home, Stock, MyStocks; search/chart/isolated official heatmap components | Real browser search, watchlist, positions/P&L, six stages/report, responsive390px and zero JS errors pass. Forced external-widget failure/retry final check recorded in BROWSER_SMOKE.md. Pixels not visually inspected because vision credential absent. |
|5 Integration | services/chat.py; API history/report/events; Research Records and Settings UI | Chat isolation and source labels, full artifacts, Markdown download, real browser backend restart/report reopen, no frontend secrets pass. Real AI answers await configured model. |
|6 Intelligence | services/intelligence.py; fixtures/industries.json; Industry Intelligence/Research/Daily Review UI |20 navigable guided templates, two representative-company six-stage workflows, actual-format mocked FRED/news, no invented news/signals. Optional headline-only AI summary uses shared client. Live news/FRED/model unverified. Sector-wide supply/demand, market breadth/sectors/volume unavailable; no comprehensive sector-analysis claim. |
|7 Quality/demo | backend/tests, frontend interaction tests, manual real-browser script, services/evaluation.py, EVALUATION.json/md, DEMO.md, README | Actual checks logged in PROGRESS.md. Same captured fixture evidence for baseline/multi; no quality/cost advantage claimed. Final credentialed live acceptance and screenshot perception remain blocked. |
|8 Deferred | ROADMAP.md | Implementation intentionally not started. Canada/TSX, transaction ledger, backtesting and other Later scope remain deferred. |

The project is runnable in explicit synthetic fixture mode. Overall research status is intentionally incomplete when material gaps exist. Do not present deterministic fixture model outputs or invented test financial inputs as real investment research.

## User-authorized provider revision — 2026-11-06

The initial plan remains preserved; the latest user request expands provider scope. Added optional yfinance history/Alpha Vantage selection, no-key Bank of Canada Valet macro, explicit Canadian .TO/.V and CA/CAD contracts, currency-safe positions, provider policies and local request-budget/error handling. Existing Strata iq3_s integration and six-stage architecture are preserved.

Actual application probes pass for AAPL/USD and RY.TO/CAD daily history and both Canadian macro series. Automated verification now passes 117 backend tests, 18 frontend tests, Ruff, TypeScript/build and real browser smoke with zero pageerrors. Detailed evidence and limits: PROGRESS.md and DATA_PROVIDERS.md. Earlier phase rows describe the original checkpoint; this revision supersedes the old statement that all Canadian features are deferred.

Canadian statements/current quotes remain unavailable. SEDAR+ is not scraped; authorized issuer reports/licensed distribution need further work. A real full-orchestrator probe stopped safely after three profile request timeouts with no report (LIVE_MODEL_CHECK.json). SEC/Finnhub configuration is now supplied and actual facts/identity/filings/quotes pass for AAPL/MSFT/NVDA, with AAPL company news verified. With the user-authorized 120-second timeout, iq3_s profile now passes; financials still stop on output/total-token limits and no report is produced; see LIVE_SOURCED_RUN.json. No additional U.S. credentials are needed; reduce redundant role/tool context before retrying. Alpha Vantage/FRED remain optional. TSXV mapping is implemented but its live history has not been probed.
