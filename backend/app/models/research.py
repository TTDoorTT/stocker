from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

STAGES = ('profile', 'financials', 'estimates', 'valuation', 'risk', 'report')
StageName = Literal['profile', 'financials', 'estimates', 'valuation', 'risk', 'report']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Claim(StrictModel):
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)
    calculation_ids: list[str] = Field(default_factory=list, max_length=30)
    value: float | None = None
    unit: str | None = None
    reference_id: str | None = None


class StageBase(StrictModel):
    summary: str = Field(min_length=1, max_length=4000)
    claims: list[Claim] = Field(max_length=30)
    evidence_ids: list[str] = Field(max_length=100)
    calculation_ids: list[str] = Field(max_length=100)
    gaps: list[str] = Field(max_length=30)


class ProfileOutput(StageBase):
    stage: Literal['profile']
    identity_check: str


class FinancialOutput(StageBase):
    stage: Literal['financials']
    performance: str


class EstimatesOutput(StageBase):
    stage: Literal['estimates']
    consensus_available: bool


class ValuationOutput(StageBase):
    stage: Literal['valuation']
    limitations: list[str]


class Dispute(StrictModel):
    stage: Literal['profile', 'financials', 'estimates', 'valuation']
    reason: str
    evidence_ids: list[str]


class RiskOutput(StageBase):
    stage: Literal['risk']
    counterevidence: list[str] = Field(min_length=1)
    invalidation_conditions: list[str] = Field(min_length=1)
    disputes: list[Dispute] = Field(max_length=4)


class ReportOutput(StageBase):
    stage: Literal['report']
    executive_summary: str


StageOutput = Annotated[
    ProfileOutput | FinancialOutput | EstimatesOutput | ValuationOutput | RiskOutput | ReportOutput,
    Field(discriminator='stage'),
]
SCHEMAS = dict(zip(STAGES, (ProfileOutput, FinancialOutput, EstimatesOutput,
                           ValuationOutput, RiskOutput, ReportOutput), strict=True))
