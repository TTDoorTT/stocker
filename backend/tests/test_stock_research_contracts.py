"""Phase 0 contracts only: entirely synthetic, no providers, API routes, or LLM."""

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.stock_research import (
    CandleSeries,
    EarningsResponse,
    EventsResponse,
    EventStudyResponse,
    FinancialTrendsResponse,
    canonical_earnings_id,
)

DATA = json.loads((Path(__file__).parent / "fixtures" / "stock_research_contracts.json").read_text())


def source():
    return copy.deepcopy(DATA["source"])


def candles(symbol="AAPL", market="US", currency="USD"):
    return {
        "symbol": symbol,
        "market": market,
        "currency": currency,
        "mode": "fixtures",
        "range": "1y",
        "interval": "1d",
        "price_basis": "provider_ohlc",
        "adjustment_note": "Synthetic provider close; adjusted close is separate from candle OHLC",
        "source": source(),
        "bars": copy.deepcopy(DATA["candle_bars"]),
        "gaps": [],
    }


def metric(value, unit="USD"):
    return {"value": value, "unit": unit, "status": "as_reported", "evidence_ids": ["synthetic:fact"]}


def period(year, quarter, value=100.0, kind="standalone_quarter"):
    dates = {
        "Q1": ("01-01", "03-31"),
        "Q2": ("04-01", "06-30"),
        "Q3": ("07-01", "09-30"),
        "Q4": ("10-01", "12-31"),
    }
    first, last = dates[quarter]
    return {
        "period_id": f"FY{year}{quarter}",
        "fiscal_year": year,
        "fiscal_quarter": quarter,
        "period_kind": kind,
        "period_start": f"{year}-{first}",
        "period_end": f"{year}-{last}",
        "filed_on": (f"{year + 1}-02-01" if quarter == "Q4" else f"{year}-11-01"),
        "form": "10-Q",
        "accession": f"fixture-{year}-{quarter}",
        "metrics": {"revenue": metric(value)},
        "source": source(),
    }


def trends():
    periods = [period(2025, "Q3"), period(2025, "Q4"), period(2026, "Q1"), period(2026, "Q2")]
    return {
        "symbol": "AAPL",
        "market": "US",
        "currency": "USD",
        "mode": "fixtures",
        "frequency": "quarterly",
        "periods": periods,
        "sources": [source()],
        "gaps": [],
        "ttm": {
            "revenue": {
                "value": 400.0,
                "unit": "USD",
                "status": "available",
                "input_period_ids": [p["period_id"] for p in periods],
                "calculation_id": "synthetic:ttm",
            }
        },
    }


def earnings(symbol="AAPL"):
    event_id = canonical_earnings_id("US", symbol, 2026, "Q2")
    return {
        "symbol": symbol,
        "market": "US",
        "currency": "USD",
        "mode": "fixtures",
        "upcoming": {"scheduled_date": "2026-12-01", "date_status": "estimated", "source": source()},
        "history": [
            {
                "event_id": event_id,
                "fiscal_year": 2026,
                "fiscal_quarter": "Q2",
                "reported_on": "2026-08-01",
                "actual_eps": 1.25,
                "actual_basis": "gaap_diluted",
                "estimate_eps": 1.20,
                "estimate_basis": "gaap_diluted",
                "surprise_pct": 4.1667,
                "source": source(),
            }
        ],
        "sources": [source()],
        "gaps": [],
    }


def events():
    return {
        "symbol": "AAPL",
        "market": "US",
        "currency": "USD",
        "mode": "fixtures",
        "events": [
            {
                "event_id": canonical_earnings_id("US", "AAPL", 2026, "Q2"),
                "fiscal_year": 2026,
                "fiscal_quarter": "Q2",
                "event_date": "2026-08-01",
                "published_at": "2026-08-01T20:30:00Z",
                "date_precision": "timestamp",
                "timing_basis": "issuer_release",
                "source": source(),
            }
        ],
        "sources": [source()],
        "gaps": [],
    }


def event_study(n):
    rows = [
        {
            "event_id": canonical_earnings_id("US", "AAPL", 2020 + i // 4, f"Q{i % 4 + 1}"),
            "day_zero": f"202{i // 4}-10-01",
            "eligible": True,
            "excess_returns": {"d0_d5": 0.02},
        }
        for i in range(n)
    ]
    return {
        "symbol": "AAPL",
        "market": "US",
        "currency": "USD",
        "mode": "fixtures",
        "benchmark_symbol": "SPY",
        "eligible_event_count": n,
        "events": rows,
        "summary": None,
        "sources": [source()],
        "gaps": [],
    }


def test_fixture_is_explicitly_synthetic():
    assert DATA["synthetic"] is True
    assert DATA["source"]["fixture"] is True
    assert "Invented" in DATA["disclaimer"]


@pytest.mark.parametrize(
    "symbol,market,currency",
    [
        ("AAPL", "US", "USD"),
        ("NVDA", "US", "USD"),
        ("RY.TO", "CA", "CAD"),
    ],
)
def test_valid_candles_for_explicit_listings(symbol, market, currency):
    assert CandleSeries.model_validate(candles(symbol, market, currency)).symbol == symbol


@pytest.mark.parametrize(
    "edit",
    [
        lambda x: x["bars"][0].update(open=-1),
        lambda x: x["bars"][0].update(high=98),
        lambda x: x["bars"][0].update(low=104),
        lambda x: x["bars"][0].update(volume=-3),
        lambda x: x["bars"][0].update(close=float("nan")),
        lambda x: x["bars"].append(copy.deepcopy(x["bars"][0])),
        lambda x: x["bars"].reverse(),
        lambda x: x.update(interval="4h"),
        lambda x: x.update(range="10y"),
        lambda x: x.update(currency="CAD"),
    ],
)
def test_bad_candles_are_rejected(edit):
    obj = candles()
    edit(obj)
    with pytest.raises(ValidationError):
        CandleSeries.model_validate(obj)


def test_live_mode_refuses_synthetic_source():
    obj = candles()
    obj["mode"] = "live"
    with pytest.raises(ValidationError):
        CandleSeries.model_validate(obj)


def test_unknown_ticker_cannot_fabricate_a_us_dollar_listing():
    obj = candles(symbol="UNKNOWN", market="CA", currency="CAD")
    with pytest.raises(ValidationError):
        CandleSeries.model_validate(obj)


def test_split_discontinuity_is_not_repaired_by_contract_layer():
    obj = candles()
    obj["bars"][1].update(open=52, high=53, low=51, close=52)
    parsed = CandleSeries.model_validate(obj)
    assert parsed.bars[1].close == 52
    assert parsed.price_basis == "provider_ohlc"
    # Price-series adjustment and return calculations belong in a later phase.


def test_four_consecutive_quarters_are_eligible_for_ttm_shape():
    assert FinancialTrendsResponse.model_validate(trends()).ttm["revenue"].value == 400


def test_missing_quarter_forbids_available_ttm():
    obj = trends()
    obj["periods"].pop(1)
    with pytest.raises(ValidationError):
        FinancialTrendsResponse.model_validate(obj)


def test_ytd_cannot_claim_standalone_quarter_ttm():
    obj = trends()
    obj["periods"][0]["period_kind"] = "ytd"
    with pytest.raises(ValidationError):
        FinancialTrendsResponse.model_validate(obj)


def test_restatement_keeps_distinct_accession_for_new_revision():
    obj = trends()
    obj["periods"][0]["accession"] = "synthetic-restated-accession"
    assert FinancialTrendsResponse.model_validate(obj).periods[0].accession == "synthetic-restated-accession"
    # Choosing latest restatement is provider normalization, not Phase 0 contracts.


def test_incompatible_eps_bases_block_surprise():
    obj = earnings()
    obj["history"][0]["estimate_basis"] = "adjusted"
    with pytest.raises(ValidationError):
        EarningsResponse.model_validate(obj)


def test_null_estimate_is_not_zero():
    obj = earnings()
    obj["history"][0].update(estimate_eps=None, estimate_basis=None, surprise_pct=None)
    assert EarningsResponse.model_validate(obj).history[0].estimate_eps is None


def test_canonical_earnings_id_shared_across_endpoints():
    actual = EarningsResponse.model_validate(earnings())
    ev = EventsResponse.model_validate(events())
    assert actual.history[0].event_id == ev.events[0].event_id


def test_noncanonical_earnings_id_rejected():
    obj = earnings()
    obj["history"][0]["event_id"] = "some-random-id"
    with pytest.raises(ValidationError):
        EarningsResponse.model_validate(obj)


def test_before_and_after_market_have_explicit_timestamp_precision():
    obj = events()
    for timestamp in ["2026-08-01T12:00:00Z", "2026-08-01T20:30:00Z"]:
        obj["events"][0]["published_at"] = timestamp
        assert EventsResponse.model_validate(obj).events[0].date_precision == "timestamp"


def test_date_only_8k_must_not_claim_release_timestamp():
    obj = events()
    obj["events"][0].update(timing_basis="sec_8k_filing", date_precision="date_only", published_at=None)
    assert EventsResponse.model_validate(obj).events[0].published_at is None
    obj["events"][0]["published_at"] = "2026-08-01T20:30:00Z"
    with pytest.raises(ValidationError):
        EventsResponse.model_validate(obj)


def test_weekend_release_timestamp_kept_without_auto_trading_day_guess():
    obj = events()
    obj["events"][0].update(event_date="2026-08-01", published_at="2026-08-01T20:30:00Z")
    assert EventsResponse.model_validate(obj).events[0].event_date.isoformat() == "2026-08-01"
    # Trading-session mapping is a future pure-calculation responsibility.


def test_seven_eligible_events_prohibit_aggregate():
    obj = event_study(7)
    obj["summary"] = [
        {
            "horizon": "d0_d5",
            "eligible_n": 8,
            "mean_excess_return": 0.01,
            "median_excess_return": 0.01,
            "positive_share": 0.6,
        }
    ]
    with pytest.raises(ValidationError):
        EventStudyResponse.model_validate(obj)


def test_eight_eligible_events_allow_aggregate():
    obj = event_study(8)
    obj["summary"] = [
        {
            "horizon": "d0_d5",
            "eligible_n": 8,
            "mean_excess_return": 0.01,
            "median_excess_return": 0.01,
            "positive_share": 0.6,
        }
    ]
    assert EventStudyResponse.model_validate(obj).summary[0].eligible_n == 8


def test_event_count_mismatch_rejected():
    obj = event_study(8)
    obj["eligible_event_count"] = 7
    with pytest.raises(ValidationError):
        EventStudyResponse.model_validate(obj)
