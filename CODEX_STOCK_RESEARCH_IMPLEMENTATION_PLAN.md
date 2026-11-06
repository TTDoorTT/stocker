**Historical record — reconciled 2026-11-06.** The initial implementation and Docker/modular baseline are complete. Current owners are `app/modules/{market_data,research,portfolio,intelligence}`, `app/contracts`, `app/core/database.py` and frontend `src/features/*`. Main `93d0ee4` passed remote CI run 42298783499; local branding checks pass 150 backend / 21 frontend tests. See [current validation](docs/VALIDATION.md). Original phase objectives, paths, failures and counts below are preserved as historical evidence. Later recorded AAPL live-budget acceptance produced six validated stages/report with incomplete evidence coverage; it was not independently repeated during cleanup.

---

# Stocker — Codex Implementation Plan

**Purpose:** Build a university multi-agent stock research application inspired by Vibe Research and OpenStock, with a U.S.-first implementation and a future Canadian/TSX extension.

**Status:** Executable implementation handoff, updated for the existing project directory `~/uni/dh399/stocker`. This is a specification for Codex to carry out; the application has not been built by this document.

**Priority:** A real, explainable agent-based workflow comes before dashboard breadth or visual polish.

---

## 0. Instructions to Codex (read first)

You are the lead software engineer implementing **Stocker**. Execute this plan in order, writing actual code, configuration, tests, and documentation; do not merely summarize it.

1. Work in **WSL2 Ubuntu** on the Linux filesystem, using **`~/uni/dh399/stocker`** as the **existing, authoritative project root**. Do not create or switch to another workspace. Inspect the existing files and Git status first; preserve all pre-existing work. Do not alter `~/ai/codx-testing`, Codex CLI configuration, or the existing LiteLLM installation.
2. Treat the two external GitHub repos as **reference implementations**, not codebases to merge. Build a small independent implementation. Only port narrowly justified Vibe MIT-licensed code with proper copyright/license attribution. **Do not copy OpenStock's AGPL-3.0 code** into the new project without explicitly resolving licensing obligations.
3. Do an initial repository audit first. Record the current commit SHA of each reference so future changes are reproducible. If a referenced path has changed, inspect the repository and locate its replacement; do not silently assume the code is identical.
4. Implement each phase, run its acceptance tests, fix failures, and **update `docs/PROGRESS.md` continuously, not just at the end**. Create it during Phase 0. Update it at the start/end of each phase, after each meaningful implementation milestone (at least every 3 completed tasks), after tests, whenever blocked or scope changes, and **before ending or compacting any Codex session**. Keep `docs/DECISIONS.md` for significant architecture choices. Maintain a runnable app after each checkpoint.
5. Avoid destructive commands (`rm -rf`, force pushes, overwriting an existing project), expensive deployment, and subscription purchases. Never commit secrets or modify account-wide settings. Request human input **only when necessary** for credentials, approvals, or genuinely ambiguous blockers.
6. Prefer the simplest working solution. Do not add LangGraph, LangChain, vector DBs, MongoDB, Redis, Celery, microservices, OAuth, or container orchestration unless evidence shows they are necessary.
7. **No fabricated financial data.** Offline tests may use clearly marked sample fixtures. Real UI or reports must show a source, timestamp, and limitations for financial facts; on missing data, show `unavailable` / `incomplete`, not an invented number.
8. One model is sufficient for all agents, provided each role has distinct instructions, scoped context, structured output, and traceable handoffs. Agents may be sequential, as in Vibe Research.
9. Run the whole project locally first. External hosting, brokerage integration, buy/sell execution, price targets, and automated investment decisions are out of scope.
10. Use the plan as a **dependency-ordered roadmap**. When context is limited, stop at a safe checkpoint and leave a precise next-action entry in `docs/PROGRESS.md` before the session ends. Future sessions must read `docs/PROGRESS.md` before continuing.

### Definition of a successful school demo

A user opens the local app, views U.S. markets and a heatmap, searches **AAPL / MSFT / NVDA**, selects a stock, clicks **Run Research**, watches six agent stages execute with actual status/events, sees validation or revision events, opens an evidence-backed report, and can reopen that run from history. The system also offers basic AI chat, watchlists/holdings, and then the selected market-intelligence pages.

---

## 1. Initial setup — GitHub repositories and environment

### 1.1 Verify tools

In WSL Ubuntu, run:

```bash
pwd
uname -a
git --version
node --version
npm --version
python3 --version
```

Requirements: Git, Node.js 22+, npm, and Python 3.11+. If something is missing, document it and use a non-destructive, project-compatible installation approach. Do not change the user's other AI projects.

### 1.2 Inspect the existing project workspace

**This is an existing user-selected working directory, not a disposable scaffold location.** Do not wipe, overwrite, or relocate its existing contents.

```bash
cd ~/uni/dh399/stocker
pwd
ls -la
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git status --short
  git rev-parse --show-toplevel
fi
```

If the directory is missing, report it as a blocker rather than silently choosing a different location. Inspect existing files, understand current structure, and integrate non-destructively. Initialize Git only if this location is not already inside a Git repository (including a parent repository):

```bash
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git init -b main; fi
mkdir -p references docs
```

Create or **carefully extend** `.gitignore` **before** staging anything; preserve existing ignore rules. At minimum ignore:

```gitignore
references/
.env
.env.*
!.env.example
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
node_modules/
dist/
coverage/
*.db
*.sqlite3
.DS_Store
```

### 1.3 Clone reference projects

```bash
cd ~/uni/dh399/stocker/references

if [ ! -d Vibe-Research ]; then
  git clone --depth 1 https://github.com/simonlin1212/Vibe-Research.git
fi

if [ ! -d OpenStock ]; then
  git clone --depth 1 https://github.com/Open-Dev-Society/OpenStock.git
fi

printf 'Vibe Research: '
git -C Vibe-Research rev-parse HEAD
printf 'OpenStock: '
git -C OpenStock rev-parse HEAD
```

These clones must remain reference-only and excluded from the current project's Git tracking. If network access is blocked, record the blocker and use the public GitHub URLs below; do not pretend the clones exist.

### 1.4 Source map — inspect these exact files

**Vibe Research — research methodology and orchestration**  
Repository: https://github.com/simonlin1212/Vibe-Research

| Path in `references/Vibe-Research/` | Why inspect it |
|---|---|
| `README_en.md` | Product scope, UI sections, capabilities, U.S. market support |
| `orchestrator/README.md` | Six-stage workflow and runtime/tool constraints |
| `orchestrator/src/orchestrate.ts` | Stage execution, retries, validation gates, saved artifacts |
| `orchestrator/src/agent_runner.ts` | Agent runner and event-log contract |
| `orchestrator/src/finance/stages_global.ts` | **U.S./HK stage-specific instructions**; prefer this to A-share rules |
| `orchestrator/src/finance/stages.ts` | Prompt design and structured handoffs |
| `orchestrator/src/finance/methodology.ts` | Stage-specific skill instruction mapping |
| `orchestrator/src/finance/plugin.ts` | Per-stage data requirements and business contracts |
| `orchestrator/src/validator.ts` | Verification strategy, stage failure/incomplete states |
| `orchestrator/src/schemas.ts` | Structured research outputs |
| `orchestrator/src/run_tools.ts` | Controlled tools: read, calculate, write stage/report |
| `orchestrator/src/api.ts` | Reference HTTP endpoints for research/jobs/history |
| `methodology/constitution.md` | Evidence and calculation discipline |
| `.agents/skills/company-research/SKILL.md` | Six-stage research SOP |
| `.agents/skills/earnings-analysis/SKILL.md` | Financial analysis rules |
| `.agents/skills/valuation/SKILL.md` | Valuation reasoning and method |
| `.agents/skills/catalyst-risk/SKILL.md` | Risk and counterevidence |
| `.agents/skills/data-access/scripts/` | Financial data adapters; do not blindly import every dependency |
| `datasources/CATALOG.md`, `datasources/registry.json` | Data-source discovery, markets, endpoint requirements |
| `calc/` and `calc/SPEC.md` | Deterministic calculations and testable formulas |
| `desktop/src/verticals/finance/router.tsx` | Navigation and layout reference |
| `desktop/src/verticals/finance/pages/` | Existing Home, DailyReview, Research, Intel, Signals, Sectors pages |
| `desktop/src/verticals/finance/data/sectors.json` | **Original 20 sector templates**; adapt for Western markets |

**OpenStock — dashboard/visualization reference only**  
Repository: https://github.com/Open-Dev-Society/OpenStock

| Path in `references/OpenStock/` | Why inspect it |
|---|---|
| `README.md` | UX concepts and data provider boundaries |
| `MARKET_SUPPORT.md` | Free-tier U.S./Canadian market support limitations |
| `app/(root)/dashboard/page.tsx` | Dashboard sections and market presentation |
| `components/TradingViewWidget.tsx` | How the project embeds TradingView widgets **(inspiration, do not copy)** |
| `lib/markets.ts` | Market identifiers and sample U.S./Canadian tickers |
| `lib/utils.ts` | Exchange / symbol handling inspiration |
| `LICENSE` | AGPL-3.0 license considerations |

**Required audit output:** `docs/REFERENCE_AUDIT.md` with repo names, SHAs, inspected file paths, specific concepts being adapted, anything reused verbatim (with license notices), and known unsupported assumptions.

---

## 2. Product scope — implement exactly these features

### Milestone A — Core school-demo MVP (build first)

- **Home:** U.S. market overview, interactive stock heatmap, watchlist, simple manually entered holdings and derived P&L, and search.
- **Stock overview:** Company identity/profile, quote and timestamp, historical price display or basic embedded chart, key financial metrics, recent earnings/filing references.
- **Research:** Six sequential specialist-agent roles: `profile -> financials -> estimates -> valuation -> risk -> report`.
- **AI chat:** Stock questions, retrieved source data, calculations, explicit option to launch full research.
- **Research history:** Save and reopen reports, stage outputs, evidence, validation failures, and the execution trace.
- **Model integration:** Configurable OpenAI-compatible endpoint, including an optional existing local LiteLLM proxy.
- **Validation:** Schema checks, source attribution, deterministic math, missing-data logic, bounded retries.
- **U.S. data:** Working financial-data adapters for an initial AAPL/MSFT/NVDA test set, generalized for valid U.S. tickers where the source allows.

### Milestone B — Remaining selected Keep features

- **Daily market review:** U.S. index/ETF performance, breadth where available, sectors, volume and significant news; no China-specific limit-up/Dragon-Tiger logic.
- **News radar:** Company/industry headlines, sources, dates, ticker/sector tags, short AI summaries when a model is available.
- **Industry signals:** A **small, genuine set** of measurable indicators (e.g. interest rates, relevant commodity series, a documented supply/demand series), with freshness and source; defer unsupported signals instead of inventing them.
- **20 industry research templates:** Import/adapt topics from Vibe's `sectors.json` to U.S./Canada relevance. Make 20 templates navigable; demonstrate 1–2 end-to-end sector analyses with sources.

### Later — preserve in roadmap, do not build in MVP

Canadian/TSX (and later TSXV) fundamentals; Bull/Bear debate; strategy backtesting; stock screener; cross-model run comparison; report share cards; full portfolio transaction ledger; portfolio risk checkups; historical crash replay; events calendar; scheduled reminders; document/PDF research; advanced TradingView drawing tools; price alerts.

### Explicitly removed

Chinese A-share-specific daily trading sentiment (limit-up/down streaks, Dragon-Tiger lists, etc.). No Chinese exchanges or China-only UX.

**Scope reconciliation:** Home **holdings** are Keep, full transaction-ledger accounting is Later. Implement the first as an editable snapshot of positions (`symbol`, `shares`, `average_cost`, `currency`), calculate unrealized P&L from sourced quotes, and label it **simple positions**. Do not claim FIFO/XIRR or realized P&L. U.S.-first means the UI can describe Canada as **Planned**, but must not claim Canadian research works yet.

---

## 3. Architecture and contracts (agree in code before building pages)

### 3.1 Recommended stack

- **Frontend:** React + TypeScript + Vite + React Router; simple, responsive CSS/Tailwind as justified.
- **Backend:** Python 3.11+ + FastAPI + Pydantic; REST endpoints; stage execution in the backend.
- **Database:** SQLite (SQLModel or SQLAlchemy) for tickers/watchlists/positions/research runs; structured JSON for captured evidence and stage results.
- **AI:** OpenAI-compatible chat-completions adapter with tool calling and/or schema-validated JSON; OpenAI SDK or a small HTTP wrapper, not a provider-specific workflow.
- **Financial calculations:** deterministic Python functions, optionally NumPy/pandas if needed.
- **Charts:** official TradingView heatmap widget; basic stock chart widget or independent price-chart component. **The heatmap does not expose prices to agents.**
- **Tests:** pytest, ruff, frontend lint/typecheck/build, and browser smoke tests if a browser testing tool is available.

Keep one backend process, one frontend dev server, and one SQLite database. No container requirement for local MVP.

### 3.2 Directory tree to create

```text
stock-research/
├── references/                 # ignored clones; read-only conceptual references
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py             # FastAPI app
│   │   ├── core/config.py      # settings and secrets handling
│   │   ├── api/                # REST routes
│   │   ├── db/                 # SQLite models/repositories
│   │   ├── models/             # Pydantic DTOs and schemas
│   │   ├── data/               # SEC/quotes/history/news providers
│   │   ├── finance/            # deterministic metric calculations
│   │   ├── agents/             # profiles, prompts, tools, output contracts
│   │   ├── orchestrator/       # state machine, retry/validation, event log
│   │   └── services/           # stock, portfolio, intel, chat, research
│   └── tests/
├── frontend/
│   ├── package.json
│   └── src/
│       ├── app/                # routes, layout
│       ├── components/         # heatmap, search, progress, charts
│       ├── pages/              # Home, Stock, Research, History, Intel, etc.
│       ├── api/                # typed backend client
│       └── types/
├── fixtures/                   # SMALL, labeled demo data only
├── docs/
│   ├── REFERENCE_AUDIT.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATA_PROVIDERS.md
│   ├── DECISIONS.md
│   ├── PROGRESS.md
│   └── DEMO.md
├── .env.example
├── .gitignore
└── README.md
```

Codex can adjust filenames for idiomatic organization, but must preserve the boundaries and document any changes.

### 3.3 Standard financial data shape

Normalize *every* provider into consistent objects. At minimum:

```json
{
  "symbol": "AAPL",
  "market": "US",
  "field": "revenue",
  "value": 0,
  "unit": "USD",
  "currency": "USD",
  "period": "FY2025",
  "period_start": "2024-09-29",
  "period_end": "2025-09-27",
  "source_name": "SEC EDGAR",
  "source_url": "https://data.sec.gov/",
  "published_at": "2025-10-31T00:00:00Z",
  "fetched_at": "2026-11-06T00:00:00Z",
  "evidence_id": "ev-example"
}
```

**Illustrative schema only — `value`, dates, and ID here are placeholders, not claims about Apple.** Use actual provider values in live runs. Track fiscal periods separately from reporting dates, currency and units. Invalid/missing values must be nullable with an explicit reason. Never combine USD and CAD without explicit dated FX rates.

### 3.4 Research state and trace

For each research run store:

- `run_id`, `symbol`, `market`, `model_id`, `started_at`, `finished_at`, `status` (`queued|running|complete|incomplete|failed|cancelled`).
- Stage state: `stage`, `attempt`, `status`, `input_evidence_ids`, `output`, `validation_errors`, `started_at`, `finished_at`.
- Evidence records and source URLs, raw normalized inputs or stable references, calculations and exact inputs.
- Event log: `run_started`, `stage_started`, `tool_called`, `stage_output`, `validation_failed`, `stage_retry`, `stage_completed`, `report_ready`, `run_finished`.
- Token/cost usage if actually exposed by model provider; never invent usage/cost values.

Use polling first (`GET /runs/{id}` every ~1–2 s) or SSE if uncomplicated. Do not fake progress with timers.

### 3.5 Minimum backend API

```text
GET  /api/health
GET  /api/markets/overview
GET  /api/stocks/search?q=...
GET  /api/stocks/{symbol}?market=US
GET  /api/stocks/{symbol}/history?range=1y
GET  /api/watchlist
POST /api/watchlist
DELETE /api/watchlist/{symbol}
GET  /api/positions
POST /api/positions
DELETE /api/positions/{id}
POST /api/chat
POST /api/research-runs
GET  /api/research-runs
GET  /api/research-runs/{run_id}
GET  /api/research-runs/{run_id}/report
GET  /api/research-runs/{run_id}/events
GET  /api/intelligence/news
GET  /api/intelligence/signals
GET  /api/daily-review
GET  /api/industries
GET  /api/industries/{slug}
```

Create typed response models. Separate endpoint completion by phase. Validate symbols, markets, IDs, query lengths, pagination, and dates. Bind local dev API to loopback; keep credentials server-side; no unauthenticated public deployment.

---

## 4. Phase-by-phase executable tasks

### Mandatory progress-tracking protocol (applies to every phase)

Create `docs/PROGRESS.md` **at the start of Phase 0** and keep it up to date throughout implementation. Treat it as the canonical handoff between Codex sessions. Never defer documentation until all phases are complete.

**Update cadence:**

- At the start of each phase: mark the phase `in_progress` and note immediate tasks.
- After each meaningful milestone (at minimum after every 3 completed tasks): update completed items, files changed, issues, and the next action.
- Immediately after running tests: log the actual commands and results, including failures (no invented PASS statuses).
- Whenever there is a blocker, provider failure, scope change, or architecture decision: record the issue and workaround/decision.
- After meeting a phase's acceptance criteria: mark the phase complete and record evidence (commands, screenshots if available, outputs or paths).
- **Before ending, restarting, or context-compacting any Codex session:** update the current state and the next exact action so another session can continue without rediscovery.

Use this concise initial template and keep it current:

```markdown
# Stocker — Implementation Progress

## Current status
- Phase: 0 — Reference audit (not started / in progress / complete)
- Last updated: YYYY-MM-DD HH:MM timezone
- Overall: brief factual summary

## Completed
- [ ] Phase 0: ...
- [ ] Phase 1: ...
- [ ] Phase 2: ...
- [ ] Phase 3: ...
- [ ] Phase 4: ...
- [ ] Phase 5: ...
- [ ] Phase 6: ...
- [ ] Phase 7: ...
- [ ] Phase 8: ...

## Current task / next action
- Current task: ...
- Next executable step: ...

## Test results
- Command: `...` — PASS / FAIL / NOT RUN; supporting details

## Blockers and decisions
- ...

## Files changed / artifacts
- ...
```

Keep this document factual, readable, and proportional. Do not rewrite it from scratch if it already contains useful prior history.


### PHASE 0 — Inspect references and establish foundations

**Tasks**

1. Inspect the existing workspace and Git state before changes, then complete Section 1 reference-clone commands and inspect all specified paths.
2. Write `docs/REFERENCE_AUDIT.md` and `docs/ARCHITECTURE.md` with the six-stage pipeline and UI/data boundaries.
3. Create or non-destructively update `.gitignore`, `.env.example`, `README.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md`, and a short root `AGENTS.md` that tells future Codex sessions to read this implementation plan and `docs/PROGRESS.md` before changing code. Preserve existing project files and instructions; do not duplicate the entire plan in `AGENTS.md`.
4. Decide *which* price-history, financial-statement, market-summary and news provider(s) are genuinely accessible, what keys/licenses they require, and their rate limits. Record in `docs/DATA_PROVIDERS.md` with verified docs URLs. Do not assume a paid API is available.
5. Document selected implementation versions and shell commands. If secrets are needed, leave placeholder env vars; never insert real secrets.

**Acceptance**: Source audit identifies all relevant code paths and repo SHAs; existing project root remains intact and under the correct Git repository; no reference files accidentally staged; architecture and provider selection documented; `docs/PROGRESS.md` is initialized and current.

### PHASE 1 — Runnable backend/frontend skeleton

**Tasks**

1. Scaffold a Vite React TypeScript UI under `frontend/` and a FastAPI app under `backend/`.
2. Set up Python project dependencies and venv. Prefer `backend/pyproject.toml` with an optional `dev` extras group.
3. Implement `/api/health`, typed API client, routing, basic empty pages, shared loading/error/empty states.
4. Add SQLite initialization and migrations (or a clearly documented simple migration strategy).
5. Add an optional `DATA_MODE=fixtures` mode that uses labeled local sample data for testing.
6. Write repeatable startup commands/scripts in README, and `backend/tests/test_health.py`.

**Example commands Codex should make work**:

```bash
cd ~/uni/dh399/stocker/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a **second** terminal:

```bash
cd ~/uni/dh399/stocker/frontend
npm install
npm run dev -- --host 127.0.0.1
```

Do not claim these commands work until the corresponding scaffold and dependencies actually exist.

**Acceptance**: Frontend opens and requests `/api/health`; backend test passes; both projects build/start without keys; README includes tested commands.

### PHASE 2 — Data layer, quotes, stocks, and finance calculations

**Tasks**

1. Implement a `MarketDataProvider` interface and provider-agnostic `Stock`, `Quote`, `PriceBar`, `FinancialFact`, `NewsItem` models.
2. Add symbol normalization: market prefix (`US`), exchange where known, uppercase ticker handling, rejection of invalid/ambiguous symbols. Preserve separate mapping for TradingView symbols.
3. Implement a **real U.S. quote/history provider** selected after verifying API terms, data coverage and keys; an adapter may use Finnhub for allowed U.S. quotes but do not assume its free tier covers everything.
4. Implement SEC EDGAR public **submissions and companyfacts/XBRL** access for U.S. filings; resolve CIK-to-ticker using documented SEC files. Respect SEC fair-access constraints and require a descriptive configured `User-Agent` with a contact email.
5. Normalize financial facts by period, statement type, fiscal year, source, unit, and filing date; avoid mixing quarter and year-to-date figures.
6. Implement basic deterministic calculations: daily return, unrealized P&L, revenue YoY, profit margin, EPS growth when comparable, P/E only when EPS is meaningful, and optionally moving-average/RSI if actual historical bars exist.
7. Add cache with provider-specific TTL, explicit stale flags, retries with backoff/rate limits, and clean failure states.
8. Provide compact recorded **fixture** datasets for AAPL, MSFT and NVDA (synthetic or clearly documented historical snapshots) to test all workflows offline. Never display a fixture as a live quote.
9. Implement `/api/stocks/*`, `/api/markets/overview`, and tests with mocked HTTP providers.

**SEC source**: https://www.sec.gov/search-filings/edgar-application-programming-interfaces  
**SEC fair access**: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data

**Acceptance**: In live mode, at least one test symbol returns real, sourced profile/financials and (when configured) quote/history; invalid data and missing keys result in honest errors; in fixture mode all math tests pass and source metadata is visible.

### PHASE 3 — Six-stage research agents (highest priority)

Implement one **shared model client**, six **role-specific agent sessions** and one **centralized orchestrator**. These roles can use the same underlying model but must have separate prompts and outputs.

| Stage / agent | Input | Required output |
|---|---|---|
| 1. `ProfileAgent` | Symbol, profile, identity/source records | Business overview, listing/currency check, relevant evidence IDs |
| 2. `FinancialAgent` | Period-normalized statements and Stage 1 | Revenue, margins, profits, cash flow/debt observations, calculation IDs, gaps |
| 3. `ExpectationsAgent` | Earnings history, licensed consensus if accessible, guidance/news | Forecasts *only if sourced*; otherwise missing-data statement; evidence IDs |
| 4. `ValuationAgent` | Normalized quotes, metrics, relevant prior stages | P/E and other defensible ratios, historical context, limitations, calculation IDs |
| 5. `RiskAgent` | All findings, source conflicts and relevant filings/news | Bearish counterevidence, unsupported assumptions, discrepancies, conditions that could invalidate claims |
| 6. `ReportAgent` | Validated results of all previous stages | Final Markdown/JSON report with evidence links and clearly flagged gaps |

**Implementation steps**

1. Define strict Pydantic schemas for each stage output; include `summary`, `claims[]`, `evidence_ids[]`, `calculation_ids[]`, `gaps[]` and stage-specific fields.
2. Implement a model interface reading environment variables: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, optional temperature/output limits/timeouts. Support OpenAI-compatible APIs. **Do not auto-load the user's Codex or LiteLLM secrets**.
3. Add `backend/app/agents/prompts/` with six explicit role instructions. Reuse Vibe's conceptual rules: sources must exist, derived numbers come from calculation tools, missing data is not filled by model knowledge, and factual claims must have traceable evidence.
4. Implement bounded tool access: `get_company_data`, `get_financial_facts`, `get_price_history`, `get_news`, `calculate_metric`, `read_prior_stage`. Do not give agents unrestricted shell, local filesystem, or network access.
5. Implement a `ResearchOrchestrator` that executes stages in order and persists results after each stage. Pass prior stage outputs **as validated data**, not as authoritative instructions.
6. Validate every stage **outside** the LLM: schema correctness, referenced evidence existence, numeric values from trusted calculations, currency/unit/period compatibility, and honest incomplete statuses. On validation failure, send actionable feedback and retry at most twice. If irreparable, flag `incomplete` or `failed`; do not loop indefinitely.
7. Let the Risk Agent challenge earlier results. It may request a correction or mark a claim disputed; the orchestrator owns decisions to retry an earlier stage and must cap total revisits.
8. Report generation should include: executive summary, company profile, financial performance, expectations (if available), valuation, risks/counterevidence, cited sources, timestamps, and data gaps. Mark content as research, not investment advice.
9. Store a full real event trail for presentation. User should be able to see what each agent received, produced, and what validation permitted (redact secrets and untrusted content as needed).
10. Implement fixture-mode deterministic model stubs so research pipelines can be tested without API charges. Live runs use actual model output; never present stub outputs as real AI responses.
11. Provide a **single-agent baseline** using the same evidence for a later quality/cost comparison.

**Acceptance**: With fixture-mode tools and model stub, six stages finish and a cited report is saved; a deliberately broken arithmetic claim is rejected, corrected or marked incomplete; run events show stage handoffs and retries; with a configured real model, run one actual test and log provider limitations.

### PHASE 4 — Home, heatmap, stock page, watchlist, simple holdings

**Tasks**

1. Build a clean responsive layout with sidebar tabs matching selected sections: Home, Daily Review, Industry Intelligence, Industry Research, Stock Research, My Stocks, Research Records, Settings/AI.
2. Embed the **official TradingView stock heatmap** (not copied OpenStock widget code). Keep TradingView attribution and its allowed settings. It is a visual-only widget; do not attempt to scrape data from it. Verify whether symbol clicking can navigate to a local stock page. If not, provide a nearby stock search and analysis button; do not claim automatic click integration.
3. Display U.S. overview (indices or explicitly labeled liquid ETF proxies, e.g., SPY/QQQ) with quote timestamp and delayed/stale flags. Never label ETF prices as literal index levels.
4. Build stock search and stock overview pages, including a basic chart, company profile, sourced metrics and a large **Run Research** button.
5. Implement watchlist add/remove/list and a **simple** manual holdings snapshot (`ticker`, `shares`, `average cost`, `USD`); derive unrealized P&L from sourced quotes. Full transaction ledger remains Later.
6. Integrate `/api/research-runs` and render real progress, stage validation status and final report. Handle failure and missing data gracefully.
7. Display clear separation between **Demo/Fixture** and **Live** data.

**TradingView heatmap**: https://www.tradingview.com/widget-docs/widgets/heatmaps/stock-heatmap/  
**TradingView data limitations**: https://www.tradingview.com/widget-docs/faq/data/

**Acceptance**: User can navigate the UI, inspect AAPL/MSFT/NVDA, manage watchlist/positions, launch research, see actual progress, and open final reports. No fake heatmap-to-app link guarantee.

### PHASE 5 — AI chat, research history, user-level integration

**Tasks**

1. Implement stock-focused `/api/chat` with current company context and *read-only* market tools. Separate ordinary chat from a full research run: no automatic six-stage research unless the user explicitly requests it.
2. Include cited answers and source timestamps. Chat must state when it lacks data; it may not fabricate precise prices, financial values, or financial performance.
3. Build a **Research Records** page: list by symbol/date/model/status, open report, view evidence, calculation logs, errors and stage trail; optional report download as Markdown.
4. Add Settings page to display model endpoint status and missing configuration without showing keys. Use server-side env vars or a locally secured configuration; do not put provider keys in frontend `VITE_` env variables.
5. Test chat/research isolation and persistence across app restarts.

**Acceptance**: User can ask a sourced stock question, explicitly start research, and revisit the completed/incomplete analysis after restarting the service.

### PHASE 6 — Daily review, news radar, signals, sector templates

**Tasks**

1. Daily review: compute market summaries from available verified prices, breadth if data coverage supports it, sector data when supported, and relevant headlines. Use accurate terminology for ETF proxies and partial-universe breadth; annotate market session and timestamps.
2. News radar: ingest a small set of allowed news/filing sources, dedupe headline + link, tag by ticker/sector, show publication date and link; do not claim social sentiment without a tested source.
3. Industry signals: choose **2–3 dependable signals**. Store units, observation period, source and retrieved date; render a trend only if a real time series exists. GPU rental rate or hiring data are optional, not prerequisites.
4. Import or adapt the 20 Vibe industry template definitions from `desktop/src/verticals/finance/data/sectors.json`. Preserve the idea of guided prompts, but remove China-only assumptions, label unavailable sources, and adapt examples to U.S. sectors and global supply chains.
5. Implement industry template selection and prompt-run workflow. End-to-end test at least two sectors; other templates may remain guided research prompts rather than a fully autonomous specialized multi-source system.
6. Reuse shared data/evidence/LLM infrastructure; avoid creating a second orchestration system.

**Acceptance**: Daily review and news have real citations/timestamps; signals never present placeholder values as live; all 20 templates render; 2 examples can be run with the model where data permits.

### PHASE 7 — Quality, security, evaluation, demonstration

**Tasks**

1. Backend tests: symbol validation, missing data, fiscal date alignment, currencies, zero/negative earnings P/E, schema violations, evidence mismatch, retry bounds, risk-agent challenge, report generation, database persistence, API errors.
2. Frontend tests: navigation, search, watchlist, holdings calculations, live-vs-demo labeling, research progress, failure states, history.
3. Complete integration using fixture mode and at least one authorized live provider/model run if credentials exist.
4. Evaluate six-stage vs single-agent baseline on a small fixed set of cases with the **same data**. Compare factual citation completeness, numeric errors, unresolved claims, failures/retries, latency and available token consumption. Do not assert a performance advantage without results.
5. Security: reject prompt-injection instructions embedded in SEC/news text, use a provider HTTP timeout, enforce per-run iteration/token budget, redact API keys, validate outbound requests, keep APIs loopback-local, and protect generated stored files.
6. Add `docs/DEMO.md`: step-by-step screen flow for presenting the project and the agent trace to the professor.
7. Update README with architecture diagram, setup, env vars, demo mode, live mode, limitations, source acknowledgments and license notices.

**Acceptance**: All automated checks pass, a fresh checkout can run in fixture mode with documented commands, and the demo works without silently depending on the author's personal environment.

### PHASE 8 — Deferred work (explicitly do not begin before phase 7)

Canadian TSX quote/history/fundamentals with valid data rights and CAD handling; licensed Canadian filings data; full transaction-ledger accounting; backtesting; portfolio risk; screener; bull/bear debate; notifications; alerts; document library; advanced charting. Create issues or a roadmap, **do not silently implement these during MVP development**.

---

## 5. Environment configuration

Create `.env.example` with safe placeholders and comments:

```dotenv
# app mode: fixtures | live
DATA_MODE=fixtures
APP_ENV=development
DATABASE_URL=sqlite:///./stocker.db

# OpenAI-compatible LLM: endpoint may be local LiteLLM or a hosted provider.
# Optional while running fixture-mode tests.
LLM_BASE_URL=http://127.0.0.1:4000/v1
LLM_MODEL=
LLM_API_KEY=

# SEC API: replace with a genuine descriptive name + contact email before live requests.
SEC_USER_AGENT=

# Optional provider keys; select only those actually implemented/documented.
FINNHUB_API_KEY=
NEWS_API_KEY=
FRED_API_KEY=
```

**WSL networking warning:** `127.0.0.1:4000` only works when the user's LiteLLM proxy is reachable from the same network namespace. Check connectivity and `/v1/models` or a small authenticated test first; do not modify the existing proxy configuration. If the model's tool calling / structured JSON is inconsistent, record the failure and keep fixture-mode tests functional.

### Tested local commands to support in the final README

```bash
# backend checks
cd ~/uni/dh399/stocker/backend
source .venv/bin/activate
pytest -q
ruff check .

# frontend checks
cd ~/uni/dh399/stocker/frontend
npm run lint
npm run build
```

Codex must add the actual scripts and dependencies to make these commands valid.

---

## 6. Critical design decisions and traps

1. **Do not fork Vibe wholesale:** Its hundreds of data endpoints and comprehensive portfolio tooling are beyond this project's scope. Its concepts and selected MIT-licensed snippets are useful; the entire platform is not the MVP.
2. **Do not directly merge OpenStock code:** It is AGPL-3.0, and its architecture (Next.js/MongoDB) is different. Use public UI concepts or the official TradingView widget instead. Respect widget terms/branding.
3. **Do not equate a stage name with a separate agent unless behavior differs:** Each specialist needs a unique instruction contract, explicit task, scoped context and output; log their handoffs. Sequential specialists count as a role-based agent workflow.
4. **No self-calculated LLM numbers:** Deterministic code owns calculations; the AI interprets results and identifies evidence.
5. **Market data quality is the bottleneck:** Choose a small, verified set of sources. Handle stale data, quote licensing, rate limits, missing estimates, splits, FX, filing date versus fiscal year and market holidays.
6. **Estimates data can be unavailable:** SEC financials do not provide analysts' consensus forecasts. Keep the ExpectationsAgent and return honest gaps when no licensed estimates data is accessible.
7. **Keep U.S. and Canada honest:** U.S. = supported in MVP; Canada = roadmap until a working data provider and tests exist. TradingView's delayed TSX visuals alone are not backend Canada support.
8. **No false real-time labels:** If quotes are delayed/cached, say so. Distinguish primary index values from ETF proxies.
9. **No unsafe financial conclusions:** Educational research only, no order execution or automatic buy/sell suggestions. Clearly label analysis as non-advisory.
10. **No feature creep:** Do not build the 14 Later features until the first seven phases meet acceptance criteria.

---

## 7. Required tests and project completion rubric

Before declaring the core MVP complete, Codex must prove the following:

- [ ] The new project starts locally from the documented setup, with fixture mode requiring no paid keys.
- [ ] The cloned reference repositories are present (or network limitation documented), with SHA audit and no unreviewed AGPL code copied.
- [ ] Basic U.S. data objects retain timestamps, currency/units, fiscal period and source URL.
- [ ] At least one configured live U.S. quote and SEC financial fact can be retrieved (if network/config is available); failures are transparent.
- [ ] Market heatmap renders or shows a clear third-party/network failure state; the rest of the app still functions.
- [ ] Search, watchlist, simple positions, stock overview and AI chat work.
- [ ] A research run has six distinct stages, structured handoffs and persisted actual execution events.
- [ ] A purposely invalid calculation is rejected; validation failures are visible and retries are bounded.
- [ ] A missing earnings-consensus provider produces `incomplete`/`unavailable`, not fabricated analyst estimates.
- [ ] Research results and evidence can be reopened after restart.
- [ ] Daily review, news radar, 2–3 genuine signals and 20 guided industry templates are available for Milestone B.
- [ ] All backend/frontend tests run; docs list remaining shortcomings and permissions/keys required.

### Definition of done for Codex's final report

For each phase report: changed files, features demonstrated, test commands/results, known failures, and exactly what happens next. Do not report success based solely on generated code or a screenshot mockup.

---

## 8. How to hand this plan to Codex

Save this Markdown file as `~/uni/dh399/stocker/CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md` in the **existing WSL project root** where Codex runs, or attach the file directly to a Codex conversation that can access your repository. The command-line Codex process cannot read a file that only exists as a ChatGPT download link; the file must be copied or attached.

In WSL, after placing the file:

```bash
cd ~/uni/dh399/stocker
ls -l CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md
# Start your existing Codex CLI / wrapper in this directory.
codex
```

If `codex` is not the command you normally use, invoke your existing configured launcher instead; do not change its config. Then send this prompt.

### Paste-this prompt into Codex

> Implement `CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md` as the authoritative project specification. **My existing WSL project directory is `~/uni/dh399/stocker`; do all work there.** First inspect the directory, existing files, and Git status; preserve prior work, do not wipe it, create a different project root, or change my other projects or account-wide Codex/LiteLLM settings. Start Phase 0 by cloning Vibe Research and OpenStock into ignored `references/` folders, recording their commit SHAs, and auditing the referenced implementation files. Build a lightweight U.S.-first React/Vite + FastAPI + SQLite application including an OpenStock-inspired heatmap, stock pages, AI chat, watchlist, simple holdings, six-stage role-based research agents, evidence/calculation validation, bounded retries, research history, and then selected market-intelligence features. Follow the KEEP/LATER/REMOVE decisions and implement the phases in dependency order with real tests and acceptance checks. **Create `docs/PROGRESS.md` immediately and update it regularly: at each phase start/end, at least every 3 completed tasks, after tests, on blockers, and before ending or compacting the session.** Record current state, actual test results, changed files, blockers, and the exact next step. Keep `docs/DECISIONS.md` for architecture choices. Do not copy OpenStock AGPL code, recreate Vibe wholesale, fabricate financial data, or silently assume missing API keys. Continue across phases as far as execution context permits. If external credentials are needed, document the blocker, implement clearly labeled fixtures where appropriate, and proceed with independent tasks.

---

## 9. References

- Vibe Research: https://github.com/simonlin1212/Vibe-Research
- Vibe English README: https://github.com/simonlin1212/Vibe-Research/blob/main/README_en.md
- Vibe orchestrator: https://github.com/simonlin1212/Vibe-Research/tree/main/orchestrator
- Vibe U.S. research instructions: https://github.com/simonlin1212/Vibe-Research/blob/main/orchestrator/src/finance/stages_global.ts
- Vibe research sector templates: https://github.com/simonlin1212/Vibe-Research/blob/main/desktop/src/verticals/finance/data/sectors.json
- OpenStock: https://github.com/Open-Dev-Society/OpenStock
- OpenStock market support: https://github.com/Open-Dev-Society/OpenStock/blob/main/MARKET_SUPPORT.md
- TradingView stock heatmap: https://www.tradingview.com/widget-docs/widgets/heatmaps/stock-heatmap/
- TradingView widget data FAQ: https://www.tradingview.com/widget-docs/faq/data/
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC fair-access policy: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
