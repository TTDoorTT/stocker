# Industry Research Workspace — initial pilot

## Shipped in this increment

- Every industry from `fixtures/industries.json` opens at `/industries/<slug>`.
- Each workspace provides Overview, Technology, Supply Chain, Competition and Outlook tabs.
- The existing representative-company six-stage run can still be launched from the workspace.
- The AI Computing Overview tab exposes the existing SEC evidence preview and supports **explicit, on-demand** qualitative source-backed AI notes.
- All industry/section cache reads are local SQLite reads. Generation does not run on navigation.
- The last **validated, successfully generated** Overview survives navigation and backend restarts.
- Regeneration does not delete an earlier result if capture, the model, or validation fails.
- The saved record contains the actual captured SEC/RSS source snapshot, rendered answer, evidence, model ID, timestamp and RSS content fingerprint.
- Staleness means that currently cached AI/semiconductor RSS news changed, or the saved note is older than seven days. It does **not** imply that SEC sources have been rechecked.

## Explicit non-goals and caveats

- The remaining 19 industries and the other four tabs offer methodologies only; there are no invented results.
- The SEC peer list (NVDA, AMD, INTC, AVGO, MU) is illustrative and does not prove industry-wide coverage.
- Source capture uses SEC XBRL Frames, filing **metadata**, and publisher RSS excerpts; it does not read full filings or articles.
- The model cannot independently search the internet or retrieve new sources during this stage.
- Model output is deliberately qualitative and constrained by Stocker's existing `ReportOutput` schema, evidence IDs and validation. Exact SEC amounts belong in the evidence table rather than generated prose. This validator does not prove that every cited sentence is semantically entailed by its source; human review is still required.
- No automatic market share, valuation forecasts, investment recommendations, or supply-chain relationship assertions.
- Citation URLs and SEC access remain subject to data availability and provider policies.

## Endpoints

| HTTP | Endpoint | Purpose |
|---|---|---|
| GET | `/api/industries` | All existing templates |
| GET | `/api/industries/{slug}` | One template |
| GET | `/api/industries/{slug}/sections/{section}` | Saved section; no model call |
| POST | `/api/industries/{slug}/sections/{section}/generate` | Model generation — currently `ai-computing` / `overview` only |
| GET | `/api/industries/ai-computing/evidence` | Existing SEC evidence preview |

Valid sections: `overview`, `technology`, `supply-chain`, `competition`, `outlook`.

## Ownership

- `intelligence/industry_research.py` owns section orchestration and persistent storage.
- `market_data/service.py` continues to own SEC retrieval. Intelligence only calls its public service facade.
- `research/service.py` provides the existing source-linked report validation interface.
- `frontend/features/intelligence/api.ts` alone imports the generic HTTP request client.
- SQLite table `industry_research_sections` is distinct from the existing research run and RSS highlight tables.

## Future work

1. Expand sanctioned source retrieval to full SEC filing text with disclosure of content vs metadata.
2. Create section-specific validation and distinct research evidence contracts (technology/supply chain/competition).
3. Add background generation status and cancellation if local model latency becomes material.
4. Add an explicit per-section audit/review path before treating model output as verified facts.
