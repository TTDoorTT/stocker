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

Open http://localhost:5173; API docs: http://localhost:8000/docs. Both host ports bind only to `127.0.0.1`. Source edits use Vite HMR and `uvicorn --reload` through bind mounts; no `--watch` command needed. Rebuild after dependency/Dockerfile changes with `docker compose up --build -d`. Native fallback commands remain in README. Stop native servers before using these ports in Compose.

Dependencies are installed inside images (Python 3.13.11, Node 22.23.3, digest pinned). The backend includes the locked optional Yahoo history dependencies. No host virtual environment/node_modules is mounted. Fixture/prompt paths retain the existing `/workspace` project layout.

## Isolated fixture acceptance

Stop the live stack first to free ports. The override removes the live env file and blanks credentials/model. The separate project name isolates its SQLite volume:

```bash
docker compose -p stockscope-fixture -f compose.yaml -f compose.fixture.yaml up -d --wait
docker compose -p stockscope-fixture -f compose.yaml -f compose.fixture.yaml exec -T backend pytest -q
docker compose -p stockscope-fixture -f compose.yaml -f compose.fixture.yaml exec -T backend ruff check .
docker compose -p stockscope-fixture -f compose.yaml -f compose.fixture.yaml exec -T frontend npm run test
docker compose -p stockscope-fixture -f compose.yaml -f compose.fixture.yaml exec -T frontend npm run lint
docker compose -p stockscope-fixture -f compose.yaml -f compose.fixture.yaml exec -T frontend npm run build
curl -fsS http://127.0.0.1:5173/api/health
docker compose -p stockscope-fixture -f compose.yaml -f compose.fixture.yaml down
```

Never remove the live volume as cleanup. The standalone native `backend/tests/browser_smoke.py` starts its own servers and temporary synthetic database: run it only with Compose/native ports free. It does not test the container stack. Current verification evidence is in PROGRESS.md.

## SQLite backup and import

Git does not protect ignored databases or `.env`. Before storage changes, run:

```bash
backend/.venv/bin/python scripts/backup_local_state.py ../stocker-backups/UNIQUE-BACKUP-NAME
```

The destination must be new and outside the repository. Files/directories are private (0600/0700); the tool uses SQLite's backup API, verifies integrity, and records schema/counts/content fingerprints in a private manifest. It also preserves `.env` without displaying it. Back up before source rollback as well if persistence may be affected. Existing native databases are never moved/deleted by these tools.

Native `sqlite:///./stockscope.db` is relative to the backend working directory. Compose explicitly uses `sqlite:////data/stockscope.db`, on volume `stockscope_stockscope_data`. An existing separately configured `backend/live-acceptance.db` is diagnostic history, not automatically merged into the default database. Preserve/import it under its own name and select it explicitly if it should be the active history. Merging would change behavior and is outside this migration.

Stop services before import. Choose the appropriate numbered source snapshot from the private manifest. Mount only that database, read-only; never mount the backup directory containing the saved `.env` into the image build. Example (replace the source path):

```bash
docker compose down
docker compose run --rm --no-deps -T \
  -v /absolute/private/backup/03-stockscope.db:/backup/native.db:ro \
  backend python /workspace/scripts/sqlite_transfer.py /backup/native.db /data/stockscope.db
```

The importer refuses an existing destination, checks v1/integrity, and verifies counts and every row's fingerprint after backup. If a volume already has history, back it up and use a new destination/volume; do not overwrite it. Startup recovers interrupted research runs as before. `docker compose down` retains SQLite; volume deletion is never a default command.

## External Strata connectivity

The backend uses the existing configured endpoint/model/auth unchanged. Test `/models` from inside the backend with a bounded authenticated request, printing status only; never log auth or `.env`. A successful connection is distinct from full six-stage research acceptance. The pre-existing iq3_s output/total-token limitation remains out of scope.

If connection fails, compare native and container reachability, route and service bindings before changing any address/security setting. The application still permits only HTTPS or loopback/link-local IPv4 HTTP model endpoints without embedded credentials. Do not disable validation or broadly relax HTTP/CORS/host restrictions. Vite uses `API_PROXY_TARGET=http://backend:8000`; native fallback remains `127.0.0.1:8000`. Only the exact `backend` service hostname was added to TrustedHost; untrusted hosts/origins stay rejected.

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

Start with `docker compose -f compose.yaml -f /absolute/path/to/history-override.yaml up -d`. This selects that database without merging/deleting either history. Subsequent invocations must use the same override to retain the selection; ordinary `docker compose up -d` uses `/data/stockscope.db`.

See [Compose service reference](https://docs.docker.com/reference/compose-file/services/) and [Docker Desktop WSL2 integration](https://docs.docker.com/desktop/features/wsl/).

## Optional Make commands

`make dev`, `stop`, `status`, `logs`, and `rebuild` wrap the normal Compose lifecycle. Make is optional; `docker compose up -d` remains sufficient. `make test`, `lint`, `typecheck`, and `build` use one-off fixture containers with isolated temporary SQLite storage and do not require stopping the live stack. `make format` / `format-check` currently apply Ruff to Python; the planned Phase 3 adds frontend formatting. `make check` runs all quality/test/build targets; format-check intentionally reports existing baseline differences until Phase 3. `make smoke` uses the native browser harness and refuses occupied ports: stop Compose first. Backend source/test/script bind mounts allow explicit format writes; normal checks keep tests/scripts read-only.

## Quality tools

Phase 3 uses Ruff (110 columns, Python 3.11 target) and exact-pinned Biome 2.6.6 (2 spaces, single quotes, semicolons, import organization). Frontend `npm run typecheck` runs TypeScript; `lint` runs Biome. `format`, `format:check`, `check`, and `ci` are distinct commands. The initial Biome rules enforce unused declarations/imports, hook placement and JSX keys; expand rules incrementally without changing financial behavior. `make format` now formats both languages; formatting changes are committed separately from moves or behavior. See [Biome configuration](https://biomejs.dev/reference/configuration/) and [Ruff formatter](https://docs.astral.sh/ruff/formatter/).
