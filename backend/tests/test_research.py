"""Research acceptance tests use explicitly synthetic data and no network/model API."""

from copy import deepcopy

import pytest

from app.core.config import Settings
from app.modules.market_data.service import DataService
from app.modules.research.agents.client import FixtureModel
from app.modules.research.orchestrator import ResearchOrchestrator, new_run
from app.modules.research.repository import ResearchRepository
from app.modules.research.schemas import STAGES
from app.modules.research.validation import validate_output


@pytest.fixture
def setup():
    settings = Settings(_env_file=None, data_mode="fixtures")
    repository = ResearchRepository("sqlite:///:memory:")
    data = DataService(settings)
    yield settings, repository, data
    repository.close()


def execute(setup, model=None, strategy="multi", symbol="AAPL"):
    settings, repository, data = setup
    run = new_run(symbol, settings, strategy)
    repository.save_run(run)
    result = ResearchOrchestrator(repository, data, settings, model=model).execute(run["run_id"])
    return result, repository.events(run["run_id"])


class ArithmeticErrorModel(FixtureModel):
    """Corrupt an actual bound deterministic result, then honor retry feedback."""

    def __init__(self, always_wrong=False):
        self.always_wrong = always_wrong
        self.feedback = []

    def complete(self, stage, context, schema, tools):
        output = super().complete(stage, context, schema, tools)
        if stage == "financials":
            self.feedback.append(context["validation_feedback"])
            if self.always_wrong or len(self.feedback) == 1:
                numeric_claim = next(claim for claim in output["claims"] if "value" in claim)
                numeric_claim["value"] += 1
        return output


@pytest.mark.parametrize("symbol", ["AAPL", "MSFT", "NVDA"])
def test_six_stage_fixture_run_has_cited_report_and_persisted_handoffs(setup, symbol):
    run, events = execute(setup, symbol=symbol)
    assert run["status"] == "incomplete"  # Missing consensus must never be concealed.
    assert [stage["stage"] for stage in run["stages"]] == list(STAGES)
    assert all(stage["status"] == "complete" for stage in run["stages"])
    assert run["stages"][2]["output"]["consensus_available"] is False
    assert run["finished_at"] is not None
    assert run["model_id"] == "fixture-stub"
    assert run["usage"] == []
    assert "SYNTHETIC FIXTURE DATA" in run["report"]
    assert "not investment advice" in run["report"]
    assert "consensus" in run["report"]
    for item in run["evidence"]:
        assert item["evidence_id"] in run["report"]
        assert item["source_url"] in run["report"]
        assert item["fetched_at"] in run["report"]
    assert setup[1].run(run["run_id"]) == run
    assert events[0]["event"] == "run_started"
    assert events[-1]["event"] == "run_finished"
    assert [event["stage"] for event in events if event["event"] == "stage_completed"] == list(STAGES)
    assert any(event["event"] == "tool_called" for event in events)
    assert any(event["event"] == "report_ready" for event in events)
    financial_input = run["stages"][1]["input"]
    assert financial_input["validated_prior"]["profile"] == run["stages"][0]["output"]
    assert financial_input["stage"] == "financials"


def test_stage_context_contains_citable_inputs_without_redundant_reads(setup):
    run, _ = execute(setup)
    inputs = {entry["stage"]: entry["input"] for entry in run["stages"]}
    assert inputs["profile"]["scope"]["evidence"]
    assert all(
        item["field"] in {"company_name", "industry_classification"}
        for item in inputs["profile"]["scope"]["evidence"]
    )
    assert inputs["financials"]["scope"]["calculations"] == run["calculations"]
    for stage in ("risk", "report"):
        assert inputs[stage]["validated_prior"]
        assert "prior" not in inputs[stage]["scope"]


def test_incorrect_arithmetic_is_rejected_and_corrected_with_feedback(setup):
    model = ArithmeticErrorModel()
    run, events = execute(setup, model=model)
    attempts = [stage for stage in run["stages"] if stage["stage"] == "financials"]
    assert len(attempts) == 2
    assert attempts[0]["status"] == "failed"
    assert "Numeric claim does not match trusted reference" in attempts[0]["validation_errors"][0]
    assert attempts[1]["status"] == "complete"
    assert model.feedback[0] == []
    assert model.feedback[1] == attempts[0]["validation_errors"]
    assert any(event["event"] == "validation_failed" and event["stage"] == "financials" for event in events)
    assert any(event["event"] == "stage_retry" and event["attempt"] == 2 for event in events)
    assert run["report"] is not None


def test_irreparable_arithmetic_stops_at_three_attempts(setup):
    model = ArithmeticErrorModel(always_wrong=True)
    run, events = execute(setup, model=model)
    financials = [stage for stage in run["stages"] if stage["stage"] == "financials"]
    assert [stage["attempt"] for stage in financials] == [1, 2, 3]
    assert all(stage["status"] == "failed" for stage in financials)
    assert len(model.feedback) == 3
    assert run["status"] == "incomplete"
    assert run["report"] is None
    assert not any(stage["stage"] == "estimates" for stage in run["stages"])
    assert "financials: exhausted bounded validation attempts" in run["gaps"]
    assert len([event for event in events if event["event"] == "stage_retry"]) == 2


def test_unknown_evidence_is_rejected_outside_model(setup):
    run, _ = execute(setup)
    output = deepcopy(run["stages"][0]["output"])
    output["evidence_ids"].append("ev-nonexistent")
    output["claims"][0]["evidence_ids"] = ["ev-nonexistent"]
    with pytest.raises(ValueError, match="Unknown evidence IDs"):
        validate_output("profile", output, run["evidence"], run["calculations"])


def test_schema_violation_is_rejected(setup):
    run, _ = execute(setup)
    output = deepcopy(run["stages"][0]["output"])
    output["uncontracted_field"] = "This field is not permitted."
    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        validate_output("profile", output, run["evidence"], run["calculations"])


class RepeatedDisputeModel(FixtureModel):
    def complete(self, stage, context, schema, tools):
        output = super().complete(stage, context, schema, tools)
        if stage == "risk":
            output["disputes"] = [
                {
                    "stage": "financials",
                    "reason": "Recheck the interpretation against the captured source.",
                    "evidence_ids": [output["evidence_ids"][0]],
                }
            ]
        return output


def test_risk_dispute_revisits_upstream_once_and_leaves_unresolved_gap(setup):
    run, events = execute(setup, model=RepeatedDisputeModel())
    stages = [stage["stage"] for stage in run["stages"]]
    assert stages.count("financials") == 2
    assert stages.count("estimates") == 2
    assert stages.count("valuation") == 2
    assert stages.count("risk") == 2
    assert stages.count("report") == 1
    assert stages.count("profile") == 1
    assert len([event for event in events if event["event"] == "risk_revision_requested"]) == 1
    assert "Unresolved risk disputes after single allowed revisit" in run["gaps"]
    assert "Unresolved risk disputes" in run["report"]
    assert run["status"] == "incomplete"
    revised = [stage for stage in run["stages"] if stage["stage"] == "financials"][1]
    assert "Recheck the interpretation" in revised["input"]["validation_feedback"][0]


def test_research_and_trace_survive_repository_reopen(tmp_path):
    settings = Settings(_env_file=None, data_mode="fixtures")
    url = f"sqlite:///{tmp_path / 'research.db'}"
    first = ResearchRepository(url)
    run, events = execute((settings, first, DataService(settings)))
    first.close()
    reopened = ResearchRepository(url)
    try:
        assert reopened.run(run["run_id"]) == run
        assert reopened.events(run["run_id"]) == events
        assert reopened.runs()[0]["report"] == run["report"]
    finally:
        reopened.close()


def test_baseline_receives_identical_captured_evidence_and_calculations(setup):
    settings, repository, data = setup
    stock = data.stock("AAPL")
    history = data.history("AAPL")

    class CapturedData:
        def stock(self, symbol):
            assert symbol == "AAPL"
            return stock.model_copy(deep=True)

        def history(self, symbol):
            assert symbol == "AAPL"
            return history

    captured_setup = settings, repository, CapturedData()
    multi, _ = execute(captured_setup)
    single, _ = execute(captured_setup, strategy="single")
    assert multi["evidence"] == single["evidence"]
    assert multi["calculations"] == single["calculations"]
    assert [stage["stage"] for stage in single["stages"]] == ["report"]
    baseline_context = single["stages"][0]["input"]["validated_prior"]["baseline_inputs"]
    assert baseline_context["evidence"] == multi["evidence"]
    assert baseline_context["calculations"] == multi["calculations"]
    assert single["strategy"] == "single"
    assert single["report"] is not None
    assert single["status"] == "incomplete"


class FailedRiskReassessmentModel(RepeatedDisputeModel):
    def __init__(self):
        self.risk_calls = 0

    def complete(self, stage, context, schema, tools):
        output = super().complete(stage, context, schema, tools)
        if stage == "risk":
            self.risk_calls += 1
            if self.risk_calls == 1:
                output["summary"] = "Original risk review awaiting upstream correction."
            else:
                output["evidence_ids"].append("ev-nonexistent")
        return output


def test_failed_risk_reassessment_does_not_render_stale_risk_findings(setup):
    model = FailedRiskReassessmentModel()
    run, _ = execute(setup, model=model)
    assert model.risk_calls == 4  # Initial review, then three bounded reassessment attempts.
    assert run["status"] == "incomplete"
    assert "risk: exhausted bounded validation attempts" in run["gaps"]
    assert run["report"] is not None
    assert "Original risk review awaiting upstream correction." not in run["report"]
    risk_section = run["report"].split("## Risks and counterevidence", 1)[1]
    assert "Unavailable: this stage did not pass validation." in risk_section


def test_exhausted_budget_does_not_trigger_validation_retries(setup):
    from app.modules.research.errors import ModelBudgetError

    class ExhaustedModel(FixtureModel):
        def complete(self, stage, context, schema, tools):
            raise ModelBudgetError("Per-run model budget exhausted")

    run, events = execute(setup, model=ExhaustedModel())
    assert run["status"] == "failed"
    assert len(run["stages"]) == 1
    assert run["stages"][0]["status"] == "failed"
    assert not any(event["event"] == "stage_retry" for event in events)


def test_run_timeout_accepts_long_local_execution_and_rejects_late_output(setup, monkeypatch):
    from app.modules.research import orchestrator

    settings, _, _ = setup
    settings.research_run_timeout = 1200
    elapsed = [0.0]
    monkeypatch.setattr(orchestrator, "monotonic", lambda: elapsed[0])

    class SlowModel(FixtureModel):
        def complete(self, stage, context, schema, tools):
            elapsed[0] += 200
            return super().complete(stage, context, schema, tools)

    run, events = execute(setup, model=SlowModel())
    assert [s["stage"] for s in run["stages"]] == list(STAGES)
    assert run["stages"][-2]["status"] == "complete"  # Past the former 600-second cap.
    assert run["stages"][-1]["status"] == "failed"  # No late output accepted at deadline.
    assert run["report"] is None
    assert not any(event["event"] == "stage_retry" for event in events)
