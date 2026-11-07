"""Dated earnings preview/review via Finnhub calendar; no inferred release dates.

The calendar's fiscal year/quarter belong to the issuer's fiscal reporting
period, not necessarily the calendar year of the release. EPS in the calendar
is vendor adjusted/non-GAAP and is never mixed with SEC GAAP diluted EPS.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import isfinite

from app.contracts.stock_research import (
    EarningsRecord,
    EarningsResponse,
    SourceMetadata,
    UpcomingEarnings,
    canonical_earnings_id,
)
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.providers.finnhub import FinnhubProvider

CALENDAR_URL = "https://finnhub.io/api/v1/calendar/earnings"
PUBLIC_SOURCE_URL = "https://finnhub.io/docs/api/earnings-calendar"
TIMINGS = {"bmo": "before_open", "amc": "after_close", "dmh": "during_session"}


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) else None


def _surprise(actual: float | None, estimate: float | None) -> float | None:
    if actual is None or estimate is None or estimate == 0:
        return None
    return 100 * (actual - estimate) / abs(estimate)


def _date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        # Explicit date-only calendar values; never infer an announcement time.
        return date.fromisoformat(value)
    except ValueError:
        return None


def unavailable(symbol: str, market: str, reason: str) -> EarningsResponse:
    return EarningsResponse(
        symbol=symbol,
        market=market,
        currency="CAD" if market == "CA" else "USD",
        mode="live",
        gaps=[reason],
    )


def parse_calendar(
    symbol: str, payload: dict, *, fetched_at: datetime, cached: bool, as_of: date
) -> EarningsResponse:
    """Only calendar rows with source-backed fiscal IDs and dates are retained.

    A dated calendar result can be reviewed. Undated /stock/earnings surprise
    entries cannot be projected onto an announcement date and are excluded.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("earningsCalendar"), list):
        raise DataUnavailable("Earnings calendar returned invalid or unavailable data")
    source = SourceMetadata(
        name="Finnhub earnings calendar (vendor estimates/adjusted EPS)",
        url=PUBLIC_SOURCE_URL,
        fetched_at=fetched_at,
        published_at=None,
        cached=cached,
        fixture=False,
    )
    future: list[tuple[date, int, int, dict]] = []
    historical: dict[str, EarningsRecord] = {}
    conflicting: set[str] = set()
    skipped = 0
    for row in payload["earningsCalendar"]:
        if not isinstance(row, dict) or row.get("symbol") != symbol:
            skipped += 1
            continue
        d = _date(row.get("date"))
        year, quarter = row.get("year"), row.get("quarter")
        if (
            d is None
            or isinstance(year, bool)
            or not isinstance(year, int)
            or not 1900 <= year <= 2200
            or isinstance(quarter, bool)
            or not isinstance(quarter, int)
            or quarter not in (1, 2, 3, 4)
        ):
            skipped += 1
            continue
        actual = _number(row.get("epsActual"))
        estimate = _number(row.get("epsEstimate"))
        revenue_actual = _number(row.get("revenueActual"))
        revenue_estimate = _number(row.get("revenueEstimate"))
        # Entries scheduled today may not yet have been released.
        if d > as_of or (d == as_of and actual is None and revenue_actual is None):
            future.append((d, year, quarter, row))
            continue
        if actual is None and revenue_actual is None:
            skipped += 1
            continue
        q = f"Q{quarter}"
        event_id = canonical_earnings_id("US", symbol, year, q)
        record = EarningsRecord(
            event_id=event_id,
            fiscal_year=year,
            fiscal_quarter=q,
            reported_on=d,
            actual_eps=actual,
            actual_basis="adjusted" if actual is not None else None,
            estimate_eps=estimate,
            estimate_basis="adjusted" if estimate is not None else None,
            surprise_pct=_surprise(actual, estimate),
            actual_revenue=revenue_actual,
            estimate_revenue=revenue_estimate,
            revenue_surprise_pct=_surprise(revenue_actual, revenue_estimate),
            source=source,
        )
        old = historical.get(event_id)
        if old is not None and old != record:
            conflicting.add(event_id)
        else:
            historical[event_id] = record
    for event_id in conflicting:
        historical.pop(event_id, None)

    upcoming = None
    if future:
        scheduled, year, quarter, row = min(future, key=lambda r: r[0])
        upcoming = UpcomingEarnings(
            scheduled_date=scheduled,
            date_status="estimated",  # A vendor calendar is not issuer confirmation.
            timing=TIMINGS.get(row.get("hour"), "unknown"),
            fiscal_year=year,
            fiscal_quarter=f"Q{quarter}",
            eps_estimate=_number(row.get("epsEstimate")),
            eps_estimate_basis="adjusted" if _number(row.get("epsEstimate")) is not None else None,
            revenue_estimate=_number(row.get("revenueEstimate")),
            source=source,
        )
    records = sorted(historical.values(), key=lambda record: record.reported_on, reverse=True)[:20]
    gaps = [
        "Calendar dates are vendor-scheduled or reported dates, not verified first-public release timestamps.",
        "Vendor EPS estimates/actuals are treated as adjusted/non-GAAP; do not compare with SEC GAAP diluted EPS.",
        "Calendar availability and older historical coverage depend on Finnhub account entitlement.",
        "No after-hours stock-price reaction is calculated in this phase.",
    ]
    if skipped or conflicting:
        gaps.append(
            f"Skipped {skipped} unusable calendar row(s) and {len(conflicting)} conflicting fiscal event(s)."
        )
    if not upcoming:
        gaps.append("No upcoming earnings date available from this calendar response.")
    if not records:
        gaps.append("No dated historical earnings results available from this calendar response.")
    return EarningsResponse(
        symbol=symbol,
        market="US",
        currency="USD",
        mode="live",
        upcoming=upcoming,
        history=records,
        sources=[source],
        gaps=gaps,
    )


def fetch_earnings(symbol: str, finnhub: FinnhubProvider, *, as_of: date | None = None) -> EarningsResponse:
    """Query a bounded calendar window with Stocker's existing keyed transport.

    Missing access is disclosed; provider failures remain errors, never fixtures.
    Historical /stock/earnings records are intentionally not added because they
    do not carry the earnings announcement date needed by EarningsRecord.
    """
    if not finnhub.settings.finnhub_api_key:
        return unavailable(symbol, "US", "FINNHUB_API_KEY is not configured; earnings calendar unavailable.")
    as_of = as_of or datetime.now(UTC).date()
    response = finnhub.http.fetch(
        CALENDAR_URL,
        params={
            "symbol": symbol,
            "from": (as_of - timedelta(days=30)).isoformat(),
            "to": (as_of + timedelta(days=45)).isoformat(),
            "token": finnhub.settings.finnhub_api_key,
        },
        ttl=3600,
        interval=1.1,
    )
    return parse_calendar(
        symbol, response.data, fetched_at=response.fetched_at, cached=response.cached, as_of=as_of
    )


def fixture_earnings(symbol: str, companies: dict, *, as_of: date | None = None) -> EarningsResponse:
    """Explicit, deterministic-for-a-given-day invented demo data, never live evidence."""
    if symbol not in companies:
        raise DataUnavailable("No synthetic fixture exists for this listing")
    as_of = as_of or datetime.now(UTC).date()
    if "revenue" not in companies[symbol]:
        return EarningsResponse(
            symbol=symbol,
            market="US",
            currency="USD",
            mode="fixtures",
            gaps=["No synthetic earnings dataset for this ETF fixture."],
        )
    source = SourceMetadata(
        name="Invented Stocker demo earnings — NOT real market data",
        url="https://example.org/stocker/synthetic-earnings",
        fetched_at=datetime.now(UTC),
        fixture=True,
    )
    quarter = "Q1"
    record = EarningsRecord(
        event_id=canonical_earnings_id("US", symbol, as_of.year, quarter),
        fiscal_year=as_of.year,
        fiscal_quarter=quarter,
        reported_on=as_of - timedelta(days=70),
        actual_eps=1.25,
        actual_basis="adjusted",
        estimate_eps=1.20,
        estimate_basis="adjusted",
        surprise_pct=_surprise(1.25, 1.20),
        actual_revenue=1_250_000_000,
        estimate_revenue=1_200_000_000,
        revenue_surprise_pct=_surprise(1_250_000_000, 1_200_000_000),
        source=source,
    )
    return EarningsResponse(
        symbol=symbol,
        market="US",
        currency="USD",
        mode="fixtures",
        upcoming=UpcomingEarnings(
            scheduled_date=as_of + timedelta(days=28),
            date_status="estimated",
            timing="unknown",
            eps_estimate=1.40,
            eps_estimate_basis="adjusted",
            revenue_estimate=1_400_000_000,
            fiscal_year=as_of.year,
            fiscal_quarter="Q2",
            source=source,
        ),
        history=[record],
        sources=[source],
        gaps=["SYNTHETIC earnings and estimates are invented for testing; no live provider was contacted."],
    )
