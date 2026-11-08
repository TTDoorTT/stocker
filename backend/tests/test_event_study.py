"""Deterministic post-date drift tests. No real market provider or AI calls."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.contracts.stock_research import (
    CandleBar,
    CandleSeries,
    EarningsEvent,
    EventsResponse,
    SourceMetadata,
    canonical_earnings_id,
)
from app.finance.event_study import calculate_event_study, empty_study
from app.modules.market_data.event_sources import fixture_events, parse_historical_events

AS_OF = date(2026, 11, 7)
FETCHED = datetime(2026, 11, 7, 18, tzinfo=UTC)


def source(*, fixture=False):
    return SourceMetadata(
        name="Test fixture" if fixture else "Finnhub vendor calendar",
        url="https://example.org/source",
        fetched_at=FETCHED,
        fixture=fixture,
    )


def dates():
    beginning = date(2023, 1, 2)
    return [
        beginning + timedelta(days=i) for i in range(1350) if (beginning + timedelta(days=i)).weekday() < 5
    ]


def candles(symbol, *, missing=None, adjusted=True, mode="live"):
    bars = []
    for index, day in enumerate(dates()):
        if day == missing:
            continue
        # Price growth deliberately differs, so excess return is non-zero.
        p = (100 if symbol == "AAPL" else 400) * (1 + (0.0009 if symbol == "AAPL" else 0.0003) * index)
        bars.append(
            CandleBar(
                date=day,
                open=p,
                high=p * 1.01,
                low=p * 0.99,
                close=p,
                adjusted_close=p if adjusted else None,
                volume=1000,
            )
        )
    return CandleSeries(
        symbol=symbol,
        market="US",
        currency="USD",
        mode=mode,
        range="5y",
        interval="1d",
        price_basis="provider_ohlc",
        adjustment_note="Test series; close not a real total return",
        source=source(fixture=mode == "fixtures"),
        bars=bars,
    )


def events(days, *, mode="live"):
    result = []
    used_ids = set()
    for d in days:
        q_number = (d.month - 1) // 3 + 1
        q = f"Q{q_number}"
        eid = canonical_earnings_id("US", "AAPL", d.year, q)
        if eid in used_ids:  # Synthetic overlap test: different fiscal period, nearby release dates.
            q = f"Q{q_number - 1 if q_number > 1 else 4}"
            eid = canonical_earnings_id("US", "AAPL", d.year, q)
        used_ids.add(eid)
        result.append(
            EarningsEvent(
                event_id=eid,
                fiscal_year=d.year,
                fiscal_quarter=q,
                event_date=d,
                timing_basis="vendor_report",
                date_precision="date_only",
                source=source(fixture=mode == "fixtures"),
            )
        )
    return EventsResponse(
        symbol="AAPL",
        market="US",
        currency="USD",
        mode=mode,
        events=result,
        sources=[source(fixture=mode == "fixtures")],
    )


def test_post_date_day_zero_is_first_strictly_later_trading_day():
    e = events([date(2023, 4, 14)])  # Friday
    result = calculate_event_study(e, candles("AAPL"), candles("SPY"), as_of=AS_OF)
    assert result.eligible_event_count == 1
    assert result.events[0].day_zero == date(2023, 4, 17)
    assert result.events[0].excess_returns["0"] == pytest.approx(0.0)
    assert result.events[0].excess_returns["1"] > 0
    assert result.summary is None
    assert "immediate earnings reaction" in " ".join(result.gaps)


def test_weekend_event_uses_monday_session_without_inventing_saturday_bar():
    result = calculate_event_study(events([date(2023, 4, 15)]), candles("AAPL"), candles("SPY"), as_of=AS_OF)
    assert result.events[0].day_zero == date(2023, 4, 17)


def test_insufficient_sample_displays_no_aggregate():
    d = [date(2023, 4, 14) + timedelta(days=98 * i) for i in range(7)]
    result = calculate_event_study(events(d), candles("AAPL"), candles("SPY"), as_of=AS_OF)
    assert result.eligible_event_count == 7 and result.summary is None


def test_eight_non_overlapping_complete_events_have_mean_median_positive_share():
    d = [date(2023, 4, 14) + timedelta(days=98 * i) for i in range(8)]
    result = calculate_event_study(events(d), candles("AAPL"), candles("SPY"), as_of=AS_OF)
    assert result.eligible_event_count == 8
    assert [s.horizon for s in result.summary] == ["+1", "+5", "+20"]
    assert all(s.eligible_n == 8 for s in result.summary)
    assert result.summary[0].mean_excess_return > 0
    assert 0 <= result.summary[0].positive_share <= 1


def test_missing_adjusted_close_does_not_use_raw_unadjusted_close():
    result = calculate_event_study(
        events([date(2023, 4, 14)]), candles("AAPL", adjusted=False), candles("SPY"), as_of=AS_OF
    )
    assert result.eligible_event_count == 0 and "Adjusted close" in result.events[0].exclusion_reason


def test_missing_stock_session_does_not_compress_trading_calendar():
    missing = date(2023, 4, 20)
    result = calculate_event_study(
        events([date(2023, 4, 14)]), candles("AAPL", missing=missing), candles("SPY"), as_of=AS_OF
    )
    assert result.eligible_event_count == 0 and "trading session" in result.events[0].exclusion_reason


def test_incomplete_forward_or_prior_window_excluded():
    result = calculate_event_study(
        events([date(2023, 1, 3), date(2026, 9, 12)]), candles("AAPL"), candles("SPY"), as_of=AS_OF
    )
    assert result.eligible_event_count == 0
    assert all(not x.eligible for x in result.events)


def test_overlapping_earnings_windows_are_not_double_counted():
    result = calculate_event_study(
        events([date(2023, 4, 14), date(2023, 5, 1)]), candles("AAPL"), candles("SPY"), as_of=AS_OF
    )
    assert result.eligible_event_count == 1
    assert "Overlapping" in result.events[1].exclusion_reason


def test_currency_and_modes_must_match():
    a, b = candles("AAPL"), candles("SPY", mode="fixtures")
    with pytest.raises(ValueError, match="Incompatible"):
        calculate_event_study(events([date(2023, 4, 14)]), a, b, as_of=AS_OF)


def test_empty_study_excludes_all_and_preserves_gaps():
    e = events([date(2023, 4, 14)])
    result = empty_study(e, "No 5-year daily adjusted-price history")
    assert result.eligible_event_count == 0 and result.summary is None
    assert "5-year" in result.gaps[-1]


def test_historical_calendar_filters_future_and_date_only_precision():
    payload = {
        "earningsCalendar": [
            {
                "symbol": "AAPL",
                "date": "2026-10-29",
                "year": 2026,
                "quarter": 4,
                "epsActual": 1.2,
                "epsEstimate": 1.1,
            },
            {
                "symbol": "AAPL",
                "date": "2026-12-01",
                "year": 2027,
                "quarter": 1,
                "epsEstimate": 1.4,
                "epsActual": None,
            },
        ]
    }
    result = parse_historical_events("AAPL", payload, FETCHED, cached=True, as_of=AS_OF)
    assert len(result.events) == 1
    assert result.events[0].date_precision == "date_only"
    assert result.events[0].published_at is None
    assert result.events[0].source.cached


def test_fixture_generates_ten_unique_synthetic_events():
    result = fixture_events("AAPL", {"AAPL": {"revenue": [1, 2]}}, as_of=AS_OF)
    assert len(result.events) == 10
    assert len({e.event_id for e in result.events}) == 10
    assert all(e.source.fixture for e in result.events)
    assert fixture_events("SPY", {"SPY": {}}, as_of=AS_OF).events == []
