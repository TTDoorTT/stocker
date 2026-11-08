# Industry Research — Phase 3D.2 automated evidence-quality gate

This is an additive **generation-time** quality gate for AI Computing's Technology, Supply Chain, and Competition research. It does not require the 24-row human-review worksheet from Phase 3D.1.

## Architecture

- `market_data/filing_excerpt.py` (Phase 3C) continues to own SEC retrieval, bounded passage selection, topic ranking, and source caching. **Unchanged.**
- New `intelligence/filing_quality.py` screens captured passages without network or model access. It checks matching topic metadata, whether the matched phrase actually appears in the text, minimum text richness, near duplicates within the same issuer, and a short denylist of obvious instruction-like phrases. It also balances accepted candidates across issuers.
- `intelligence/filing_section.py` first verifies filing form, issuer, allowlisted SEC URL and dates, then screens the passages, then produces existing typed `Evidence` records. Evidence IDs, existing generation APIs, and SQLite storage are unchanged.
- Rejected-source counts and reasons are added to research `gaps`. Nothing is generated on GET. If all usable evidence is rejected, POST generation fails before the LLM is invoked. Previously saved notes remain intact.

## Important limitations

- **This is heuristic quality screening, not source-grounded semantic verification.** An accepted excerpt can still be incomplete, misleading, wrong, or fail to support a model's interpretation. Citation IDs only establish that the model cited a captured record.
- Neither the source context nor SEC Item boundaries are independently verified by these tests. Manual checking of a generated claim remains appropriate for consequential financial decisions.
- Instruction-pattern detection is narrow and not an exhaustive prompt-injection defense; captured content always remains untrusted model input.
- A single issuer can provide sufficient material for a cautious issuer-disclosure note; the result explicitly reports that it is not industry-wide consensus.
- Rejection criteria can reject useful short excerpts (false negatives). Preserve the original SEC excerpt preview for debugging.
- This phase intentionally does not introduce new LLM calls, a new model, a database migration, frontend controls, or new API endpoints.

## Automated acceptance tests

- Valid legacy and Phase 3C passages retain original SEC links and text.
- Topic/text mismatches, duplicate/low-information excerpts, obvious instruction-like snippets, foreign URLs and impossible filing chronology are excluded.
- Generated research retains citation IDs and company attribution.
- An all-rejected evidence set prevents calling the LLM and leaves the previously saved note untouched.
- Full app architecture, Ruff, backend unit tests, frontend CI, TypeScript and production build must pass before merge.

## Files

- New: `backend/app/modules/intelligence/filing_quality.py`
- Updated: `backend/app/modules/intelligence/filing_section.py`
- New: `backend/tests/test_industry_filing_quality.py`
- This documentation file.
