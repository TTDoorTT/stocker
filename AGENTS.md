# Stocker implementation — full development archive

Before changing code, read `CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md` and `docs/PROGRESS.md`. Resume from the recorded next action and preserve existing work.

Update `docs/PROGRESS.md` at phase boundaries, after meaningful milestones and test runs, on blockers, and before ending a session. Record architecture changes in `docs/DECISIONS.md`.

Financial fixtures must remain visibly labeled synthetic. Live facts require source metadata; derived values come from deterministic calculations. Reference clones stay ignored; OpenStock is conceptual reference only (AGPL).

For image inspection, use `vision-analyze IMAGE_PATH "specific question"`. It requires HTTPS; report network failures. Keep all implementation within this project and preserve user-wide Codex/LiteLLM configuration.

## Docker/modular migration

Read `docs/migration/STOCKSCOPE_DOCKER_MODULAR_MIGRATION_PLAN.md`, `docs/ARCHITECTURE.md`, `docs/API.md` and current progress before migration changes. Complete Docker acceptance before module moves. Use the dedicated migration branch and small verified commits; no pushes without authorization. Preserve ignored `.env` and SQLite history with verified backups outside Git. Never change user-wide Strata/Codex/LiteLLM settings. Keep ports on host loopback and validation/host/origin policies restrictive. Historical migration exclusions are preserved in its specification; later project-budget acceptance is recorded in progress. This cleanup changes neither model budgets nor runtime behavior.

## Module and quality conventions

New feature code belongs to its owned market-data/research/portfolio/intelligence module. Keep HTTP routers thin, provider access behind normalized market-data interfaces and finance calculations pure. Avoid private imports across feature modules; share only stable contracts. Preserve public API types, routes, persistence and all evidence/fixture/coverage guarantees. Run `make check` (isolated fixture containers) before declaring a gate complete; TypeScript is separate from Biome lint. Commit formatter output separately from moves/behavior; document any new dependency rationale. Native browser smoke requires free ports.

The feature migration is implemented. Current backend owners are `app/modules/{market_data,research,portfolio,intelligence}`; stable DTOs are `app/contracts`, SQLite lifecycle is `app/core/database.py`. Frontend owners are `src/features/*` with app composition and generic shared code. Follow enforced import boundaries; extend public contracts deliberately rather than bypassing adapters. `make check` covers unit/integration/boundary/API snapshot/format/lint/type/build checks. `scripts/compose_smoke.py` is only for an isolated fixture Compose project. Remote GitHub Actions results must not be claimed without actual execution.

## Repository cleanup checkpoint

The completed baseline is summarized in `docs/VALIDATION.md`. Main CI at `93d0ee4` passed run 42298783499. Preserve older failure/no-push entries as dated history, superseded by the final checkpoint. The archive freezes synchronized history; subsequent cleanup must use main-compatible contributor instructions and must keep runtime prompts/tests/fixtures untouched.
