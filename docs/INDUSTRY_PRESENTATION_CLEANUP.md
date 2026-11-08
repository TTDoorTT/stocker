# Phase 5C.4 — Research Presentation Cleanup

## Objective

Avoid displaying the same model-screened findings twice.

## New reports with structured issuer findings

- Present issuer-attributed findings first.
- Keep the original AI-generated narrative in an expandable section.
- Keep all detailed data limitations in an expandable section.
- Display the limited-source and independent-verification warning
  even while details are collapsed.
- Preserve the complete captured evidence table.

## Existing reports

- Saved reports without structured issuer findings retain their
  previous narrative and limitations presentation.
- Existing research contents and SQLite records are unchanged.

## Constraints

No additional SEC requests or LLM calls.
No database migrations or new API endpoints.
No change to claim review, citation validation, or source attribution.
