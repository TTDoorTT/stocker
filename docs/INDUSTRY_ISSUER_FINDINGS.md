# Phase 5C.2 — Structured Issuer Findings

## Purpose

Preserve individual, model-screened industry research findings
and their exact SEC citations as structured data.

## Behavior

- Store claim text and cited IDs after successful claim review.
- Map each cited ID to its accepted SEC issuer.
- Classify each finding as single-issuer or multiple-issuer.
- Never infer relative performance or verified comparisons.
- Reject inconsistent citation and reviewer metadata.
- Preserve previously saved research on generation failure.

## Compatibility

- No database migration.
- No additional SEC requests or LLM calls.
- Existing saved reports remain readable.
- Existing generated answer remains unchanged.
- Frontend rendering remains unchanged in this increment.

## Next

Use structured findings to develop a side-by-side issuer
research interface with clearly distinguished disclosures,
supported comparisons, and missing comparative evidence.
