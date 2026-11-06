# Stocker contributor rules

Read `README.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/VALIDATION.md` and the latest entry in `progress/PROGRESS.md` before changing code. Use current source/architecture for implementation; consult [progress records](progress/README.md) for past plans, decisions, migrations and debugging context.

Keep application changes and their development records together on `main` through the normal PR workflow. Update `progress/PROGRESS.md` at meaningful milestones, after test runs, on blockers and before ending a session; record architecture decisions in `progress/DECISIONS.md`. Include actual validation results, limitations and a precise next action. No separate development-history branch or archive synchronization is required. Older archive branches are preserved snapshots; their workflow instructions are superseded. Preserve history and existing branches; pushes require user authorization.

Keep new code in its owned backend `app/modules/{market_data,research,portfolio,intelligence}` or frontend `src/features/*` module. Keep routers thin, provider access behind normalized market-data services and finance calculations pure. Share stable public contracts; preserve enforced import boundaries and API/DTO compatibility.

Keep fixtures visibly synthetic. Live facts require source metadata; derived values use deterministic calculations. Preserve explicit unavailable/incomplete coverage, runtime model prompts and existing tests. Reference clones stay ignored; OpenStock is conceptual reference only (AGPL). Retain industry attribution.

Preserve ignored configuration/databases and user-wide Codex/Strata/LiteLLM settings. Back up persistence before storage changes. Keep loopback bindings and restrictive host/origin/endpoint policies. Preserve legacy Compose/volume/SQLite and internal identifiers unless a separate migration explicitly authorizes changes.

Run `docker compose config --quiet` and `make check` before declaring a gate complete; TypeScript is separate from Biome lint. Commit formatter-only changes separately from moves/behavior and document new dependency rationale. Native browser smoke needs free ports and local browser dependencies; `scripts/compose_smoke.py` is only for an isolated fixture stack. Report actual local and remote CI results, with unrun gates explicit.

For image inspection use `vision-analyze IMAGE_PATH "specific question"`; it requires HTTPS. Report missing credentials/network failures and claim only observed visual details. Keep implementation within this project.
