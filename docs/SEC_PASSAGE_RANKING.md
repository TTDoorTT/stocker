# Industry Research — SEC passage ranking (Phase 3C)

## Scope

- An explicitly requested SEC filing excerpt fetch continues to use existing Market Data ownership and pacing.
- Reads at most five selected 10-K primary filing documents (one per selected peer), each capped at 8 MB.
- Extracts text from a bounded window and excludes HTML head/script/style/noscript contents.
- Recognizes common `Item 1`, `Item 1A`, `Item 7`, `Item 7A` **heading cues** when they appear in short blocks; these are *not* verified SEC Item boundaries.
- Independently scores Technology, Supply Chain and Competition evidence using deterministic keyword matching.
- Returns up to two distinct excerpts per topic and issuer, at most 30 excerpts total. Within-topic near-duplicate passages are removed.
- Interleaves issuers per topic so downstream evidence selection doesn't over-represent the first filing.
- The existing response keys (`matched_term`, `text`, `symbol`, `source_url`, `filed`, `fetched_at`, `cached`) remain intact. Additional `topic`, `section_hint`, and `relevance_score` fields are advisory.
- Uses the existing in-memory 24-hour response cache; this is **not** SQLite storage of entire filing text.

## Safety and limitations

- No LLM runs when excerpts are loaded. The existing explicit research generation is unchanged.
- Snippets are literal excerpts with a limited context window; they are **not** verified complete paragraphs or filings.
- A term match, ranking score, or inferred heading does not establish a financial fact, legal conclusion, company relationship, or broader industry condition.
- No arbitrary URL fetch; only primary SEC document URLs derived from the submissions snapshot are allowed. No redirects are followed.
- No source annotations prove that every displayed sentence is semantically supported. Human review remains necessary.
- At most the first 2.4 million characters of extracted visible text are considered. Later content can be missed.
- Additional documents increase work per explicit request; keep SEC request pacing and User-Agent configuration in place.
- The full 10-K document and its excerpts must not be mistaken for licensed third-party research.

## Acceptance checks

- `ruff check`, `ruff format --check`, backend fixture suite and architecture tests pass.
- Offline tests establish topic diversity, source diversity, duplicate removal, unsafe URL blocking, fixture mode, and caching.
- Verify excerpts against actual original SEC filings in live mode before relying on the research summary.
- Ensure a user can load saved Technology/Supply Chain/Competition research without any new SEC or LLM calls.
- Existing Industry Overview, RSS, and Company Research remain unchanged.
