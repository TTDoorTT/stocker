# Stocker

Local educational stock research for U.S. companies, with partial Canadian support. Stocker combines a React workspace, six specialist research stages, source-linked deterministic calculations and saved reports in SQLite. It runs locally with Docker; synthetic fixture mode needs no credentials.

## Quick start

Install Docker with Compose (on WSL2, enable your distribution's Docker integration), then:

```bash
git clone https://github.com/TTDoorTT/stocker.git
cd stocker
docker compose up --build -d
```

Open **http://localhost:5173**. Interactive API docs: **http://localhost:8000/docs**. First startup builds dependencies. For later starts use `docker compose up -d`; stop with `docker compose down`, which retains the database volume. If `.env` already exists, its settings take precedence: preserve it and check the UI's data-mode banner.

## What works

- Stock search, company views, daily history, SPY/QQQ ETF proxies and an isolated official TradingView heatmap.
- Watchlists and simple USD/CAD position snapshots with unrealized P&L when a matching quote exists.
- Profile → financials → expectations → valuation → risk → report, with independent validation, bounded retries and a persisted execution trace.
- Stock-context chat, research history and Markdown report downloads.
- Limited daily review/news, explicit headline-only live summaries, optional macro indicators and 20 guided industry topics.

`DATA_MODE=fixtures` is the default: invented, visibly **synthetic** data and a deterministic model stub exercise the workflow. The independent TradingView widget uses external data and may be blocked without preventing research. `DATA_MODE=live` uses configured providers/model and never silently falls back to fixtures.

## Configuration

The root `.env` is optional. For live use, copy `.env.example` only if `.env` does not already exist, then configure the desired server-side variables. A genuine `SEC_USER_AGENT` enables SEC access; `FINNHUB_API_KEY` enables authorized U.S. quotes/news; `LLM_BASE_URL`, `LLM_MODEL` and, where required, `LLM_API_KEY` select an OpenAI-compatible model outside Docker. Optional Yahoo daily history and Bank of Canada macro need no key; Alpha Vantage and FRED are optional alternatives/additions.

Recreate the backend after changing settings. Keep credentials out of frontend `VITE_*` variables. See [development](docs/DEVELOPMENT.md) for native setup, exact configuration, model networking and safe backups, and [providers](docs/DATA_PROVIDERS.md) for coverage and access limits.

## Limitations

This is local educational software, not a hosted multiuser service or investment advice. Synthetic results are not financial facts. Six validated stages can still produce an overall `incomplete` run when material evidence is missing.

A previous live AAPL run recorded all six validated stages and a sourced report; it is historical acceptance evidence, **not independently rerun for this cleanup** or proof of general model accuracy. Licensed consensus, interim/TTM coverage, peer comparisons and other evidence remain incomplete. Annual ratios are not TTM; there are no trading actions or target-price features.

Canadian support covers explicit `.TO`/`.V` daily-history mapping, CAD positions and Bank of Canada context. Canadian fundamentals/current quotes and automatic currency conversion are unavailable; TSXV history has not been live-probed. Market-data access and redistribution depend on provider rights. Widget prices never feed agents.

## Tests

```bash
make check
```

Runs isolated fixture tests, Ruff/Biome lint and formatting, strict TypeScript and a production build without live credentials. Current verified baseline: **150 backend / 21 frontend tests**. [Validation](docs/VALIDATION.md) separates reproducible checks, actual CI evidence and external acceptance limits.

## Docs

- [Development and configuration](docs/DEVELOPMENT.md)
- [Architecture](docs/ARCHITECTURE.md) and [API](docs/API.md)
- [Data providers](docs/DATA_PROVIDERS.md)
- [Fixture demo](docs/DEMO.md) and [industry topics / attribution](docs/INDUSTRIES.md)
- [Future work](docs/ROADMAP.md)

Vibe Research (MIT) inspired the methodology/topic concepts; its attribution is retained in the industry guide. OpenStock (AGPL) was conceptual reference only; no implementation was copied. The official TradingView embed retains its attribution and terms.
