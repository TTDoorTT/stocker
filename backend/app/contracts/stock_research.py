"""Future stock-research API contracts. Phase 0: no routes or provider calls."""

from datetime import date
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

Market = Literal["US", "CA"]
Mode = Literal["fixtures", "live"]
Currency = Literal["USD", "CAD"]
Quarter = Literal["Q1", "Q2", "Q3", "Q4"]
MetricName = Literal["revenue", "net_income", "diluted_eps", "operating_cash_flow", "gross_profit"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SourceMetadata(StrictModel):
    name: str = Field(min_length=1)
    url: HttpUrl
    fetched_at: AwareDatetime
    published_at: AwareDatetime | None = None
    cached: bool = False
    fixture: bool = False


class MarketResponse(StrictModel):
    symbol: str = Field(min_length=1, max_length=24, pattern=r"^[A-Z0-9][A-Z0-9.]*$")
    market: Market
    currency: Currency
    mode: Mode
    gaps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_listing_currency(self):
        if (self.market == "US" and self.currency != "USD") or (
            self.market == "CA" and self.currency != "CAD"
        ):
            raise ValueError("listing currency must match explicitly selected market")
        if self.market == "CA" and not self.symbol.endswith((".TO", ".V")):
            raise ValueError("Canadian listing requires explicit .TO or .V ticker")
        if self.market == "US" and self.symbol.endswith((".TO", ".V")):
            raise ValueError("Canadian listing cannot be declared as US")
        return self


def _check_sources(mode: Mode, sources: list[SourceMetadata]):
    if any(source.fixture != (mode == "fixtures") for source in sources):
        raise ValueError("synthetic and live provenance must not be mixed")


class CandleBar(StrictModel):
    date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: int | None = Field(default=None, ge=0, strict=True)
    adjusted_close: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_envelope(self):
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high below OHLC value")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low above OHLC value")
        return self


class CandleSeries(MarketResponse):
    range: Literal["1m", "3m", "6m", "1y", "2y", "5y"]
    interval: Literal["1d", "1wk", "1mo"]
    price_basis: Literal["provider_ohlc", "split_adjusted_ohlc", "fully_adjusted_ohlc"]
    adjustment_note: str = Field(min_length=1)
    source: SourceMetadata
    bars: list[CandleBar] = Field(default_factory=list, max_length=1400)

    @model_validator(mode="after")
    def check_series(self):
        dates = [bar.date for bar in self.bars]
        if dates != sorted(set(dates)):
            raise ValueError("candle dates must be unique and ascending")
        _check_sources(self.mode, [self.source])
        return self


class MetricValue(StrictModel):
    value: float | None = None
    unit: str = Field(min_length=1)
    status: Literal["as_reported", "derived", "unavailable"]
    evidence_ids: list[str] = Field(default_factory=list)
    calculation_id: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def check_metric(self):
        if self.status == "unavailable":
            if self.value is not None or not self.reason:
                raise ValueError("unavailable metric needs null value and reason")
        elif self.value is None or not self.evidence_ids:
            raise ValueError("present metric needs value and evidence IDs")
        if self.status == "derived" and not self.calculation_id:
            raise ValueError("derived metric needs calculation ID")
        return self


class FinancialPeriod(StrictModel):
    period_id: str = Field(min_length=1)
    fiscal_year: int = Field(ge=1900, le=2200)
    fiscal_quarter: Quarter | None = None
    period_kind: Literal["standalone_quarter", "ytd", "annual"]
    period_start: date
    period_end: date
    filed_on: date
    form: Literal["10-Q", "10-K"]
    accession: str = Field(min_length=1)
    metrics: dict[MetricName, MetricValue] = Field(default_factory=dict)
    source: SourceMetadata

    @model_validator(mode="after")
    def check_period(self):
        if self.period_start >= self.period_end:
            raise ValueError("period start must precede end")
        if self.period_kind != "annual" and self.fiscal_quarter is None:
            raise ValueError("quarterly/YTD period needs fiscal_quarter")
        if self.period_kind == "annual" and self.fiscal_quarter is not None:
            raise ValueError("annual period must not claim standalone quarter")
        return self


class TTMValue(StrictModel):
    value: float | None = None
    unit: str = Field(min_length=1)
    status: Literal["available", "unavailable"]
    input_period_ids: list[str] = Field(default_factory=list)
    calculation_id: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def check_status(self):
        if self.status == "available":
            if self.value is None or not self.calculation_id or len(self.input_period_ids) != 4:
                raise ValueError("available TTM needs value, calculation ID, four periods")
        elif self.value is not None or not self.reason:
            raise ValueError("unavailable TTM needs null value and reason")
        return self


class FinancialTrendsResponse(MarketResponse):
    frequency: Literal["quarterly", "annual"]
    periods: list[FinancialPeriod] = Field(default_factory=list, max_length=20)
    ttm: dict[MetricName, TTMValue] = Field(default_factory=dict)
    sources: list[SourceMetadata] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_ttm_and_sources(self):
        _check_sources(self.mode, self.sources + [p.source for p in self.periods])
        by_id = {p.period_id: p for p in self.periods}
        if len(by_id) != len(self.periods):
            raise ValueError("duplicate financial period IDs")
        for key, result in self.ttm.items():
            if result.status != "available":
                continue
            quarters = []
            for pid in result.input_period_ids:
                p = by_id.get(pid)
                if p is None or p.period_kind != "standalone_quarter" or p.fiscal_quarter is None:
                    raise ValueError("available TTM references must be included standalone quarters")
                fact = p.metrics.get(key)
                if fact is None or fact.value is None or fact.status == "unavailable":
                    raise ValueError("available TTM requires all four metric observations")
                quarters.append(p.fiscal_year * 4 + int(p.fiscal_quarter[1]) - 1)
            if len(set(quarters)) != 4 or max(quarters) - min(quarters) != 3:
                raise ValueError("TTM quarters must be four consecutive fiscal quarters")
        return self


def canonical_earnings_id(market: Market, symbol: str, year: int, quarter: Quarter) -> str:
    return f"{market}:{symbol}:earnings_release:FY{year}{quarter}"


class UpcomingEarnings(StrictModel):
    scheduled_date: date
    date_status: Literal["estimated", "confirmed"]
    timing: Literal["before_open", "after_close", "during_session", "unknown"] = "unknown"
    fiscal_year: int | None = None
    fiscal_quarter: Quarter | None = None
    eps_estimate: float | None = None
    eps_estimate_basis: Literal["gaap_diluted", "gaap_basic", "adjusted"] | None = None
    revenue_estimate: float | None = None
    source: SourceMetadata


class EarningsRecord(StrictModel):
    event_id: str
    fiscal_year: int
    fiscal_quarter: Quarter
    reported_on: date
    actual_eps: float | None = None
    actual_basis: Literal["gaap_diluted", "gaap_basic", "adjusted"] | None = None
    estimate_eps: float | None = None
    estimate_basis: Literal["gaap_diluted", "gaap_basic", "adjusted"] | None = None
    surprise_pct: float | None = None
    actual_revenue: float | None = None
    estimate_revenue: float | None = None
    revenue_surprise_pct: float | None = None
    source: SourceMetadata

    @model_validator(mode="after")
    def check_surprise(self):
        if self.actual_eps is not None and self.actual_basis is None:
            raise ValueError("EPS actual requires basis")
        if self.estimate_eps is not None and self.estimate_basis is None:
            raise ValueError("EPS estimate requires basis")
        if self.surprise_pct is not None and (
            self.actual_eps is None
            or self.estimate_eps in (None, 0)
            or self.actual_basis != self.estimate_basis
        ):
            raise ValueError("surprise requires comparable EPS actual and estimate")
        if self.revenue_surprise_pct is not None and (
            self.actual_revenue is None or self.estimate_revenue in (None, 0)
        ):
            raise ValueError("revenue surprise requires both actual and nonzero estimate")
        return self


class EarningsResponse(MarketResponse):
    upcoming: UpcomingEarnings | None = None
    history: list[EarningsRecord] = Field(default_factory=list, max_length=20)
    sources: list[SourceMetadata] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_earnings(self):
        _check_sources(
            self.mode,
            self.sources
            + ([self.upcoming.source] if self.upcoming else [])
            + [h.source for h in self.history],
        )
        ids = [h.event_id for h in self.history]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate earnings event IDs")
        for h in self.history:
            if h.event_id != canonical_earnings_id(self.market, self.symbol, h.fiscal_year, h.fiscal_quarter):
                raise ValueError("noncanonical earnings event ID")
        return self


class EarningsEvent(StrictModel):
    event_id: str
    fiscal_year: int
    fiscal_quarter: Quarter
    event_date: date
    published_at: AwareDatetime | None = None
    date_precision: Literal["date_only", "timestamp"]
    timing_basis: Literal["issuer_release", "vendor_report", "sec_8k_filing"]
    source: SourceMetadata

    @model_validator(mode="after")
    def check_precision(self):
        if self.date_precision == "timestamp" and self.published_at is None:
            raise ValueError("timestamp precision requires published_at")
        if self.date_precision == "date_only" and self.published_at is not None:
            raise ValueError("date-only evidence cannot claim publication timestamp")
        if self.timing_basis == "sec_8k_filing" and self.date_precision != "date_only":
            raise ValueError("8-K filing date cannot be silently treated as release timestamp")
        return self


class EventsResponse(MarketResponse):
    events: list[EarningsEvent] = Field(default_factory=list)
    sources: list[SourceMetadata] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_events(self):
        _check_sources(self.mode, self.sources + [e.source for e in self.events])
        ids = [e.event_id for e in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event IDs")
        for event in self.events:
            if event.event_id != canonical_earnings_id(
                self.market, self.symbol, event.fiscal_year, event.fiscal_quarter
            ):
                raise ValueError("noncanonical event ID")
        return self


class EventWindow(StrictModel):
    event_id: str = Field(pattern=r"^(US|CA):[A-Z0-9][A-Z0-9.]*:earnings_release:FY\d{4}Q[1-4]$")
    day_zero: date | None = None
    eligible: bool
    exclusion_reason: str | None = None
    excess_returns: dict[str, float | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_eligibility(self):
        if self.eligible and (self.exclusion_reason or self.day_zero is None):
            raise ValueError("eligible event needs day zero and no exclusion")
        if not self.eligible and not self.exclusion_reason:
            raise ValueError("excluded event needs reason")
        return self


class EventStudySummary(StrictModel):
    horizon: str = Field(min_length=1)
    eligible_n: int = Field(ge=8)
    mean_excess_return: float
    median_excess_return: float
    positive_share: float = Field(ge=0, le=1)


class EventStudyResponse(MarketResponse):
    benchmark_symbol: str = Field(min_length=1)
    pre_trading_days: Literal[5] = 5
    post_trading_days: Literal[20] = 20
    return_method: Literal["compounded_close_to_close_excess"] = "compounded_close_to_close_excess"
    minimum_sample: Literal[8] = 8
    eligible_event_count: int = Field(ge=0)
    events: list[EventWindow] = Field(default_factory=list)
    summary: list[EventStudySummary] | None = None
    sources: list[SourceMetadata] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_summary(self):
        _check_sources(self.mode, self.sources)
        actual = sum(event.eligible for event in self.events)
        if self.eligible_event_count != actual:
            raise ValueError("eligible count does not match event rows")
        if self.eligible_event_count < self.minimum_sample and self.summary:
            raise ValueError("no aggregate event statistics with fewer than eight eligible events")
        if self.summary and any(s.eligible_n > self.eligible_event_count for s in self.summary):
            raise ValueError("summary sample count exceeds eligible events")
        if len({e.event_id for e in self.events}) != len(self.events):
            raise ValueError("duplicate event IDs")
        if any(
            not e.event_id.startswith(f"{self.market}:{self.symbol}:earnings_release:") for e in self.events
        ):
            raise ValueError("event-study event belongs to a different listing")
        return self
