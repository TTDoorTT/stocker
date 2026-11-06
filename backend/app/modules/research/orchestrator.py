from datetime import datetime, timezone
from time import monotonic
from uuid import uuid4

from app.modules.market_data.symbols import symbol_market
from app.modules.research.agents.client import FixtureModel, ModelClient
from app.modules.research.agents.tools import ResearchTools
from app.modules.research.errors import ModelError
from app.modules.research.reports import render_report
from app.modules.research.schemas import SCHEMAS, STAGES
from app.modules.research.validation import validate_output


def now():
    return datetime.now(timezone.utc).isoformat()


def new_run(symbol, settings, strategy="multi"):
    return {
        "run_id": str(uuid4()),
        "symbol": symbol,
        "market": symbol_market(symbol),
        "model_id": "fixture-stub" if settings.data_mode == "fixtures" else settings.llm_model,
        "strategy": strategy,
        "mode": settings.data_mode,
        "started_at": now(),
        "finished_at": None,
        "status": "queued",
        "stages": [],
        "evidence": [],
        "calculations": [],
        "report": None,
        "gaps": [],
        "usage": [],
        "latency_seconds": None,
    }


class ResearchOrchestrator:
    def __init__(self, repo, data, settings, model=None):
        self.repo = repo
        self.data = data
        self.settings = settings
        self.injected_model = model

    def execute(self, run_id):
        from app.finance.metrics import build_calculations

        run = self.repo.run(run_id)
        start = monotonic()
        model = self.injected_model or (
            FixtureModel() if self.settings.data_mode == "fixtures" else ModelClient(self.settings)
        )
        outputs = {}

        def emit(event, **fields):
            self.repo.event(run_id, {"event": event, "at": now(), **fields})

        def save():
            self.repo.save_run(run)

        def execute_stage(stage, correction=None):
            feedback = [correction] if correction else []
            for attempt in range(1, 4):
                if monotonic() - start > 600:
                    raise ModelError("Run wall-clock budget exhausted")
                entry = {
                    "stage": stage,
                    "attempt": attempt,
                    "status": "running",
                    "input_evidence_ids": [e["evidence_id"] for e in stock["evidence"]],
                    "started_at": now(),
                    "finished_at": None,
                    "output": None,
                    "validation_errors": [],
                    "input": None,
                }
                run["stages"].append(entry)
                prior = {key: value for key, value in outputs.items() if key != stage}
                tools = ResearchTools(stock, run["calculations"], history, prior, emit, stage)
                # Stage scope is distinct; source text remains data within this envelope.
                scopes = {
                    "profile": {
                        "symbol": run["symbol"],
                        "market": stock["market"],
                        "currency": stock["currency"],
                        "profile": stock["profile"],
                        "evidence": [
                            e
                            for e in stock["evidence"]
                            if e["field"] in {"company_name", "industry_classification"}
                        ],
                    },
                    "financials": {"facts": stock["facts"], "calculations": run["calculations"]},
                    "estimates": {"news": stock["news"], "consensus": None},
                    "valuation": {"quote": stock["quote"], "calculations": run["calculations"]},
                    "risk": {"source_gaps": stock["gaps"]},
                    "report": {"gaps": list(dict.fromkeys(run["gaps"]))},
                }
                context = {
                    "stage": stage,
                    "mode": run["mode"],
                    "scope": scopes[stage],
                    "validated_prior": prior,
                    "validation_feedback": feedback,
                }
                if run.get("industry"):
                    context["industry_question"] = run["industry"]
                    context["coverage_limit"] = (
                        "Representative company only; sector-wide conclusions are unsupported."
                    )
                entry["input"] = context
                emit(
                    "stage_started",
                    stage=stage,
                    attempt=attempt,
                    input_evidence_ids=entry["input_evidence_ids"],
                )
                save()
                try:
                    raw = model.complete(stage, context, SCHEMAS[stage].model_json_schema(), tools)
                    entry["output"] = raw
                    emit("stage_output", stage=stage, attempt=attempt)
                    output = validate_output(stage, raw, run["evidence"], run["calculations"])
                    entry.update(status="complete", output=output, finished_at=now())
                    outputs[stage] = output
                    run["gaps"].extend(output["gaps"])
                    emit("stage_completed", stage=stage, attempt=attempt)
                    save()
                    return True
                except (ValueError, ModelError) as exc:
                    # Validation messages only; model transport already redacts provider details.
                    feedback = [str(exc)[:1800]]
                    entry.update(status="failed", validation_errors=feedback, finished_at=now())
                    emit("validation_failed", stage=stage, attempt=attempt, errors=feedback)
                    save()
                    if attempt < 3:
                        emit("stage_retry", stage=stage, attempt=attempt + 1, feedback=feedback)
            run["gaps"].append(f"{stage}: exhausted bounded validation attempts")
            return False

        try:
            run["status"] = "running"
            emit("run_started", model_id=run["model_id"], mode=run["mode"], strategy=run["strategy"])
            save()
            stock_model = self.data.stock(run["symbol"])
            stock = stock_model.model_dump(mode="json")
            run["evidence"] = stock["evidence"]
            run["gaps"] = list(stock["gaps"])
            run["calculations"] = [calc.model_dump(mode="json") for calc in build_calculations(stock_model)]
            try:
                history = [bar.model_dump(mode="json") for bar in self.data.history(run["symbol"])]
            except Exception:
                history = []
                run["gaps"].append("Price history unavailable")
            save()
            stages = ("report",) if run["strategy"] == "single" else STAGES
            for stage in stages:
                if run["strategy"] == "single":
                    # Same full captured evidence, one model session instead of specialist handoffs.
                    outputs["baseline_inputs"] = {
                        "evidence": stock["evidence"],
                        "calculations": run["calculations"],
                    }
                if not execute_stage(stage):
                    break
                if stage == "risk" and outputs["risk"]["disputes"]:
                    dispute = outputs["risk"]["disputes"][0]
                    emit("risk_revision_requested", stage=dispute["stage"], reason=dispute["reason"])
                    target = dispute["stage"]
                    if not execute_stage(target, correction=dispute["reason"]):
                        outputs.pop(target, None)
                    # Revalidate dependent interpretations once, not just the requested stage.
                    dependent = list(STAGES[STAGES.index(target) + 1 : STAGES.index("risk")])
                    for downstream in dependent:
                        if not execute_stage(
                            downstream, correction="Upstream correction; reassess findings."
                        ):
                            outputs.pop(downstream, None)
                    if execute_stage(
                        "risk", correction="One revision used; unresolved disputes become gaps."
                    ):
                        if outputs["risk"]["disputes"]:
                            run["gaps"].append("Unresolved risk disputes after single allowed revisit")
                    else:
                        outputs.pop("risk", None)
                        run["gaps"].append("Risk reassessment unavailable after upstream revision")
            expected = {"report"} if run["strategy"] == "single" else set(STAGES)
            run["status"] = "complete" if expected <= outputs.keys() and not run["gaps"] else "incomplete"
            if "report" in outputs:
                run["report"] = render_report(run, outputs)
                emit("report_ready", status=run["status"])
        except Exception as exc:
            run["status"] = "failed"
            run["gaps"].append(f"Run failed safely ({type(exc).__name__}); check provider configuration")
            emit("run_error", error_type=type(exc).__name__)
        finally:
            run["finished_at"] = now()
            run["latency_seconds"] = round(monotonic() - start, 4)
            run["usage"] = model.usage
            save()
            emit("run_finished", status=run["status"])
        return run
