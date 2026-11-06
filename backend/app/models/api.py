from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.market_data.symbols import normalize_symbol, symbol_market


class SymbolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    symbol: str = Field(min_length=1, max_length=12)

    @field_validator("symbol")
    @classmethod
    def valid_symbol(cls, value):
        return normalize_symbol(value)


class ResearchRequest(SymbolRequest):
    strategy: Literal["multi", "single"] = "multi"
    industry_slug: str | None = Field(default=None, max_length=60, pattern=r"^[a-z0-9-]+$")


class PositionRequest(SymbolRequest):
    shares: float = Field(gt=0, le=1e9)
    average_cost: float = Field(ge=0, le=1e9)
    currency: Literal["USD", "CAD"] = "USD"

    @model_validator(mode="after")
    def currency_matches_listing(self):
        expected = "CAD" if symbol_market(self.symbol) == "CA" else "USD"
        if self.currency != expected:
            raise ValueError("Position currency must match the listing; FX conversion is not automatic")
        return self


class ChatRequest(SymbolRequest):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    evidence: list[dict]
    mode: str
    gaps: list[str]


class StageAttempt(BaseModel):
    stage: str
    attempt: int
    status: str
    input_evidence_ids: list[str]
    started_at: str
    finished_at: str | None
    output: dict | None
    validation_errors: list[str]
    input: dict | None


class ResearchRun(BaseModel):
    run_id: str
    symbol: str
    market: Literal["US", "CA"]
    model_id: str
    strategy: Literal["multi", "single"]
    mode: Literal["fixtures", "live"]
    started_at: str
    finished_at: str | None
    status: Literal["queued", "running", "complete", "incomplete", "failed", "cancelled"]
    stages: list[StageAttempt]
    evidence: list[dict]
    calculations: list[dict]
    report: str | None
    gaps: list[str]
    usage: list[dict]
    latency_seconds: float | None
    industry: dict | None = None


class HealthResponse(BaseModel):
    status: str
    mode: Literal["fixtures", "live"]
    model_configured: bool
    model_id: str
    missing_configuration: list[str]
    limitations: list[str]
