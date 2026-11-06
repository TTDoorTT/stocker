# Architecture

Stocker is a feature-oriented modular monolith: one React/TypeScript/Vite application, one FastAPI backend, and one SQLite database. The six logical specialist roles run inside the backend, not separate containers. External Strata iq3_s and financial providers remain outside Docker. The official TradingView embed is an isolated visual and never supplies data to agents.

## Development runtime

```text
Browser localhost:5173 -> frontend Vite -> /api proxy -> backend:8000
                                                     |-> SQLite /data/stockscope.db
                                                     |-> external Strata / providers
```

Compose publishes only host loopback ports 5173/8000. Source bind mounts support Vite HMR and Uvicorn reload with ordinary `docker compose up -d`. Dependencies stay inside digest-pinned Python 3.13.11/Node 22.23.3 images. The Vite proxy permits the exact backend service hostname; existing host/origin restrictions and model endpoint validation stay enabled. Backend credentials never reach browser code or image build contexts.

SQLite persists across `docker compose down`. Configuration and native histories are separate from the Docker volume; existing histories must be explicitly backed up/imported rather than silently merged. See [development](DEVELOPMENT.md) for persistence identifiers, safe selection and rollback.

## Backend ownership

```text
backend/app/
  main.py                    composition, lifespan, security, health
  core/config.py             settings and stable project root
  core/database.py           SQLite lifecycle/schema/transaction lock
  contracts/{api,market}.py   stable public DTOs
  finance/metrics.py         pure deterministic calculations
  modules/
    market_data/             normalized DataService, symbols/evidence/errors, synthetic fixtures
      providers/             SEC, Finnhub, Yahoo, Alpha Vantage, FRED, Bank of Canada, shared HTTP
    research/                scheduler/service, repository, orchestrator, schemas, validation, reports, chat
      agents/                bounded model client/tools and unchanged specialist prompts
    portfolio/               watchlist/positions router, service and repository
    intelligence/            router/service, news processing, industry catalog
```

Routers handle transport validation/error mapping and call owned services. Feature services use public service/type/error contracts across modules; provider parsers and repositories stay private. Research receives normalized market data and pure calculations; portfolio uses listing-currency quotes without implicit FX. Intelligence uses normalized news/macro data and research's public captured-headline summary entrypoint. Main supplies industry lookup as a callback, avoiding an import cycle. No dependency-injection framework or extra Python distributions were introduced.

Research follows profile → financials → estimates → valuation → risk → report. Each role gets distinct instructions, scoped context and validated prior output. Schema/evidence/numeric validation runs outside the model. Existing bounded retries, single risk revisit, tool/token/context/wall-time budgets, one worker/four-slot scheduling, event ordering and restart recovery remain unchanged. A deterministic model is used only in visibly synthetic fixture mode; live failures never trigger fixture fallback.

SQLite retains schema v1 and existing runs/events/watchlist/positions tables. Research snapshots preserve immutable evidence/calculations; repositories share one connection/transaction lock. Unknown future schema versions require explicit migration. Interrupted runs become incomplete at startup.

Providers preserve currency, units, fiscal periods, original retrieval/publication timestamps, source URLs/evidence IDs and explicit unavailable states. Cache hits retain network capture times; failures never silently use stale/fictional facts. U.S. SEC/Finnhub coverage, optional Yahoo/Alpha Vantage history and FRED/Valet semantics are unchanged. Canadian .TO/.V history, CAD positions and no-key macro are partial coverage; Canadian statements/current quotes remain unavailable without permitted verified sources. There is no SEDAR+ scraper or automatic FX conversion. Annual EPS ratios are not TTM.

## Frontend ownership

```text
frontend/src/
  app/                       root, router, health API, layout and Settings
  features/
    market/                  Home/Stock pages, search/chart/heatmap, market API/types
    research/                landing/run/records, chat/progress, research API/types
    portfolio/               My Stocks/positions preview, portfolio API/types
    intelligence/            news/daily review/industries/signals, intelligence API/types
  shared/                    generic HTTP/errors, resource hook, UI/evidence, formatting, stable DTOs
  styles/global.css          original global styling
```

Endpoint functions stay in feature/app API files; shared HTTP only handles requests/errors. Shared DTOs are genuinely cross-feature source/evidence/currency contracts. Market consumes explicitly public research Chat and portfolio PositionsPreview components; other cross-feature imports use API/types. Routes, labels, 1500ms research polling, Markdown downloads, charts and iframe failure/retry behavior remain stable. No browser-facing provider keys exist.

## Enforced gates

Backend AST tests reject private cross-feature imports, persistence in routers and side-effect dependencies in finance. Frontend TypeScript-AST tests guard shared ownership, endpoint-only HTTP and public feature imports. A complete OpenAPI snapshot detects route/schema/status/validation changes; its only cleanup change is the display title, now Stocker. Public-facade integration and original API/provider/model/browser tests verify behavior and persistence.

Ruff targets Python 3.11 with 110-column formatting; Biome 2.6.6 owns frontend formatting/lint/import organization; strict TypeScript remains separate. GitHub Actions uses SHA-pinned actions, read-only permissions and credential-free fixture checks, including Docker recreation/persistence. `make check` provides local equivalents. Remote baseline CI passed on main at `93d0ee4`; see [validation](VALIDATION.md) for the exact run and current acceptance limits.
