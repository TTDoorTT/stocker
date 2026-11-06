from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.config import Settings
from app.db.repository import Repository
from app.models.api import ChatRequest, ChatResponse, ResearchRequest, ResearchRun
from app.modules.market_data.service import DataService
from app.orchestrator.engine import ResearchOrchestrator, new_run
from app.services.chat import answer_chat
from app.services.intelligence import IntelligenceService


def create_router(
    settings: Settings,
    service: DataService,
    repository: Repository,
    intel: IntelligenceService,
    executor: ThreadPoolExecutor,
    capacity: BoundedSemaphore,
) -> APIRouter:
    router = APIRouter()

    def get_run(run_id):
        try:
            UUID(run_id)
        except ValueError:
            raise HTTPException(422, "Run ID must be a UUID") from None
        run = repository.run(run_id)
        if not run:
            raise HTTPException(404, "Research run not found")
        return run

    @router.post("/api/research-runs", status_code=202, response_model=ResearchRun)
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

    @router.get("/api/research-runs", response_model=list[ResearchRun])
    def runs(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> list[dict]:
        return repository.runs(limit, offset)

    @router.get("/api/research-runs/{run_id}", response_model=ResearchRun)
    def run_detail(run_id: str) -> dict:
        return get_run(run_id)

    @router.get("/api/research-runs/{run_id}/report")
    def report(run_id: str) -> dict:
        run = get_run(run_id)
        if not run["report"]:
            raise HTTPException(409, "Report is not available; inspect run status and validation errors")
        return {"report": run["report"], "mode": run["mode"], "status": run["status"]}

    @router.get("/api/research-runs/{run_id}/events")
    def events(run_id: str) -> list[dict]:
        get_run(run_id)
        return repository.events(run_id)

    @router.post("/api/chat", response_model=ChatResponse)
    def chat(body: ChatRequest):
        try:
            return answer_chat(body, service, settings)
        except ValueError:
            raise HTTPException(
                502, "Chat output failed evidence/numeric validation; no answer published"
            ) from None

    return router
