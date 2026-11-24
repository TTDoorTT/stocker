# Phase 4A — Industry Research capability registry

## Why this exists

The initial AI Computing pilot implemented SEC/RSS Overview and filing-backed Technology, Supply Chain and Competition generation. Twenty industry templates exist, but only the AI Computing source pipeline is integrated. The old UI and backend hardcoded that permission separately. Phase 4A makes it a single, fail-closed backend capability registry.

## Ownership

- `backend/app/modules/intelligence/industry_profiles.py`: source-profile registry and enabled section pipelines. Nothing in the registry fetches SEC data or calls the LLM.
- `backend/app/modules/intelligence/industries.py`: enriches all existing industry templates with `research_status`, `ai_sections` and `research_coverage`.
- `backend/app/modules/intelligence/industry_research.py`: checks the same registry before starting a live model or source call. It dispatches the **existing** `sec_rss_overview` and `sec_filing_review` flows without changing their evidence, quality checks, second-pass review, or persistence.
- Frontend: reads `industry.ai_sections`; it must not independently enable industry generation by slug or symbol.

## Contract

- `research_status`: `guided_only` or `limited_pilot`.
- `ai_sections`: section identifiers enabled for explicit AI generation, ordered as displayed in the workspace.
- `research_coverage`: bounded, human-readable description of the current evidence coverage and limitations.

The `GET /api/industries` and `GET /api/industries/{slug}` responses gain these fields. The endpoint paths and schema snapshot do not change because both endpoints are currently untyped `dict` responses. The generated-report storage schema, SEC retrieval, and LLM calls are unchanged.

## Not permission to add arbitrary sectors

Merely adding an industry to the existing `fixtures/industries.json` does **not** enable AI generation. The new source strategy must be implemented and tested first. Phase 4B enables the **Semiconductor** pilot (`INDUSTRY_SEMICONDUCTOR_PILOT.md`) and Phase 4D enables the **Grid Infrastructure** (`power-grid`) pilot (`INDUSTRY_POWER_GRID_PILOT.md`), each for Technology, Supply Chain and Competition using a dedicated SEC 10-K source universe. The other 17 industries remain guided-only.

## Acceptance

- All 20 templates remain navigable with the same research prompts.
- AI Computing Overview, Technology, Supply Chain and Competition expose Generate.
- Semiconductor and Grid Infrastructure (`power-grid`) Technology, Supply Chain and Competition expose Generate and raw SEC 10-K excerpt previews via `/api/industries/{slug}/filing-excerpts`.
- All Outlook tabs, Semiconductor/Power-Grid Overview, and the other 17 industries remain guided-only (including direct POST requests).
- GETs do not invoke SEC or the model.
- Existing saved notes load unchanged.
- Backend architecture and complete fixture tests; frontend Biome, typecheck, tests, build; Docker smoke all pass.
