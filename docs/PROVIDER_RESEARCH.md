# Provider research — 2026-11-06

Research scope: primary documentation and limited unauthenticated HTTP probes. No project secrets, `.env`, account settings, or authenticated provider APIs were accessed. Documentation establishes a provider contract; it does not prove that this project's account has the entitlement or that a live application integration succeeds.

## Recommended provider boundaries

Use SEC for U.S. filings and financial facts, Finnhub free for supported U.S. quotes/news, an explicitly selected personal/educational Yahoo history adapter if its use conditions fit, and Bank of Canada Valet for Canadian macro/FX. Alpha Vantage and FRED can remain optional. Canadian exchange quotes and Canadian-only issuer financial statements need independent coverage decisions: neither follows automatically from U.S. support.

Do not implement a SEDAR+ scraper. This research found no documented free public financial-statements API with permission to build this app's evidence database. Licensed SEDAR+ distribution exists; a narrowly sourced issuer-report workflow is a possible later alternative, subject to the issuer's permissions and manual verification.

## SEC: identifying automated requests

SEC requires declared request headers identifying the requester; its example combines a company name and administrator contact email. The fair-access ceiling is 10 requests/second across the user, not per worker. Configure a genuine project/operator identifier and monitored email; do not generate an invented address. A university project name plus the user's genuine authorized contact is a practical identification format. Cache and pace well below the ceiling. SEC may block excessive or unidentified automation. [SEC accessing EDGAR data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), [SEC developer resources](https://www.sec.gov/about/developer-resources).

SEC exposes submissions and XBRL company-facts JSON through `data.sec.gov`; it is a filings source, not a stock-price feed. Canadian incorporation or a TSX listing alone does not establish SEC filings or company-facts availability. Map issuer identity/CIK and confirm actual filings first. [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces).

**Probe status:** SEC policy/documentation read; no financial endpoint probe was performed because this research was not supplied a genuine authorized contact identity.

## Finnhub free: actual documented coverage

The official pricing UI is rendered by JavaScript. Its first-party bundle was inspected directly after the web reader returned no page text. Its free-plan column specifies 60 calls/minute, U.S. fundamentals and estimates, profile v2, as-reported financials, key metrics, one year of company news, and 50 WebSocket symbols. Standardized statements, U.S. historical OHLC, and international TSX market data are excluded. [Finnhub pricing](https://finnhub.io/pricing), [first-party pricing UI bundle inspected on this date](https://finnhub.io/static/js/webpack/dist/main.bundle.4de77626bde75a453a2c.js).

The embedded official `window.docSchema` confirms:

| Endpoint | Documented boundary |
| --- | --- |
| `/quote` | Real-time U.S. stock quotes; international real-time requires Enterprise arrangements. |
| `/stock/candle` | Explicitly premium; do not use as a free history dependency. |
| `/stock/profile2` | Free version of company profile. |
| `/stock/metric` | Basic financial metrics; not audited statement normalization. |
| `/company-news` | North American companies; one year free history plus updates. |
| `/stock/symbol` | Provider-specific exchange symbology; symbol discovery is not data entitlement. |

[Official API documentation](https://finnhub.io/docs/api).

Therefore **do not claim free TSX/TSXV quotes or full Canadian fundamentals**. North American news documentation is broader than the pricing table's U.S. fundamentals label: test actual Canadian news symbols before claiming support. Maintain explicit endpoint/market capability flags.

**Probe status:** pricing HTML, API documentation/schema and bundle returned HTTP 200. No authenticated quote/news/candle call was made; no free-key Canadian entitlement was experimentally established.

Finnhub self-serve plans are personal-use unless otherwise stated; business use and sharing/redistribution, including derived results, require the relevant permission. A free key does not establish publication rights. [Finnhub terms](https://finnhub.io/terms-of-service).

## Yahoo Finance via yfinance: optional personal history

yfinance is an independent open-source wrapper, not an endorsed Yahoo service. Its maintainers describe research/educational intent and warn that Yahoo's API is for personal use. Apache licensing covers the software, not rights to redistribute downloaded market data. Keep a visible provider/use limitation, do not present it as a licensed production feed, and evaluate Yahoo's linked terms before broader deployment. [yfinance README and linked Yahoo terms](https://github.com/ranaroussi/yfinance).

The public Python interface is `Ticker(symbol).history(...)`. Current source documents daily `interval="1d"`, periods including `1mo`, `3mo`, `6mo`, `1y`, and explicit date bounds (`start` inclusive, `end` exclusive). `auto_adjust=True` is the default; set an explicit adjustment policy and label it. Intraday history has separate short-window limits and is unnecessary for the current daily chart. The return value is a pandas DataFrame; preserve dates, exchange timezone, currency and capture time, validate OHLCV, and sort observations before selecting the latest bar. [History method reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html), [maintainer history implementation](https://github.com/ranaroussi/yfinance/blob/main/yfinance/scrapers/history.py).

Use an explicit canonical-to-provider mapping for Canadian `.TO` and `.V` symbols and verify each returned instrument's identity/currency; do not silently transform a TSX issuer into its U.S. listing. A daily close is not a current quote. Empty history, throttling, unsupported instruments or parsing failures must yield unavailable data, not synthetic fallback. These are implementation recommendations; this research did not execute yfinance or establish Yahoo availability for any ticker.

## Bank of Canada Valet: no-key, verified IDs

Valet is free and needs neither registration nor an access key. Official guidance supports JSON/CSV/XML, discovery lists, and caching daily exchange-rate results. [Valet guide](https://www.bankofcanada.ca/valet-api-how-to/).

Actual unauthenticated public GETs on 2026-11-06 returned **HTTP 200**, parseable JSON and these source-owned definitions:

| Series | Actual response definition | Unit / frequency |
| --- | --- | --- |
| `FXUSDCAD` | Daily average exchange rate of the U.S. dollar in Canadian dollars | Canadian dollars per U.S. dollar / business daily |
| `V39079` | Target for the overnight rate, also called policy interest rate | Percent / business daily |

Reproducible URLs: [FX recent observations](https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=2), [policy-rate recent observations](https://www.bankofcanada.ca/valet/observations/V39079/json?recent=2). These are actual API responses, not fixture data or a claim of app integration.

Response contract:

```text
seriesDetail[SERIES] = {label, description, dimension, dateFormat, metadata}
observations = [{"d": "YYYY-MM-DD", SERIES: {"v": "decimal string"}}, ...]
terms.url = "https://www.bankofcanada.ca/terms/"
```

Observed `recent=2` arrays were newest first. Parse/sort by `d` rather than assuming order; handle missing values/dates, business-day gaps and series-specific publication lag. Date-bounded form is `observations/FXUSDCAD/json?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`; validate against actual HTTP response when implementing (the recent form above is the one probed).

Implementation advice: expose `V39079` as percent, not a fraction; converting USD amounts to CAD multiplies by `FXUSDCAD`, while CAD to USD divides. Keep observation date separate from HTTP capture time and show the rate is a daily average rather than executable FX pricing. No key or placeholder credential is needed. Retain attribution and the returned terms link. [Bank of Canada terms](https://www.bankofcanada.ca/terms/).

## Alpha Vantage and FRED: optional services

Alpha Vantage's current support page states a standard free limit of 25 requests/day and an additional route for **verified** open-source/educational projects. Being a student does not automatically grant that entitlement. U.S. realtime and 15-minute-delayed data are premium. [Official support](https://www.alphavantage.co/support/), [official premium page](https://www.alphavantage.co/premium/).

For the existing history adapter, `TIME_SERIES_DAILY` with `outputsize=compact` documents the latest 100 observations; full daily output and adjusted/intraday products have separate premium constraints. Do not promise a complete one-year daily chart from 100 bars. Parse API error/information messages as unavailable even when transport returns success. [Official Alpha Vantage API documentation](https://www.alphavantage.co/documentation/).

FRED API v1 requires a registered API key and specifies separate keys for applications, with each application user using their own key. This app's configured server-side integration should remain optional and follow the intended usage terms; missing FRED credentials need not disable unrelated research or Bank of Canada signals. [FRED API key documentation](https://fred.stlouisfed.org/docs/api/api_key.html).

**Probe status:** first-party documentation reviewed; no Alpha Vantage/FRED data calls, authenticated calls, trial signups or entitlement requests were made. Alpha Vantage support was available via the web reader while a separate shell fetch returned HTTP 403; that does not establish API failure.

## Canadian-only statements: SEDAR+ and alternatives

SEDAR+ public-site terms allow limited use of unaltered material under conditions, but explicitly prohibit automated scraping and building/storing its public information in databases. Educational intent does not waive those restrictions. Its linking rules also restrict deep links absent permission. Publicly visible internal endpoints are not permission to automate them. [SEDAR+ terms](https://www.sedarplus.com/onlinehelp/terms-of-use/), [CSA-hosted terms PDF](https://www.securities-administrators.ca/wp-content/uploads/2023/02/SEDAR_Terms_of_Use.pdf).

An authorized **subscription Data Distribution Service** exists. CSA's FAQ says public continuous-disclosure financial statements become available through it and directs prospective users to the service desk. The privacy statement describes licensed bulk distribution to subscribers. Neither source establishes a free public fundamentals REST API. [CSA filing FAQ](https://systems.securities-administrators.ca/onlinehelp/faqs/general-faqs-about-filings/), [CSA privacy statement](https://www.securities-administrators.ca/wp-content/uploads/2023/05/UPDATED-Privacy-Statement.pdf).

Free access to issuer-published reports is a practical alternative for a small later Canadian workflow: for example, Canadian Tire explicitly makes electronic annual/quarterly reports available on its own site and publishes downloadable annual disclosures. These establish document access, **not a general automation/redistribution licence or normalized API**. [Issuer reporting FAQ](https://investors.canadiantire.ca/English/investors/investor-resources/faqs/default.aspx?LanguageId=1), [issuer annual disclosures](https://corp.canadiantire.ca/English/investors/financials-reporting/annual-disclosures/default.aspx).

Recommended next step for Canadian-only issuers: choose a few issuers, confirm their own document-use permissions or obtain permission, then manually acquire the authorized reports and capture title, original URL, period, publication date, currency, accounting basis and exact table/page evidence. Normalize deterministically and validate extracted values against the report. Until that workflow or a licensed feed exists, show Canadian fundamentals as incomplete. SEC cross-listed coverage helps only issuers that actually file there; Yahoo summary fields are not a replacement for source financial statements.

**Probe status:** no SEDAR+ search/document endpoints were scraped or probed; no bulk download or issuer report ingestion was performed. This research does not establish a general permitted free automated Canadian-only issuer fundamentals source.
