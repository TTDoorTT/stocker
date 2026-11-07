# Industry Research — SEC Filing Excerpts pilot

This increment retrieves a **small, bounded sample of literal text** from recent SEC 10-K primary filings. It is separate from AI analysis.

## Scope

- `GET /api/industries/ai-computing/filing-excerpts?year=2025`
- For selected AI Computing peers, derive the latest 10-K primary-document URLs from SEC submissions (the existing read-only evidence service).
- Permit **only** SEC Archive links matching the allowlisted primary-document structure; no client-supplied URLs.
- Fetch at most 3 documents, no more than 8 MB per document, cache successful responses in memory for 24 hours; throttle with the existing SEC provider lock.
- Normalize rendered HTML into plain text and extract at most 3 short keyword-matched passages per filing (360 characters maximum each), with source URL, filing date, and fetch timestamp.
- Show exact matched passages and links on the AI Computing Overview workspace, only when the user clicks **Load SEC filing excerpts**.
- Report permission errors, unsupported formats, oversized filings, and missing 10-K documents as gaps. Never fabricate excerpts.
- Fixture mode performs **no network calls** and shows a clear limitation.
- User-Agent still comes from the existing genuine `SEC_USER_AGENT` configuration.

## Data-quality limits

- Keyword matches **are not verified 10-K Item sections**, validated claims, a complete filing read, or proof of supply-chain relationships.
- Some Inline XBRL pages exceed the size limit, have non-HTML documents, or reject scripted access; a gap is preferable to bypassing access controls.
- The selected latest 10-K may have a filing date different from the financial frame year.
- No company, industry, growth, or competitive claim can be inferred from these excerpts without further validation.
- Nothing retrieved through this endpoint is sent to the LLM. A subsequent milestone can add vetted excerpts as cited evidence after live-source QA.
- Source contents are treated as untrusted text and rendered as plain React text nodes; they are never inserted as HTML.

## Source access

The SEC publishes public EDGAR materials for free but requires fair automated access: identifiable User-Agent, moderate requests, and the current ceiling of 10 requests/second aggregated per user. Stocker deliberately uses much lower pacing and a bounded document count. SEC access may still be denied by its automated-access defenses.

Official documentation: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
