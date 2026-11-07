# Stocker contributor rules

Read `README.md` first. Consult `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/API.md` and `docs/VALIDATION.md` only as relevant to the task. Use current source code as the authority for behavior. Do not load archived development history by default.

Keep active documentation aligned with implemented code. Record new development decisions, validation results and changes in commits, pull requests or issues. Do not recreate or maintain `progress/PROGRESS.md` or a separate progress-log directory. Preserve Git history and existing archive branches; pushes require user authorization.

Keep new code in its owned backend `app/modules/{market_data,research,portfolio,intelligence}` or frontend `src/features/*` module. Keep routers thin, provider access behind normalized market-data services and finance calculations pure. Share stable public contracts; preserve enforced import boundaries and API/DTO compatibility.

Keep fixtures visibly synthetic. Live facts require source metadata; derived values use deterministic calculations. Preserve explicit unavailable/incomplete coverage, runtime model prompts and existing tests. RSS industry news is independent of financial `DATA_MODE`: reading/refreshing/categorizing news and restoring saved highlights must not call an LLM. Only explicit user-triggered generation can call the validated summarizer. Preserve RSS publisher links, excerpts limitations, per-category SQLite persistence/staleness, and the MIT-derived source inventory/license in `docs/THIRD_PARTY_NEWS_SOURCES.md`. Reference clones stay ignored; OpenStock is conceptual reference only (AGPL). Retain industry attribution.

Preserve ignored configuration/databases and user-wide Codex/Strata/LiteLLM settings. Back up persistence before storage changes. Keep loopback bindings and restrictive host/origin/endpoint policies. Preserve legacy Compose/volume/SQLite and internal identifiers unless a separate migration explicitly authorizes changes.

Run `docker compose config --quiet` and `make check` before declaring a gate complete; TypeScript is separate from Biome lint. Commit formatter-only changes separately from moves/behavior and document new dependency rationale. Native browser smoke needs free ports and local browser dependencies; `scripts/compose_smoke.py` is only for an isolated fixture stack. Report actual local and remote CI results, with unrun gates explicit.

For image inspection use `vision-analyze IMAGE_PATH "specific question"`; it requires HTTPS. Report missing credentials/network failures and claim only observed visual details. Keep implementation within this project.
