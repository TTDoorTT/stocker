# Architecture

Stocker is a feature-oriented modular monolith: one React/TypeScript/Vite application, one FastAPI backend, and one SQLite database. The six logical specialist roles run inside the backend, not separate containers. External Strata iq3_s and financial providers remain outside Docker. The official TradingView embed is an isolated visual and never supplies data to agents.

## Development runtime

```text
Browser localhost:5173 -> frontend Vite -> /api proxy -> backend:8000
                                                     |-> SQLite /data/stocker.db
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
    intelligence/            router/service, company news, industry catalog
      rss.py                separate curated RSS fetch/parse/refresh and headline evidence
      rss_sources.json     source/category inventory (third-party attribution required)
      highlight_cache.py   saved per-category validated AI-highlight results
```

Routers handle transport validation/error mapping and call owned services. Feature services use public service/type/error contracts across modules; provider parsers and repositories stay private. Research receives normalized market data and pure calculations; portfolio uses listing-currency quotes without implicit FX. Intelligence uses normalized company-news/macro data and research's public captured-headline summary entrypoint. Its separate RSS collector parses publisher feeds in a background thread, stores compact metadata and short excerpts in SQLite, and never calls the model during list, refresh or cache reads. Explicit highlights use the existing validated model summarizer; one successful result is cached per category. Main supplies industry lookup as a callback, avoiding an import cycle. No dependency-injection framework or extra Python distributions were introduced.

Research follows profile → financials → estimates → valuation → risk → report. Each role gets distinct instructions, scoped context and validated prior output. Schema/evidence/numeric validation runs outside the model. Existing bounded retries, single risk revisit, tool/token/context/wall-time budgets, one worker/four-slot scheduling, event ordering and restart recovery remain unchanged. A deterministic model is used only in visibly synthetic fixture mode; live failures never trigger fixture fallback.

SQLite retains the versioned research/portfolio schema v1 and existing runs/events/watchlist/positions tables. The RSS feature lazily creates separate `rss_articles`, `rss_refresh` and `rss_highlights_cache` tables in that same database; the news cache is not part of the versioned research schema and must still be included in backups. Research snapshots preserve immutable evidence/calculations; research repositories share one connection/transaction lock. Unknown future schema versions require explicit migration. Interrupted runs become incomplete at startup.

Providers preserve currency, units, fiscal periods, original retrieval/publication timestamps, source URLs/evidence IDs and explicit unavailable states. Cache hits retain network capture times; failures never silently use stale/fictional facts. U.S. SEC/Finnhub coverage, optional Yahoo/Alpha Vantage history and FRED/Valet semantics are unchanged. Canadian .TO/.V history, CAD positions and no-key macro are partial coverage; Canadian statements/current quotes remain unavailable without permitted verified sources. There is no SEDAR+ scraper or automatic FX conversion. Annual EPS ratios are not TTM.

## Frontend ownership

```text
frontend/src/
  app/                       root, router, health API, layout and Settings
  features/
    market/                  Home/Stock pages, search/chart/heatmap, market API/types
    research/                landing/run/records, chat/progress, research API/types
    portfolio/               My Stocks/positions preview, portfolio API/types
    intelligence/            RSS category feed/highlights, daily review, guided topics and signals
  shared/                    generic HTTP/errors, resource hook, UI/evidence, formatting, stable DTOs
  styles/global.css          base layout and shared styling
  styles/themes.css          dark/light color overrides and header toggle styling
  styles/rss.css             RSS intelligence component styling
```

Endpoint functions stay in feature/app API files; shared HTTP only handles requests/errors. Shared DTOs are genuinely cross-feature source/evidence/currency contracts. Market consumes explicitly public research Chat and portfolio PositionsPreview components; other cross-feature imports use API/types. Routes, labels, 1500ms research polling, Markdown downloads, charts and iframe failure/retry behavior remain stable. The header toggles dark/light appearance and stores only `stocker-theme` in browser localStorage (no secrets). The homepage begins with market information instead of the removed introductory hero. No browser-facing provider keys exist.

## Enforced gates

Backend AST tests reject private cross-feature imports, persistence in routers and side-effect dependencies in finance. Frontend TypeScript-AST tests guard shared ownership, endpoint-only HTTP and public feature imports. A complete OpenAPI snapshot detects route/schema/status/validation changes; its new revision includes the four RSS endpoints. Public-facade integration and original API/provider/model/browser tests verify behavior and persistence.

Ruff targets Python 3.11 with 110-column formatting; Biome 2.6.6 owns frontend formatting/lint/import organization; strict TypeScript remains separate. GitHub Actions uses SHA-pinned actions, read-only permissions and credential-free fixture checks, including Docker recreation/persistence. `make check` provides local equivalents. The latest reviewed main baseline `87001b7` passed GitHub Actions CI; see [validation](VALIDATION.md) for the exact run and acceptance limits.

## Runtime AI configuration

Research owns `modules/research/configuration`: validated preferences, private atomic file persistence and a small bounded connectivity probe, exposed by thin settings routes. Main composes its immutable `current()` settings snapshots into research/chat and intelligence summaries. Queued/running research retains its original snapshot; new operations see saved changes. Model budgets, financial provider settings and data mode remain environment-owned. No dependency or SQLite schema change is needed.

Compose stores `/data/ai-settings/config.json` in the existing `stocker_data` volume; native fallback uses ignored `.ai-settings/config.json`. `AI_CONFIG_FILE` can select another private persistent path. Files are 0600 and their dedicated directory 0700. This is access-controlled local secret storage, not application encryption; OS/Docker administrators can read it. Saved fields override the original environment until reset. Corrupt saved configuration fails closed with a sanitized error. Settings validation responses omit input values; status exposes only key presence. The UI holds a newly entered key in form memory until save/unmount and uses no browser storage. No secrets enter reports or application logs.
