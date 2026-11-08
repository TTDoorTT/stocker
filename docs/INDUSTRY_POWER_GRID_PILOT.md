# Phase 4D — Grid infrastructure SEC research pilot

- Existing `power-grid` template enables Technology, Supply Chain and Competition.
- Overview and Outlook remain guided-only. No new endpoints or database migrations.
- Approved SEC 10-K issuer examples: GEV, ETN, HUBB, PWR, NEE.
- Coverage spans examples in grid equipment, electrical products, construction and utilities. These issuers do not form a sector census.
- Topic terms and peer universe are configured in `app/contracts/industry_sources.py`.
- The current SEC allowlist, rate pacing, bounded extraction, issuer checks, duplicate filtering, citation validation and second-pass claim reviewer are reused unchanged.
- The same configured AI model performs the claim review; it is not independent verification.
- No automatic inferences about utility spending approvals, projects, interconnection timelines, customer contracts, supplier relationships or forecasts.
- GET of saved sections must remain network-free. Failed regeneration must not overwrite existing work.
- Pilot uses selected SEC filings only, not provincial utility records, FERC rate cases, project filings or Canadian-only issuers.
- Run the focused test, full backend suite, frontend CI and optional live SEC test before merge.
