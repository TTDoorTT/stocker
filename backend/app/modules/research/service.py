"""Research application entrypoints; scheduling stays local and bounded."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

from app.contracts.api import ChatRequest, ResearchRequest
from app.core.config import Settings
from app.modules.market_data.service import DataService
from app.modules.research.chat import answer_chat
from app.modules.research.errors import IndustryNotFound, ResearchQueueFull, RunNotFound
from app.modules.research.orchestrator import ResearchOrchestrator, new_run, now
from app.modules.research.repository import ResearchRepository


class ResearchService:
    def __init__(
        self,
        repository: ResearchRepository,
        data: DataService,
        settings: Settings,
        industry: Callable[[str], dict],
    ):
        self.repository = repository
        self.data = data
        self.settings = settings
        self.industry = industry
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="research")
        self.capacity = BoundedSemaphore(4)

    def recover_interrupted(self) -> None:
        for run in self.repository.runs(limit=10000):
            if run["status"] in ("running", "queued"):
                run.update(status="incomplete", finished_at=now())
                run["gaps"].append("Service restart interrupted execution; launch a new run to retry.")
                self.repository.save_run(run)
                self.repository.event(
                    run["run_id"],
                    {
                        "event": "run_finished",
                        "at": now(),
                        "status": "incomplete",
                        "reason": "service_restart",
                    },
                )

    def shutdown(self) -> None:
        self.executor.shutdown(wait=True)

    def start(self, body: ResearchRequest) -> dict:
        try:
            industry = self.industry(body.industry_slug) if body.industry_slug else None
        except KeyError:
            raise IndustryNotFound("Industry template not found") from None
        if not self.capacity.acquire(blocking=False):
            raise ResearchQueueFull("Local research queue is full; wait for an existing run")
        run = new_run(body.symbol, self.settings, body.strategy)
        if industry:
            run["industry"] = industry
        self.repository.save_run(run)

        def execute():
            try:
                ResearchOrchestrator(self.repository, self.data, self.settings).execute(run["run_id"])
            finally:
                self.capacity.release()

        self.executor.submit(execute)
        return run

    def runs(self, limit: int = 50, offset: int = 0) -> list[dict]:
        return self.repository.runs(limit, offset)

    def run(self, run_id: str) -> dict:
        run = self.repository.run(run_id)
        if not run:
            raise RunNotFound("Research run not found")
        return run

    def events(self, run_id: str) -> list[dict]:
        return self.repository.events(run_id)

    def chat(self, body: ChatRequest) -> dict:
        return answer_chat(body, self.data, self.settings)
