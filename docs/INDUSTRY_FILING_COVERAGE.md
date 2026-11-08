# Phase 4E — Accepted SEC filing evidence coverage

## Purpose

Stocker previously displayed the evidence table but did not explicitly summarize how many of the preselected U.S. issuers contributed accepted passages to a generated Industry Research section. An analysis from one company can be source-cited without representing an industry.

## Behavior

- The shared filing pipeline calculates coverage **only from accepted Evidence records** after SEC metadata and deterministic passage checks and before the model call.
- The existing LLM receives an explicit caveat containing the represented-issuer count; no SEC or LLM calls are added.
- The generated, validated research result stores `filing_coverage` inside its existing SQLite `result_json`. No table changes or migration.
- The UI displays accepted excerpt count, represented and missing selected issuers, and a limitation statement. Older saved reports without this field still render unchanged.
- The metric is **not** a factual quality score or a count of citations actually used in generated claims. Five selected issuers are not the whole sector. The semantic claim-review safeguard remains the same.
- Unsupported issuers, wrong-section evidence and empty evidence fail closed before generation. Failed regeneration does not replace a previous saved result.

## Contract

`filing_coverage` inside the saved result is optional for backward compatibility:

```json
{
  "selected_issuers": ["NVDA", "AMD", "INTC", "AVGO", "MU"],
  "represented_issuers": ["NVDA"],
  "missing_issuers": ["AMD", "INTC", "AVGO", "MU"],
  "accepted_excerpts": 1,
  "limitation": "Accepted SEC passages represent 1 of 5 ..."
}
```

The fields are derived from the configured issuer universe, not user input. No new route, provider host, database schema, automated verification claim, or background work is introduced.

## Tests

Run `tests/test_industry_filing_coverage.py`, existing industry generation/persistence/claim-review tests, backend Ruff + full suite, frontend Biome + typecheck + tests + build. In browser, verify a generated filing research section shows the coverage line and older saved research still renders.
