from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from threading import BoundedSemaphore
from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.agents.client import ModelError
from app.core.config import Settings
from app.data.http import DataUnavailable
from app.data.service import DataService, normalize_symbol, symbol_market
from app.db.repository import Repository
from app.finance.metrics import unrealized_pnl
from app.models.api import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    PositionRequest,
    ResearchRequest,
    ResearchRun,
    SymbolRequest,
)
from app.models.market import PriceBar, Stock
from app.orchestrator.engine import ResearchOrchestrator, new_run, now
from app.services.chat import answer_chat
from app.services.intelligence import IntelligenceService
from app.services.news_summary import summarize_news


def create_app(settings=None, data=None, repo=None):
    settings = settings or Settings()
    repository = repo or Repository(settings.database_url)
    service = data or DataService(settings)
    intel = IntelligenceService(service, settings)
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="research")
    capacity = BoundedSemaphore(4)

    @asynccontextmanager
    async def lifespan(app):
        for run in repository.runs(limit=10000):
            if run["status"] in ("running", "queued"):
                run.update(status="incomplete", finished_at=now())
                run["gaps"].append("Service restart interrupted execution; launch a new run to retry.")
                repository.save_run(run)
                repository.event(
                    run["run_id"],
                    {
                        "event": "run_finished",
                        "at": now(),
                        "status": "incomplete",
                        "reason": "service_restart",
                    },
                )
        yield
        executor.shutdown(wait=True)
        if repo is None:
            repository.close()

    app = FastAPI(title="StockScope AI", lifespan=lifespan)
    app.state.repo = repository
    app.state.data = service
    app.state.settings = settings
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver", "backend"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def local_origin(request: Request, call_next):
        from fastapi.responses import JSONResponse

        origin = request.headers.get("origin")
        if (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and origin
            and origin not in ("http://127.0.0.1:5173", "http://localhost:5173")
        ):
            return JSONResponse({"detail": "Untrusted request origin"}, status_code=403)
        return await call_next(request)

    @app.exception_handler(DataUnavailable)
    async def unavailable(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.exception_handler(ModelError)
    async def model_error(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": str(exc)}, status_code=503)

    def symbol(value):
        try:
            return normalize_symbol(value)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    def get_run(run_id):
        try:
            UUID(run_id)
        except ValueError:
            raise HTTPException(422, "Run ID must be a UUID") from None
        run = repository.run(run_id)
        if not run:
            raise HTTPException(404, "Research run not found")
        return run

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> dict:
        return {
            "status": "ok",
            "mode": settings.data_mode,
            "model_configured": bool(settings.llm_model),
            "model_id": "fixture-stub" if settings.data_mode == "fixtures" else settings.llm_model,
            "missing_configuration": [
                key
                for key, value in {
                    "LLM_MODEL": settings.llm_model,
                    "SEC_USER_AGENT": settings.sec_user_agent,
                    "FINNHUB_API_KEY": settings.finnhub_api_key,
                    "ALPHA_VANTAGE_API_KEY": settings.alpha_vantage_api_key,
                    "FRED_API_KEY": settings.fred_api_key,
                }.items()
                if not value
            ],
            "limitations": [
                "Canada: optional daily history and Valet macro; statements and Finnhub quotes unavailable",
                "No licensed consensus",
                "Loopback local use only",
            ],
        }

    @app.get("/api/stocks/search")
    def search(q: str = Query(min_length=1, max_length=80)) -> list[dict[str, str]]:
        return service.search(q)

    @app.get("/api/markets/overview", response_model=list[Stock])
    def overview():
        return service.overview()

    @app.get("/api/stocks/{ticker}", response_model=Stock)
    def stock(ticker: str, market: Literal["US", "CA"] | None = None):
        ticker = symbol(ticker)
        if market and market != symbol_market(ticker):
            raise HTTPException(422, "Market does not match the explicit listing symbol")
        return service.stock(ticker)

    @app.get("/api/stocks/{ticker}/history", response_model=list[PriceBar])
    def history(ticker: str, range: Literal["1m", "3m", "1y"] = "1y"):
        return service.history(symbol(ticker), range)

    @app.get("/api/watchlist")
    def watchlist() -> list[dict[str, str]]:
        return repository.query("SELECT symbol FROM watchlist ORDER BY symbol")

    @app.post("/api/watchlist", status_code=201)
    def add_watchlist(body: SymbolRequest) -> dict[str, str]:
        repository.query("INSERT OR IGNORE INTO watchlist VALUES (?)", (body.symbol,))
        return {"symbol": body.symbol}

    @app.delete("/api/watchlist/{ticker}")
    def delete_watchlist(ticker: str) -> dict[str, bool]:
        repository.query("DELETE FROM watchlist WHERE symbol=?", (symbol(ticker),))
        return {"deleted": True}

    @app.get("/api/positions")
    def positions() -> list[dict]:
        rows = repository.query("SELECT * FROM positions ORDER BY id DESC")
        for row in rows:
            try:
                quote = service.stock(row["symbol"]).quote
                if quote and quote.currency != row["currency"]:
                    quote = None
            except DataUnavailable:
                quote = None
            row.update(
                quote_price=quote.price if quote else None,
                unrealized_pnl=unrealized_pnl(
                    row["shares"], row["average_cost"], quote.price if quote else None
                ),
                mode=settings.data_mode,
                quote=quote.model_dump(mode="json") if quote else None,
            )
        return rows

    @app.post("/api/positions", status_code=201)
    def add_position(body: PositionRequest) -> dict:
        repository.query(
            "INSERT INTO positions(symbol,shares,average_cost,currency) VALUES (?,?,?,?)",
            (body.symbol, body.shares, body.average_cost, body.currency),
        )
        return {"saved": True}

    @app.delete("/api/positions/{position_id}")
    def delete_position(position_id: int) -> dict[str, bool]:
        if position_id <= 0:
            raise HTTPException(422, "Position ID must be positive")
        repository.query("DELETE FROM positions WHERE id=?", (position_id,))
        return {"deleted": True}

    @app.post("/api/research-runs", status_code=202, response_model=ResearchRun)
    def start_research(body: ResearchRequest) -> dict:
        industry = None
        if body.industry_slug:
            try:
                industry = intel.industry(body.industry_slug)
            except KeyError:
                raise HTTPException(404, "Industry template not found") from None
        if not capacity.acquire(blocking=False):
            raise HTTPException(429, "Local research queue is full; wait for an existing run")
        run = new_run(body.symbol, settings, body.strategy)
        if industry:
            run["industry"] = industry
        repository.save_run(run)

        def execute():
            try:
                ResearchOrchestrator(repository, service, settings).execute(run["run_id"])
            finally:
                capacity.release()

        executor.submit(execute)
        return run

    @app.get("/api/research-runs", response_model=list[ResearchRun])
    def runs(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> list[dict]:
        return repository.runs(limit, offset)

    @app.get("/api/research-runs/{run_id}", response_model=ResearchRun)
    def run_detail(run_id: str) -> dict:
        return get_run(run_id)

    @app.get("/api/research-runs/{run_id}/report")
    def report(run_id: str) -> dict:
        run = get_run(run_id)
        if not run["report"]:
            raise HTTPException(409, "Report is not available; inspect run status and validation errors")
        return {"report": run["report"], "mode": run["mode"], "status": run["status"]}

    @app.get("/api/research-runs/{run_id}/events")
    def events(run_id: str) -> list[dict]:
        get_run(run_id)
        return repository.events(run_id)

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(body: ChatRequest):
        try:
            return answer_chat(body, service, settings)
        except ValueError:
            raise HTTPException(
                502, "Chat output failed evidence/numeric validation; no answer published"
            ) from None

    @app.get("/api/daily-review")
    def daily_review() -> dict:
        return intel.daily_review()

    @app.get("/api/intelligence/news")
    def news() -> dict:
        return intel.news()

    @app.post("/api/intelligence/news/summary", response_model=ChatResponse)
    def news_summary():
        try:
            return summarize_news(service, settings)
        except (DataUnavailable, ModelError):
            raise
        except ValueError:
            raise HTTPException(
                502, "Headline summary failed evidence validation; no summary published"
            ) from None

    @app.get("/api/intelligence/signals")
    def signals() -> dict:
        return intel.signals()

    @app.get("/api/industries")
    def industries() -> list[dict]:
        return intel.industries()

    @app.get("/api/industries/{slug}")
    def industry(slug: str) -> dict:
        if len(slug) > 60:
            raise HTTPException(422, "Industry slug too long")
        try:
            return intel.industry(slug)
        except KeyError:
            raise HTTPException(404, "Industry template not found") from None

    return app


app = create_app()
