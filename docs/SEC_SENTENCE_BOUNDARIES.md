# Phase 5B — SEC Passage Boundary Improvements

## Purpose

Improve the completeness of keyword-selected SEC filing excerpts.

The previous extractor selected arbitrary 360-character windows, sometimes
beginning or ending mid-word or omitting important qualifications.

## Implementation

- Prefer complete sentence-shaped passages from original filing text.
- Preserve adjacent sentences and risk qualifiers when they fit.
- Skip overlong sentences rather than silently truncating them.
- Preserve the existing 360-character maximum.
- Retain source URLs, topic matching, relevance ranking, caching,
  issuer balancing, and bounded SEC retrieval.

## Limitations

Sentence detection is heuristic. Unusual HTML formatting and abbreviations
may still produce imperfect boundaries.

These are not verified SEC Item boundaries.

Discarding overlong or incomplete passages may reduce source coverage.
Compare accepted issuer and cited issuer coverage with the previous
implementation before wider deployment.

No saved reports are changed unless the user explicitly regenerates them.
