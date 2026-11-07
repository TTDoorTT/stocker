"""Synthetic SEC XBRL contexts; no requests, credentials, or AI interactions."""

import copy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.contracts.stock_research import FinancialTrendsResponse
from app.finance.quarterly import trailing_twelve_months
from app.modules.market_data.errors import DataUnavailable
from app.modules.market_data.quarterly import (
    fetch_sec_financial_trends,
    fixture_financial_trends,
    no_coverage,
    parse_sec_quarters,
)

FETCHED = datetime(2026, 2, 1, tzinfo=UTC)


def row(start, end, value, fy, fp, form, filed, accession):
    return {
        "start": start,
        "end": end,
        "val": value,
        "fy": fy,
        "fp": fp,
        "form": form,
        "filed": filed,
        "accn": accession,
    }


def sec_fixture():
    q1 = row("2024-10-01", "2024-12-31", 200, 2025, "Q1", "10-Q", "2025-01-31", "q1")
    q2 = row("2025-01-01", "2025-03-31", 240, 2025, "Q2", "10-Q", "2025-05-01", "q2")
    q3 = row("2025-04-01", "2025-06-30", 260, 2025, "Q3", "10-Q", "2025-08-01", "q3")
    ytd3 = row("2024-10-01", "2025-06-30", 700, 2025, "Q3", "10-Q", "2025-08-01", "q3")
    fy = row("2024-10-01", "2025-09-30", 1000, 2025, "FY", "10-K", "2025-11-15", "fy")
    # SEC filing fy is not necessarily fiscal year of comparative fact: file lag is filtered.
    comparative = row("2024-10-01", "2024-12-31", 9999, 2025, "Q1", "10-Q", "2026-01-29", "old")

    def block(key, unit, items):
        return {key: {"units": {unit: items}}}

    gaap = {
        **block(
            "RevenueFromContractWithCustomerExcludingAssessedTax", "USD", [q1, q2, q3, ytd3, fy, comparative]
        ),
        **block(
            "NetIncomeLoss",
            "USD",
            [
                row("2024-10-01", "2024-12-31", 40, 2025, "Q1", "10-Q", "2025-01-31", "ni1"),
                row("2024-10-01", "2025-03-31", 90, 2025, "Q2", "10-Q", "2025-05-01", "ni2ytd"),
                row("2025-04-01", "2025-06-30", 60, 2025, "Q3", "10-Q", "2025-08-01", "ni3"),
                row("2024-10-01", "2025-06-30", 150, 2025, "Q3", "10-Q", "2025-08-01", "ni3ytd"),
                row("2024-10-01", "2025-09-30", 210, 2025, "FY", "10-K", "2025-11-15", "nify"),
            ],
        ),
        **block(
            "NetCashProvidedByUsedInOperatingActivities",
            "USD",
            [
                row("2024-10-01", "2024-12-31", 22, 2025, "Q1", "10-Q", "2025-01-31", "cf1"),
                row("2024-10-01", "2025-03-31", 50, 2025, "Q2", "10-Q", "2025-05-01", "cf2ytd"),
                row("2024-10-01", "2025-06-30", 80, 2025, "Q3", "10-Q", "2025-08-01", "cf3ytd"),
                row("2024-10-01", "2025-09-30", 130, 2025, "FY", "10-K", "2025-11-15", "cffy"),
            ],
        ),
        **block(
            "EarningsPerShareDiluted",
            "USD/shares",
            [
                row("2024-10-01", "2024-12-31", 0.5, 2025, "Q1", "10-Q", "2025-01-31", "eps1"),
                row("2025-01-01", "2025-03-31", 0.6, 2025, "Q2", "10-Q", "2025-05-01", "eps2"),
                row("2025-04-01", "2025-06-30", 0.7, 2025, "Q3", "10-Q", "2025-08-01", "eps3"),
                row("2024-10-01", "2025-09-30", 2.5, 2025, "FY", "10-K", "2025-11-15", "epsfy"),
            ],
        ),
    }
    return {"cik": 320193, "facts": {"us-gaap": gaap}}


def trends(payload=None, *, cached=False):
    return parse_sec_quarters(
        "AAPL", payload if payload is not None else sec_fixture(), FETCHED, cached=cached
    )


def lookup(response: FinancialTrendsResponse, quarter: str):
    return next(p for p in response.periods if p.fiscal_quarter == quarter)


def test_four_standalone_quarters_and_ttm():
    result = trends()
    assert [p.fiscal_quarter for p in result.periods] == ["Q4", "Q3", "Q2", "Q1"]
    assert [lookup(result, q).metrics["revenue"].value for q in ("Q1", "Q2", "Q3", "Q4")] == [
        200,
        240,
        260,
        300,
    ]
    assert result.ttm["revenue"].value == 1000
    assert result.ttm["revenue"].status == "available"
    assert result.ttm["net_income"].value == 210
    assert result.ttm["operating_cash_flow"].value == 130
    assert result.ttm["gross_profit"].status == "unavailable"
    assert result.ttm["diluted_eps"].status == "unavailable"
    assert all(p.period_kind == "standalone_quarter" for p in result.periods)


def test_ytd_subtraction_is_derived_with_two_inputs_and_q4_eps_not_inferred():
    result = trends()
    q2 = lookup(result, "Q2")
    q4 = lookup(result, "Q4")
    metric = q2.metrics["net_income"]
    assert metric.value == 50 and metric.status == "derived"
    assert metric.calculation_id and len(metric.evidence_ids) == 2
    assert q4.metrics["revenue"].status == "derived"
    assert q4.metrics["revenue"].value == 300
    assert "diluted_eps" not in q4.metrics


def test_incompatible_ytd_starts_cannot_generate_quarter():
    payload = sec_fixture()
    values = payload["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    next(x for x in values if x["accn"] == "ni2ytd")["start"] = "2024-09-01"
    result = trends(payload)
    assert "net_income" not in lookup(result, "Q2").metrics
    assert result.ttm["net_income"].status == "unavailable"


def test_comparative_over_lag_and_future_filing_are_excluded():
    payload = sec_fixture()
    values = payload["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"][
        "USD"
    ]
    values.append(row("2024-10-01", "2024-12-31", 999, 2025, "Q1", "10-Q", "2027-01-01", "future"))
    assert lookup(trends(payload), "Q1").metrics["revenue"].value == 200


def test_no_false_q4_when_year_to_date_missing():
    payload = sec_fixture()
    values = payload["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"][
        "USD"
    ]
    values[:] = [v for v in values if not (v["fp"] == "Q3" and v["start"] == "2024-10-01")]
    result = trends(payload)
    assert "revenue" not in lookup(result, "Q4").metrics
    assert result.ttm["revenue"].status == "unavailable"


def test_filing_context_and_source_metadata_do_not_claim_earnings_time():
    result = trends(cached=True)
    assert all(p.source.cached for p in result.periods)
    assert all(p.source.published_at is None for p in result.periods)
    assert all(
        p.filed_on.isoformat() in ("2025-01-31", "2025-05-01", "2025-08-01", "2025-11-15")
        for p in result.periods
    )
    assert result.sources[0].fixture is False
    assert result.sources[0].url.host == "data.sec.gov"


def test_nan_or_infinite_facts_cannot_be_converted_into_quarters():
    payload = sec_fixture()
    values = payload["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"][
        "USD"
    ]
    values[0]["val"] = float("nan")
    values[1]["val"] = float("inf")
    result = trends(payload)
    assert "revenue" not in lookup(result, "Q1").metrics
    assert "revenue" not in lookup(result, "Q2").metrics


def test_sec_cik_mismatch_is_unavailable_not_mislabeled():
    sec = SimpleNamespace(
        tickers=lambda: [{"ticker": "AAPL", "cik_str": 320193}],
        headers=lambda: {"User-Agent": "research contact test@example.org"},
        http=SimpleNamespace(fetch=lambda *a, **k: SimpleNamespace(data={"cik": 8888}, fetched_at=FETCHED)),
    )
    with pytest.raises(DataUnavailable, match="CIK"):
        fetch_sec_financial_trends("AAPL", sec)


def test_sec_provider_keeps_original_retrieval_time_and_cached_flag():
    raw = sec_fixture()
    seen = []

    def fetch(*args, **kwargs):
        seen.append((args, kwargs))
        return SimpleNamespace(data=raw, fetched_at=FETCHED, cached=True)

    sec = SimpleNamespace(
        tickers=lambda: [{"ticker": "AAPL", "cik_str": 320193}],
        headers=lambda: {"User-Agent": "research contact test@example.org"},
        http=SimpleNamespace(fetch=fetch),
    )
    result = fetch_sec_financial_trends("AAPL", sec)
    assert result.mode == "live" and result.sources[0].cached
    assert result.sources[0].fetched_at == FETCHED
    assert seen[0][0][0].startswith("https://data.sec.gov/")


def test_missing_sec_issuer_and_canadian_coverage_are_explicit():
    empty_sec = SimpleNamespace(tickers=lambda: [], headers=lambda: {}, http=None)
    result = fetch_sec_financial_trends("SPY", empty_sec)
    assert result.periods == [] and result.gaps
    assert result.ttm["revenue"].status == "unavailable"
    canadian = no_coverage("RY.TO", "CA", "live", "No licensed Canadian fundamentals")
    assert canadian.market == "CA" and canadian.currency == "CAD"
    assert all(metric.status == "unavailable" for metric in canadian.ttm.values())


def test_synthetic_fixture_has_four_periods_and_no_live_sources():
    demo = {
        "AAPL": {
            "revenue": [1000, 1200],
            "net_income": [200, 250],
            "cashflow": [220, 270],
            "eps": [4, 5],
            "fiscal_end": "09-30",
        },
        "SPY": {"name": "ETF"},
    }
    result = fixture_financial_trends("AAPL", demo)
    assert len(result.periods) == 4
    assert result.ttm["revenue"].value == pytest.approx(1200)
    assert result.ttm["diluted_eps"].value is None
    assert all(period.source.fixture for period in result.periods)
    assert all(not p.metrics.get("gross_profit") for p in result.periods)
    assert fixture_financial_trends("SPY", demo).periods == []
    with pytest.raises(DataUnavailable):
        fixture_financial_trends("ZZZZ", demo)


def test_missing_interior_quarter_blocks_ttm_instead_of_using_older_data():
    result = trends()
    remaining = [p for p in result.periods if p.fiscal_quarter != "Q2"]
    assert trailing_twelve_months(remaining)["revenue"].status == "unavailable"


def test_strict_contract_rejects_extra_fields():
    result = trends()
    data = result.model_dump(mode="json")
    data["surprise_target"] = "100%"
    with pytest.raises(ValidationError):
        FinancialTrendsResponse.model_validate(data)


def test_fixtures_not_allowed_in_live_financial_response():
    result = fixture_financial_trends(
        "AAPL",
        {
            "AAPL": {"revenue": [1, 2], "fiscal_end": "09-30"},
        },
    )
    value = result.model_dump(mode="json")
    value["mode"] = "live"
    with pytest.raises(ValidationError):
        FinancialTrendsResponse.model_validate(value)


def test_ytd_source_must_match_annual_fiscal_year():
    payload = copy.deepcopy(sec_fixture())
    values = payload["facts"]["us-gaap"]["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"][
        "USD"
    ]
    next(v for v in values if v["accn"] == "q3" and v["start"] == "2024-10-01")["fy"] = 2024
    result = trends(payload)
    assert "revenue" not in lookup(result, "Q4").metrics
