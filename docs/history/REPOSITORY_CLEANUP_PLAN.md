# Stocker — Documentation Reconciliation, Development Archive, and Clean Main

**Document type:** Executable Codex handoff. **Status:** PLAN ONLY — not executed by ChatGPT.
**Repository:** `https://github.com/TTDoorTT/stocker.git`
**Local workspace:** `~/uni/dh399/stocker` (WSL)
**Inspection baseline:** `main` at `93d0ee44656c9d711e4a581f6b3b3a700cd3705b`, reviewed 2026-11-06.
**Latest observed CI:** GitHub Actions run [42298783499](https://github.com/TTDoorTT/stocker/actions/runs/42298783499), `main`, **success**. Recheck current head before execution.

## 0. Goal, branch model, and nonnegotiable boundaries

**Goal:** Make the product name **Stocker** consistently visible; bring all documentation into alignment with implemented code and verified checks; preserve the complete, updated implementation/progress/migration record in an immutable-by-convention Git branch; and deliver a tidy `main` with practical user and contributor documentation. Treat the existing automated validation and modular migration as a **completed baseline**. Do **not** claim full live-model research has passed without evidence; future model improvements/features are separate work.

Use this exact ancestry (names may receive a suffix **only** if the branch already exists; report any change):

```text
origin/main @ baseline
    |
    |-- A: refactor(branding): present Stocker in UI and API metadata
    |-- B: docs: reconcile implemented baseline and historic documentation
    |       |-- archive/stocker-development-history-2026-11-06   <-- push FIRST, freeze here
    |       |
    |       `-- C: docs: remove history-only assets and simplify public docs
    |             `-- chore/stocker-public-docs  ---> PR ---> main
```

The archive branch is **not** a second active development codebase. It is a recoverable snapshot of the *same application* with all original plans, progress logs, acceptance reports, and diagnostic artifacts, updated/annotated to reflect the implementation. `main` will retain history through Git regardless, but the named branch makes old documentation easy to browse.

**Hard constraints**

- Never use `git reset --hard`, `git clean -fd`, force pushes, history rewriting, or automatic stashing; stop on unexpected uncommitted changes/conflicts. Never delete original branches.
- Never modify or print ignored `.env`, model tokens, provider keys, real SQLite data, personal global Codex/Strata/LiteLLM configuration, or private backup directories.
- Do not change financial calculations, providers, AI prompts, orchestration, budgets, API routes/DTOs, schema/persistence, authentication/security restrictions, or runtime configuration for a documentation/brand cleanup.
- **Do not rename** the Compose `name: stockscope`, `stockscope_data` named volume, `stockscope.db` database paths, `STOCKSCOPE_ENV_FILE`, fixture project names, internal state identifiers, or file paths during this task. These are persistence/compatibility identifiers. They may retain legacy spelling; explain once in developer documentation. A separate migration with backups/volume mapping is necessary if renaming is wanted later.
- The Markdown files under `backend/app/modules/research/agents/prompts/` are **executable agent prompts**. Inventory them but do **not** rewrite, delete, or archive them as mere documentation.
- Keep `backend/tests/contracts/openapi.json`, synthetic fixtures, tests, CI workflow, Dockerfiles, scripts, source code, configuration templates, license/attribution requirements, and user-facing screenshots on `main`.
- Changes to the FastAPI **display title** and corresponding OpenAPI golden snapshot are permitted. The only intended contract-snapshot difference is `info.title`; fail if any other OpenAPI fields change.
- Prefer targeted staging (`git add <paths>`, `git rm <paths>`) and review every staged diff. The user requested a clean `main`, so push the branches and merge the cleanup PR **after** all required checks are green, if your GitHub permissions and branch rules allow it. If review/approval is required or checks fail, leave the PR open and report the blocker; never bypass protections.
- If today's remote repo or implementation differs from the inspected baseline, re-inventory first and adapt based on real files instead of applying old statements blindly.

## 1. Preflight: verify remote, local state, and baseline

Run in the WSL terminal. **If the working tree is dirty, stop and show the paths**; do not stash, reset, or overwrite. Store this handoff document *outside the repo*, e.g. `~/Downloads/STOCKER_REPOSITORY_CLEANUP_CODEX_PLAN.md`, until you intentionally copy it to the archive branch.

```bash
cd ~/uni/dh399/stocker
pwd
git remote -v
git status --short
# STOP here if unexpected local edits/untracked files require user decision.
git fetch --prune origin
git switch main
git pull --ff-only origin main
git status --porcelain=v1
git rev-parse HEAD
git log -5 --oneline
```

Verify repository is `TTDoorTT/stocker`, default is `main`, and the current head is known. Record the actual start SHA and date in the final report. If `main` moved past the inspected `93d0ee4`, explicitly audit the new changes. Do not roll back those commits. Existing branches `chore/docker-modular-migration` and `strata_optimization` must remain untouched.

Read the relevant files **before editing**:

```bash
git ls-files '*.md' '*.json' | sort
sed -n '1,240p' README.md
cat AGENTS.md
cat docs/ARCHITECTURE.md
cat docs/IMPLEMENTATION_STATUS.md
cat docs/ROADMAP.md
cat docs/migration/ACCEPTANCE.md
cat .github/workflows/ci.yml
cat compose.yaml
cat .env.example
rg -n -i 'stockscope|stock[ -]?scope|remote (ci|github actions).*(pending|unrun)|not (run|pushed)|phase [0-9]|PROGRESS\.md|CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN|docs/migration' --glob '!**/package-lock.json' .
```

Also review **latest** sections of `docs/PROGRESS.md`, `docs/DECISIONS.md`, `docs/DEVELOPMENT.md`, `docs/DATA_PROVIDERS.md`, and final live research JSON status summaries. Use `tail`, focused `rg`, or a pager instead of reading only an early phase. Re-run `git ls-files '*.md'` after cleanup to confirm new files and retained prompt Markdown.

### Known, grounded findings to reconcile

- Working architecture: FastAPI modular monolith (`app/modules/{market_data,research,portfolio,intelligence}`), React/Vite feature folders, SQLite, Docker Compose dev stack, separate external model and provider services.
- The current user-visible product name is **StockScope AI** in `README.md`, `frontend/index.html`, `frontend/src/app/layout/Sidebar.tsx`, `frontend/src/app/layout/Shell.tsx`, and `backend/app/main.py`'s FastAPI title. Search for additional UI/test occurrences before changing.
- `compose.yaml` and DB paths contain compatibility names `stockscope` and must remain unchanged in this pass.
- Automated baseline documented locally as 132 backend / 21 frontend tests, checks, build, fixture Docker persistence, and browser smoke. Verify current counts rather than blindly copying them. The latest **actual remote main CI run succeeded** at commit `93d0ee4`; older README, AGENTS, and acceptance/progress text wrongly imply GitHub CI was never run.
- Live SEC/Finnhub AAPL/MSFT/NVDA, yfinance U.S./Canadian daily history and Bank of Canada macro probes were previously recorded as passing **for tested symbols/paths only**. Other paid/keyed integrations and TSXV history were not all independently verified.
- Existing records describe **incomplete sourced six-stage Strata runs** with output/total-token/time limits. A recent `strata_optimization` merge altered model budget/timeout configuration; do not assume it proves a successful end-to-end sourced report. Document as "not yet independently accepted" unless an actual completed trace is demonstrated.
- Fixture mode is intentionally synthetic and works without live credentials. Six stages can validate while *overall research remains incomplete* when material evidence is missing. Do not market this as factual live investment advice.
- Partial Canadian support means explicit `.TO`/`.V` daily history, CAD positions, BoC macro; Canadian company fundamentals/current Finnhub quotes and automatic cross-currency portfolio conversion are still unsupported.

## 2. Create the work branch and safely change product branding

```bash
# Starting from clean, current main:
git switch -c chore/stocker-public-docs
```

Change only **display/marketing name**:

1. `frontend/index.html` browser `<title>`: `Stocker` (or `Stocker — AI Stock Research`).
2. `frontend/src/app/layout/Sidebar.tsx` brand: `Stocker`; retain any suitable accessible mark/subtitle. No navigation changes.
3. `frontend/src/app/layout/Shell.tsx` footer brand: `Stocker`.
4. `backend/app/main.py` FastAPI title: `Stocker` (pure metadata only).
5. `frontend/src/app/App.test.tsx`, any brand-specific snapshots/assertions, and `backend/tests/contracts/openapi.json`: update *only* intentional title expectations. Investigate any other test failures rather than weakening assertions.
6. Search the entire codebase for additional **user-visible** `StockScope` text. Avoid a global search-replace; database, Compose, paths, test data, migration history, and original reference titles should remain historically accurate.

For the OpenAPI baseline, compare old/new normalized JSON and require every field other than `info.title` to be identical. A backend test should explicitly allow the intended one-field branding change while retaining protection against endpoint/schema changes. Prefer an additional explicit assertion rather than deleting the snapshot test.

Run appropriate checks (see §7) and commit only after they pass:

```bash
git diff --check
git diff --stat
git add frontend/index.html frontend/src/app/layout/Sidebar.tsx frontend/src/app/layout/Shell.tsx backend/app/main.py
# Stage only the specific test/golden files actually changed, after review.
git diff --cached --check
git commit -m "refactor(branding): display Stocker without changing runtime identities"
```

If a requested branding change forces a substantive API or persistence migration, do **not** perform it here. Document the conflict and keep the original stable identifier.

## 3. Reconcile *all* Markdown in the archival snapshot

Inventory every Markdown. Classify each as public reference, historical development artifact, or executable prompt. Do not mechanically rewrite all wording; bring **current-facing statements** up to date while preserving historical evidence, timestamps, failures, and original plan objectives as a record of what actually happened.

**Current/public-facing sources** to update on this branch:

| File | Required final content |
|---|---|
| `README.md` | **Stocker** name, one-paragraph pitch, actual feature summary, 5-minute Docker quickstart, `fixtures` vs `live`, ports 5173/8000, optional `.env` config, link to fuller docs, clear limitations and educational-only disclaimer, tests and support status, screenshot if helpful. Remove long chronological migration narration and stale "CI not run" language. |
| `docs/ARCHITECTURE.md` | Actual modular backend/frontend/SQLite and Docker roles; six specialist stages *inside one backend*, not six containers; model outside Docker; source/contract boundaries, persistence. |
| `docs/DEVELOPMENT.md` | Exact first-run and repeat-run commands, native fallback, fixture tests, live configuration, logs/rebuild, smoke prerequisites, persistence/backups, safe rollback. Document legacy Docker/DB naming as intentional compatibility. |
| `docs/API.md` | Verify endpoint and OpenAPI references against running code/tests; no unimplemented routes. |
| `docs/DATA_PROVIDERS.md` | Accurate providers, required keys, U.S./Canadian support, explicit unavailability/licensing caveats, no provider quality overclaims, no links to files subsequently deleted from `main`. |
| `docs/DEMO.md` | Runnable visitor-facing fixture demonstration, accurate routes/screens, no claims of proven live six-stage reports. |
| `docs/INDUSTRIES.md` | Preserve necessary source acknowledgments/attribution and accurate twenty-topic scope. |
| `docs/ROADMAP.md` | Short **future-only** feature list; move done phases out of roadmap. Model tuning/full live sourced research is an *improvement/follow-up*, not a reason to label the accepted baseline incomplete. |
| `AGENTS.md` | Initially reconcile as development instructions in the full archive. After cleanup, replace with a **short main-compatible** rules file (§6). |

**Historical docs** — preserve and annotate, then archive off `main`:

| File or group | How to update in the archival snapshot |
|---|---|
| `CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md` | Add a visible **historical/completed initial plan** header with date and current implementation/limits; preserve the original detailed instructions, don't rewrite past phases as new work. |
| `docs/PROGRESS.md` | Append a dated final baseline checkpoint: current main SHA, new branding/docs, locally verified gates, **successful GitHub CI**, remaining live-model/Canadian limitations, archive intention. Preserve chronological entries. |
| `docs/IMPLEMENTATION_STATUS.md` | Add an up-to-date status summary or superseding table. Early paths and test counts are historical, not current architecture. Distinguish accepted implementation from open enhancement work. |
| `docs/DECISIONS.md` | Preserve ADR/history; append final rationale for archive vs clean main and technical-identifier compatibility. |
| `docs/BROWSER_SMOKE.md` | Maintain previous measured result, exact prerequisites, and limitation of screenshot/pixel inspection; add newer rerun only if actually performed. |
| `docs/EVALUATION.md` | Preserve fixture-evaluation methodology and its limits; don't claim financial/model superiority. |
| `docs/PROVIDER_RESEARCH.md` | Maintain provenance/restrictions as a historical research artifact; correct statements if genuinely outdated. |
| `docs/REFERENCE_AUDIT.md` | Preserve reference-code audit/attribution. |
| `docs/migration/STOCKSCOPE_DOCKER_MODULAR_MIGRATION_PLAN.md` | Add **migration completed; archival specification** header and final acceptance pointer. Do not globally rename historically correct migration filenames. |
| `docs/migration/ACCEPTANCE.md` | Append post-push evidence that remote GitHub Actions did run successfully (Nov 6 commit/run); preserve original "not run" statement as an earlier checkpoint, clearly superseded. |
| `docs/migration/PHASE_1_ACCEPTANCE.md` | Preserve intermediate blocked/resolved chronology; mark superseded by final acceptance. |
| `backend/app/modules/research/agents/prompts/*.md` | **Keep untouched**: these are runtime prompt assets, not progress documentation. |

Optional: copy **this** execution plan into the archive-only history (e.g. `docs/history/REPOSITORY_CLEANUP_PLAN.md`) *if* the handoff file is supplied locally and can be safely copied. Do not leave it tracked in the public main branch.

Create `docs/VALIDATION.md` as a short **public** summary (prefer < 2 pages): commands to reproduce fixture checks, verified past remote CI link/commit/date, and candid split between completed automated baseline and unverified external/live runs. Do not print secrets or dump hundreds of lines of logs.

### Documentation truth rules

- Use "implemented and verified" only when the named behavior really passed tests or acceptance.
- Keep one status vocabulary: `Implemented`, `Verified locally`, `Verified on CI`, `Partial coverage`, `Deferred`, `Not independently verified`. Don't confuse `run status: incomplete` with a failed automated test suite.
- Cite previous acceptance run IDs and commit SHAs. If tests are rerun, include the actual output and date; don't invent new counts.
- Never replace historical failed attempts with fabricated successes. Append superseding notes.
- The native Docker command for a new clone is `docker compose up --build -d` first, then `docker compose up -d` thereafter; default mode is `fixtures` and requires no credentials. Use ports 5173 (web) and 8000 (API docs).
- Keep documentation clear that the app is local educational software, not a hosted multiuser platform or investment-advice service.

## 4. Secret/privacy scan, baseline tests, and **archive checkpoint**

Before any push, inspect newly staged files **and current public diagnostic JSON logs** for accidentally committed tokens, authorization headers, private addresses, `.env` contents or personal logs. At minimum:

```bash
git status --short
git grep -n -I -E '(sk-[A-Za-z0-9]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|Authorization: Bearer|BEGIN (RSA |OPENSSH )?PRIVATE KEY|NVIDIA_API_KEY=.+|LLM_API_KEY=.+)' -- ':!frontend/package-lock.json' || true
git diff --check
# Review any matches manually without echoing actual secrets into a report.
```

If a real secret appears anywhere in already-public Git history, **stop and report only its file path and nature, not its value**. Rotation/redaction/history rewriting needs a separate explicit decision; deleting the file on `main` does not remove historical exposure.

Run local checks (see §7). On success, create **one documentation-sync commit** (or a few coherent commits), recording actual results. Do not include `.env` or private databases. Ensure full history markdown, newly generated public validation page, and optional archive-only plan are committed at this checkpoint. A fresh remote CI green run should be confirmed later through the cleanup PR.

```bash
# Review and explicitly stage documentation files created/changed in §3.
git diff --check
git diff --stat
# Example; add the exact reviewed files and optional plan path, not a blind git add -A.
git add README.md AGENTS.md docs
# Also stage root historical plan only if it was actually edited.
git add CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md
# Never include ignored local credentials/databases.
git diff --cached --check
git diff --cached --stat
git commit -m "docs: reconcile Stocker baseline, validation and historical records"
```

**Critical ordering: preserve the remote archive before deleting anything.**

```bash
ARCHIVE_SHA="$(git rev-parse HEAD)"
git branch archive/stocker-development-history-2026-11-06 "$ARCHIVE_SHA"
git push -u origin archive/stocker-development-history-2026-11-06
REMOTE_SHA="$(git ls-remote origin refs/heads/archive/stocker-development-history-2026-11-06 | cut -f1)"
test "$REMOTE_SHA" = "$ARCHIVE_SHA" || { echo 'Archive verification FAILED; STOP'; exit 1; }
git branch --contains "$ARCHIVE_SHA"
```

Open the archive branch on GitHub and verify it contains all updated `PROGRESS.md`, the root implementation plan, migration docs, original evaluation/JSON diagnostics and `AGENTS.md` as of this milestone. Record `ARCHIVE_SHA` in the final handoff. **Do not delete historical files until the remote SHA check succeeds.**

## 5. Clean public `main` contents (on existing cleanup work branch)

Stay on `chore/stocker-public-docs` at commit B. The archive branch points at this same commit B and is already pushed. Create cleanup commit C that deletes only development-history material.

### Files to REMOVE from the branch destined for `main` (retain in remote archive)

```text
CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md
docs/PROGRESS.md
docs/IMPLEMENTATION_STATUS.md
docs/DECISIONS.md
docs/BROWSER_SMOKE.md
docs/EVALUATION.md
docs/EVALUATION.json
docs/PROVIDER_RESEARCH.md
docs/REFERENCE_AUDIT.md
docs/LIVE_MODEL_CHECK.json
docs/LIVE_MODEL_RESUME_CHECK.json
docs/LIVE_PROVIDER_ACCEPTANCE.json
docs/LIVE_SOURCED_RUN.json
docs/LIVE_SOURCED_RUN_45S_TIMEOUT.json
docs/LIVE_SOURCED_RUN_INITIAL.json
docs/LIVE_SOURCED_RUN_TOKEN_FAILURE.json
docs/migration/  (entire migration history directory)
docs/history/REPOSITORY_CLEANUP_PLAN.md  (if added to archive)
```

Confirm each path really exists and whether any code/test/tool references it before removal. Apply removals with `git rm` using **exact verified paths**. If files have moved, re-inventory and adjust. Never delete `backend/tests/contracts/openapi.json`, `fixtures/*.json`, app prompts, or active test scripts.

### Files to KEEP / improve on public `main`

```text
README.md                       # concise landing page + quickstart
AGENTS.md                       # short AI contributor rules; NO missing-file requirements
docs/ARCHITECTURE.md            # current code boundaries
docs/DEVELOPMENT.md             # getting started, configuration, safety
docs/API.md                     # routes/contracts
docs/DATA_PROVIDERS.md          # source/coverage/rights
docs/DEMO.md                    # fixture walkthrough
docs/INDUSTRIES.md              # topic provenance and attribution
docs/ROADMAP.md                 # only future work
docs/VALIDATION.md              # short verified-baseline/limits summary
docs/screenshots/*              # helpful viewer screenshots, no secret payloads
backend/app/modules/research/agents/prompts/*.md  # app logic, MUST keep
```

The whole application still needs tests, `.github/workflows/ci.yml`, `Makefile`, `.env.example`, compose files, Dockerfiles, fixtures and scripts; none are archival clutter.

Revise all retained public Markdown to fix now-broken local links to `PROGRESS.md`, migration documents, evaluation JSON, provider-research files, or any removed asset. Where long historical evidence is genuinely useful, provide **one discreet link** to:

`https://github.com/TTDoorTT/stocker/tree/archive/stocker-development-history-2026-11-06`

Do not leave numerous links that make the public documentation feel like a migration journal. `AGENTS.md` **must not instruct future Codex sessions to read removed local files**. Replace with instructions to read current `README.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/VALIDATION.md`, preserve `fixtures` and data integrity, run `make check`, and use PR/issue descriptions or feature branches for detailed incremental progress. Do not reintroduce a giant `docs/PROGRESS.md` on main.

### Recommended README structure

1. `# Stocker` — honest local U.S./Canadian research overview and small screenshot.
2. `Quick start` — Docker first run + everyday command + stop (retain volume).
3. `What works` — feature bullets/table, fixture vs live mode.
4. `Configuration` — `.env.example` and optional keys/model endpoint; no secrets client-side.
5. `Limitations` — synthetic data, partial Canada, missing consensus, live-model end-to-end not yet independently accepted, data licensing.
6. `Tests` — `make check`, link short validation page.
7. `Docs` — links to current architecture, development, API, providers, demo, roadmap.
8. Optional single `Development history (archive)` link in a low-emphasis final paragraph.

### Repository metadata

The GitHub repository URL is already named `stocker`; **do not rename the repository** or its remote. If the GitHub repository description still mentions StockScope, propose a short update in the final report, but avoid changing account/repository settings as part of source cleanup unless expressly directed.

## 6. Link/name validation, staging, and cleanup commit

Run at minimum:

```bash
# Old name in current tracked files: classify all hits; don't globally replace legacy identifiers.
git grep -n -i 'StockScope' -- ':!backend/tests/contracts/openapi.json' || true
# Broken references to files deleted from main must be fixed in remaining docs/config/scripts.
rg -n 'PROGRESS\.md|IMPLEMENTATION_STATUS\.md|DECISIONS\.md|BROWSER_SMOKE\.md|EVALUATION\.(md|json)|PROVIDER_RESEARCH\.md|REFERENCE_AUDIT\.md|LIVE_.*\.json|CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN|docs/migration' --glob '*.md' . || true
# Confirm all remaining .md docs are intended and model prompts still present.
git ls-files '*.md' | sort
git status --short
git diff --check
git diff --stat
```

Write/run a temporary (untracked, outside repo) relative Markdown link checker for all retained `README.md`, `AGENTS.md`, `docs/*.md`. Ignore external web URLs and anchors; resolve repo paths correctly and verify targets exist. Also check links to assets/screenshots; no broken local references are acceptable. A script under `/tmp` is fine; no new dependency required.

Ensure markdown points to `docs/VALIDATION.md` instead of logs, and archive links use the exact verified remote branch name.

After staging the **reviewed** deletions and edited public files:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
# Confirm no application logic, persistent state identifiers or prompt content was removed.
git commit -m "docs: keep public Stocker docs and archive development history"
```

Keep the historical branch SHA unchanged; do not merge cleanup commit C into the archival branch.

## 7. Validation gates — checks before archive, after cleanup, and in PR

**Minimum gating for naming, documentation cleanup, and CI**:

```bash
docker compose config --quiet
make check
# Optional native smoke (requires installed Playwright/Chromium, available ports 8000/5173):
# backend/.venv/bin/python backend/tests/browser_smoke.py
```

`make check` uses isolated fixture containers; record both backend and frontend counts, formatting/lint, TypeScript, build result. If Docker or the environment is unavailable, use existing native checks with the project's lock files and clearly report any unrun gate. Never label a skipped test as passed. Do not automatically shut down a user's live stack just to run the native smoke; check port occupancy first and get authorization before disrupting running services.

**Additional acceptance criteria:**

- UI shows **Stocker** in sidebar, footer and browser title; OpenAPI `info.title` says Stocker. Route paths and DTOs unchanged.
- API snapshot diff contains only `info.title` and no unrelated test/contract changes.
- Default `DATA_MODE=fixtures`, explicit synthetic labels and local-only binding retain original behavior. `docker compose up --build -d` is a valid fresh-clone startup; `docker compose up -d` remains repeatable.
- Existing SQLite volume/data paths are untouched; no `docker compose down -v`, DB deletion, data import, or forced migration occurs.
- No broken relative Markdown or image links, missing `AGENTS.md` references, secrets, or executable prompt deletions.
- No live provider/model requests are required to pass fixture CI; claims about sourced research remain accurate.
- `main` landing docs are concise and there are no chronological migration/progress files, diagnostic JSON logs or root Codex execution plan on the cleanup branch.
- The **remote archive branch exists** and still has all synchronized historical artifacts.

Push cleanup branch and open a PR (using `gh` if installed/authenticated; otherwise give the compare URL and manual steps). **Merge only after all checks pass and applicable branch protections/reviews are satisfied.**

```bash
git push -u origin chore/stocker-public-docs
# If gh CLI is available and authenticated:
gh pr create --base main --head chore/stocker-public-docs \
  --title "docs: release Stocker baseline with archived development history" \
  --body "Rebrand user-facing project to Stocker, reconcile documentation and remote CI status, preserve all development history on archive/stocker-development-history-2026-11-06, and simplify public documentation. Docker/database persistent identifiers and application behavior remain unchanged. Verified: <insert actual commands, counts, and results>."
```

Wait for the actual GitHub Actions PR jobs to reach a terminal state; read the results. If checks fail, fix the cause on this branch, rerun locally, and push; never claim green remotely before the workflow finishes. When PR checks are green and no branch protection/reviewer requirement blocks the operation, merge the PR normally (prefer squash or the repository-approved method), then fetch/pull `main` and confirm **post-merge `main` CI** actually succeeds. If GitHub requires an additional review, leave the PR open and report precisely what remains. Do not delete the archive branch.

## 8. Final Codex report (required, concise)

Return:

1. Start SHA, work branch, **archive branch URL/SHA**, cleanup PR URL, and commit SHAs/messages.
2. Exactly which historical paths were archived/removed from public main, and which public docs remain.
3. Branding changes; a clear note that legacy Compose/volume/SQLite identifiers intentionally remain unchanged.
4. Actual local command outputs summarized (backend/frontend test counts, lint, type/build, optionally browser smoke) and final PR and merged-`main` CI status/URLs (or explicit reason a protected PR remains open).
5. Any skipped/unverified items: full live sourced six-stage research, model budgets, partial Canadian data, visually-perceived screenshots, provider entitlements, etc. Do not equate completed fixture verification with live financial correctness.
6. Safety checks: no .env/DB change, no prompt modifications, no leaked credentials, and archive branch verified remotely.
7. Remaining user actions only if GitHub requires them (e.g. mandated PR review); optional later branded-volume migration or live-model tuning.

## 9. Recovery / stop conditions

- **Archive push fails:** STOP. Do not remove a single historical file; fix credentials/permissions/network or report blocker.
- **Dirty or diverged branch:** STOP; show actual state. No stash/reset/force.
- **CI fails or OpenAPI changes unexpectedly:** stop, diagnose, keep main untouched. Do not overwrite golden contracts broadly.
- **GitHub branch already exists:** inspect it; never force-repoint it. Use a new date/suffix after reporting name change.
- **Secrets found:** stop and report only file paths/secret classes; get explicit authority for rotation or history cleanup.
- **Conflict with an existing live database or stack:** do not rename Compose project/volume or delete data; preserve as-is.
- **If main somehow receives an unexpected change before PR merge:** rebase/merge normally only after inspecting changes and rerunning gates. Do not force-update main or archive.

---

## Copy/paste Codex task prompt

> You are working on `~/uni/dh399/stocker`, repository `https://github.com/TTDoorTT/stocker.git`. Execute the attached `STOCKER_REPOSITORY_CLEANUP_CODEX_PLAN.md` in order. **Read the whole document first.** Your goal is to brand the public project **Stocker**, reconcile all current and historical Markdown against actual code, push a frozen development-history archive branch, then prepare a clean public-documentation PR targeting `main`. Do not modify runtime behavior, data providers, model prompts/orchestration, database volume/path identifiers, `.env`, or user-wide services. Don't delete historical files until the archive branch has been pushed and its remote SHA verified. Treat the existing automated validation baseline as complete but document live-model six-stage research limits honestly. Run all available fixture tests, formatting/lint/type/build and verify PR CI. Merge the PR into `main` only after required CI and protections pass, then verify post-merge CI; if a required review or other safeguard blocks merging, leave the PR open and report it. Return exact archive/PR/main links, commits, test results and any blockers. If unexpected changes or uncommitted files are present, stop and report instead of resetting or stashing.
