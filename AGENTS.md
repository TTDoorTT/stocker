# Stocker contributor rules

Read `README.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md` and `docs/VALIDATION.md` before changing code. Keep main documentation focused on current use and contribution. For previous implementation context, plans, migration/debugging records or decisions, read the permanent `archive/stocker-development-history` branch: `git show archive/stocker-development-history:docs/PROGRESS.md` and `git show archive/stocker-development-history:docs/DECISIONS.md`. Fetch that branch from origin when absent; the dated `archive/stocker-development-history-2026-11-06` is the preserved earlier snapshot.

At each major feature/milestone, follow [the archive workflow](docs/DEVELOPMENT.md#development-history-workflow): merge the verified main or feature commit into the archive, update its progress/decisions with actual test results and next actions, and verify application trees match. Keep archive-only records there; never merge the archive into main. Preserve history and existing branches; pushes require user authorization.

Keep new code in its owned backend `app/modules/{market_data,research,portfolio,intelligence}` or frontend `src/features/*` module. Keep routers thin, provider access behind normalized market-data services and finance calculations pure. Share stable public contracts; preserve enforced import boundaries and API/DTO compatibility.

Keep fixtures visibly synthetic. Live facts require source metadata; derived values use deterministic calculations. Preserve explicit unavailable/incomplete coverage, runtime model prompts and existing tests. Reference clones stay ignored; OpenStock is conceptual reference only (AGPL). Retain industry attribution.

Preserve ignored configuration/databases and user-wide Codex/Strata/LiteLLM settings. Back up persistence before storage changes. Keep loopback bindings and restrictive host/origin/endpoint policies. Preserve legacy Compose/volume/SQLite and internal identifiers unless a separate migration explicitly authorizes changes.

Run `docker compose config --quiet` and `make check` before declaring a gate complete; TypeScript is separate from Biome lint. Commit formatter-only changes separately from moves/behavior and document new dependency rationale. Native browser smoke needs free ports and local browser dependencies; `scripts/compose_smoke.py` is only for an isolated fixture stack. Report actual local and remote CI results, with unrun gates explicit.

For image inspection use `vision-analyze IMAGE_PATH "specific question"`; it requires HTTPS. Report missing credentials/network failures and claim only observed visual details. Keep implementation within this project.
