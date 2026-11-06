Historical public validation before runtime AI configuration. Current validation is in ../VALIDATION.md.

# Validation

Reconciled 2026-11-06. Stocker's automated baseline is implemented; fixture verification is separate from financial coverage and live-model quality.

## Reproduce locally

```bash
docker compose config --quiet
make check
```

`make check` runs isolated `stockscope-check` one-off containers with explicit fixtures and temporary SQLite; it does not publish ports or require live credentials. On 2026-11-06, the branding gate passed **150 backend tests** (8.12s), **21 frontend tests**, Ruff/Biome lint/format/import checks, strict TypeScript and the production build (233 modules). One existing Starlette/httpx deprecation warning remains. Both sidebar/footer branding assertions and the full OpenAPI snapshot pass; the normalized snapshot diff from `93d0ee4` is exactly `info.title` → `Stocker`.

Optional browser and isolated Compose persistence commands are in [development](../DEVELOPMENT.md). Earlier migration acceptance recorded real restart/report persistence, Markdown download, widget failure/retry, source reload and mobile DOM-overflow checks. Those browser checks and screenshot perception were not rerun for this cleanup. Existing screenshots are historical artifacts and may show the previous brand. Fixture persistence will also run in PR CI.

## Verified on CI

Baseline main commit `93d0ee44656c9d711e4a581f6b3b3a700cd3705b` passed [GitHub Actions run 42298783499](https://github.com/TTDoorTT/stocker/actions/runs/42298783499) on 2026-11-06; its successful terminal state was queried during cleanup. The workflow covers Python 3.11/3.13, Node 22 quality/tests/build, and isolated Docker proxy/recreation/persistence. This historical result is not a claim that a later revision has passed; cleanup PR and post-merge results must be inspected separately.

## External acceptance and partial coverage

Previous 2026-11-06 records report successful SEC/Finnhub AAPL/MSFT/NVDA facts/quotes/news, Yahoo U.S. daily history and RY.TO/CAD history, and Valet FXUSDCAD/V39079 observations. They establish those symbols/paths at that time, not all providers or entitlements.

The later live-budget checkpoint records AAPL run `a3fb27ea-3a21-4341-b150-1d1363422443`: all six latest stages independently revalidated, a 22191-character sourced report, 19 evidence records, 5 calculations, 34 events, 806.153 seconds and 101745 provider-reported total tokens. Overall status remained **incomplete** because material consensus, interim/TTM, identity and other coverage was absent. Earlier JSON diagnostics record failed/incomplete attempts and were not rewritten as successes. The successful run's database/report is private; **this cleanup has not independently inspected it or rerun live inference**. Treat this as recorded prior acceptance, not newly reproduced live validation or proof of financial accuracy.

Canadian fundamentals/current quotes and automatic FX conversion remain unavailable. Alpha Vantage/FRED, TSXV live history, provider entitlements and broad live-model quality are **not independently verified** here. Fixture strategy comparisons establish equal captured evidence and validation mechanics, not six-agent superiority. No model settings, prompts or financial logic are changed by the cleanup.

Post-cleanup gate on 2026-11-06 also passed `docker compose config --quiet` and complete `make check`: 150 backend tests (8.85s), 21 frontend tests and all quality/type/build gates. The 20 removed history files were compared with their archived blobs after exact remote-SHA verification; public Markdown/image links resolve, and all seven executable prompt files remain byte-identical. The final case-insensitive audit also corrected the shared page-heading display label to STOCKER and added its assertion; the archive stays frozen at its original checkpoint.

Final branding follow-up gate: complete `make check` passed again with **150 backend tests (8.10s) / 21 frontend tests**, lint/format/import, TypeScript and production build. Relative Markdown/image links have zero broken targets. Compared with starting main, only display-branding source files and their assertions/snapshot differ; finance/providers/model/prompts/configuration/persistence/CI/fixtures/scripts and screenshots are preserved.
