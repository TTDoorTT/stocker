# Phase 3D.3 — Model-assisted claim screening

## Scope

On explicit AI Computing **Technology**, **Supply Chain**, and **Competition** generation only:

1. Capture and quality-screen live SEC filing excerpts (Phase 3D.2).
2. Generate a short, cited report with the existing research model.
3. **Before saving**, validate the report JSON and citation IDs with the existing research validator.
4. Send the validated claim text and **only its cited issuer excerpts** through a second bounded model call using `claim_review.md`, the same configured model, and **no tools**.
5. Require one reviewer decision for each claim, the exact original cited evidence IDs, and a `supported` response for every claim. Any missing, invalid, inconclusive, or negative judgment fails closed, leaving a previous saved report intact.
6. Persist `claim_review` metadata describing the result as `model_screened`, **never `verified`**.

The Overview, RSS highlights, standalone Company Research, quote and earnings routes, and all GET endpoints retain their previous behavior. No SQLite migration, new API endpoint, or extra credentials required.

## Limitations

- The *same model* may review its own output. This is not independent checking, a guarantee of factual truth, or proof of semantic entailment.
- The reviewer sees only short keyword-selected SEC excerpts and can miss absent qualifiers or document context.
- Evidence remains issuer-reported, not independently corroborated.
- The second call adds latency and uses additional local LLM budget. A model timeout, malformed response, or unsupported finding prevents a new save.
- Numeric claims remain prohibited; this check does not enable market share, forecasting, price targets, or investing advice.
- The `claim_review` object is saved for traceability; the frontend need not render it until a separate design milestone.

## Automated regressions

`backend/tests/test_industry_claim_review.py` covers supported/rejected/inconclusive output, citation substitution, duplicate/missing judgments, unsafe evidence, opt-in behavior, and claim count limits. Existing tests ensure failed regeneration preserves the prior saved result.

Use fixture-mode CI for structural regression tests. Separately generate a **single live** Technology/Supply Chain/Competition note and confirm the second LLM review runs and its metadata is persisted. This is not a substitute for source inspection when accuracy matters.
