# Financial data providers

Reconciled 2026-11-06 for Stocker, a local U.S./Canadian educational prototype. See [validation](VALIDATION.md) for actual check scope. Provider documentation, configured credentials and successful live retrieval are distinct states. Access/redistribution rights must be checked for the intended use; the application does not grant them.

| Purpose | Provider / configuration | Scope and fallback |
|---|---|---|
| U.S. company identity, filings and annual statements | SEC EDGAR; genuine descriptive `SEC_USER_AGENT` with contact email, **no API key** | Existing submissions/companyfacts normalization retained. Does not establish Canadian-only issuer coverage. Missing contact/access produces explicit gaps. |
| Quotes and company news | Finnhub free; optional `FINNHUB_API_KEY` | `/quote` documents U.S. coverage. Free TSX market data is excluded; Canadian news requires separate verification. No automatic Canadian request/entitlement assumption. `/stock/candle` is premium and unused. |
| Optional daily history | Yahoo Finance via optional yfinance extra; no key | Explicit `.TO`/`.V` Canadian listing mapping and U.S. share-class mapping; verify returned symbol/currency. Personal/educational-use limitations displayed. Unofficial access, not a licensed production or redistribution feed. |
| Alternative U.S. daily history | Alpha Vantage; optional `ALPHA_VANTAGE_API_KEY` | Compact `TIME_SERIES_DAILY`, at most 100 observations, not a guaranteed year. Remains an alternative; its key never gates application startup. Canadian symbol mapping not implemented for this adapter. |
| Optional U.S. macro | FRED; optional `FRED_API_KEY` | DGS10, FEDFUNDS, DCOILWTICO. Each missing/failed series stays unavailable independently. |
| Canadian macro and FX | Bank of Canada Valet; **no key** | FXUSDCAD (CAD per USD daily average), V39079 (target overnight rate, percent). `BANK_OF_CANADA_ENABLED=false` disables these requests. FX is shown as context, not silently applied to holdings. |
| Canadian-only company statements | No automated source enabled | SEDAR+ prohibits scraping and storing public information in databases. Official licensed distribution or issuer-authorized reports need separate arrangements. Identity/statements remain unavailable, never borrowed from a U.S. ticker. |
| Market overview / visual heatmap | Sourced SPY/QQQ ETF proxies / official TradingView | U.S. overview remains limited to these proxies. Widget values never feed agents. Canadian market-wide overview is not implemented. |
| Analyst consensus | No integrated licensed feed | Estimates stage explicitly records missing consensus. |

## History selection and installation

Install only if Yahoo's personal-use conditions suit the project:

```bash
backend/.venv/bin/python -m pip install -r backend/requirements-history.lock
backend/.venv/bin/python -m pip install -e 'backend[history]'
```

`HISTORY_PROVIDER=auto` (default) tries installed yfinance first, then configured Alpha Vantage for U.S. symbols on failure. `yfinance` or `alpha_vantage` selects just that adapter. Auto selection does not install dependencies, require a key, or use fixtures. Every returned bar identifies its actual provider/currency; no histories are merged. If neither source is usable, history returns a sanitized unavailable error while stocks, watchlists, model configuration, macro and history records remain usable.

Yahoo calls use daily `auto_adjust=False` Close values, not total returns; historical split handling is provider-specific, so the UI does not claim raw as-traded or split-unadjusted data. Alpha Vantage compact daily data remains raw daily as documented. Both are non-executable historical observations, never a live quote substitute. Yahoo cookie/timezone caches stay under ignored project `.provider-cache/yfinance`; no user-wide model/service configuration changes.

## Symbols, markets and currencies

- U.S.: `AAPL`, `MSFT`, `NVDA`, `BRK.B`, optional `US:` prefix.
- Canada: explicit Yahoo-style `RY.TO` / `SHOP.TO` for TSX, `.V` for TSXV, optional `CA:` prefix. Bare `CA:RY` and `TSX:RY` are rejected to avoid ambiguous mapping. Exact Canadian search entries are labeled **identity unverified**, not company-name search results or provider confirmation.
- An optional API market must match the symbol. Canadian stocks/runs carry `market=CA`, listing currency CAD. Canadian positions require CAD; U.S. positions require USD. P&L remains unavailable without a matching-currency sourced quote. No automatic FX conversion or USD/CAD aggregation.
- Canadian history and macro do not imply company-fundamental coverage. Cross-listed issuers can be researched under a verified U.S. ticker using its own source coverage; there is no automatic cross-listing equivalence.

## Cache, pacing and failure contracts

One transport retains fixed HTTPS hosts, 15-second request timeouts, no redirects, at most three attempts with backoff, independent per-host pacing, original fetch timestamps and per-response cache flags. Calls are currently serialized under the existing lock. There is no expired-cache fallback.

| Provider | Minimum interval | Cache TTLs | Additional bound |
|---|---|---|---|
| SEC | 0.2 seconds per host | mapping 24h; facts/submissions 6h | Below SEC's documented 10 requests/sec; global transport serialization also limits the two hosts. |
| Finnhub | 1.1 seconds | quote 60s; news 15min; search 1h | Below documented free 60 calls/min locally. Other apps using the same key share account quotas. |
| Alpha Vantage | 3 seconds | daily history 24h | Rolling local 25 network requests/24h, including retries; cache hits do not spend the budget. In-memory budget resets at process restart, so it is not an account-wide quota guarantee. |
| FRED | 0.6 seconds | 6h | Optional integration; request errors affect only that series. |
| Bank of Canada | 1 second | 6h | Conservative app policy; not a claimed provider quota. |
| yfinance | 2 seconds between adapter history operations | normalized bars 1h | Daily calls use timeout 15s, no app retry; third-party library may perform multiple internal HTTP requests. This limits adapter operations, not every Yahoo internal HTTP call. |

Transport HTTP errors, provider soft-error JSON, invalid symbols, wrong currencies, nonfinite bars and malformed responses produce explicit unavailable states. Error bodies/URLs with keys are not exposed. Provider-level throttling and request errors never select synthetic fixtures in live mode. Separate service processes do not share these in-memory caches/budgets.

`DATA_MODE=fixtures` remains fully synthetic and uses the deterministic model stub without financial-provider requests. Live mode uses the existing Strata `iq3_s` model configuration; provider selection never changes the model endpoint, key or six-stage orchestration.

## Timestamp and evidence discipline

Cache hits preserve network `fetched_at`. Observation/fiscal dates are distinct from publication dates; unknown publication dates are null. SEC filing dates use source date granularity, and companyfacts `fy` describes the filing context rather than necessarily the fact's fiscal year. Model numeric claims still require deterministic calculation/evidence bindings. Reports persist their captured inputs.

## Verified availability and remaining limits

Actual application probes on 2026-11-06 succeeded for Valet FXUSDCAD and V39079 and for yfinance AAPL/USD and RY.TO/CAD daily history, including cached fetch-time preservation. This establishes only those tested paths/symbols at that time. Installed yfinance 1.8.0 returns Mapping metadata; both Mapping and earlier dict formats are supported.

Previously recorded application probes returned SEC facts/identity/filings, Finnhub quotes/company news and Yahoo daily history for AAPL/MSFT/NVDA, plus the Valet observations above. A separate prior AAPL iq3_s run recorded six validated stages and a sourced report, while overall status remained `incomplete` for missing material evidence. Earlier timeout/token-failure diagnostics are historical attempts, not the latest acceptance state. This cleanup does not independently repeat live requests, inspect the private acceptance database or establish model-quality superiority. Alpha Vantage/FRED entitlements and TSXV history remain not independently verified. No SEDAR+ scraper, Canadian current-quote fallback or production/public redistribution rights are claimed.

Primary references: [SEC APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [SEC access policy](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data), [Finnhub docs](https://finnhub.io/docs/api), [Finnhub pricing](https://finnhub.io/pricing), [yfinance](https://github.com/ranaroussi/yfinance), [Alpha Vantage support](https://www.alphavantage.co/support/), [FRED API keys](https://fred.stlouisfed.org/docs/api/api_key.html), [Valet guide](https://www.bankofcanada.ca/valet-api-how-to/), [SEDAR+ terms](https://www.sedarplus.com/onlinehelp/terms-of-use/).
