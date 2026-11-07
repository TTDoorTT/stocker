"""U.S. SEC companyfacts to standalone quarterly statements, no LLM or scraping.

Annual facts used by the research pipeline are deliberately untouched. SEC
``fy``/``fp`` describe filing contexts; comparative rows are filtered by a
current-period filing lag, and time ranges are validated rather than guessed.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from math import isfinite

from app.contracts.stock_research import (
    FinancialPeriod,
    FinancialTrendsResponse,
    MetricValue,
    SourceMetadata,
)
from app.finance.quarterly import ADDITIVE_METRICS, ALL_METRICS, UNITS, calculation_id, trailing_twelve_months
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.sec import SecProvider

# One concept per metric per response prevents silently combining incompatible tags.
CONCEPTS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "net_income": ("NetIncomeLoss",),
    "gross_profit": ("GrossProfit",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "diluted_eps": ("EarningsPerShareDiluted",),
}


@dataclass(frozen=True)
class Observation:
    metric: str
    concept: str
    value: float
    unit: str
    start: date
    end: date
    filed: date
    fiscal_year: int
    fiscal_period: str
    form: str
    accession: str

    @property
    def duration(self) -> int:
        return (self.end - self.start).days

    @property
    def evidence_id(self) -> str:
        return calculation_id(
            "sec-fact:" + self.metric,
            [self.concept, self.start.isoformat(), self.end.isoformat(), self.accession, str(self.value)],
        ).replace("calc-", "sec-", 1)


def _observations(metric: str, taxonomy: dict, as_of: date) -> list[Observation]:
    choices: list[tuple[date, int, list[Observation]]] = []
    for rank, concept in enumerate(CONCEPTS[metric]):
        candidate = taxonomy.get(concept, {})
        raw = candidate.get("units", {}).get(UNITS[metric], []) if isinstance(candidate, dict) else []
        if not isinstance(raw, list):
            continue
        accepted = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            try:
                start, end, filed = (date.fromisoformat(row[k]) for k in ("start", "end", "filed"))
                value = row["val"]
                fy = row["fy"]
                fp = row["fp"]
                form = row["form"]
                accn = row["accn"]
                if isinstance(value, bool) or not isinstance(value, (float, int)):
                    continue
                if isinstance(fy, bool) or not isinstance(fy, int) or not 1900 <= fy <= 2200:
                    continue
                if not isinstance(accn, str) or not accn or len(accn) > 64:
                    continue
                if not isfinite(value) or start >= end or not end <= filed <= as_of:
                    continue
                delay = (filed - end).days
                if form == "10-Q" and fp in ("Q1", "Q2", "Q3") and delay <= 150:
                    pass
                elif form == "10-K" and fp == "FY" and delay <= 200:
                    pass
                else:
                    continue
                accepted.append(
                    Observation(
                        metric, concept, float(value), UNITS[metric], start, end, filed, fy, fp, form, accn
                    )
                )
            except (ValueError, TypeError, KeyError, OverflowError):
                continue
        if accepted:
            # Choose the most recently available concept, with configured order as tie-breaker.
            choices.append((max(row.end for row in accepted), -rank, accepted))
    return max(choices, key=lambda option: (option[0], option[1]))[2] if choices else []


def _latest(rows: list[Observation]) -> Observation | None:
    return max(rows, key=lambda r: (r.filed, r.accession)) if rows else None


def _reported(rows: list[Observation], fy: int, fp: str, minimum: int, maximum: int) -> Observation | None:
    return _latest(
        [
            r
            for r in rows
            if r.fiscal_year == fy and r.fiscal_period == fp and minimum <= r.duration <= maximum
        ]
    )


@dataclass(frozen=True)
class QuarterFact:
    value: float
    unit: str
    start: date
    end: date
    filed: date
    form: str
    accession: str
    evidence: tuple[str, ...]
    derived: bool

    def metric(self, name: str) -> MetricValue:
        return MetricValue(
            value=self.value,
            unit=self.unit,
            status="derived" if self.derived else "as_reported",
            evidence_ids=list(self.evidence),
            calculation_id=calculation_id("quarter:" + name, list(self.evidence)) if self.derived else None,
        )


def _direct(row: Observation) -> QuarterFact:
    return QuarterFact(
        row.value, row.unit, row.start, row.end, row.filed, row.form, row.accession, (row.evidence_id,), False
    )


def _difference(current: Observation, previous: Observation, metric: str) -> QuarterFact | None:
    # Duration-based identity, not calendar-year or unrelated 'fy' arithmetic.
    if (
        metric not in ADDITIVE_METRICS
        or current.fiscal_year != previous.fiscal_year
        or current.start != previous.start
        or current.unit != previous.unit
        or not 65 <= (current.end - previous.end).days <= 110
    ):
        return None
    return QuarterFact(
        current.value - previous.value,
        current.unit,
        previous.end + timedelta(days=1),
        current.end,
        current.filed,
        current.form,
        current.accession,
        (current.evidence_id, previous.evidence_id),
        True,
    )


def _quarter_fact(rows: list[Observation], fy: int, q: int, metric: str) -> QuarterFact | None:
    fp = f"Q{q}"
    if q < 4:
        direct = _reported(rows, fy, fp, 65, 110)
        if direct:
            return _direct(direct)
        if q == 1 or metric == "diluted_eps":
            return None
        ytd_ranges = {2: (150, 220), 3: (230, 310)}
        lo, hi = ytd_ranges[q]
        current = _reported(rows, fy, fp, lo, hi)
        prior_lo, prior_hi = (65, 110) if q == 2 else (150, 220)
        previous = _reported(rows, fy, f"Q{q - 1}", prior_lo, prior_hi)
        if current and previous:
            return _difference(current, previous, metric)
        return None
    annual = _reported(rows, fy, "FY", 335, 390)
    if annual is None:
        return None
    # A genuine standalone Q4 context in the 10-K takes precedence.
    standalone = _reported(rows, fy, "FY", 65, 110)
    if standalone and standalone.end == annual.end:
        return _direct(standalone)
    if metric == "diluted_eps":
        return None  # Weighted-average EPS cannot be reconstructed by subtraction.
    nine_months = _reported(rows, fy, "Q3", 230, 310)
    if nine_months:
        return _difference(annual, nine_months, metric)
    return None


def parse_sec_quarters(
    symbol: str, payload: dict, fetched_at: datetime, *, cached: bool = False
) -> FinancialTrendsResponse:
    """Extract directly reported or safely derived standalone quarters.

    Unknown, amended, partial, comparative and mismatched contexts are excluded;
    a missing metric is never estimated.
    """
    if not isinstance(payload, dict):
        raise DataUnavailable("SEC companyfacts returned an invalid object")
    facts = payload.get("facts")
    taxonomy = facts.get("us-gaap", {}) if isinstance(facts, dict) else {}
    if not isinstance(taxonomy, dict):
        raise DataUnavailable("SEC companyfacts lacks a valid US-GAAP object")
    cik = payload.get("cik")
    if isinstance(cik, bool) or not isinstance(cik, int) or cik <= 0:
        raise DataUnavailable("SEC companyfacts CIK unavailable")
    root_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    source = SourceMetadata(
        name="SEC EDGAR companyfacts (US-GAAP)",
        url=root_url,
        fetched_at=fetched_at,
        published_at=None,  # Filing dates are available, exact publication time is not.
        cached=cached,
        fixture=False,
    )
    observations = {name: _observations(name, taxonomy, fetched_at.date()) for name in ALL_METRICS}
    years = sorted(
        {row.fiscal_year for rows in observations.values() for row in rows if row.form in ("10-Q", "10-K")},
        reverse=True,
    )[:8]
    periods = []
    for fy in years:
        for q in range(1, 5):
            candidates = {
                metric: val
                for metric in ALL_METRICS
                if (val := _quarter_fact(observations[metric], fy, q, metric)) is not None
            }
            if not candidates:
                continue
            anchor = next((candidates[name] for name in ALL_METRICS if name in candidates), None)
            if anchor is None:
                continue
            consistent = {
                name: fact.metric(name)
                for name, fact in candidates.items()
                if fact.start == anchor.start and fact.end == anchor.end
            }
            periods.append(
                FinancialPeriod(
                    period_id=f"FY{fy}Q{q}",
                    fiscal_year=fy,
                    fiscal_quarter=f"Q{q}",
                    period_kind="standalone_quarter",
                    period_start=anchor.start,
                    period_end=anchor.end,
                    filed_on=anchor.filed,
                    form=anchor.form,
                    accession=anchor.accession,
                    metrics=consistent,
                    source=source,
                )
            )
    periods.sort(key=lambda p: (p.fiscal_year, int(p.fiscal_quarter[1])), reverse=True)
    periods = periods[:16]
    gaps = [
        "SEC companyfacts filings have date-level timestamps, not confirmed earnings-release times.",
        "Quarterly metrics require comparable standalone contexts. YTD and annual totals are subtracted only for additive metrics with matched starts and adjacent period ends.",
        "Derived Q4 is FY minus nine-month YTD, not a separately reported quarter. Weighted diluted EPS is not derived by subtraction.",
        "SEC fy/fp identifies the filing context; comparative observations and ambiguous periods are excluded by filing-date and duration rules.",
    ]
    if not periods:
        gaps.append("No verifiable current-period quarterly SEC observations were found for this issuer.")
    return FinancialTrendsResponse(
        symbol=symbol,
        market="US",
        currency="USD",
        mode="live",
        frequency="quarterly",
        periods=periods,
        ttm=trailing_twelve_months(periods),
        sources=[source],
        gaps=gaps,
    )


def fetch_sec_financial_trends(symbol: str, sec: SecProvider) -> FinancialTrendsResponse:
    """Reuse the existing SEC ticker index, user-agent and HTTPS transport."""
    match = next((row for row in sec.tickers() if row["ticker"].upper() == symbol), None)
    if match is None:
        return no_coverage(symbol, "US", "live", "SEC issuer mapping unavailable for this ticker.")
    cik = int(match["cik_str"])
    response = sec.http.fetch(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
        headers=sec.headers(),
        ttl=21600,
        interval=0.2,
    )
    if not isinstance(response.data, dict) or response.data.get("cik") != cik:
        raise DataUnavailable("SEC companyfacts CIK does not match the requested issuer")
    return parse_sec_quarters(symbol, response.data, response.fetched_at, cached=response.cached)


def no_coverage(symbol: str, market: str, mode: str, reason: str) -> FinancialTrendsResponse:
    return FinancialTrendsResponse(
        symbol=symbol,
        market=market,
        currency="CAD" if market == "CA" else "USD",
        mode=mode,
        frequency="quarterly",
        periods=[],
        sources=[],
        ttm=trailing_twelve_months([]),
        gaps=[reason],
    )


def _subtract_months(day: date, months: int) -> date:
    month_index = day.year * 12 + day.month - 1 - months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def fixture_financial_trends(symbol: str, companies: dict) -> FinancialTrendsResponse:
    """Synthetic offline values; never request SEC or relabel them as live facts."""
    company = companies.get(symbol)
    if company is None:
        raise DataUnavailable("No synthetic fixture exists for this listing")
    yearly = company.get("revenue", [])
    if not yearly:
        return no_coverage(symbol, "US", "fixtures", "Synthetic fixture has no company financial statements.")
    fiscal_year = 2023 + len(yearly) - 1
    month, day = map(int, company["fiscal_end"].split("-"))
    end = date(fiscal_year, month, day)
    source = SourceMetadata(
        name="Synthetic offline fixture — invented financial facts",
        url="https://example.org/stocker/synthetic-fixture-not-market-data",
        fetched_at=datetime.now(UTC),
        fixture=True,
    )
    weights = [0.20, 0.24, 0.27, 0.29]
    periods = []
    for q in range(1, 5):
        prev_end = _subtract_months(end, 3 * (4 - q))
        start = _subtract_months(end, 3 * (5 - q)) + timedelta(days=1)
        metrics = {}
        for metric, company_field in (
            ("revenue", "revenue"),
            ("net_income", "net_income"),
            ("operating_cash_flow", "cashflow"),
            ("diluted_eps", "eps"),
        ):
            history = company.get(company_field, [])
            if not history:
                continue
            metrics[metric] = MetricValue(
                value=history[-1] * weights[q - 1],
                unit=UNITS[metric],
                status="as_reported",
                evidence_ids=[f"synthetic:{symbol}:FY{fiscal_year}Q{q}:{metric}"],
            )
        periods.append(
            FinancialPeriod(
                period_id=f"FY{fiscal_year}Q{q}",
                fiscal_year=fiscal_year,
                fiscal_quarter=f"Q{q}",
                period_kind="standalone_quarter",
                period_start=start,
                period_end=prev_end,
                filed_on=prev_end + timedelta(days=35),
                form="10-K" if q == 4 else "10-Q",
                accession=f"synthetic-{symbol}-Q{q}",
                metrics=metrics,
                source=source,
            )
        )
    periods.reverse()
    return FinancialTrendsResponse(
        symbol=symbol,
        market="US",
        currency="USD",
        mode="fixtures",
        frequency="quarterly",
        periods=periods,
        ttm=trailing_twelve_months(periods),
        sources=[source],
        gaps=["SYNTHETIC quarterly observations are invented for offline demonstration, not real filings."],
    )
