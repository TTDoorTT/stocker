"""Explicit live six-stage acceptance; requires a dedicated, new SQLite path.

Example: docker compose exec -T -e DATA_MODE=live -e LLM_MAX_TOKENS=8192
-e LLM_TIMEOUT=600 backend python /workspace/scripts/live_research_check.py
--database /data/live-budget-acceptance.db
Never uses fixtures or prints credentials/provider response bodies.
"""

import argparse
import json
from pathlib import Path

from app.core.config import Settings
from app.modules.market_data.service import DataService
from app.modules.research.orchestrator import ResearchOrchestrator, new_run
from app.modules.research.repository import ResearchRepository
from app.modules.research.schemas import STAGES


class AcceptanceRepository(ResearchRepository):
    def event(self, run_id, event):
        result = super().event(run_id, event)
        if event["event"] in {"stage_started", "stage_completed", "validation_failed", "run_finished"}:
            print(
                json.dumps(
                    {
                        k: v
                        for k, v in event.items()
                        if k in {"event", "stage", "attempt", "at", "status", "errors"}
                    }
                ),
                flush=True,
            )
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--symbol", default="AAPL", choices=["AAPL", "MSFT", "NVDA"])
    args = parser.parse_args()
    settings = Settings()
    if settings.data_mode != "live" or args.database.exists():
        parser.error("Requires DATA_MODE=live and a new dedicated database; existing history is preserved")
    settings.database_url = f"sqlite:///{args.database.resolve()}"
    repo = AcceptanceRepository(settings.database_url)
    try:
        run = new_run(args.symbol, settings)
        repo.save_run(run)
        print(
            json.dumps(
                {
                    "run_id": run["run_id"],
                    "mode": settings.data_mode,
                    "budgets": {
                        key: getattr(settings, key)
                        for key in (
                            "llm_max_tokens",
                            "llm_timeout",
                            "llm_context_window_tokens",
                            "llm_run_output_tokens",
                            "llm_run_total_tokens",
                            "research_run_timeout",
                        )
                    },
                }
            ),
            flush=True,
        )
        result = ResearchOrchestrator(repo, DataService(settings), settings).execute(run["run_id"])
        latest = {s["stage"]: s for s in result["stages"]}
        completed = {name for name, stage in latest.items() if stage["status"] == "complete"}
        passed = set(STAGES) <= completed and bool(result["report"]) and bool(result["evidence"])
        assert all(not e.get("fixture", False) for e in result["evidence"])
        assert repo.run(run["run_id"]) == result
        print(
            json.dumps(
                {
                    "six_stages_and_report_pass": passed,
                    "status": result["status"],
                    "latency_seconds": result["latency_seconds"],
                    "gaps": result["gaps"],
                    "reported_total_tokens": sum(u.get("total_tokens", 0) for u in result["usage"]),
                    "model_requests_with_usage": len(result["usage"]),
                }
            ),
            flush=True,
        )
        return 0 if passed else 1
    finally:
        repo.close()


if __name__ == "__main__":
    raise SystemExit(main())
