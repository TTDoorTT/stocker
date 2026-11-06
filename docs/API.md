# Stocker local API

Base URL `http://127.0.0.1:8000/api`; OpenAPI interactive contracts at `/docs`. All configuration credentials stay server-side. Mutations accept JSON. Supported listing markets are US and CA (.TO/.V suffixes); Canadian fundamentals/current quotes remain unavailable; invalid requests return 422, unknown run IDs 404, missing providers 503, unavailable reports 409, full research queue 429. The local queue holds at most four jobs with one worker.

- `GET /health`: data mode, model ID/configuration status and missing variable names, never keys.
- `GET /stocks/search?q=AAPL`: at most 20 provider/fixture results.
- `GET /stocks/{symbol}?market=US|CA` (market optional; must match listing): normalized profile, facts, evidence, quote, gaps.
- `GET /stocks/{symbol}/history?range=1y`: provider-labeled daily bars with currency and limitations; selected via HISTORY_PROVIDER. Alpha Vantage compact covers at most 100 observations, not a guaranteed year. Ranges 1m/3m/1y.
- `GET /markets/overview`: SPY/QQQ explicitly treated as ETF proxies.
- `GET/POST /watchlist`, `DELETE /watchlist/{symbol}`; POST `{symbol}`.
- `GET/POST /positions`, `DELETE /positions/{id}`; POST `{symbol,shares,average_cost,currency:"USD"|"CAD"}`. Simple position snapshots, no realized P&L or transaction ledger. Currency must match listing; missing/mismatched quotes produce null unrealized P&L. No automatic FX conversion.
- `POST /research-runs`: `{symbol,strategy:"multi"|"single",industry_slug?:string}`, 202 with saved run ID. Multi is the six-stage workflow; single is an evaluation baseline.
- `GET /research-runs?limit=50&offset=0`, `GET /research-runs/{id}`, `GET /research-runs/{id}/events`, `GET /research-runs/{id}/report`: saved artifacts and timestamped real execution trace. Poll detail/events every 1.5 seconds while queued/running. Stages can pass while overall analysis is incomplete due to missing data.
- `POST /chat`: `{symbol,message}`; stock-context answer with validated evidence/numbers. Does not launch research. Fixture mode returns a visibly labeled deterministic stub.

Saved provider keys are never returned. Local AI settings accept validated OpenAI-compatible endpoints; public unauthenticated hosting remains unsupported.

Selected intelligence APIs:

- `GET /daily-review`: timestamped SPY/QQQ ETF proxy returns and source calculations, headlines and explicit coverage gaps. No inferred market session or whole-market breadth.
- `GET /intelligence/news`: `{mode,items,gaps,fetched_at}`. Items retain headline, source URL/name, published/fetched timestamps and ticker tags. Coverage is limited and missing headlines are not invented.
- `GET /intelligence/signals`: three optional FRED plus two no-key Bank of Canada Valet series descriptors (Valet can be disabled) with null unavailable observations or genuine source series. Observation date differs from publication date; freshness is explicit.
- `GET /industries`, `GET /industries/{slug}`:20 guided topics with prompt, representative symbols and limitations. Optional industry_slug on a research run adds this question to the existing six-stage company workflow; it does not establish comprehensive industry coverage.

- `POST /intelligence/news/summary`: explicit headline-only AI summary of at most12 retrieved live headlines, using the shared model client and evidence validation. Returns `{answer,evidence,mode,gaps}`; fixture mode/missing model/no headlines =>503, invalid unsupported model output =>502. Never auto-launches research or treats article contents as retrieved.

Canadian exact-symbol search results are explicitly unverified listing candidates, not verified company identity. Live stock objects and research runs retain CA market metadata; unsupported fundamentals and quotes remain explicit gaps. Fixture mode remains the original synthetic U.S. demo with no fabricated Canadian fixtures.

The complete contract is protected by `backend/tests/contracts/openapi.json` and its API regression test. The Stocker cleanup changes only OpenAPI `info.title`; routes, request/response schemas and error contracts are preserved.

## AI configuration

- `GET /settings/ai`: `{base_url,model_id,has_api_key,configured,source}`; source is `environment` or `saved`. No key value.
- `POST /settings/ai/test`: `{base_url,model_id,api_key?:string|null}`; small bounded chat-completion request, returns `{ok,message}`. Never saves. HTTP failures/provider bodies are sanitized. A successful probe verifies connectivity/model access, not research quality.
- `POST /settings/ai`: same request shape; persists atomically and returns status. Applies to new operations immediately. UI requires a successful test of the current fields first; API clients may save directly.
- `DELETE /settings/ai`: removes the saved override and returns environment status. Does not edit `.env`.

Omitted/null `api_key` retains the effective key only for the same endpoint; an empty string explicitly clears it. A changed endpoint requires an explicit key or empty string. Requests reject embedded URL credentials, query/fragment and non-HTTPS URLs except the existing loopback/link-local IPv4 allowance and exact `host.docker.internal` HTTP hostname. Invalid fields return sanitized 422 errors. Settings responses use `Cache-Control: no-store`; existing host/origin checks apply. Storage failures return 503 and keep active settings unchanged. Fixtures and financial provider settings remain independent.
