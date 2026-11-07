# Industry Research Phase 3B — filing-backed sections

## Scope

This increment extends the existing AI Computing workspace with **explicit, on-demand** generation of three sections:

- `technology`: passages tagged artificial intelligence, semiconductor, accelerator, advanced packaging, high bandwidth memory, or data-center topics.
- `supply-chain`: passages tagged supply chain, manufacturing, advanced packaging, or customer demand.
- `competition`: passages tagged competition, risk factors, or customer demand.

`overview` remains on its existing SEC XBRL / filing-metadata / RSS route. `outlook` and the other nineteen industries remain guided-only. Nothing is generated when a page or saved note is opened.

## Architecture

1. The existing `DataService.sec_filing_excerpts(year)` owns SEC retrieval and returns at most three recent 10-K documents with three short matched passages per document.
2. The new `intelligence/filing_section.py` adapter validates the SEC primary-document URL, ticker, filing form, filed/fetched dates, excerpt length, and section-specific matched term. It converts up to nine candidate passages into immutable typed `Evidence` records with stable IDs and original SEC URLs. It does **not** call an LLM or fetch networks.
3. The existing `IndustryResearchService.generate()` uses that public DataService callback when users explicitly generate Technology, Supply Chain, or Competition. Its existing `summarize_captured_headlines` routine performs strict JSON-schema validation, evidence-ID matching, and restrictions against numeric prose.
4. After valid output, the existing `industry_research_sections` SQLite table stores the result, original source snapshot, model ID, and timestamp. Failed generation never overwrites a previous saved section.
5. GET `/api/industries/{slug}/sections/{section}` reads SQLite, never SEC or the LLM. The existing POST endpoint is reused with no OpenAPI change.

## Limitations, not optional

- These are **issuer-disclosure notes**, not independently verified industry research. Keyword excerpts are not verified SEC Item boundaries and may omit vital surrounding context.
- A citation ID means the report references the supplied excerpt; it does **not** guarantee every interpretation is semantically entailed by the passage. Human comparison to the original SEC filing is required.
- The existing filing extractor picks the **first few matches per document**. This can skew topics and leave sections with zero relevant excerpts. An unavailable-data result is correct in that case; do not fall back to the model's training data.
- The excerpt sample is bounded and may not correspond to the chosen calendar-year SEC XBRL frame.
- Source URLs are allowlisted to original SEC EDGAR filing documents. Never allow arbitrary user-supplied fetch targets.
- Source excerpts may contain adversarial instructions; they are untrusted text inside the research request.
- Model output is deliberately qualitative. Financial values, rankings, market shares, causal claims, forecasts, and trading recommendations are not generated here.
- Staleness is age-based after seven days for these sections; reading saved research does not recheck live SEC filings.
- Live generation depends on a working model and permissibly accessible SEC documents. Unit tests use mock model/provider responses, not live SEC.

## Before merging

- Run the backend architecture tests and full fixture-mode suite.
- Run Ruff check and Ruff format --check.
- Run frontend Biome CI, typecheck, tests, and production build.
- Exercise a live section in AI Computing, inspect the actual excerpt against the original 10-K, confirm the model cites the correct passage, and verify failed regeneration preserves the previous note.
- PR #16 (filing excerpts) is already merged. Base the Phase 3B branch directly on the latest `main`.
