# Development

Keep source in the WSL2 Linux filesystem. Use Docker Desktop's WSL2 integration with this distribution; `docker info` and `docker compose version` must work. The approved stack has two application containers and a named SQLite volume. Existing Strata and financial services stay external.

## Startup

The root `.env` is optional for synthetic fixture development. If it already exists, preserve it: Compose passes it only to the backend. Otherwise create it from `.env.example` only when live settings are needed. Never put credentials in `VITE_*` variables. Do not print `docker compose config` with values; use `docker compose config --quiet`.

Before first live startup, back up/import existing native SQLite using the procedure below. First build:

```bash
docker compose config --quiet
docker compose up --build -d
```

Everyday use:

```bash
docker compose up -d
docker compose ps
docker compose logs -f
docker compose down
```

Open http://localhost:5173; API docs: http://localhost:8000/docs. Both host ports bind only to `127.0.0.1`. Source edits use Vite HMR and `uvicorn --reload` through bind mounts; no `--watch` command needed. Rebuild after dependency/Dockerfile changes with `docker compose up --build -d`. Native fallback commands are below. Stop native servers before using these ports in Compose.

Dependencies are installed inside images (Python 3.13.11, Node 22.23.3, digest pinned). The backend includes the locked optional Yahoo history dependencies. No host virtual environment/node_modules is mounted. Fixture/prompt paths retain the existing `/workspace` project layout.

## Isolated fixture acceptance

This optional running-stack acceptance needs free ports 8000/5173. Stop a live stack only when you intend to interrupt it; `make check` below uses one-off containers and needs no published ports. The override removes the live env file and blanks credentials/model. The separate project name isolates its SQLite volume:

```bash
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml up -d --wait
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml exec -T backend pytest -q
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml exec -T backend ruff check .
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml exec -T frontend npm run test
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml exec -T frontend npm run lint
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml exec -T frontend npm run build
curl -fsS http://127.0.0.1:5173/api/health
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml down
```

Never remove the live volume as cleanup. The standalone native `backend/tests/browser_smoke.py` starts its own servers and temporary synthetic database: run it only with Compose/native ports free. It does not test the container stack. Current verification evidence is in [validation](VALIDATION.md).

## SQLite backup and import

Git does not protect ignored databases or `.env`. Before storage changes, run:

```bash
backend/.venv/bin/python scripts/backup_local_state.py ../stocker-backups/UNIQUE-BACKUP-NAME
```

The destination must be new and outside the repository. Files/directories are private (0600/0700); the tool uses SQLite's backup API, verifies integrity, and records schema/counts/content fingerprints in a private manifest. It also preserves `.env` without displaying it. Back up before source rollback as well if persistence may be affected. Existing native databases are never moved/deleted by these tools.

Native `sqlite:///./stocker.db` is relative to the backend working directory. Compose explicitly uses `sqlite:////data/stocker.db`, on volume `stocker_stocker_data`. An existing separately configured `backend/live-acceptance.db` is diagnostic history, not automatically merged into the default database. Preserve/import it under its own name and select it explicitly if it should be the active history. Merging histories requires a separately planned data migration.

Stop services before import. Choose the appropriate numbered source snapshot from the private manifest. Mount only that database, read-only; never mount the backup directory containing the saved `.env` into the image build. Example (replace the source path):

```bash
docker compose down
docker compose run --rm --no-deps -T \
  -v /absolute/private/backup/03-stocker.db:/backup/native.db:ro \
  backend python /workspace/scripts/sqlite_transfer.py /backup/native.db /data/stocker.db
```

The importer refuses an existing destination, checks v1/integrity, and verifies counts and every row's fingerprint after backup. If a volume already has history, back it up and use a new destination/volume; do not overwrite it. Startup recovers interrupted research runs as before. `docker compose down` retains SQLite; volume deletion is never a default command.

## External Strata connectivity

Without saved UI settings, the backend uses the environment endpoint/model/auth unchanged. Test `/models` from inside the backend with a bounded authenticated request, printing status only; never log auth or `.env`. A successful connection is distinct from full six-stage research acceptance. Existing project budgets are documented below. A prior live AAPL report passed all stages with incomplete evidence coverage; this cleanup does not rerun live inference or alter budgets.

If connection fails, compare native and container reachability, route and service bindings before changing any address/security setting. The application permits HTTPS, existing loopback/link-local IPv4 HTTP, and exact `host.docker.internal` HTTP model endpoints without embedded credentials. Do not disable validation or broadly relax HTTP/CORS/host restrictions. Vite uses `API_PROXY_TARGET=http://backend:8000`; native fallback remains `127.0.0.1:8000`. Only the exact `backend` service hostname was added to TrustedHost; untrusted hosts/origins stay rejected.

The reusable status-only probe is:

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/model_connectivity.py
docker compose run --rm --no-deps -T backend python /workspace/scripts/model_connectivity.py
```

To inspect the separately imported diagnostic history through the normal app, stop the stack and create an explicit local Compose override outside Git with:

```yaml
services:
  backend:
    environment:
      DATABASE_URL: sqlite:////data/live-acceptance.db
```

Start with `docker compose -f compose.yaml -f /absolute/path/to/history-override.yaml up -d`. This selects that database without merging/deleting either history. Subsequent invocations must use the same override to retain the selection; ordinary `docker compose up -d` uses `/data/stocker.db`.

See [Compose service reference](https://docs.docker.com/reference/compose-file/services/) and [Docker Desktop WSL2 integration](https://docs.docker.com/desktop/features/wsl/).

## Optional Make commands

`make dev`, `stop`, `status`, `logs`, and `rebuild` wrap the normal Compose lifecycle. Make is optional; `docker compose up -d` remains sufficient. `make test`, `lint`, `typecheck`, and `build` use one-off fixture containers with isolated temporary SQLite storage and do not require stopping the live stack. `make format` / `format-check` apply Ruff to Python and Biome to the frontend. `make check` runs all quality/test/build targets; format-check rejects unformatted source. `make smoke` uses the native browser harness and refuses occupied ports: stop Compose first. The explicit `compose.format.yaml` override allows formatter writes as the host UID/GID with a temporary Ruff cache; normal checks keep tests/scripts read-only.

## Quality tools

The project uses Ruff (110 columns, Python 3.11 target) and exact-pinned Biome 2.6.6 (2 spaces, single quotes, semicolons, import organization). Frontend `npm run typecheck` runs TypeScript; `lint` runs Biome. `format`, `format:check`, `check`, and `ci` are distinct commands. The initial Biome rules enforce unused declarations/imports, hook placement and JSX keys; expand rules incrementally without changing financial behavior. `make format` now formats both languages; formatting changes are committed separately from moves or behavior. See [Biome configuration](https://biomejs.dev/reference/configuration/) and [Ruff formatter](https://docs.astral.sh/ruff/formatter/).

## CI and Docker acceptance

`.github/workflows/ci.yml` runs on pull requests and pushes to main/the migration branch, with read-only repository permissions and SHA-pinned checkout/setup actions. Backend jobs target Python 3.11/3.13; frontend uses Node 22. No personal credentials, provider keys or Strata are required. Docker CI builds and starts an isolated fixture stack, seeds a synthetic research/portfolio record, recreates containers, and compares the persisted report/events/positions. Remote main CI passed at `93d0ee4`; exact run and local checks are recorded in [validation](VALIDATION.md).

With native/live Compose stopped, repeat the isolated persistence acceptance:

```bash
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml up -d --wait
backend/.venv/bin/python scripts/compose_smoke.py seed /tmp/stocker-smoke.json
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml down
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml up -d --wait
backend/.venv/bin/python scripts/compose_smoke.py verify /tmp/stocker-smoke.json
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml down
```

The smoke refuses live data mode or live research history. Never use the fixture override on the live project name. The full native browser harness additionally checks actual restart persistence, download filename/content, mobile layout and external-widget failure/retry; stop all Compose stacks on 8000/5173 before `make smoke`. Pixel-level screenshot review remains separately unverified.

For source rollback, stop Compose, preserve current local state with verified backups, and check out a known compatible commit on a separate branch. Do not overwrite `.env` or databases during checkout; never reset/clean user changes automatically. `.git-blame-ignore-revs` records the format-only commit.

Docker frontend sets `WATCH_USE_POLLING=true` with a 200ms interval because final WSL2 bind-mount verification found missed restore events and stale Vite transforms. Native Vite retains event-based watching. Polling trades some CPU for reliable development reload and does not require Compose Watch. See [Vite server.watch](https://vite.dev/config/server-options#server-watch). Against an isolated running fixture stack, `backend/.venv/bin/python scripts/reload_smoke.py` verifies backend reload and frontend HMR/restoration without rebuilding. It refuses live mode and restores temporary source edits even on failure.

## Back up the active Docker database

`backup_local_state.py` protects project-native files and `.env`; it cannot see the named Docker volume. Export that separately after research finishes and while portfolio edits are paused. Use new snapshot/destination names each time (the helper refuses existing targets):

```bash
mkdir -m 700 ../stocker-backups/docker-UNIQUE
# SQLite backup API, with integrity/schema/content verification inside the container:
docker compose exec -T backend python /workspace/scripts/sqlite_transfer.py \
  /data/stocker.db /tmp/stocker-backup-UNIQUE.db
# Compose cp creates the local copy owned by the invoking user; don't use archive ownership mode.
docker compose cp backend:/tmp/stocker-backup-UNIQUE.db \
  ../stocker-backups/docker-UNIQUE/stocker.db
```

Repeat for `/data/live-acceptance.db` if preserving the separate diagnostic archive. Keep copies private and outside Git; verify permissions/integrity before destructive storage changes. The temporary container file disappears on recreation, while the exported private copy remains. Verify exported backups against the source row fingerprints and keep them private (0600 files). No default command deletes volumes.

## Local model research budgets

New settings and `.env.example` default to `LLM_MAX_TOKENS=8192`, `LLM_TIMEOUT=600`, `LLM_CONTEXT_WINDOW_TOKENS=131072`, `LLM_RUN_OUTPUT_TOKENS=196608`, `LLM_RUN_TOTAL_TOKENS=1048576`, `LLM_RUN_CONTEXT_BYTES=8388608`, `RESEARCH_RUN_TIMEOUT=7200`. Existing `.env` values take precedence; defaults alone never overwrite them. A previous live acceptance session recorded these budgets; this cleanup leaves existing settings untouched. To adopt these values in the normal application, edit only the desired project `.env` budget fields and recreate the backend with `docker compose up -d --force-recreate backend`. Keep global Strata settings separate from project configuration.

Output caps must be positive (128–65536), leave input space plus a 2048-token margin in the configured context, and fit both run token budgets. HTTP timeout is at most 3600 seconds, research duration at most 86400 seconds. Context-byte accounting is conservative and includes tools; it is not exact tokenization. Deadlines are cooperative around synchronous calls; the HTTP timeout bounds network inactivity, not absolute elapsed time. Late model output is rejected. All retry/tool/call limits and evidence validation remain enabled.

Explicit live acceptance (calls real providers/model; never run from fixture CI) uses a new dedicated database, refuses existing database paths, and prints safe stage/summary results:

```bash
docker compose exec -T -e DATA_MODE=live -e LLM_MAX_TOKENS=8192 -e LLM_TIMEOUT=600 backend python /workspace/scripts/live_research_check.py --database /data/live-budget-new.db
```

The run remains honestly `incomplete` when data gaps exist even when all six stages and the sourced report pass. Inspect the dedicated database's persisted run, events, evidence and report rather than equating a report with full financial coverage.

## Native fallback

Requires Python 3.11+ and Node 22+. From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, from the root:

```bash
cd frontend
npm ci --legacy-peer-deps
npm run dev -- --host 127.0.0.1
```

The npm option preserves the tested lockfile resolution for the Vite/Vitest optional-peer combination. Optional native Yahoo history uses `backend/requirements-history.lock` and the `backend[history]` extra as described in [providers](DATA_PROVIDERS.md). Native checks are `cd backend && .venv/bin/pytest -q && .venv/bin/ruff check .`, followed separately by `cd frontend && npm run ci && npm run typecheck && npm run test && npm run build` from the root.

## Naming and existing installations

The application, packages, Compose project and images use **Stocker**. The default Compose project is `stocker`, volume key `stocker_data` (normally `stocker_stocker_data`), database `stocker.db`, and optional environment-file selector `STOCKER_ENV_FILE`.

Existing installations must migrate their data before starting the renamed project; see [storage migration](#storage-name-migration). The new project name selects a different Docker volume. Preserve the original volume and ignored configuration until migration is verified. Model/provider values remain unchanged.

## AI configuration and host networking

The initial setup window appears when neither saved settings nor `LLM_MODEL` configures a model. Skip it for synthetic fixture use; it can reappear on a fresh page session until configured. Settings → AI is always available. Enter the base URL including `/v1` where required, exact model identifier and optional key. Test Connection makes a small real chat-completion request (it can consume provider tokens); Save persists only after a successful test in this UI. Changing any field requires retesting. A saved key is never populated into an input. Blank keeps it for the same endpoint; the no-key checkbox clears it. Changing endpoints requires a new key or explicit no-key choice.

Saved UI fields override only `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`. Environment budgets, providers and `DATA_MODE` remain intact. Reset with Use environment configuration. Existing `.env` values are never edited. Saving does not rebuild/restart containers and affects new operations; queued/running research keeps its original settings. Fixture mode continues to use deterministic synthetic outputs even after AI is configured. Enable live mode/providers separately through `.env` if desired.

Inside Docker, `127.0.0.1` means the backend container. For a model running on the host, use `http://host.docker.internal:PORT/v1`. Compose supplies the exact host-gateway alias for Linux; Docker Desktop also supports host access. On Windows/WSL2, the host model must listen on an interface reachable from Docker, and Windows firewall/WSL networking must permit that connection. A model bound only to Windows or WSL loopback may remain unreachable; the alias does not rebind external services. Check the model's bind address and Docker Desktop WSL integration. Keep Stocker's published ports on loopback and firewall access limited to the Docker network. Use HTTPS for remote providers; do not broaden endpoint/host/origin validation to troubleshoot reachability. The existing `.env` endpoint remains unchanged until explicitly replaced.

Compose persists private credentials at `/data/ai-settings/config.json` in the existing volume, with 0600 file/0700 directory permissions. Native defaults to ignored `.ai-settings/config.json` at the repository root. `AI_CONFIG_FILE` must point to a dedicated private directory, on persistent storage for Docker. Secrets are access-controlled plaintext: protect volume exports and backups; local OS/Docker administrators can read them. No encryption key management dependency is introduced. Never print this file or include it in diagnostics. Back up the file separately from SQLite, using `docker compose cp backend:/data/ai-settings/config.json /absolute/private/backup/ai-config.json` into a private 0700 backup directory; set the exported file to 0600 and compare with `cmp` silently after restoring to a private staging path. Restoring requires stopping the backend, preserving the current file, copying the backup to the configured path, restoring 0600/0700 permissions and starting the backend. Never commit backups. A corrupt file fails startup safely rather than silently discarding credentials.

## Development progress workflow

Keep application source, user/contributor documentation and development records on `main`. Put detailed progress, implementation plans, execution/debugging notes, migration acceptance and decision history in the root [`progress/`](../progress/README.md) folder. Keep current setup, architecture, API contracts, roadmap and limitations in `README.md` and `docs/`.

Read the latest entry in [`progress/PROGRESS.md`](../progress/PROGRESS.md) before resuming work. Update it at meaningful milestones, after test runs, on blockers and before ending a session, recording actual results, limitations and the precise next action. Record architecture decisions in [`progress/DECISIONS.md`](../progress/DECISIONS.md). Include these records in the same commit/PR workflow as the corresponding implementation; a temporary feature/PR branch may still be used for required checks.

The separate archive synchronization workflow is retired. The existing archive branches remain unchanged as historical snapshots. Their imported Markdown is indexed in `progress/`; historical instructions do not override current `AGENTS.md` or current architecture. Raw JSON diagnostics remain accessible through the pinned snapshot links in the progress guide. Verify relocated Markdown links when adding or moving records, keep secrets/private backups outside Git, and follow repository branch protections when publishing.

AI-specific browser acceptance on an isolated fixture stack uses a synthetic loopback responder (never start this in live mode):

```bash
docker compose -p stocker-fixture -f compose.yaml -f compose.fixture.yaml exec -d backend python /workspace/backend/tests/fixture_model_server.py
backend/.venv/bin/python scripts/ai_configuration_smoke.py
```

The harness refuses non-fixture data and real model settings, verifies setup/skip/test/save/reset, secret absence, mobile overflow and page errors. `STOCKER_SMOKE_BASE` can point to alternate fixture ports; the harness sends the exact supported UI origin without changing application policy. It changes only synthetic AI preferences. The general Compose smoke also verifies a synthetic saved AI configuration survives container recreation. Never run either smoke against the live project. The loopback responder ends when its fixture backend container is stopped.

## Storage name migration

Older installations must copy their storage before switching Compose projects. The migration helper preserves the source, refuses a nonempty destination, verifies SQLite schema/integrity/table counts and every row fingerprint, and compares other files byte-for-byte. It copies private AI configuration too, with 0700 directory/0600 file permissions. It never prints credentials. Stop writes/research before copying; retain verified private backups outside Git and the old volume until the new application is accepted.

Use `docker volume ls` and the previous container's mount metadata to identify the source volume. The new default is `stocker_stocker_data`; do not assume an empty new volume contains the old history. Record your previous project name, database filename and any custom environment-file selection privately. Build the new images, stop the previous Compose project without deleting its volume, then copy using explicit source/target mounts (replace the uppercase placeholders):

```bash
docker compose build
docker volume create stocker_stocker_data
docker run --rm --network none \
  -v PREVIOUS_VOLUME:/source:ro \
  -v stocker_stocker_data:/target \
  -v "$PWD/scripts:/migration:ro" \
  --entrypoint python stocker-backend:dev \
  /migration/migrate_storage_names.py /source /target \
  --source-database PREVIOUS_DATABASE.db --target-database stocker.db
docker compose up -d --wait
```

First run the same helper into a new private 0700 backup directory mounted at `/target` and use `--target-database PREVIOUS_DATABASE.db` to retain its filename in the backup; source and destination filenames may be equal. Verify the backup before copying into the new volume. An error leaves the source intact; inspect the partial destination and choose a new empty target for a retry. No default command deletes volumes. On failure, stop the new project and start the recorded previous Compose definition against its untouched original volume; keep both versions' source/configuration available until acceptance.

For native installations, use `scripts/sqlite_transfer.py` to copy the previous database to a new `backend/stocker.db` path and verify it. If `.env` sets `DATABASE_URL` explicitly, update only that database path after making a private backup; preserve model/provider values. `STOCKER_ENV_FILE` selects a custom Compose env file; update any shell or local override that used the previous selector. Other custom database URLs remain respected. Do not rewrite global model/Codex configuration or delete previous databases/backups.
