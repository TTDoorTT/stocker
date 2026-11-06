# StockScope implementation

Before changing code, read `CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md` and `docs/PROGRESS.md`. Resume from the recorded next action and preserve existing work.

Update `docs/PROGRESS.md` at phase boundaries, after meaningful milestones and test runs, on blockers, and before ending a session. Record architecture changes in `docs/DECISIONS.md`.

Financial fixtures must remain visibly labeled synthetic. Live facts require source metadata; derived values come from deterministic calculations. Reference clones stay ignored; OpenStock is conceptual reference only (AGPL).

For image inspection, use `vision-analyze IMAGE_PATH "specific question"`. It requires HTTPS; report network failures. Keep all implementation within this project and preserve user-wide Codex/LiteLLM configuration.

## Docker/modular migration

Read `docs/migration/STOCKSCOPE_DOCKER_MODULAR_MIGRATION_PLAN.md`, `docs/ARCHITECTURE.md`, `docs/API.md` and current progress before migration changes. Complete Docker acceptance before module moves. Use the dedicated migration branch and small verified commits; no pushes without authorization. Preserve ignored `.env` and SQLite history with verified backups outside Git. Never change user-wide Strata/Codex/LiteLLM settings. Keep ports on host loopback and validation/host/origin policies restrictive. The existing live iq3_s token-budget limitation is outside this migration.
