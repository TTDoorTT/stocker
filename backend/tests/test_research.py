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
    assert "# AAPL — Quick Research Brief" in single["report"]
    assert "Quick (1-pass synthesis)" in single["report"]
    assert "Unavailable: this stage did not pass validation." not in single["report"]


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


def test_research_enriches_financials_and_estimates_with_quarterly_ttm_and_earnings(setup):
    run, _ = execute(setup, symbol="AAPL")
    inputs = {entry["stage"]: entry["input"] for entry in run["stages"]}
    ev_fields = {item["field"] for item in run["evidence"]}
    calc_metrics = {item["metric"] for item in run["calculations"]}

    assert "quarterly_revenue" in ev_fields
    assert "ttm_revenue" in calc_metrics
    assert "quarterly_trends" in inputs["financials"]["scope"]
    assert inputs["financials"]["scope"]["quarterly_trends"]["ttm_calculation_ids"]

    assert "vendor_earnings_actual_eps" in ev_fields
    assert "vendor_earnings" in inputs["estimates"]["scope"]
    assert inputs["estimates"]["scope"]["consensus"] is None
    assert run["stages"][2]["output"]["consensus_available"] is False


def test_research_enrichment_degrades_gracefully_on_provider_errors_or_mode_mismatch(setup):
    from app.modules.market_data.errors import DataUnavailable

    settings, repository, data = setup

    class DegradedData:
        def stock(self, symbol):
            return data.stock(symbol)

        def history(self, symbol):
            return data.history(symbol)

        def financial_trends(self, symbol):
            raise DataUnavailable("SEC quarterly endpoint unavailable")

        def earnings(self, symbol):
            report = data.earnings(symbol)
            return report.model_copy(update={"mode": "live"})

    run, _ = execute((settings, repository, DegradedData()), symbol="AAPL")
    assert len(run["stages"]) == 6
    assert all(stage["status"] == "complete" for stage in run["stages"])
    assert any("Quarterly financial trends unavailable" in gap for gap in run["gaps"])
    assert any("Earnings calendar mode mismatch" in gap for gap in run["gaps"])
    assert not any(item["field"].startswith("vendor_earnings") for item in run["evidence"])


def test_cancellation_token_stops_orchestrator_between_stages(setup):
    from app.modules.research.agents.client import CancellationToken

    settings, repository, data = setup
    token = CancellationToken()

    class CancelAfterProfileModel(FixtureModel):
        def complete(self, stage, context, schema, tools):
            output = super().complete(stage, context, schema, tools)
            if stage == "profile":
                token.cancel()
            return output

    run = new_run("AAPL", settings, "multi")
    repository.save_run(run)
    result = ResearchOrchestrator(
        repository, data, settings, model=CancelAfterProfileModel(), cancel_token=token
    ).execute(run["run_id"])
    events = repository.events(run["run_id"])
    assert result["status"] == "cancelled"
    assert result["report"] is None
    assert "Research run was stopped by the user." in result["gaps"]
    assert any(event["event"] == "run_cancelled" for event in events)
    assert events[-1]["event"] == "run_finished" and events[-1]["status"] == "cancelled"


def test_cancel_endpoint_marks_queued_run_cancelled_and_validates_id(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path}/cancel.db")
    repository = ResearchRepository(settings.database_url)
    run = new_run("AAPL", settings, "multi")
    repository.save_run(run)
    with TestClient(create_app(settings, repo=repository)) as client:
        # Directly seeded queued run is marked incomplete on startup; seed a fresh queued run after startup.
        queued = new_run("MSFT", settings, "multi")
        repository.save_run(queued)
        res = client.post(f"/api/research-runs/{queued['run_id']}/cancel")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "cancelled"
        assert "Research run was stopped by the user." in body["gaps"]
        assert client.post("/api/research-runs/not-a-uuid/cancel").status_code == 422
        assert (
            client.post("/api/research-runs/00000000-0000-0000-0000-000000000001/cancel").status_code == 404
        )


def test_delete_endpoint_removes_terminal_run_and_blocks_active_runs(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path}/delete.db")
    repository = ResearchRepository(settings.database_url)
    with TestClient(create_app(settings, repo=repository)) as client:
        active = new_run("MSFT", settings, "multi")
        repository.save_run(active)
        assert client.delete(f"/api/research-runs/{active['run_id']}").status_code == 409

        assert client.post(f"/api/research-runs/{active['run_id']}/cancel").status_code == 200
        deleted = client.delete(f"/api/research-runs/{active['run_id']}")
        assert deleted.status_code == 200
        assert deleted.json() == {"deleted": True, "run_id": active["run_id"]}
        assert client.get(f"/api/research-runs/{active['run_id']}").status_code == 404
        assert repository.events(active["run_id"]) == []
        assert client.delete("/api/research-runs/not-a-uuid").status_code == 422
        assert client.delete("/api/research-runs/00000000-0000-0000-0000-000000000001").status_code == 404


def test_cancellation_token_aborts_blocked_live_model_socket_immediately():
    import socket
    import threading
    from time import monotonic

    from app.modules.research.agents.client import CancellationToken, ModelClient
    from app.modules.research.agents.tools import ResearchTools
    from app.modules.research.errors import RunCancelledError

    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    accepted = threading.Event()
    release = threading.Event()

    def accept_and_hang():
        conn, _ = server.accept()
        accepted.set()
        release.wait(timeout=5)
        conn.close()
        server.close()

    threading.Thread(target=accept_and_hang, daemon=True).start()
    token = CancellationToken()

    def trigger():
        accepted.wait(timeout=2)
        token.cancel()

    threading.Thread(target=trigger, daemon=True).start()

    settings = Settings(
        _env_file=None,
        data_mode="live",
        llm_base_url=f"http://127.0.0.1:{port}/v1",
        llm_model="test-model",
        llm_timeout=10,
    )
    toolset = ResearchTools(
        {"evidence": [], "facts": [], "news": []}, [], [], {}, lambda *args, **kwargs: None, "profile"
    )
    start = monotonic()
    try:
        with pytest.raises(RunCancelledError):
            ModelClient(settings, cancel_token=token).complete("profile", {}, {}, toolset)
        assert monotonic() - start < 1.5
    finally:
        release.set()


def test_report_renders_human_readable_metrics_identity_performance_and_tables(setup):
    from app.modules.research.reports import format_numeric_value

    assert format_numeric_value(391035000000.0, "USD") == "$391.04B"
    assert format_numeric_value(-42500000.0, "CAD") == "-CA$42.50M"
    assert format_numeric_value(26.44123, "%") == "26.44%"
    assert format_numeric_value(34.2, "ratio") == "34.20x"
    assert format_numeric_value(6.11, "USD/shares") == "$6.11/share"

    run, _ = execute(setup, symbol="AAPL")
    report = run["report"]
    assert "### Key metrics snapshot" in report
    assert "### Identity verification" in report
    assert "Fixture identity only; no live cross-source verification." in report
    assert "### Performance overview" in report
    assert "Synthetic annual data exercises calculations only." in report
    assert "### Counterevidence" in report
    assert "### Invalidation conditions" in report
    assert "| Evidence ID | Field | Period | Source | Published | Fetched |" in report
    assert "e+" not in report.lower()


def test_prompts_preserve_untrusted_data_guard_and_zero_digit_rules():
    from app.modules.research.agents.client import PROMPTS

    common = (PROMPTS / "common.md").read_text()
    assert "untrusted data" in common
    assert "Zero-digit prose rule" in common
    for stage in STAGES:
        text = (PROMPTS / f"{stage}.md").read_text()
        assert text.strip()
        assert "Inputs to use directly" in text
    assert "Use calculate_metric" not in (PROMPTS / "financials.md").read_text()


def test_research_captures_price_history_return_scope_records_and_filters_ui_footnotes(setup):
    run, _ = execute(setup, symbol="AAPL")
    inputs = {entry["stage"]: entry["input"] for entry in run["stages"]}
    calc_metrics = {item["metric"] for item in run["calculations"]}

    assert "price_history_return" in calc_metrics
    assert "price_history" in inputs["valuation"]["scope"]
    assert inputs["valuation"]["scope"]["price_history"]["observations"] == 10
    assert inputs["profile"]["scope"]["reporting_currencies"] == ["USD"]
    assert inputs["financials"]["scope"]["quarterly_trends"]["records"]
    assert inputs["estimates"]["scope"]["vendor_earnings"]["records"]
    assert "calculations_summary" in inputs["risk"]["scope"]
    assert inputs["financials"]["scope"]["facts"]
    assert "source_url" not in inputs["financials"]["scope"]["facts"][0]
    assert not any("after-hours stock-price reaction" in gap for gap in run["gaps"])


def test_report_deduplicates_gaps_and_links_evidence_and_calculations(setup):
    run, _ = execute(setup, symbol="AAPL")
    report = run["report"]
    assert "> **Bottom line:**" in report
    assert "(#ref-ev-" in report
    assert "(#ref-calc-" in report
    gaps_section = report.split("## Data gaps", 1)[1].split("## Sources and timestamps", 1)[0]
    gap_lines = [line for line in gaps_section.splitlines() if line.startswith("- ")]
    # Report stage distilled gaps are rendered instead of repeating every stage's raw gaps.
    assert len(gap_lines) == 1
    assert "Synthetic test data only" in gap_lines[0]


def test_model_client_omits_tools_payload_when_tool_definitions_empty(monkeypatch):
    import json

    import httpx

    from app.modules.research.agents.client import ModelClient
    from app.modules.research.agents.tools import ResearchTools

    captured = []
    original = httpx.Client

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"stage":"risk"}'}}]})

    monkeypatch.setattr(
        "app.modules.research.agents.client.httpx.Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    settings = Settings(
        _env_file=None,
        llm_model="test-model",
        llm_base_url="https://model.example/v1",
    )
    toolset = ResearchTools(
        {"evidence": [], "facts": [], "news": []},
        [],
        [],
        {},
        lambda *args, **kwargs: None,
        "risk",
        expose_tools=False,
    )
    assert toolset.definitions == []
    assert ModelClient(settings).complete("risk", {}, {}, toolset) == {"stage": "risk"}
    assert "tools" not in captured[0]
    assert captured[0]["response_format"] == {"type": "json_object"}
