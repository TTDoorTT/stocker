# Phase 5C.3 — Issuer Findings Interface

## Purpose

Display structured, model-screened issuer findings alongside
saved industry research.

## Behavior

- Show issuer-specific claims in a searchable-by-eye table.
- Display exact cited SEC evidence IDs and filing links.
- Keep multiple-issuer citations in a separate section.
- Never classify multi-issuer citations as verified comparisons.
- Hide the structured view for older reports without issuer_findings.
- Preserve the original generated research answer.
- Make no additional SEC or AI requests while viewing saved research.

## Security

Only explicitly shaped SEC EDGAR document URLs become citation links.
Unrecognized URLs are rendered without navigation.

## Limitations

Model-screened statements are not independently verified.
Cross-company technical and performance comparisons are not inferred.

This is a frontend-only change with no database migration.
