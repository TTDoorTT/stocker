"""Dated historical US earnings events, with conservative vendor provenance.

A Finnhub calendar's reported date is never asserted to be the exact original
public earnings announcement time. Dates alone can support a carefully labeled
POST-DATE drift study, not an intraday or announcement-jump analysis.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.contracts.stock_research import (
    EarningsEvent,
    EventsResponse,
    SourceMetadata,
    canonical_earnings_id,
)
from app.modules.market_data.earnings import CALENDAR_URL, parse_calendar
from app.modules.market_data.providers.finnhub import FinnhubProvider


def empty_events(symbol: str, market: str, mode: str, reason: str) -> EventsResponse:
    return EventsResponse(
        symbol=symbol,
        market=market,
        currency="CAD" if market == "CA" else "USD",
        mode=mode,
        gaps=[reason],
    )


def parse_historical_events(
    symbol: str, payload: dict, fetched_at: datetime, *, cached: bool, as_of: date
) -> EventsResponse:
    """Use Phase 3's fiscal-ID/duplicate validation; retain dates only."""
    earnings = parse_calendar(symbol, payload, fetched_at=fetched_at, cached=cached, as_of=as_of)
    events = [
        EarningsEvent(
            event_id=record.event_id,
            fiscal_year=record.fiscal_year,
            fiscal_quarter=record.fiscal_quarter,
            event_date=record.reported_on,
            date_precision="date_only",
            timing_basis="vendor_report",
            source=record.source,
        )
        for record in earnings.history
        if record.reported_on < as_of
    ]
    return EventsResponse(
        symbol=symbol,
        market="US",
        currency="USD",
        mode="live",
        events=events,
        sources=earnings.sources,
        gaps=[
            "Finnhub calendar provides a vendor-reported date, not a verified earnings release timestamp.",
            "Past dates and actuals are subject to the configured account's coverage and data rights.",
            "Only rows with dated actual results and valid fiscal period IDs are included.",
            *(
                ["No usable historical dated earnings rows in the requested five-year window."]
                if not events
                else []
            ),
        ],
    )


def fetch_historical_events(
    symbol: str, finnhub: FinnhubProvider, *, as_of: date | None = None
) -> EventsResponse:
    if not finnhub.settings.finnhub_api_key:
        return empty_events(
            symbol, "US", "live", "FINNHUB_API_KEY not configured; historical earnings events unavailable."
        )
    as_of = as_of or datetime.now(UTC).date()
    response = finnhub.http.fetch(
        CALENDAR_URL,
        params={
            "symbol": symbol,
            "from": (as_of - timedelta(days=5 * 366)).isoformat(),
            "to": as_of.isoformat(),
            "token": finnhub.settings.finnhub_api_key,
        },
        ttl=21600,
        interval=1.1,
    )
    return parse_historical_events(
        symbol, response.data, response.fetched_at, cached=response.cached, as_of=as_of
    )


def fixture_events(symbol: str, companies: dict, *, as_of: date) -> EventsResponse:
    """At least ten visible, wholly invented quarterly events for offline tests."""
    if symbol not in companies or "revenue" not in companies[symbol]:
        return empty_events(symbol, "US", "fixtures", "No synthetic earnings events for this ticker.")
    source = SourceMetadata(
        name="Stocker SYNTHETIC earnings dates — not real events",
        url="https://example.org/stocker/synthetic-event-study",
        fetched_at=datetime.now(UTC),
        fixture=True,
    )
    events = []
    for i in range(10):
        event_date = as_of - timedelta(days=65 + i * 96)
        q = f"Q{(event_date.month - 1) // 3 + 1}"
        events.append(
            EarningsEvent(
                event_id=canonical_earnings_id("US", symbol, event_date.year, q),
                fiscal_year=event_date.year,
                fiscal_quarter=q,
                event_date=event_date,
                date_precision="date_only",
                timing_basis="vendor_report",
                source=source,
            )
        )
    return EventsResponse(
        symbol=symbol,
        market="US",
        currency="USD",
        mode="fixtures",
        events=events,
        sources=[source],
        gaps=["SYNTHETIC: dates are completely invented, not real earnings announcements."],
    )
