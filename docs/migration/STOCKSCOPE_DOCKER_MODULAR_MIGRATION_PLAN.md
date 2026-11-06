# StockScope AI — Docker Compose + Modular Monolith Migration

**Status:** EXECUTION PLAN — not yet applied to the repository  
**Repository:** https://github.com/TTDoorTT/stocker  
**Working directory:** `~/uni/dh399/stocker` (WSL2 Ubuntu on Windows 11)  
**Date prepared:** 2026-11-06  
**Owner decision:** Development environment **B (Docker Compose)** and architecture **B (feature-oriented modular monolith)**.

> This document is an instruction specification for Codex CLI. It is **not a claim that any proposed file or command already exists**. Codex should examine the live working tree before every change and implement this plan incrementally. Never replace working code with an empty scaffold merely to match a diagram.

## 0. Objective, non-goals, and operating constraints

### Required outcome

After one-time Docker Desktop/WSL integration and Docker image setup, a developer executes:

```bash
cd ~/uni/dh399/stocker
docker compose up -d
```

Then opens **http://localhost:5173**. Backend docs: **http://localhost:8000/docs**. `docker compose down` stops the stack **without losing saved research/portfolio data**. Normal source edits hot-reload without rebuilding images; dependency or Dockerfile changes require `docker compose up --build -d`. Include `docker compose ps` and `docker compose logs -f` in documentation.

The backend and frontend are each **one application**. The Python backend retains the six existing logical specialist roles and one orchestrator; Docker runs **two application containers**, not one per agent. SQLite stays SQLite on a persistent named volume. Strata `iq3_s` and all financial-provider services remain **outside** Docker. No new distributed infrastructure.

### Hard non-goals

- **No new stock-research features** during migration (no DCF, screener, new agents, etc.).
- **No live-model performance refactoring** during migration. Known pre-existing `iq3_s` truncation/token-budget failures are out of scope except connectivity regression checks.
- Do not containerize, reinstall, reconfigure, or restart the user's Strata, Codex CLI, LiteLLM, or other user-wide AI services.
- Do not introduce PostgreSQL, Redis, Celery, message brokers, Kubernetes, paid APIs, or microservices.
- Do not copy OpenStock AGPL source code. Keep existing reference/license boundaries intact.
- Do not duplicate old source directories within the repo as a rollback strategy; **Git is the source-code rollback mechanism**.
- Do not push to GitHub automatically without user authorization. Local commits on a dedicated branch are appropriate and expected at verified phase boundaries.
- Do not change financial behavior, formula semantics, evidence references, API paths/DTOs, or the SQLite schema as part of file moves.

### Preserve these existing invariants

1. The current six stages: `profile -> financials -> estimates -> valuation -> risk -> report`, including bounded revalidation, risk correction, event trace, reports, and run persistence.
2. Explicit `DATA_MODE=fixtures` with **visibly synthetic** data and deterministic model stub; **never** silently use fixtures in live mode.
3. Live finance provider semantics, provenance (currency/period/source/capture time), and explicit unavailable data.
4. Canadian `.TO`/`.V`, CAD history/positions, Bank of Canada macro availability labels, and lack of Canadian-only statements/quotes; no SEDAR+ scraping.
5. Existing REST endpoints, response models, frontend routes, visual components, tests and browser smoke behavior.
6. Existing user-owned ignored root `.env`, SEC contact, Finnhub key, and `iq3_s` model/auth details. **Never show the secrets in logs, artifacts, responses or commits.** The documented model address is `http://169.254.83.107:47832/v1`, but read the *current environment configuration* instead of hardcoding it.
7. Historical research data and SQLite v1 persistence. Docker must not initialize an empty database while making existing history appear lost without a documented/imported migration path.
8. Source on the WSL2 Linux filesystem (`~/uni/dh399/stocker`), not copied into `/mnt/c` to develop.
9. The official TradingView embed remains an isolated third-party visual, not a data source for agents.

### Current repository map (verify again, do not assume unchanged)

- Backend: `backend/app/main.py`, `app/data/service.py`, `data/http.py`, `data/history.py`, `data/valet.py`, `agents/client.py`, `agents/tools.py`, `agents/prompts/*.md`, `orchestrator/engine.py`, `orchestrator/validation.py`, `finance/metrics.py`, `db/repository.py`, `services/*`, `models/*`.
- Frontend: `frontend/src/app/App.tsx`, `src/pages/{Home,Stock,Research,Intelligence,MyStocks}.tsx`, `src/components/{shared,Search,PriceChart,Heatmap}.tsx`, `src/api/client.ts`, `src/types/index.ts`, `src/styles.css`.
- Root: `.env.example`, `.gitignore`, `AGENTS.md`, `CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md`, `docs/{PROGRESS,DECISIONS,ARCHITECTURE,API,DATA_PROVIDERS,DEMO,...}.md`, `fixtures/`.
- Backend lock/dependency files: `backend/requirements.lock`, `backend/requirements-history.lock`, `backend/pyproject.toml`.
- Frontend lock/dependency files: `frontend/package-lock.json`, `frontend/package.json`.
- Current native Vite proxy: `http://127.0.0.1:8000`; current backend `TrustedHostMiddleware` only permits loopback and testserver.
- `backend/app/core/config.py` derives `ROOT` from `__file__`; this will break if moved without care.
- Current browser smoke script, `backend/tests/browser_smoke.py`, **starts its own native servers and refuses occupied ports**. It must be tested separately from the running Docker stack or refactored with an explicit externally-running mode.
- The repository previously documented **117 backend tests** and **18 frontend tests** passing; these are historical baselines, not acceptance by themselves. Verify at execution time.
- Current documented live research is **not** fully passing: sourced `iq3_s` profile previously succeeded, but financials hit output length/token limits. Do not misrepresent that as a new Docker failure or promise it will be solved here.

## 1. Architecture contract (implement and document first)

### Runtime architecture

```text
Windows 11 + WSL2 (source, Git, Codex CLI)
      |
      v
Docker Compose (single local project)
  ├── frontend: Node 22 + React/Vite dev server, localhost:5173
  │       └── Vite proxy /api -> http://backend:8000
  ├── backend: Python 3.13 + FastAPI/uvicorn, localhost:8000
  │       ├── app modules: market_data, research, portfolio, intelligence
  │       ├── pure finance calculations
  │       └── SQLite file -> named Docker volume (e.g. /data/stockscope.db)
  └── named data volume (not a separate database container)

Backend outbound connections:
  ├── SEC / Finnhub / Yahoo / Alpha Vantage / FRED / Bank of Canada (HTTPS)
  └── authorized existing Strata OpenAI-compatible model endpoint (external)
```

Use a normal **development Compose setup**, with Vite HMR and `uvicorn --reload`, using bind mounts. Do not require `docker compose up --watch` for everyday use. Configure the services to restart with `docker compose up -d` and publish ports only on host loopback (`127.0.0.1`). Containers may listen on `0.0.0.0` **internally**.

### Backend module ownership

Target layout (add subfiles **only** when actual responsibility warrants them):

```text
backend/
  Dockerfile
  pyproject.toml
  app/
    main.py                       # composition root: app setup / router registration
    core/
      config.py                   # app settings and stable root/path configuration
      dependencies.py             # shared FastAPI dependency wiring (if necessary)
      database.py                 # connection setup/SQLite lifecycle
    modules/
      market_data/
        router.py                 # market/stock/history/search API endpoints
        service.py                # typed stock snapshot + history facade
        schemas.py                # normalized stock/data models or exports
        providers/
          sec.py
          finnhub.py
          yahoo.py
          alpha_vantage.py
          bank_of_canada.py
      research/
        router.py                 # research-runs, events/report, chat API endpoints
        service.py                # run scheduling and research application facade
        schemas.py                # research inputs, stages, claims and run DTOs
        repository.py             # run/event persistence adapter
        orchestrator.py           # six-stage execution and retry/handoff
        validation.py             # schema/evidence/numeric validation
        reports.py                # Markdown report renderer
        agents/
          client.py               # model client, fixture model
          tools.py                # captured data tools
          prompts/*.md            # unchanged prompts
      portfolio/
        router.py                 # watchlists/positions endpoints
        service.py                # position operations, valuation using market facade
        repository.py             # watchlist/position persistence adapter
      intelligence/
        router.py                 # daily-review/news/signals/industries endpoints
        service.py                # orchestration of intelligence views
        news.py                   # news processing/summary
        industries.py             # industry templates
    finance/
      metrics.py                  # pure functions; no HTTP, DB, or AI requests
  tests/                          # tests by feature, plus integration tests
```

**Do not** split the existing repository into separate Python distributions. Maintain a single `app` package. Move logic from `main.py` into `APIRouter` modules; keep `create_app(...)` support for dependency-injected tests. Pure calculations remain in `finance/` and must not depend on API modules. A new feature is normally added as `modules/<feature>/` with routes, service, schemas, and tests as needed.

**Module contracts and dependency rules:**

- `api/router` functions may call their own service, validate input, map errors and return schemas; they must not contain provider parsing, SQL, financial formulae or lengthy AI orchestration.
- Feature services own their behavior and use stable typed public interfaces of other features; never reach into other module's internal provider/DB helpers.
- `market_data` exposes normalized snapshots / data-availability information and hides provider-specific network details.
- `research` consumes a `market_data` facade and pure `finance` calculations; it does not call SEC/Finnhub adapters directly.
- `portfolio` owns holdings and position logic, consuming market prices with currency checks; it does not call research internals.
- `intelligence` consumes market-data facade and invokes research through a supported application entrypoint when needed.
- `finance/metrics.py` is dependency-free domain code and never imports database, FastAPI, AI or external HTTP clients.
- Cross-feature shared Pydantic schemas are allowed only where they are stable contracts; do not create a generic `utils.py` as a dumping ground.
- Avoid circular imports by using interfaces and dependency injection. Do **not** build a heavy dependency-injection framework unless needed.
- Existing repository SQLite tables (`runs`, `events`, `watchlist`, `positions`) remain unchanged for this migration. Feature repositories may wrap the existing storage layer without altering DB file format or query behavior.
- Prefer smaller cohesive files, but **do not** enforce hard line-count caps; any threshold (e.g., 300 lines) is only a review warning.

### Frontend feature ownership

```text
frontend/
  Dockerfile
  src/
    app/
      App.tsx                  # small root composition
      router.tsx               # application route registration
      layout/                  # Sidebar, Header, Shell
    features/
      market/
        pages/                 # HomePage, StockPage
        components/            # StockSearch, PriceChart, Heatmap
        api.ts                 # market endpoint wrappers
        types.ts               # optional feature-owned types
      research/
        pages/                 # ResearchLanding, RunDetail, Records
        components/            # Progress, Report, Evidence detail
        api.ts
      portfolio/
        pages/                 # MyStocks
        components/
        api.ts
      intelligence/
        pages/                 # DailyReview, NewsRadar, Industries
        components/
        api.ts
    shared/
      api/client.ts            # ONLY generic fetch/error abstraction
      ui/                      # generic Empty, Loading, Error etc.
      hooks/                   # reusable useResource or replacements
      utils/                   # date/number/currency formatting
      types/                   # stable truly shared DTOs
    styles/                    # global tokens/resets; feature CSS as needed
```

- Put business/feature-specific components in the **feature** folder, even if multiple pages in that feature use them. `shared/` is reserved for broadly reusable UI/hooks/utilities.
- `shared/api/client.ts` handles HTTP requests/errors; endpoint functions live with their features (`features/research/api.ts` etc.).
- Keep browser-facing provider keys **absent**; React receives only backend-provided normalized data.
- Route URLs, navigational labels, API request shapes and current chart/TradingView behavior must remain stable.
- Avoid massive page files; extract behavior into hooks or feature components when it increases cohesion, not artificially.

### Naming & style

| Entity | Standard | Example |
|---|---|---|
| Python modules, functions | `snake_case` | `report_renderer.py`, `build_report()` |
| Python classes, Pydantic types | `PascalCase` | `ResearchOrchestrator` |
| Backend feature folders | `snake_case` | `market_data/` |
| React components/files | `PascalCase.tsx` | `AgentProgress.tsx` |
| React hooks | `useCamelCase.ts` | `useResearchRun.ts` |
| TS variables/functions | `camelCase` | `startResearch()` |
| Frontend feature folder names | `kebab-case` | `market-data/` for new multiword names |
| Test files | `test_*.py`, `*.test.ts(x)` | `test_providers.py` |
| Env variables | `UPPER_SNAKE_CASE` | `DATA_MODE` |
| REST resources | lowercase/hyphen/plural | `/api/research-runs` |

Python: 4-space indentation, Ruff with consistent 110-character width (matching existing repo); frontend: 2-space indentation, consistent quotes/semicolons/imports, Biome. Avoid redundant tools (no Prettier+Biome overlap). TypeScript strict/type checking remains. Python typing introduced progressively (Pyright as a subsequent non-blocking baseline and gradually enforced new-module check).

## 2. Delivery strategy and guardrails

### Version control

- Use **one dedicated migration branch**, e.g. `chore/docker-modular-migration`, created from the current user-approved stable commit. Do not alter the existing `main` history.
- Use small commits at phase gates: `chore: establish baseline`, `chore: add compose dev environment`, `chore: add formatting and CI`, `refactor: modularize backend ...`, etc. Each commit should represent one verified coherent step.
- Git is the rollback for **committed source**. Do not store duplicate legacy source directories inside this repo.
- Git does **not** protect ignored `.env` or local SQLite data. Preserve the current settings file and make a safe database backup **outside the repository** before moving storage. Do not commit secrets or sensitive database contents.
- If the working tree is dirty, inspect and preserve user changes; never `git reset --hard`, `git clean -fd`, overwrite `.env`, or stash user modifications automatically without review.
- **No automatic GitHub push** unless user explicitly requests it. Provide a final branch/commit list and test evidence.

### Execution rhythm

At each phase:

1. Read relevant existing files and identify constraints; make a small change.
2. Run relevant tests; capture exit codes and concise failures.
3. Compare API behavior/schema, existing fixture labels and feature behavior against baseline.
4. Commit only verified progress; if blocked, preserve the working tree, document the blocker, and do not falsely mark the phase complete.
5. Update `docs/PROGRESS.md` with date/time, actual commands/results, changed files, known remaining failures, **exact next step**; record architectural decisions in `docs/DECISIONS.md`.
6. Keep `docs/ARCHITECTURE.md`, `README.md`, and `docs/DEVELOPMENT.md` aligned with reality.

Avoid pure file moves mixed with business changes. If a module migration needs a small compatibility shim, document why and remove it once callers migrate; do not leave two independent implementations indefinitely.

## 3. Phase 0 — Baseline, branch and data protection

**Goal:** Know exactly what works today, preserve user data, ensure source rollback via Git.

### Commands for Codex to execute (adapt only for environment)

```bash
cd ~/uni/dh399/stocker
pwd
git status --short
git branch --show-current
git log -1 --format='%h %s'
git check-ignore .env || true
docker --version
docker compose version
```

Review `AGENTS.md`, `CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md`, `docs/PROGRESS.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `backend/pyproject.toml`, `frontend/package.json`, `backend/tests/browser_smoke.py`. If user changes are present, preserve them and decide whether branch creation is safe before doing it.

On a clean working tree, create a branch:

```bash
git switch -c chore/docker-modular-migration
```

Baseline native checks (do not reinstall/upgrade anything unnecessarily):

```bash
cd ~/uni/dh399/stocker/backend
./.venv/bin/pytest -q
./.venv/bin/ruff check .
cd ../frontend
npm run lint
npm run test
npm run build
cd ..
```

If virtual environment/dependencies absent, first follow README's documented install or establish a clean documented environment. Do not claim tests passed if they were not executed. Browser smoke starts ports 8000/5173; run it **with native servers stopped**, in a safe fixture context, if its local Playwright dependencies are available.

**Database:** inspect the configured `DATABASE_URL` safely without printing secrets. Check file path (defaults to relative `backend/stockscope.db` for native backend cwd). Use Python `sqlite3.Connection.backup()` or `sqlite3 .backup` to make an integrity-verified copy outside the project root, only if user data exists; do not copy source trees. Document where it is, never commit it. Treat SQLite WAL mode/live connection consistency correctly—prefer the backup API over copying a live `.db` file. Do **not** run `docker compose down -v`.

**Acceptance:** baseline command results recorded; branch exists; secrets ignored; database state/backups documented; no behavior change.

## 4. Phase 1 — Docker development stack (before module moves)

**Goal:** Achieve simple startup from existing code without changing application behavior.

### 4.1 Files to implement

```text
compose.yaml
backend/Dockerfile
frontend/Dockerfile
.dockerignore                 # root build context; optional frontend/.dockerignore for frontend context
docs/DEVELOPMENT.md
frontend/vite.config.ts       # configurable proxy
backend/app/main.py           # narrow TrustedHost fix if needed
backend/app/core/config.py    # only narrow configuration/path fix if needed
README.md                      # Docker first; native alternative still documented
.gitignore                     # exclude new local runtime artifacts
```

Use **Python 3.13** and **Node 22** to match existing tested environment, unless runtime verification requires a documented compatible adjustment. Pin image minor/digest for reproducibility when feasible. Use `npm ci --legacy-peer-deps` as the current README notes a peer resolution issue; verify lockfile compatibility before changing it. Backend dependencies are pinned in `requirements.lock` and optional history in `requirements-history.lock`; support existing yfinance functions if the optional extra is included. Put installed dependencies **inside images**, not mounted from the Windows host.

### 4.2 Compose specification (implementation reference, not a fully built file)

```yaml
name: stockscope
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file:
      - .env
    environment:
      DATABASE_URL: sqlite:////data/stockscope.db
      PYTHONDONTWRITEBYTECODE: "1"
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - stockscope_data:/data
      - ./backend/app:/workspace/backend/app
      - ./fixtures:/workspace/fixtures:ro
      # Add read-only test mounts only if tests are intended to run inside the container.
    working_dir: /workspace/backend
    command: ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]
      interval: 10s
      timeout: 5s
      retries: 5
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      API_PROXY_TARGET: http://backend:8000
    ports:
      - "127.0.0.1:5173:5173"
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/index.html:/app/index.html:ro
      - ./frontend/vite.config.ts:/app/vite.config.ts:ro
    depends_on:
      backend:
        condition: service_healthy
    working_dir: /app
    command: ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
volumes:
  stockscope_data:
```

**Codex must adapt, validate, and finish this sketch:** Dockerfiles must install all needed packages, set workdirs consistently, copy required `fixtures/` and prompt files into backend image, avoid `.env` copying, and ensure dependency/lock compatibility. Verify that container runtime maps old `ROOT` fixture lookup correctly; if `config.py` moves later, replace brittle `parents[...]` logic with explicit project path resolution without breaking tests. If bind-mount behavior is unreliable, troubleshoot WSL integration; only then consider Compose Watch with a separate documented command. The *default everyday* UX must remain `docker compose up -d`.

Expose container ports only on host loopback. It is correct for Vite/Uvicorn to listen on `0.0.0.0` *inside* containers. Keep API CORS/local-origin policies restrictive. Vite proxy target should use an env variable and `changeOrigin` as appropriate. Backend `TrustedHostMiddleware` should allow the specific Docker service hostname (`backend`) if/when it is needed, **not** wildcard hosts. Keep native Vite proxy fallback `127.0.0.1:8000` for non-Docker development.

### 4.3 Strata connectivity — strict, separate diagnostic

- Existing model: `iq3_s`, user-configured bearer key, external OpenAI-compatible endpoint. Do not log the key or print `.env` contents.
- First verify Docker backend container can reach the configured endpoint *as-is*. A request to `GET /models` or a minimal authorized authenticated call is sufficient; never trigger long production-style research merely for connectivity.
- If the link-local address is not routed from Docker, diagnose network route, firewall, service binding, Docker bridge and host reachability. On Docker Desktop, `host.docker.internal` may help **only if** the model is actually accessible via the host; do not assert this in advance.
- `Settings.model_endpoint` currently allows HTTP only for loopback or link-local IPv4. If a host-bridge hostname is genuinely needed, implement a **narrow and test-covered dev-only allowlist**; do not allow arbitrary insecure HTTP or embedded credentials. Keep existing SSRF/access protections.
- If model access cannot be made to work safely, **stop** and record exact connectivity failure; fixture Docker acceptance can pass, but do not label live-model connectivity complete.

### 4.4 Database migration

- Named SQLite volume path `sqlite:////data/stockscope.db` (four slashes for absolute `/data/..` in SQLite SQLAlchemy-like URL syntax used by the custom repository parser; test actual parsing and file creation).
- Inspect existing database and back it up outside repo. Validate it (`PRAGMA integrity_check`, `PRAGMA user_version`, table counts) and transfer/import *only with a verified, documented procedure*. Do not use raw `cp` against actively writing DB; prefer SQLite backup API and a container that can access the volume with services stopped.
- Check run IDs, events, watchlist symbols and positions before/after import. If no existing database, create a new one explicitly and document this fact.
- The project currently has no user auth; keep local-only host port binding. Treat saved research and position data as sensitive local state.
- `docker compose down` must retain the volume; **never** use `down -v` in default cleanup targets.

### 4.5 Functional verification

```bash
cd ~/uni/dh399/stocker
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
curl --fail http://127.0.0.1:8000/api/health
curl --fail http://127.0.0.1:5173/
# Browser: open http://localhost:5173; confirm proxy /api works, no 400 TrustedHost.
docker compose logs --tail=100 backend frontend
# Stop/restart; recheck database records
docker compose down
docker compose up -d
```

For fixture tests, do **not overwrite the user's live `.env`**. Use an isolated fixture-mode override file/environment or separate Compose test profile; ensure the isolated DB is not the real live DB. Test hot-reload by editing/restoring a harmless fixture/test-visible code path. Rebuild after dependency modifications.

**Acceptance:** first `up --build -d` and subsequent `up -d` work; real frontend `/api` proxy succeeds; hot reload observed; persistence preserved; external model connectivity explicitly pass/fail recorded; native startup still possible.

## 5. Phase 2 — Unified developer commands

Add root `Makefile` with targets: `dev`, `stop`, `status`, `logs`, `test`, `lint`, `format`, `format-check`, `typecheck`, `check`, `build`, `smoke` (only if safe in current test context), `rebuild`. Default `dev` invokes `docker compose up -d` (first build as necessary); `stop` invokes `docker compose down`. Document `make` as an optional convenience wrapper, **not an additional required runtime**. Every target must have a real underlying command, correct workdir and exit status; fail loudly. `make test` can use `docker compose exec -T` when running services or `docker compose run --rm` for one-off tests; ensure tests never write to the live database. Do not install a second task runner unless clearly justified.

**Acceptance:** commands work from repo root; `make stop` does not remove SQLite; docs match commands; `docker compose up -d` remains sufficient without Make.

## 6. Phase 3 — Quality tooling / format-only baseline

Implement/extend:

- `backend/pyproject.toml`: Ruff linter and formatter; keep line width 110; start with existing `E4,E7,E9,F,I` rules and add `B`, `UP` incrementally after fixing actual diagnostics. Configure Python target as the **minimum supported version**, not just the dev interpreter. Avoid blanket ignores.
- `frontend`: exact-pinned `@biomejs/biome` dev dependency, committed lockfile; `biome.json` with 2-space indentation, consistent quotes/semicolons, import organization, practical React hooks checks. Keep `tsc --noEmit` as a separate `typecheck` script; do not relabel it as lint.
- `.editorconfig` (optional, helpful): LF, charset UTF-8, newline at EOF, Python 4-space, TS/TSX/JSON/CSS 2-space.
- `pre-commit` hook configuration is optional but valuable; **CI is authoritative**. If hooks are added, never require global tools not documented/installed.
- Incremental `pyright` typing (optional initial baseline) on new/typed modules only; do not add hundreds of suppressions simply to pass.

Suggested frontend scripts (adapt to actual Biome version syntax):

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "typecheck": "tsc --noEmit",
    "lint": "biome lint .",
    "format": "biome format --write .",
    "format:check": "biome format .",
    "check": "biome check .",
    "ci": "biome ci .",
    "test": "vitest run"
  }
}
```

For Python:

```bash
cd backend
ruff format --check .
ruff check .
pytest -q
```

**Crucial sequencing:** Run the formatter in a **standalone formatting-only commit** that doesn't mix moves, renames, behavior changes or rule rewrites. Then incrementally fix lint warnings without changing business behavior. Avoid overly broad auto-fixes in financial calculations or safety code; review diffs carefully. Store a `.git-blame-ignore-revs` entry for the bulk format commit if useful.

**Acceptance:** format/lint commands pass, existing tests and frontend build still pass, no external behavior changes; no binary/data files automatically reformatted.

## 7. Phase 4 — Backend modularization (one subsection at a time)

### 4A. Separate API transport

- Extract endpoints from `backend/app/main.py` into named `APIRouter`s in `modules/{market_data,research,portfolio,intelligence}/router.py`.
- Preserve exact route paths, HTTP methods, status codes, validations, response models, exception handlers, CORS/origin checks, and testable `create_app(...)` dependency injection.
- Leave `main.py` to configure app lifespan, exception handlers, shared services and register routers; don't create a second parallel backend app.
- Tests: `backend/tests/test_api.py`, `test_health.py` + route contract comparison; existing route list should remain equivalent.

### 4B. Market data provider separation

- Move from `data/service.py` into provider adapters; preserve common `ProviderHTTP` policies, caching, rate limits and error sanitization.
- Preserve `normalize_symbol` handling, SEC fiscal period/filing semantics, annual calculations and evidence IDs, yfinance history metadata/currency checks, Canadian Valet series, and exact unavailable behavior.
- Public typed facade `MarketDataService` or existing `DataService` alias should remain stable for callers and tests until migration complete.
- Tests: `test_data.py`, `test_provider_strategy.py`, `test_intelligence.py`; no new provider endpoints or financial behavior changes.

### 4C. Portfolio ownership

- Extract watchlist/position API+service/repository while using the same existing tables/columns.
- Preserve CAD/USD listing-currency matching and no silent FX conversion.
- Tests: existing API/finance tests plus a new service-level regression if necessary.

### 4D. Research ownership

- Move model client, prompts, tools, orchestrator, output validation, report renderer, events and run persistence behind research module facade.
- Preserve the **exact six stages**, correction loop bound, tool and model budgets, metadata, reasons for incomplete status, fixture stub, storage JSON and state transitions.
- Reports, chat, and research-runs remain available at current routes.
- Tests: `test_model.py`, `test_research.py`, `test_api.py`, `test_news_summary.py`; fixture report and saved events equal semantically (timestamps/run IDs may legitimately differ).
- No attempted repair of already-existing `iq3_s` output-truncation and total-token budget limitation in this phase.

### 4E. Intelligence ownership

- Separate daily-review/news/signals/industries route and services; preserve all 20 templates, existing unsupported coverage labels, headline-only summary limitations and Valet/FRED semantics.
- Tests: `test_intelligence.py`, `test_news_summary.py` and browser smoke.

### 4F. Imports and architectural checks

- Remove temporary compatibility imports only when all callers have migrated.
- Add a small dependency-boundary test (AST/import inspection or vetted tool) that checks key forbidden imports, e.g., `research` must not import `market_data.providers` or `db.repository` internals; `finance.metrics` must not import FastAPI/httpx/SQLite/model clients.
- Keep shared typed contracts in a deliberate stable location, not generic global helpers.
- Include positive tests for public service facades.

**Acceptance per subphase:** run focused tests + relevant lint/typecheck + full suite where changes cross boundaries. Small verified commits; no simultaneous frontend-wide rewrites.

## 8. Phase 5 — Frontend feature migration

Move incrementally; preserve routes, display labels and existing interaction semantics:

| Current file | Target module | Notes |
|---|---|---|
| `app/App.tsx` | `app/App.tsx`, `app/router.tsx`, `app/layout/*` | Keep root small; preserve navigation/settings route |
| `pages/Home.tsx` | `features/market/pages/HomePage.tsx` | Existing home/positions preview behavior must persist |
| `pages/Stock.tsx` | `features/market/pages/StockPage.tsx`; research landing -> research feature | Chat component may live in research feature but retain stock page integration |
| `pages/Research.tsx` | `features/research/pages/*`, `features/research/components/*` | Preserve 1.5-second polling and report download |
| `pages/MyStocks.tsx` | `features/portfolio/pages/MyStocksPage.tsx` | Preserve validation and currency labels |
| `pages/Intelligence.tsx` | `features/intelligence/pages/*`, `components/*` | Keep news, FRED/Valet, daily review, industries |
| `components/Search.tsx` | `features/market/components/StockSearch.tsx` | Keep topbar integration |
| `components/PriceChart.tsx`, `Heatmap.tsx` | `features/market/components/*` | Keep TradingView failure/retry isolation |
| `components/shared.tsx` | `shared/ui/*`, `shared/hooks/*`, `shared/utils/*` | Do not create one giant new shared module |
| `api/client.ts` | `shared/api/client.ts` + per-feature `api.ts` | Only generic fetch stays shared |
| `types/index.ts` | feature `types.ts` and truly shared DTOs | Avoid cyclic type imports |

Use `Biome` and TypeScript checks after each move. Prefer the existing React tests (`frontend/src/app/App.test.tsx`, `components/Heatmap.test.tsx`) as regression guards, adapting imports without weakening assertions. Add tests for extracted feature logic when needed.

**Acceptance:** all routes work, no browser runtime/page errors, mobile 390px layout still works, report download works, stock search/positions/news/heatmap behavior preserved.

## 9. Phase 6 — CI, automated architecture gates, documentation

Create `.github/workflows/ci.yml` running on pull requests and pushes for the migration branch/main, with **no credentials** or external Strata dependency:

1. **Backend quality:** Python setup, install pinned dependencies, `ruff format --check .`, `ruff check .`, incremental typing scope.
2. **Backend tests:** `pytest -q` in fixture/mocked mode; run against isolated SQLite test DB.
3. **Frontend quality:** Node 22 setup, `npm ci --legacy-peer-deps`, `npm run ci`, `npm run typecheck`.
4. **Frontend test/build:** `npm run test`, `npm run build`.
5. **Docker build/boot check:** `docker compose config --quiet`, `docker compose build`, isolated fixture-mode smoke (backend health and frontend /api proxy). Do not use the live `.env` or require provider keys. Use an explicit test env file / test-profile config created from safe fixture values for CI; never check in live credentials.

Use least-privilege action permissions and verified/pinned action revisions. CI logs must not show secrets, reports with sensitive data, or authorization headers. Run semantic import-boundary tests with the backend tests. If browser smoke executes in CI, provide a CI-safe mode that tests already-started services or runs native smoke with ports unoccupied; don't call the existing standalone `browser_smoke.py` while Docker occupies ports.

Update root docs:

- `README.md`: quickstart with Docker first; native fallback; accurate live-mode limitations.
- `docs/DEVELOPMENT.md`: prerequisites (Docker Desktop + WSL integration), first-run `.env` rules, startup/rebuild/stop, logs, test commands, source reload, networking/Strata diagnostics, persistent volume and safe DB import, troubleshooting.
- `docs/ARCHITECTURE.md`: module boundaries, public interfaces, dependency arrows, frontend/back structure, runtime diagram; do **not** delete meaningful original architectural constraints.
- `AGENTS.md`: formal Codex conventions and mandatory verification checklist; preserve all existing financial/safety instructions and `docs/PROGRESS.md` update requirement.
- `docs/DECISIONS.md`: ADR-style notes explaining two-container Compose, SQLite persistence, modular monolith, static tooling, and why no microservices.
- `docs/PROGRESS.md`: concise current status at top; preserve history (do not throw it away), record exact next action and test results; optional historical sections can be moved to a well-labeled `docs/history/` document if necessary, not duplicate old *source code*.

### Codex-specific `AGENTS.md` rules to enforce

1. Read architecture + progress + API contracts before changes.
2. Every new feature belongs to an owned module; create only warranted files.
3. HTTP routers are thin; providers are isolated; finance is pure; research consumes normalized market-data contracts.
4. No private cross-module imports; shared code must be truly reusable.
5. Type all API/public service contracts; avoid unjustified `Any` / `any`.
6. Preserve evidence citations, numeric validation, fixture/live separation, Canadian limitations and data-rights restrictions.
7. Bug fixes require regression tests; new integrations require mocked tests, and any live tests must be explicitly authorized and accurately labeled.
8. Format/lint/typecheck/tests/build pass before a phase is declared complete.
9. No new dependencies/infrastructure without documented rationale.
10. Never write credentials into Dockerfiles, frontend `VITE_*`, source control, artifacts, or logs.
11. Never modify the user's global Strata/Codex/LiteLLM settings to make local Docker tests pass.
12. Update `docs/PROGRESS.md` at milestones with real commands/results; record core architecture choices in `docs/DECISIONS.md`.
13. End each phase with changed files, acceptance evidence, deviations, unresolved issues and rollback commit.

## 10. Phase 7 — Final acceptance and cleanup

### Acceptance matrix (do not check a box without a successful command or direct verification)

| Gate | Verification |
|---|---|
| G1 First-run setup | Docker Desktop WSL integration works; `docker compose up --build -d` starts both |
| G2 Everyday startup | `docker compose down && docker compose up -d` succeeds with no dependency reinstall |
| G3 UI available | Browser `http://localhost:5173` loads Home in fixtures; no JS runtime errors |
| G4 API proxy | Frontend `/api/health` and search work without 400 Bad Host/502 proxy |
| G5 Reload | Edit source => Vite HMR and backend reload without image rebuild |
| G6 Persistence | Watchlists/positions/saved run/events survive container recreation |
| G7 Test isolation | Fixture checks do not read/write live database or call paid/credentialed APIs |
| G8 Unit tests | Current backend and frontend suites pass (baseline historically 117/18) |
| G9 Build/types | Python lint/format, Biome, TypeScript and production frontend build pass |
| G10 E2E/visual behavior | Existing browser fixture smoke, widget failure/retry and 390px layout pass |
| G11 Financial semantics | Source IDs, currencies, fiscal periods, failure and unavailable modes preserved |
| G12 Agent behavior | Six stages/retry/risk loop/report/events unchanged in synthetic mode |
| G13 Strata reachability | Container reaches authenticated configured `iq3_s` (if accessible); if not, explicit documented blocker, no hidden change |
| G14 CI | Required GitHub Actions checks pass on branch with no personal credentials |
| G15 Code boundaries | No forbidden cross-module imports; new architecture rules documented |
| G16 Developer guide | Docker, rollback, DB backup/import, commands and troubleshooting match actual behavior |

**Note:** G13 may be documented as blocked without invalidating **fixture-only Compose delivery**, but the overall migration must not be labeled **fully accepted for live mode** until connectivity is verified. Likewise, pre-existing full sourced research token failures must remain disclosed and are not solved by rearranging files.

### Final verification commands (adapt to actual implemented scripts)

```bash
cd ~/uni/dh399/stocker

docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:5173/
# Use an isolated fixture environment for the automated tests:
# docker compose run --rm ... pytest -q
# docker compose run --rm ... npm run test
# docker compose run --rm ... npm run typecheck
# docker compose run --rm ... npm run ci
# docker compose run --rm ... npm run build

docker compose down
docker compose up -d
# Verify saved data still exists, then stop if appropriate.

git status --short
git diff --check
```

Do not report success based solely on build success. Distinguish **implemented**, **tested**, **live verified**, and **blocked**.

## 11. Common hazards / stop conditions

Stop the affected phase rather than making an unsafe workaround if any of these occurs:

- User-owned `.env` is overwritten/exposed or any key appears in staged files/logs.
- Existing SQLite data cannot be safely located/verified or is at risk of being replaced.
- Docker connectivity to Strata fails and the only proposed fix is broad HTTP/host security disablement.
- Build requires altering/removing unrelated user-wide services or invasive Windows firewall changes.
- New provider access terms would require unapproved data scraping or paid entitlement.
- Tests begin using live finance providers silently, or fixture data is presented as sourced research.
- Architecture refactor changes API DTOs, formulas, evidence semantics, run states, or DB schema unexpectedly.
- Broad auto-format changes obscure functional changes; split the commits and rerun tests.

## 12. Required Codex completion summary

At the end, provide:

1. Branch name, base commit, new commits (short SHA + purpose), whether pushed (default **no**).
2. Final directory tree showing key backend and frontend modules.
3. Docker setup and day-to-day commands, URLs, hot reload behavior, DB volume path.
4. Actual commands/run results for tests, CI, Docker health/proxy/browser checks and Strata connectivity.
5. Explanation of any intentional API/contract changes (ideally none).
6. Confirmation that `.env`, keys, and SQLite data were preserved; do not print secrets or personal data.
7. Known limitations, especially pre-existing live research token failures and incomplete Canadian coverage.
8. `docs/PROGRESS.md` exact next action for subsequent feature development.

## 13. Official implementation references

Use the official documentation when implementing details; verify current syntax and versions instead of relying on this sketch alone:

- Docker Compose Getting Started — https://docs.docker.com/compose/gettingstarted/
- Compose `depends_on` / healthchecks — https://docs.docker.com/reference/compose-file/services/
- Docker Compose Watch vs bind mounts — https://docs.docker.com/compose/how-tos/file-watch/
- Docker Desktop WSL 2 — https://docs.docker.com/desktop/features/wsl/
- Ruff formatter and lint — https://docs.astral.sh/ruff/formatter/ and https://docs.astral.sh/ruff/linter/
- Biome CLI — https://biomejs.dev/reference/cli/
- GitHub Actions Python — https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- GitHub Actions Node — https://docs.github.com/en/actions/tutorials/build-and-test-code/nodejs

---

**Implementation philosophy:** Minimal runtime complexity, clear feature ownership, gradual refactoring, small verified commits, and honest validation. The user should need only **`docker compose up -d` after initial setup**; future new features should not require new containers by default.
