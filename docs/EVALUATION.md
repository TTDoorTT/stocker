# Offline workflow evaluation

Run `cd backend && .venv/bin/python -m app.services.evaluation` to regenerate [EVALUATION.json](EVALUATION.json). The command explicitly uses fixture mode and the deterministic fixture model stub. It does not call a live model, consult personal configuration files, or incur inference charges. Results are actual local executions, including measured runtime, rather than hand-entered expected scores.

Each AAPL/MSFT/NVDA case captures one synthetic company snapshot and history bundle. Both six-stage research and the single-agent baseline receive identical evidence and deterministic calculations; SHA-256 digests in the JSON verify that invariant. Every run remains `incomplete`, because synthetic data and unavailable licensed analyst consensus are explicit gaps.

The first recorded execution produced these structured-output measurements:

| Case | Strategy | Claims with valid references / claims | Numeric validation errors | Failed attempts | Retries |
|---|---|---|---|---|---|
| AAPL | Six-stage | 16 / 16 | 0 | 0 | 0 |
| AAPL | Single-agent | 1 / 1 | 0 | 0 | 0 |
| MSFT | Six-stage | 16 / 16 | 0 | 0 | 0 |
| MSFT | Single-agent | 1 / 1 | 0 | 0 | 0 |
| NVDA | Six-stage | 16 / 16 | 0 | 0 | 0 |
| NVDA | Single-agent | 1 / 1 | 0 | 0 | 0 |

Consult JSON for the actual per-run latency, unique gaps, unresolved claims, evidence hashes and timestamps. Local latency includes Python orchestration and SQLite persistence; it does not measure network or inference latency. Token usage and cost are `null`, because neither is exposed by the fixture stub. They are never estimated from text length or substituted with zero.

Citation completeness measures whether each structured claim cites existing evidence/calculation IDs. It does not establish that a narrative claim follows from its cited source. Numeric validation errors count rejected numeric claims/prose in stage validation and revalidation of accepted outputs. Unresolved claims count invalid or missing structured citations and explicit risk disputes; unique data gaps are listed separately. Failed attempts and retry/revision counts come from persisted execution records/events.

These measurements cannot establish a quality, reliability, latency or cost advantage of six agents over one live model. The stub constructs predictable outputs, and specialist stages emit more claims than the baseline stub. A meaningful future comparison requires the same configured model, source snapshot, final-report task, scoring rubric and repeated cases across both strategies, with a reviewer checking semantic support and available provider usage. This evaluation proves the comparison harness and evidence equality only.

Separate regression tests deliberately corrupt arithmetic, cite unknown evidence, repeat risk disputes, and exhaust reassessment attempts. Those tests establish validation/retry behavior; their induced failures are not mixed into this clean fixture comparison.
