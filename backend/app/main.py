from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from threading import BoundedSemaphore

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.agents.client import ModelError
from app.core.config import Settings
from app.core.database import Repository
from app.models.api import (
    HealthResponse,
)
from app.modules.intelligence.router import create_router as intelligence_router
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.router import create_router as market_router
from app.modules.market_data.service import DataService
from app.modules.portfolio.repository import PortfolioRepository
from app.modules.portfolio.router import create_router as portfolio_router
from app.modules.portfolio.service import PortfolioService
from app.modules.research.router import create_router as research_router
from app.orchestrator.engine import now
from app.services.intelligence import IntelligenceService


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

    app.include_router(market_router(service))
    portfolio = PortfolioService(PortfolioRepository(repository), service, settings)
    app.include_router(portfolio_router(portfolio))
    app.include_router(research_router(settings, service, repository, intel, executor, capacity))
    app.include_router(intelligence_router(settings, service, intel))
    return app


app = create_app()
