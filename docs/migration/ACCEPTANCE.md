# Docker/modular migration acceptance

Date: 2026-11-06 15:37 EST

Branch: `chore/docker-modular-migration`; base: `cb83b66`. No push. Phases 0–6 implemented and locally accepted; Phase 7 local gates accepted. Remote GitHub Actions (G14) remains unrun, pending explicit push authorization. The configured Python 3.11 CI lane was not executed locally. Pixel-level screenshot perception was not run.

## Final gate matrix

| Gate | Evidence / result |
|---|---|
| G1 / G2 setup and everyday startup | Final `docker compose up --build -d --wait`, `down`, `up -d --wait` passed; only frontend/backend application containers; no dependency reinstall for everyday startup |
| G3 / G4 UI and proxy | Real fixture-container browser UI and frontend API health/search passed; direct/proxied default health also passed; host ports 127.0.0.1 only |
| G5 reload | `scripts/reload_smoke.py` passed backend edit/restore and Vite HMR edit/restore, no rebuild; Docker-only polling fixes diagnosed missed filesystem restore event |
| G6 / G7 persistence and isolation | Final fixture seed/down/up/verify retained exact watchlist, stored position/P&L, full immutable run/report and ordered events; separate project/volume, no live env file; make checks use per-container /tmp SQLite |
| G8 / G9 tests and quality | Final `make check`: 132 backend tests in 8.09s, 21 frontend tests in 2.78s; Ruff/Biome lint/format/import/CI, TypeScript and production build (233 modules) passed |
| G10 browser behavior | Full native smoke passed with zero pageerrors, actual backend restart/report reopen, downloaded filename/content, holdings, 20 templates, Canadian gaps, widget failure/retry and mobile 390px no overflow |
| G11 / G12 semantics | Full OpenAPI exactly matches original snapshot; original finance/client/stub/tools/orchestrator/new_run/report ASTs unchanged; prompts byte-identical; fixed-clock fixture report/events exactly equal original engine |
| G13 external model | Native WSL, one-off Docker and final running backend discovery HTTP 200/configured iq3_s listed; user restored service/key; endpoint/security/global services unchanged |
| G14 remote CI | NOT RUN: workflow implemented and validated by official checksum-verified actionlint 1.7.12; local equivalents pass; no push authorized |
| G15 boundaries | Backend AST forbidden-import tests and public-facade integration; frontend TypeScript-AST ownership/endpoint/public-contract tests pass |
| G16 documentation/data protection | README/DEVELOPMENT/ARCHITECTURE/DECISIONS/AGENTS/PROGRESS updated; private .env/native SQLite backups and Docker exports verified outside Git; rollback uses coherent local commits |

One existing Starlette/httpx deprecation warning remains. Earlier failures/corrections are recorded chronologically in PROGRESS.md, including omitted Vitest config, formatter mounts, extraction errors, temporary harness state selection and WSL watcher diagnosis; none are claimed as passing before their successful reruns.

## Changed responsibilities

```text
compose.yaml / compose.fixture.yaml / compose.format.yaml
backend/Dockerfile
backend/app/
  main.py
  core/{config,database}.py
  contracts/{api,market}.py
  finance/metrics.py
  modules/
    market_data/{router,service,symbols,provenance,errors,fixtures}.py
      providers/{sec,finnhub,yahoo,alpha_vantage,fred,bank_of_canada,http}.py
    research/{router,service,repository,schemas,orchestrator,validation,reports,chat,evaluation,errors}.py
      agents/{client,tools}.py + prompts/*.md
    portfolio/{router,service,repository}.py
    intelligence/{router,service,news,industries}.py
frontend/Dockerfile
frontend/src/
  app/{App,router}.tsx + api.ts + layout/* + pages/SettingsPage.tsx
  features/{market,research,portfolio,intelligence}/{api,types}.ts + pages/* + components/*
  shared/{api,hooks,types,ui,utils}/*
  styles/global.css
Makefile / .editorconfig / .git-blame-ignore-revs
.github/workflows/ci.yml
scripts/{backup_local_state,sqlite_transfer,model_connectivity,compose_smoke,reload_smoke}.py
```

No intentional REST/DTO/schema/formula/provider/agent/Canadian-label changes. Stable DTOs deliberately live in explicit contracts rather than duplicate feature exports. Existing tests/assertions remain; imports/mock injection setup follow ownership. No compatibility source trees or duplicate implementations remain. The formatter-only baseline is isolated in `e9cfd5b`.

## Commands

```bash
docker compose up -d                  # everyday startup
# http://localhost:5173 ; API docs http://localhost:8000/docs
docker compose ps
docker compose logs -f
docker compose down                   # retains SQLite
docker compose up --build -d          # dependency/Dockerfile changes
make check                           # isolated fixture quality/test/build
# With Compose stopped and native browser extras installed:
make smoke
```

Source binds provide Uvicorn reload and Vite HMR; Docker frontend polls at 200ms, native Vite stays event-based. SQLite: `/data/stockscope.db` on `stockscope_stockscope_data`. Diagnostic history remains separately at `/data/live-acceptance.db`; DEVELOPMENT.md explains explicitly selecting it.

Backups: `../stocker-backups/migration-resume-20261106-1453`, private root.env/five native SQLite copies/manifest plus user-owned 0600 Docker exports. Original `.env` and database contents still match; named-volume fingerprints match the pre-check snapshots. Default native history was empty; four diagnostic runs and 67 events are preserved, without silently merging histories. Credentials never entered Git/build contexts/frontend/logs.

## Commits before this final documentation checkpoint

```text
35e03dd chore: establish migration baseline and protect local state
d8e6e31 chore: add compose development stack with isolated fixtures
831473a chore: add isolated developer commands and close Docker gate
0baee62 chore: configure Ruff Biome and separate TypeScript checks
ef8d62a fix: allow explicit formatter writes to source mounts
e9cfd5b style: establish Ruff and Biome formatting baseline
c27adb9 chore: enforce organized imports and accept quality baseline
511e762 refactor: extract feature API routers without contract changes
be5c9da refactor: isolate market data providers behind normalized facade
b9086c9 refactor: give portfolio service and persistence ownership
44a616f refactor: encapsulate research execution and persistence
e56750e refactor: isolate intelligence and use public research entrypoint
642cd6c test: enforce backend boundaries and unchanged API contract
ceb10bd refactor: separate shared frontend infrastructure and feature APIs
eae7e6d refactor: organize frontend features and application layout
fac913b fix: use reliable Docker source watching on WSL2
17382bb ci: add credential-free quality and Compose persistence gates

```

## Remaining external acceptance

After explicit push authorization, execute and inspect GitHub Actions, including Python 3.11. No push or background work is promised. Existing sourced iq3_s research output/total-token failures remain independently unresolved and were not worked on; Canadian statements/current quotes retain unavailable labels. No new providers/features or user-wide Strata/Codex/LiteLLM changes were introduced.

## Superseding remote acceptance — 2026-11-06

The earlier “not run / no push authorized” statements describe the original local checkpoint. GitHub Actions subsequently **succeeded** on main `93d0ee44656c9d711e4a581f6b3b3a700cd3705b`: [run 42298783499](https://github.com/TTDoorTT/stocker/actions/runs/42298783499), terminal state rechecked during cleanup. The later project-budget phase recorded a six-stage sourced AAPL report with incomplete coverage, superseding earlier model-budget blockers without changing this historical migration scope. Cleanup branding gate: 150 backend / 21 frontend tests, lint/format, TypeScript and build pass. See [validation](../VALIDATION.md).
