# Architecture

React + TypeScript + Vite talks to a loopback FastAPI REST service through `/api`. SQLite persists watchlists, simple positions, runs, stage attempts, evidence, calculations and append-only events. The backend owns credentials, provider requests, calculations and agent execution. The official TradingView widget is visual only and supplies no agent data.

Research follows profile → financials → estimates → valuation → risk → report. Each session receives distinct instructions and scoped, validated prior outputs. One OpenAI-compatible client serves all roles. The orchestrator validates schemas, evidence references and numeric calculation bindings outside the model, retries at most twice, caps risk revisits, and persists each transition. Polling exposes actual stored events. Missing data makes an analysis incomplete. A deterministic model is available only in visibly labeled fixture mode.

Providers normalize facts with unit/currency, fiscal period, publication/retrieval timestamps and stable evidence IDs. Live provider failures remain explicit; fixture fallback is never automatic. One process and SQLite suffice for local demo concurrency. Versioned additive schema initialization is used initially; incompatible future migrations require explicit migration scripts.

The existing DataService routes optional history to YFinanceHistory or Alpha Vantage without merging sources. Bank of Canada Valet uses the existing macro-signals contract and shared transport. Provider policies define per-host pacing/TTLs and a local Alpha Vantage daily budget.

U.S. equities retain SEC/Finnhub coverage. User-requested Canadian scope now includes explicit .TO/.V listings, optional daily history, CA/CAD runs/positions and no-key macro/FX. Canadian company identity, statements and current quotes stay explicitly unavailable until a permitted, verified provider exists. These gaps preserve incomplete research status. There is no SEDAR+ scraper or assumed SEC equivalence. Transaction accounting and other Later features remain roadmap items.
