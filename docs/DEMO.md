# Local school demonstration

Start backend and frontend using README. Default DATA_MODE=fixtures requires no keys and shows SYNTHETIC FIXTURE labels. These invented numbers exercise the application, not actual Apple/Microsoft/NVIDIA performance.

1. Open http://127.0.0.1:5173. Read the data-mode banner and SPY/QQQ ETF proxy labels. The third-party heatmap can show external market data independently of fixture mode; its prices are not passed to agents. If blocked, use its retry/fallback and nearby stock search.
2. Search AAPL, MSFT or NVDA and open a stock. Inspect quote timestamp, source and stale/delayed labels, annual facts and fiscal periods. Fixture chart bars are synthetic.
3. Add a stock to the watchlist and add a simple position with shares/average cost. Explain unrealized P&L uses a quote snapshot; no realized-return or transaction accounting is claimed.
4. Click Run Research. Open six-stage progress and execution trace. Events are actual persisted transitions; fixture stages can finish too quickly to watch sequentially. Reloading keeps the trace.
5. Open stage details to compare role context and validated outputs. Expectations explicitly lacks licensed consensus. Overall incomplete is expected and honest, even with six passing stage validations.
6. Inspect the report, cited evidence, timestamps, deterministic calculation inputs and gaps. Download Markdown. Explain that numeric prose is prohibited in model outputs; bound numeric claims and server-rendered tables provide numeric fidelity.
7. Ask a stock question in chat. Fixture mode deliberately uses a deterministic stub, not a live AI response. Chat does not start research automatically. Launch full research only with its separate action.
8. Open Research Records. Stop/restart the backend, then reopen the same run to demonstrate SQLite persistence. Interrupted queued/running runs become incomplete with a restart event.
9. Open Daily Review, news/signals and Industry Research. Missing live headlines and FRED/Valet values are unavailable in fixture mode. Explore all 20 guided topics; AI computing and semiconductors can launch representative-company analysis through the same pipeline. One company is not comprehensive sector coverage.
10. Settings lists missing configuration names, never keys. Live acceptance requires user-supplied provider/model settings; never substitute fixtures silently.

## Validation demonstration

Run backend tests to show intentionally corrupt math is rejected, validation_failed/stage_retry events occur, retry bounds hold, and RiskAgent can request one earlier-stage correction. The default demo intentionally does not manufacture a failure just for animation. The offline evaluation command is `cd backend && .venv/bin/python -m app.modules.research.evaluation`. It generates `docs/EVALUATION.json` locally from identical synthetic evidence and establishes workflow/reference validation, not a live-model quality or cost advantage. The generated output is not required for startup or tests. See [validation](VALIDATION.md).

## Live mode

Set DATA_MODE=live; the existing iq3_s endpoint/model/key remain configured server-side. A genuine SEC contact enables U.S. statements and an optional Finnhub free key enables U.S. quotes/news. Optional installed yfinance supplies daily history without an API key; Bank of Canada Valet supplies Canadian macro without a key. Alpha Vantage and FRED remain optional. Verify endpoint connectivity from WSL without editing an existing LiteLLM proxy. Restart backend, open a stock and inspect actual sources. Previous acceptance records cover Yahoo AAPL/RY.TO history, Valet FX/rate observations, SEC/Finnhub AAPL/MSFT/NVDA paths and an AAPL six-stage sourced report with incomplete coverage. These are past, scoped results; this cleanup does not rerun live acceptance. See [validation](VALIDATION.md). There is no paid consensus integration and no Canadian fundamentals support.

With real live headlines and a configured model, Industry Intelligence offers an explicit Summarize headlines action. It summarizes only captured headline text with cited evidence and timestamps; it does not retrieve full articles or start research. Fixture mode never invents news or summary results.

Optional automated walkthrough: `make smoke` with native Playwright/Chromium installed and ports 8000/5173 free; prerequisites are in [development](DEVELOPMENT.md). The existing harness checks loopback servers, restart persistence and widget failure/retry. Retained screenshots are earlier artifacts and may show the previous branding; visual perception was not rerun for this cleanup.

Partial Canadian demo: in live mode search the exact listing `RY.TO`, inspect its CAD history and explicit missing statement/quote/identity gaps, and add a CAD position (P&L remains unavailable without a matching sourced quote). Open Industry Intelligence for Bank of Canada FXUSDCAD and V39079 with original observation dates/source links. These features do not establish Canadian-only fundamentals or a licensed current quote feed.
