from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Evidence(StrictModel):
    evidence_id: str
    symbol: str
    market: Literal['US', 'CA'] = 'US'
    field: str
    value: float | str | None
    unit: str
    currency: str | None = 'USD'
    period: str
    period_start: date | None = None
    period_end: date | None = None
    source_name: str
    source_url: str
    published_at: datetime | None
    fetched_at: datetime
    missing_reason: str | None = None
    fixture: bool = False
    stale: bool = False
    cached: bool = False


class FinancialFact(Evidence):
    statement: Literal['income', 'balance', 'cashflow'] = 'income'
    fiscal_year: int | None = None
    filing_fiscal_year: int | None = None
    fiscal_period: str = 'FY'


class Quote(StrictModel):
    price: float = Field(gt=0)
    previous_close: float | None = Field(default=None, gt=0)
    timestamp: datetime
    source_url: str
    source_name: str
    stale: bool
    delayed: bool = True
    evidence_id: str
    currency: str = 'USD'
    fixture: bool = False
    fetched_at: datetime | None = None
    cached: bool = False


class PriceBar(StrictModel):
    date: date
    close: float = Field(gt=0)
    source_url: str
    source_name: str
    fetched_at: datetime
    adjusted: bool = False
    fixture: bool = False
    cached: bool = False
    currency: Literal['USD', 'CAD'] = 'USD'
    limitations: list[str] = Field(default_factory=list)


class NewsItem(StrictModel):
    headline: str
    source_name: str
    source_url: str
    published_at: datetime
    fetched_at: datetime
    symbols: list[str] = Field(default_factory=list)
    sector: str | None = None
    fixture: bool = False
    cached: bool = False


class Stock(StrictModel):
    symbol: str
    name: str
    market: Literal['US', 'CA'] = 'US'
    currency: str = 'USD'
    mode: Literal['fixtures', 'live']
    profile: str
    quote: Quote | None = None
    facts: list[FinancialFact] = Field(default_factory=list)
    news: list[NewsItem] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class Calculation(StrictModel):
    calculation_id: str
    metric: str
    value: float | None
    unit: str
    input_evidence_ids: list[str]
    inputs: dict[str, float | str | None]
    reason: str | None = None
