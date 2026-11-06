"""Reproducible offline comparison harness, not a live model quality benchmark.

Run from backend: python -m app.services.evaluation
Only a deterministic stub and explicitly synthetic fixture values are used.
"""

import hashlib
import json
from datetime import UTC, datetime

from app.agents.client import FixtureModel
from app.core.config import ROOT, Settings
from app.db.repository import Repository
from app.modules.market_data.service import DataService
from app.orchestrator.engine import ResearchOrchestrator, new_run
from app.orchestrator.validation import validate_output


class CapturedData:
    """Give both strategies independent copies of exactly one captured input bundle."""

    def __init__(self, stock, history):
        self.captured_stock = stock
        self.captured_history = history

    def stock(self, symbol):
        if symbol != self.captured_stock.symbol:
            raise ValueError("Evaluation symbol does not match captured inputs")
        return self.captured_stock.model_copy(deep=True)

    def history(self, symbol):
        if symbol != self.captured_stock.symbol:
            raise ValueError("Evaluation symbol does not match captured inputs")
        return [bar.model_copy(deep=True) for bar in self.captured_history]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def score(run, events):
    """Measure traceable structured claims; do not infer semantic factual accuracy."""
    latest_successful_outputs = {}
    for attempt in run["stages"]:
        if attempt["status"] == "complete":
            latest_successful_outputs[attempt["stage"]] = attempt["output"]
        elif attempt["stage"] in latest_successful_outputs:
            # A failed revision invalidates the earlier output for evaluation purposes.
            latest_successful_outputs.pop(attempt["stage"])
    evidence_ids = {item["evidence_id"] for item in run["evidence"]}
    calculation_ids = {item["calculation_id"] for item in run["calculations"]}
    total_claims = cited_claims = unresolved_claims = numeric_claims = 0
    numeric_validation_errors = 0
    validation_errors = []
    for stage, output in latest_successful_outputs.items():
        try:
            validate_output(stage, output, run["evidence"], run["calculations"])
        except ValueError as exc:
            validation_errors.append(str(exc))
            numeric_validation_errors += "Numeric" in str(exc)
        for claim in output["claims"]:
            total_claims += 1
            refs = claim["evidence_ids"] + claim["calculation_ids"]
            has_valid_citation = bool(refs) and all(ref in evidence_ids | calculation_ids for ref in refs)
            cited_claims += has_valid_citation
            unresolved_claims += not has_valid_citation
            numeric_claims += claim.get("value") is not None
        unresolved_claims += len(output.get("disputes", []))
    failed_attempts = [attempt for attempt in run["stages"] if attempt["status"] == "failed"]
    failed_errors = [error for attempt in failed_attempts for error in attempt["validation_errors"]]
    numeric_validation_errors += sum("Numeric" in error for error in failed_errors)
    usage = run.get("usage", [])
    token_usage = None
    if usage:
        # Only return fields actually exposed by the provider, never estimate missing usage.
        token_usage = {
            field: sum(item[field] for item in usage if field in item)
            for field in ("prompt_tokens", "completion_tokens", "total_tokens")
            if any(field in item for item in usage)
        } or None
    return {
        "strategy": run["strategy"],
        "status": run["status"],
        "model_id": run["model_id"],
        "evidence_sha256": digest(run["evidence"]),
        "calculations_sha256": digest(run["calculations"]),
        "evidence_records": len(run["evidence"]),
        "calculation_records": len(run["calculations"]),
        "successful_stages": len(latest_successful_outputs),
        "factual_claims": total_claims,
        "claims_with_valid_citations": cited_claims,
        "citation_completeness": cited_claims / total_claims if total_claims else None,
        "structured_numeric_claims": numeric_claims,
        "numeric_validation_errors": numeric_validation_errors,
        "unresolved_claims": unresolved_claims,
        "unique_data_gaps": sorted(set(run["gaps"])),
        "failed_attempts": len(failed_attempts),
        "retry_events": sum(event["event"] == "stage_retry" for event in events),
        "risk_revision_events": sum(event["event"] == "risk_revision_requested" for event in events),
        "validation_errors": validation_errors + failed_errors,
        "latency_seconds": run["latency_seconds"],
        "token_usage": token_usage,
        "cost_usd": None,
    }


def evaluate():
    # Explicit override prevents accidental use of live mode, personal env files or model credentials.
    settings = Settings(_env_file=None, data_mode="fixtures")
    data = DataService(settings)
    cases = []
    repository = Repository("sqlite:///:memory:")
    try:
        for symbol in ("AAPL", "MSFT", "NVDA"):
            captured = CapturedData(data.stock(symbol), data.history(symbol))
            results = []
            for strategy in ("multi", "single"):
                run = new_run(symbol, settings, strategy=strategy)
                repository.save_run(run)
                result = ResearchOrchestrator(repository, captured, settings, model=FixtureModel()).execute(
                    run["run_id"]
                )
                results.append(score(result, repository.events(run["run_id"])))
            same_evidence = results[0]["evidence_sha256"] == results[1]["evidence_sha256"]
            same_calculations = results[0]["calculations_sha256"] == results[1]["calculations_sha256"]
            if not same_evidence or not same_calculations:
                raise ValueError("Comparison requires identical captured evidence and calculations")
            cases.append(
                {
                    "symbol": symbol,
                    "same_evidence": same_evidence,
                    "same_calculations": same_calculations,
                    "results": results,
                }
            )
    finally:
        repository.close()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "data_mode": "fixtures",
        "model_kind": "deterministic fixture stub",
        "limitations": [
            "Synthetic financial inputs are not real financial facts.",
            "No live model was called; this does not measure real model quality or cost.",
            "Citation completeness measures reference existence, not whether prose follows from a source.",
            "Multi-stage outputs contain more claims; baseline and specialist stubs are not equivalent tasks.",
            "Latency measures local code and SQLite work, not inference latency.",
            "Token usage and costs are null because the fixture stub exposes neither.",
            "Missing licensed consensus and fixture restrictions make every run incomplete.",
        ],
        "cases": cases,
    }


def main():
    result = evaluate()
    output_path = ROOT / "docs" / "EVALUATION.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    temp_path.replace(output_path)
    print(f"Wrote measured fixture comparison to {output_path}")
    for case in result["cases"]:
        for row in case["results"]:
            print(
                f"{case['symbol']} {row['strategy']}: {row['status']}; "
                f"{row['claims_with_valid_citations']}/{row['factual_claims']} claims cited; "
                f"{row['numeric_validation_errors']} numeric validation errors; "
                f"{row['latency_seconds']} seconds"
            )


if __name__ == "__main__":
    main()
