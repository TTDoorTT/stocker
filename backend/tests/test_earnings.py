"""Isolated, source-backed earnings calendar parsing; no network calls or LLM."""

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.contracts.stock_research import EarningsResponse
from app.modules.market_data.earnings import (
    _surprise,
    fetch_earnings,
    fixture_earnings,
    parse_calendar,
    unavailable,
)
from app.modules.market_data.errors import DataUnavailable

AS_OF = date(2026, 11, 7)
FETCHED = datetime(2026, 11, 7, 17, 0, tzinfo=UTC)


def row(**kwargs):
    return {
        "symbol": "AAPL",
        "date": "2026-10-29",
        "year": 2026,
        "quarter": 4,
        "hour": "amc",
        "epsActual": 1.25,
        "epsEstimate": 1.20,
        "revenueActual": 1250000000,
        "revenueEstimate": 1200000000,
        **kwargs,
    }


def parse(*rows, cached=False):
    return parse_calendar(
        "AAPL", {"earningsCalendar": list(rows)}, fetched_at=FETCHED, cached=cached, as_of=AS_OF
    )


def test_dated_actual_and_upcoming_keep_fiscal_year_and_revenue():
    response = parse(
        row(),
        row(
            date="2026-12-01",
            year=2027,
            quarter=1,
            hour="bmo",
            epsActual=None,
            epsEstimate=1.4,
            revenueActual=None,
            revenueEstimate=1_400_000_000,
        ),
    )
    assert response.mode == "live" and response.currency == "USD"
    assert len(response.history) == 1
    record = response.history[0]
    assert record.event_id == "US:AAPL:earnings_release:FY2026Q4"
    assert record.reported_on == date(2026, 10, 29)
    assert record.actual_basis == record.estimate_basis == "adjusted"
    assert record.surprise_pct == pytest.approx(100 * (1.25 - 1.2) / 1.2)
    assert record.revenue_surprise_pct == pytest.approx(100 * (1250 - 1200) / 1200)
    assert response.upcoming.fiscal_year == 2027  # Fiscal != release calendar year.
    assert response.upcoming.fiscal_quarter == "Q1"
    assert response.upcoming.date_status == "estimated"
    assert response.upcoming.timing == "before_open"
    assert response.upcoming.eps_estimate == pytest.approx(1.4)
    assert response.upcoming.revenue_estimate == 1_400_000_000
    assert response.upcoming.eps_estimate_basis == "adjusted"


def test_zero_eps_estimate_not_divided_and_negative_estimate_uses_absolute_denominator():
    result = parse(row(epsEstimate=0))
    assert result.history[0].surprise_pct is None
    assert _surprise(-0.30, -0.50) == pytest.approx(40.0)
    assert _surprise(1.1, -0.0) is None


def test_invalid_numbers_are_not_fabricated_and_date_only_is_not_timestamp():
    result = parse(row(epsActual=float("nan"), epsEstimate=float("inf"), revenueActual=100))
    assert result.history[0].actual_eps is None
    assert result.history[0].estimate_eps is None
    assert result.history[0].surprise_pct is None
    assert result.sources[0].published_at is None


def test_conflicting_duplicate_fiscal_quarters_are_excluded():
    result = parse(row(), row(date="2026-10-30", epsActual=1.5))
    assert not result.history
    assert any("conflicting" in gap for gap in result.gaps)


def test_wrong_symbol_bad_quarter_missing_actual_and_bad_date_skipped():
    result = parse(
        row(symbol="MSFT"),
        row(quarter=5),
        row(date="2026-10-01", epsActual=None, revenueActual=None),
        row(date="nonsense"),
    )
    assert not result.history and result.upcoming is None
    assert any("Skipped 4" in gap for gap in result.gaps)


def test_today_with_unknown_actual_is_upcoming_not_historical():
    result = parse(row(date="2026-11-07", epsActual=None, revenueActual=None))
    assert not result.history
    assert result.upcoming.scheduled_date == AS_OF


def test_finnhub_cached_source_preserves_original_fetch_time_and_no_key_leak():
    result = parse(row(), cached=True)
    assert result.sources[0].cached is True
    assert result.sources[0].fetched_at == FETCHED
    assert "token" not in str(result.sources[0].url)
    assert "calendar" in str(result.sources[0].url)


def test_provider_transport_called_once_with_bounded_date_window_and_no_model():
    seen = []

    def fetch(url, **kwargs):
        seen.append((url, kwargs))
        return SimpleNamespace(data={"earningsCalendar": [row()]}, fetched_at=FETCHED, cached=False)

    provider = SimpleNamespace(
        settings=SimpleNamespace(finnhub_api_key="private-key"),
        http=SimpleNamespace(fetch=fetch),
    )
    result = fetch_earnings("AAPL", provider, as_of=AS_OF)
    assert len(result.history) == 1
    assert len(seen) == 1
    assert seen[0][1]["params"]["from"] == "2026-10-08"
    assert seen[0][1]["params"]["to"] == "2026-12-22"
    assert seen[0][1]["params"]["token"] == "private-key"
    assert "private-key" not in str(result.model_dump(mode="json"))


def test_missing_key_does_not_contact_provider():
    provider = SimpleNamespace(settings=SimpleNamespace(finnhub_api_key=""), http=None)
    result = fetch_earnings("AAPL", provider, as_of=AS_OF)
    assert result.history == [] and result.upcoming is None
    assert result.gaps and result.sources == []


def test_invalid_provider_payload_is_unavailable_not_fake_response():
    with pytest.raises(DataUnavailable):
        parse_calendar("AAPL", {"error": "denied"}, fetched_at=FETCHED, cached=False, as_of=AS_OF)


def test_fixture_mode_is_labeled_and_never_interleaved_with_live():
    result = fixture_earnings("AAPL", {"AAPL": {"revenue": [1, 2]}}, as_of=AS_OF)
    assert result.mode == "fixtures" and result.history[0].source.fixture is True
    assert result.sources[0].fixture is True
    assert result.upcoming.source.fixture is True
    assert "SYNTHETIC" in " ".join(result.gaps)
    item = result.model_dump(mode="json")
    item["mode"] = "live"
    with pytest.raises(ValidationError):
        EarningsResponse.model_validate(item)


def test_fixture_without_financials_and_canadian_unavailable():
    fixture = fixture_earnings("SPY", {"SPY": {"name": "ETF"}}, as_of=AS_OF)
    assert fixture.history == [] and fixture.upcoming is None
    ca = unavailable("RY.TO", "CA", "No rights to earnings dates")
    assert ca.market == "CA" and ca.currency == "CAD" and ca.history == []


def test_revenue_surprise_requires_comparable_present_values():
    payload = parse(row()).model_dump(mode="json")
    payload["history"][0]["estimate_revenue"] = None
    with pytest.raises(ValidationError):
        EarningsResponse.model_validate(payload)
