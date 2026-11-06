import json

TOOL_NAMES = (
    "get_company_data",
    "get_financial_facts",
    "get_price_history",
    "get_news",
    "calculate_metric",
    "read_prior_stage",
)
TOOL_DESCRIPTIONS = {
    "get_company_data": "Read the full captured company snapshot, including identity evidence. "
    "Use only if company context is absent from scope.",
    "get_financial_facts": "Read captured annual statements with evidence IDs and source metadata. "
    "Not needed when scope already contains facts.",
    "get_price_history": "Read historical daily prices as a lossless table with shared provenance. "
    "Not needed for identity, annual statements or consensus availability.",
    "get_news": "Read captured filing references or headlines; no article bodies or consensus forecasts.",
    "calculate_metric": "Read already computed deterministic metrics and their exact input references. "
    "Not needed when scope already contains calculations.",
    "read_prior_stage": "Read validated earlier stage outputs. Not needed when validated_prior is supplied.",
}


class ToolArgumentsError(ValueError):
    pass


def history_table(history):
    """Losslessly share repeated bar provenance within the model-only tool view."""
    metadata = []
    indices = {}
    rows = []
    for bar in history:
        source = {key: value for key, value in bar.items() if key not in {"date", "close"}}
        key = json.dumps(source, sort_keys=True)
        if key not in indices:
            indices[key] = len(metadata)
            metadata.append(source)
        rows.append([indices[key], [bar["date"], bar["close"]]])
    return {
        "format": "history_table",
        "columns": ["date", "close"],
        "metadata": metadata,
        "rows": rows,
        "row_format": "[metadata index, values in columns order]",
    }


class ResearchTools:
    def __init__(self, stock, calculations, history, prior, emit, stage):
        self.stock = stock
        self.calculations = calculations
        self.history = history
        self.prior = prior
        self.emit = emit
        self.stage = stage
        self.count = 0
        self.definitions = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": (
                        TOOL_DESCRIPTIONS[name] + " This tool takes NO arguments: "
                        "always pass exactly {}. No symbol, fields, period or network parameters."
                    ),
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            }
            for name in TOOL_NAMES
        ]

    def call(self, name, args):
        self.count += 1
        if self.count > 40:
            raise ValueError("Tool call budget exceeded")
        if name not in TOOL_NAMES or args:
            self.emit("tool_rejected", stage=self.stage, reason="Unknown tool or unexpected arguments")
            if name in TOOL_NAMES:
                raise ToolArgumentsError("Tool has unexpected arguments; use exactly {}")
            raise ValueError("Unknown tool or unexpected arguments")
        self.emit("tool_called", stage=self.stage, tool=name)
        payloads = {
            "get_company_data": self.stock,
            "get_financial_facts": self.stock.get("facts", []),
            "get_price_history": history_table(self.history),
            "get_news": self.stock.get("news", []),
            "calculate_metric": self.calculations,
            "read_prior_stage": self.prior,
        }
        # A bounded serialization prevents provider text from expanding the session arbitrarily.
        value = payloads[name]
        if len(json.dumps(value)) > 150000:
            raise ValueError("Tool output exceeds context limit")
        return value
