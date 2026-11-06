import math
import re

from app.modules.research.schemas import SCHEMAS


def validate_output(stage, raw, evidence, calculations):
    output = SCHEMAS[stage].model_validate(raw)
    data = output.model_dump()
    errors = []
    ev = {item["evidence_id"]: item for item in evidence}
    calcs = {item["calculation_id"]: item for item in calculations}
    if set(data["evidence_ids"]) - ev.keys():
        errors.append("Unknown evidence IDs")
    if set(data["calculation_ids"]) - calcs.keys():
        errors.append("Unknown calculation IDs")
    for claim in data["claims"]:
        if not claim["evidence_ids"] and not claim["calculation_ids"]:
            errors.append("Every factual claim needs a source or calculation")
        if set(claim["evidence_ids"]) - set(data["evidence_ids"]):
            errors.append("Claim evidence must exist and be declared at stage level")
        if set(claim["calculation_ids"]) - set(data["calculation_ids"]):
            errors.append("Claim calculations must exist and be declared at stage level")
        if claim["value"] is not None:
            ref = claim["reference_id"]
            record = calcs.get(ref) or ev.get(ref)
            if (
                not record
                or not isinstance(record.get("value"), (int, float))
                or not math.isclose(claim["value"], record["value"], rel_tol=1e-10, abs_tol=1e-10)
                or claim["unit"] != record["unit"]
            ):
                errors.append("Numeric claim does not match trusted reference value and unit")
            if ref not in claim["calculation_ids"] + claim["evidence_ids"]:
                errors.append("Numeric reference must be cited in the claim")

    # Numeric prose bypasses structured value binding; reject it, including dates.
    def text_values(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key not in {"evidence_ids", "calculation_ids", "reference_id", "value", "unit", "stage"}:
                    yield from text_values(item)
        elif isinstance(value, list):
            for item in value:
                yield from text_values(item)
        elif isinstance(value, str):
            yield value

    if any(re.search(r"\d", value) for value in text_values(data)):
        errors.append("Numeric prose is forbidden; put exact numbers in bound claims.value")
    if stage == "estimates" and (data["consensus_available"] or not data["gaps"]):
        errors.append("No consensus provider is integrated; report unavailable consensus as a gap")
    if stage == "risk":
        for dispute in data["disputes"]:
            if not dispute["evidence_ids"] or set(dispute["evidence_ids"]) - ev.keys():
                errors.append("Risk disputes require existing evidence IDs")
    if errors:
        raise ValueError("; ".join(errors))
    return data
