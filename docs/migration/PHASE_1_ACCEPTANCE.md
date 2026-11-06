# Migration acceptance — 2026-11-06

Branch: `chore/docker-modular-migration`, base `cb83b66`. Source rollback uses Git; no pushes. The supplied root migration plan was relocated unchanged to its requested `docs/migration/` path. No pre-existing tracked user edits were present.

## Phase 0 — accepted

- Native backend: `cd backend && ./.venv/bin/pytest -q && ./.venv/bin/ruff check .` — 117 passed in 8.07s; Ruff passed, existing Starlette/httpx deprecation warning.
- Native frontend: `cd frontend && npm run lint && npm run test && npm run build` — TypeScript passed, 18 tests passed, 209-module build passed.
- `backend/.venv/bin/python backend/tests/browser_smoke.py` — passed, zero pageerrors. Includes synthetic six-stage workflow, real restart/report reopen, positions, 20 templates, Canadian labels, 390px layout and widget failure/retry. Screenshot perception not run. The regenerated research screenshot was restored to its baseline; it is not a migration source change.
- Branch created; ignored `.env` and five SQLite files backed up using SQLite backup API under private sibling `/home/siche/uni/dh399/stocker-backups/migration-phase0-20261106-verified`. Manifest includes integrity, versions, counts and content fingerprints. Original `.env` byte fingerprint and all original database contents still match. First partial backup failed on a cache WITHOUT ROWID table; accepted retry handles that format.
- Docker client/daemon 29.8.2, Compose 5.5.1, WSL2 Linux. No application behavior changed in Phase 0.

## Phase 1 — fixture Docker accepted; external-model gate blocked

Implemented files: `compose.yaml`, `compose.fixture.yaml`, both Dockerfiles, root/frontend `.dockerignore`, Vite proxy target, exact `backend` TrustedHost allowance/test, backup/import/connectivity utilities and development documentation. Existing source directories remain in place. No formulas, provider contracts, prompts, API paths/DTOs, SQLite schemas, agent logic or Canadian labels changed.

| Verification | Actual result |
|---|---|
| `docker compose config --quiet` | Passed |
| `docker compose -p stockscope-fixture -f compose.yaml -f compose.fixture.yaml config --quiet` | Passed; override removes live env file |
| `docker compose build` | Passed after sandbox retry for Buildx metadata; locked dependencies including history extra installed |
| Fixture `up -d --wait` / `ps` | Both services up; backend healthy; ports bound to 127.0.0.1 |
| Backend `/api/health`, frontend `/api/health` and `/api/stocks/search?q=AAPL` | Passed through real Vite proxy, fixture labels/model stub explicit |
| Container backend `pytest -q && ruff check .` | 118 passed in 7.66s; Ruff passed |
| Container frontend `npm run lint`, `npm run test`, `npm run build` | TypeScript passed; 18 tests passed; build passed (209 modules) |
| Native after host-policy change | 118 backend tests in 8.32s + Ruff; 18 frontend tests + TypeScript/build passed |
| Real Chromium against fixture containers | Home/fixture banner/proxy passed; zero pageerrors |
| Backend reload | Temporary health-marker edit observed over HTTP, restored and observed again; no rebuild |
| Vite HMR | Temporary Home heading edit observed in open browser, restored and observed again; no rebuild |
| Fixture `down` / `up -d --wait` persistence | Identical watchlist, stored position/P&L, full immutable six-stage run/report and ordered events |
| SQLite import to default named volume | Native empty v1 DB imported to `/data/stockscope.db`; separate 4-run/67-event diagnostic history imported to `/data/live-acceptance.db`; integrity/version/counts/all row fingerprints match snapshots |
| Default live stack `up --build -d --wait`, `down`, `up -d --wait`, `ps`, logs and both health URLs | Passed; backend healthy, frontend proxy reports live/iq3_s; existing configuration retained. Volume integrity/v1/counts confirmed after recreation; no `.env` file baked into backend image. Stack left running |
| External model discovery | BLOCKED: native WSL `ConnectTimeout`, same on outside-sandbox retry; Docker `ConnectError`; raw TCP native timeout / Docker ECONNREFUSED (111) |

The first frontend container test attempt failed all 18 tests with `document is not defined`: missing `vitest.config.ts` in the image. Added the configuration to image and bind mounts; rerun passed. The first persistence comparison included regenerated fixture quote timestamps and failed `/api/positions`; the corrected check compares persisted position fields and financial values, while run/evidence/event payloads remain compared in full. No persistence loss was observed.

Native and container routing tables both have an IPv4 default route (WSL gateway 172.19.0.1, Docker bridge gateway 172.22.0.1 during this run). These checks do not establish whether the refusal/timeout originates at service binding, Windows firewall or downstream routing. No endpoint, HTTP allowlist, CORS/origin validation, host wildcard, firewall or external service configuration was changed. No model inference/full research request was triggered by connectivity checks.

The plan §4.3 requires stopping when external model access cannot be made to work safely. Phases 2–7 (developer commands, format baseline, module moves, boundary checks and CI) remain unstarted. Existing iq3_s truncation/total-token limitations remain independently unresolved and out of scope. Canadian statements/current quotes retain their existing unavailable labels.

## Resume

Restore external reachability of the currently configured Strata endpoint without changing user-wide services or weakening security. Re-run:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/model_connectivity.py
docker compose run --rm --no-deps -T backend python /workspace/scripts/model_connectivity.py
```

Require HTTP 200 with the configured model listed. Reconfirm Phase 1 startup/proxy/persistence, then implement Phase 2 in order. The default active Docker DB corresponds to the configured native default, which was empty. Historical diagnostic research is preserved separately, not silently merged into the default history. Development docs explain selecting a separate history database explicitly.

## Resolved — 2026-11-06 14:53 EST

User confirmed Strata was down, restored the existing service and updated the ignored project API key. Both native and container `scripts/model_connectivity.py` now return HTTP 200 / configured_model_listed=true. No endpoint, security or service configuration changes by the migration. Phase 1 accepted; continue Phase 2. New private backup protects the updated `.env`: `../stocker-backups/migration-resume-20261106-1453`.
