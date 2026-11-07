# Stock research expansion — provider capability matrix (Phase 0)

**Status:** contract/planning baseline only; **new API endpoints, charts, earnings and studies are not yet implemented**. No live provider access was verified as part of this Phase 0 contract package. This document does not confer rights to store, redistribute, or commercialize external data.

Only the five selected capabilities are in scope: (1) OHLCV charts, (2) earnings preview/review, (3) historical earnings event studies, (4) earnings markers, (5) quarterly financial trends. US/Canada only.

| Market / capability | Candidate source | Key / entitlement | Current state in Stocker | Phase 1+ verification / fallback |
|---|---|---|---|---|
| US daily OHLCV and adjusted close | Yahoo via optional yfinance | No key; Yahoo usage rights must be reviewed | Existing adapter exposes only daily close | Verify actual source metadata, corporate actions, bar count, price basis and 1m–5y coverage. If unsupported show unavailable, never invent OHLC. |
| CA daily OHLCV (explicit `.TO`/`.V`) | Yahoo via optional yfinance | No key; terms apply | AAPL and RY.TO *close-only* probes previously documented; TSXV not confirmed | Verify CAD/listing identity and per-symbol timeframe; do not assume TSXV or Canadian quote availability. |
| US compact history alternative | Alpha Vantage | Optional key and account quota | Existing compact close history fallback; at most 100 observations | Does not satisfy multi-year event-study needs without separately verified extended access. |
| US quarterly facts | SEC EDGAR companyfacts / submissions | No key; descriptive SEC_USER_AGENT contact | **Annual 10-K contexts only**, intentionally filters quarterly out | Build separate quarter/YTD/10-Q parser preserving annual-only behavior; verify restatements, accession, units, duration and availability as-of. |
| CA quarterly facts | Permitted licensed/issuer-authorized data | Not selected | **Unavailable** | Do not scrape SEDAR+ or infer from cross-listed US symbols. |
| US upcoming earnings date | Finnhub calendar or verified issuer release; optional yfinance calendar | Finnhub key; exact endpoint entitlement **unverified** | Not wired | Verify AAPL/NVDA with configured key; distinguish confirmed from estimated; unknown timestamp stays unknown. |
| US historical actual vs consensus | Finnhub company earnings or appropriately licensed feed | Endpoint entitlement / historical coverage **unverified** | No licensed consensus feed | Never invent estimates. Compare same EPS basis, period and as-of context. Missing consensus remains a gap. |
| US release event dates | Verified issuer earnings press releases, SEC 8-K Item 2.02 evidence | SEC no key; issuer release rights per source | Existing SEC submissions list 8-K, without precise first-public earnings time | A filing date is **not** necessarily release time. Date-only evidence cannot claim precise session mapping; exclude ambiguous cases from reaction aggregates. |
| CA earnings/events | Permitted issuer-authorized/licensed feed | Not selected | **Unavailable** | Charts can succeed while earnings, study and quarterly trends are unavailable. |
| US benchmark close | SPY historical bars on identical date and price basis | Same market-history restrictions | Basic SPY history already available via existing providers | Require shared trading-day calendar, matching price adjustment basis, full window and explicit gaps. |

## Locked future data contracts

- `backend/app/contracts/stock_research.py` declares **strict additive models only**. It is not imported by existing routers and exposes no OpenAPI changes in Phase 0.
- Tickers use existing explicit symbol semantics (`AAPL`, `NVDA`, `RY.TO`, `SHOP.V`); US prices are USD; explicit Canadian listings are CAD. No automatic FX or cross-listing identity translation.
- Daily/weekly/monthly candles must disclose OHLC price basis independently from optional adjusted close. Never patch a split gap with an invented candle.
- Quarterly values are either standalone quarter, year-to-date or annual. TTM requires four consecutive fiscal quarters with evidence-backed observations for that metric; never treat YTD and EPS as interchangeable.
- Canonical earnings event ID: `MARKET:SYMBOL:earnings_release:FY<year>Q<quarter>` (e.g., `US:AAPL:earnings_release:FY2026Q2`). Reuse this across earnings cards, normalized events, and event studies.
- An upcoming earnings date is `estimated` or `confirmed`; an actual event date has `timestamp` or `date_only` precision. SEC 8-K filing-day proxies cannot silently masquerade as issuer announcement timestamps.
- Event study is user-triggered; v1 scope is historical **US earnings releases**, benchmark `SPY`, event window −5 to +20 trading days. Future calculation method is compounded close-to-close stock return minus the comparable benchmark return. No aggregate statistics with fewer than eight eligible independent completed event windows.
- Market-data failures remain unavailable in live mode. Fixture results must be explicitly synthetic and never escape into live results. No automatic LLM calls.

## Verification gate before implementation

Perform bounded, read-only provider checks (AAPL, NVDA, RY.TO; optionally SHOP.V) only when configured credentials and permitted access exist. Log fields obtained, source timestamps, symbol/currency, coverage length, exact price adjustment definition, historical earnings and consensus availability, HTTP/rate errors, and data-use restrictions. Never log private keys or raw sensitive HTTP responses.

Do not mark an untested feed as verified based solely on documentation or an API key being configured. Do not block the fixture-only tests when a live source is unavailable.

## Phase 0 test scope

The synthetic contract tests cover OHLC validation, date ordering, unsupported ranges/intervals, listing currency, no live-to-fixture mixing, unavailable/TTM shapes, canonical event IDs, EPS basis comparability, date-only vs timestamp evidence, and 7-vs-8 sample gates. Source-specific mapping, quarterly calculations, adjustments, and event-window maths belong to future phase tests.
