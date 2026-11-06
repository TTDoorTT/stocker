from app.agents.client import FixtureModel, ModelClient
from app.agents.tools import ResearchTools
from app.finance.metrics import build_calculations
from app.models.research import SCHEMAS
from app.orchestrator.validation import validate_output


def answer_chat(request, data, settings):
    stock = data.stock(request.symbol)
    payload = stock.model_dump(mode="json")
    calculations = [c.model_dump(mode="json") for c in build_calculations(stock)]
    tools = ResearchTools(payload, calculations, [], {}, lambda *args, **kw: None, "report")
    model = FixtureModel() if settings.data_mode == "fixtures" else ModelClient(settings)
    raw = model.complete(
        "report",
        {
            "question": request.message,
            "company": payload,
            "instruction": "Answer this stock question only. No research run is launched.",
        },
        SCHEMAS["report"].model_json_schema(),
        tools,
    )
    result = validate_output("report", raw, payload["evidence"], calculations)
    answer = result["summary"] + "\n\n" + result["executive_summary"]
    for claim in result["claims"]:
        answer += "\n- " + claim["text"]
        if claim["value"] is not None:
            answer += f" {claim['value']:g} {claim['unit']}"
        answer += " (" + ", ".join(claim["evidence_ids"] + claim["calculation_ids"]) + ")"
    return {
        "answer": answer,
        "evidence": payload["evidence"],
        "mode": settings.data_mode,
        "gaps": list(set(payload["gaps"] + result["gaps"])),
    }
