> Historical record imported from `docs/REFERENCE_AUDIT.md` at `f8d3cbc`. Current workflow and file locations are in the [progress guide](README.md); old execution steps and branch policies below are historical context.

**Historical artifact — reconciled 2026-11-06.** Pinned reference SHAs and licensing boundaries below are preserved. Stocker is the historical product name, now Stocker; OpenStock remains conceptual reference only. Current status: [validation](../docs/VALIDATION.md).

---

# Reference audit

Audited 2026-11-06. Both shallow clones exist under ignored `references/`. These are conceptual references, not dependencies or upstream code to merge.

| Repository | Recorded HEAD | License |
|---|---|---|
| https://github.com/simonlin1212/Vibe-Research | `84c141b86b5e7540b29f5f4cd5457dc0ebd6052e` | MIT; copyright 2026 simonlin1212 |
| https://github.com/Open-Dev-Society/OpenStock | `eac478f71dcff342d196a65c724dc955c221eeee` | GNU AGPL version 3 |

Initial sandbox clone attempts failed with `Could not resolve host: github.com`; approved escalated clone commands succeeded. No code, prompts, assets or financial datasets were copied verbatim into Stocker by this audit. OpenStock remains inspiration only. If later implementation adapts substantial Vibe material, include its MIT copyright and full permission notice with the adapted artifact.

## Vibe Research inspected paths

All specification paths exist at this SHA; no replacements were necessary. Large modules were inspected by contracts, key execution/validation sections and targeted searches rather than assuming every implementation detail carries over.

| Path | Findings and selected adaptation |
|---|---|
| `README_en.md` | Broad desktop research platform, including many features outside Stocker. Adopt research-first navigation; avoid wholesale feature migration. |
| `orchestrator/README.md` | Explicit six stages and controlled runtime. Use backend-owned sequence and durable stage artifacts. |
| `orchestrator/src/orchestrate.ts` | Runs each stage through bounded attempts and independent validation; logs completion, protects inputs, checks final artifacts. Implement a smaller state machine with persisted attempts, errors and terminal status. |
| `orchestrator/src/agent_runner.ts` | Injectable runner separates model execution from event ledger. Records usage only when returned and redacts known secrets before writing events. Use one injectable model client and real timestamped events. |
| `orchestrator/src/finance/stages_global.ts` | Distinct US/HK contracts: identity and listing/reporting currency checks; fiscal start/end dates rather than forced calendar quarters; point-in-time filing filters; no unsupported nonrecurring-profit metric; sources and calculation IDs on report rows. Use US rules, not A-share defaults. Its Yahoo consensus availability is not assumed for Stocker. |
| `orchestrator/src/finance/stages.ts` | Prompt context includes attempt and validator errors; routes global markets to separate stage instructions. Use six concise role prompts and actionable retry feedback. Remove China-only extensions. |
| `orchestrator/src/finance/methodology.ts` | Maps each stage to specialist methodology and provides calculation contracts explicitly. Adopt role-specific instructions plus common evidence/math rules; no filesystem discovery by agents. |
| `orchestrator/src/finance/plugin.ts` | Declares ordered stages, required/optional sources and computations, report sections and regional contracts. Stocker will use simple explicit contracts rather than a general plugin framework. Unlike this reference, absent consensus is an honest gap rather than an unconditional critical dependency. |
| `orchestrator/src/validator.ts` | Validates referenced IDs, required calculations or explicit gaps, calculation inputs and upstream contracts; recalculation is outside model trust. Adopt independent reference/math validation and bounded corrections. |
| `orchestrator/src/schemas.ts` | Evidence, fetch envelopes, calculation records, gaps, stage outputs and manifests have machine-readable contracts. Use strict Pydantic outputs and normalize source metadata. |
| `orchestrator/src/run_tools.ts` | Allowlisted read/calculate/write tools with path and size bounds; tool definitions separate from transport. Stocker agents receive bounded data/tool interfaces, never shell or arbitrary HTTP. |
| `orchestrator/src/api.ts` | Local HTTP research start, run listing, reports and evidence; origin/content-type protections and secret handling. Use FastAPI REST plus polling; do not reproduce its many unrelated routes. |
| `methodology/constitution.md` | Explicit evidence/calculation discipline, missing-data states, source text as untrusted input, durable trace. Adopt principles in independently written English contracts. |
| `.agents/skills/company-research/SKILL.md` | Fixed stage sequence, dependency matrix and report skeleton; gaps have operation and reason. Keep six roles and explicit incomplete states. |
| `.agents/skills/earnings-analysis/SKILL.md` | Separates cumulative and single-quarter/TTM data; comparable periods and deterministic computations. US fiscal periods must stay intact. |
| `.agents/skills/valuation/SKILL.md` | Every derived ratio needs a calculation ID; missing inputs stay missing; negative denominators can be not meaningful. Do not port A-share-specific deducted-profit or scenario anchors. |
| `.agents/skills/catalyst-risk/SKILL.md` | Counterevidence and conditions for invalidating conclusions; external discussion is not verified fact. Keep risk review and disputed-claim trace; defer speculative signals. |
| `.agents/skills/data-access/scripts/` | Inspected script inventory and adapter organization: thin fetch entrypoints, `sources/`, `core/`, tests and locked requirements. Implement a small independent SEC/quote adapter set; do not import its broad dependencies. |
| `datasources/CATALOG.md`, `datasources/registry.json` | Generated catalog and endpoint registry separate markets, requirements and compliance. Registry root contains version/documentation/endpoints; catalog advertises 168 endpoints. This is discovery material, not proof Stocker can access any endpoint. |
| `calc/`, `calc/SPEC.md` | Pure formulas and series operations separated from CLI/file handling; finite-number guard, units/currency, calculation identities and input references. Implement only required formulas in Python. |
| `desktop/src/verticals/finance/router.tsx` | Finance routes separate research, records, watchlists, sectors, intelligence and settings. Adopt selected navigation only. |
| `desktop/src/verticals/finance/pages/` | Inspected Home, DailyReview, Research, Intel, Signals and Sectors modules. Research surfaces runs and evidence; intelligence and signals label freshness/failures. Do not copy components or China-only market semantics. |
| `desktop/src/verticals/finance/data/sectors.json` | Exactly 20 topic skeletons. Only humanoid and AI computing are marked verified in the source; most have empty nodes. Adapt topics as guided prompts, never treat unverified nodes as factual industry analyses. |

The 20 source topic keys are `humanoid`, `ai-computing`, `hbm`, `cpo`, `pcb`, `semiconductor`, `solid-state-battery`, `low-altitude`, `smart-driving`, `innovative-drug`, `power-grid`, `defense`, `fusion`, `business-space`, `ai-pharma`, `resources`, `ai-application`, `ai-hardware`, `energy-storage`, `data-element`. Adapt semiconductor substitution into global semiconductor supply chains, low-altitude economy into eVTOL/aviation, and data elements into data infrastructure/governance. US examples and Canada-planned labels require independent sourcing.

## OpenStock inspected paths

All named paths exist at this SHA.

| Path | Findings and boundary |
|---|---|
| `README.md` | Dashboard, stock pages, watchlist and provider freshness concepts. Its Next.js/MongoDB/accounts/jobs stack is intentionally not adopted. |
| `MARKET_SUPPORT.md` | Reference's September 2026 testing distinguishes TradingView visuals from Finnhub backend quotes and marks Canada delayed in widgets but unsupported by Finnhub free. This is a reference claim, not verified entitlement for this project. |
| `app/(root)/dashboard/page.tsx` | Market pulse, grouped symbols, heatmap and news panels; widgets and API quotes are independent. Independently design a small dashboard using this public UX concept. |
| `components/TradingViewWidget.tsx` | Wrapper handles sizing/fullscreen and delegates widget creation to a hook. Do not copy it; independently integrate official widget documentation and attribution. |
| `lib/markets.ts` | Distinguishes market ID, timezone, symbols, TradingView prefixes and quote support. Time-of-day trading helper explicitly does not model holidays. Do not claim market-open precision without a calendar. |
| `lib/utils.ts` | Symbol-to-exchange mapping and unavailable-value formatting. Independently validate US symbols and keep TradingView symbols separate from backend tickers. |
| `LICENSE` | GNU AGPL v3. No OpenStock implementation is copied; licensing obligations have not been resolved for reuse. |

## Unsupported assumptions and acceptance limits

- Clones and SHAs are verified; provider/model credentials and live data requests are separate acceptance checks.
- Reference quote freshness, free-tier permissions, source licenses and Canadian support cannot be inherited.
- TradingView is visual-only; no heatmap-to-local-navigation guarantee or agent data extraction.
- SEC does not supply analyst consensus or market quotes. Fiscal dates differ among AAPL, MSFT and NVDA.
- Source registry breadth is not a requirement. No A-share UX, price targets, trade execution, scheduling or transaction ledger is being ported.
