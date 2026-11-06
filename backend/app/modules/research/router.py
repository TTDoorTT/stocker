from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.contracts.api import ChatRequest, ChatResponse, ResearchRequest, ResearchRun
from app.modules.research.errors import IndustryNotFound, ResearchQueueFull, RunNotFound
from app.modules.research.service import ResearchService


def create_router(service: ResearchService) -> APIRouter:
    router = APIRouter()

    def get_run(run_id):
        try:
            UUID(run_id)
        except ValueError:
            raise HTTPException(422, "Run ID must be a UUID") from None
        try:
            return service.run(run_id)
        except RunNotFound:
            raise HTTPException(404, "Research run not found") from None

    @router.post("/api/research-runs", status_code=202, response_model=ResearchRun)
    def start_research(body: ResearchRequest) -> dict:
        try:
            return service.start(body)
        except IndustryNotFound:
            raise HTTPException(404, "Industry template not found") from None
        except ResearchQueueFull as exc:
            raise HTTPException(429, str(exc)) from None

    @router.get("/api/research-runs", response_model=list[ResearchRun])
    def runs(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> list[dict]:
        return service.runs(limit, offset)

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
        return service.events(run_id)

    @router.post("/api/chat", response_model=ChatResponse)
    def chat(body: ChatRequest):
        try:
            return service.chat(body)
        except ValueError:
            raise HTTPException(
                502, "Chat output failed evidence/numeric validation; no answer published"
            ) from None

    return router
