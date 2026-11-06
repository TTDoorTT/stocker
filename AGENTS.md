# StockScope implementation

Before changing code, read `CODEX_STOCK_RESEARCH_IMPLEMENTATION_PLAN.md` and `docs/PROGRESS.md`. Resume from the recorded next action and preserve existing work.

Update `docs/PROGRESS.md` at phase boundaries, after meaningful milestones and test runs, on blockers, and before ending a session. Record architecture changes in `docs/DECISIONS.md`.

Financial fixtures must remain visibly labeled synthetic. Live facts require source metadata; derived values come from deterministic calculations. Reference clones stay ignored; OpenStock is conceptual reference only (AGPL).

For image inspection, use `vision-analyze IMAGE_PATH "specific question"`. It requires HTTPS; report network failures. Keep all implementation within this project and preserve user-wide Codex/LiteLLM configuration.
