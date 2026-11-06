"""Intelligence tests use labeled synthetic company fixtures and mocked macro HTTP responses."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.contracts.market import NewsItem
from app.core.config import Settings
from app.db.repository import Repository
from app.modules.market_data.providers.http import ProviderHTTP
from app.modules.market_data.service import DataService
from app.orchestrator.engine import ResearchOrchestrator, new_run
from app.services.intelligence import IntelligenceService


def services(**kwargs):
    kwargs.setdefault("bank_of_canada_enabled", False)
    settings = Settings(_env_file=None, **kwargs)
    data = DataService(settings)
    return IntelligenceService(data, settings)


def test_daily_review_proxy_labels_and_evidence_bound_returns():
    review = services().daily_review()
    assert review["mode"] == "fixtures"
    assert "ETF proxies" in review["coverage"]
    assert "not inferred" in review["session"]
    assert len(review["proxies"]) == 2
    spy = review["proxies"][0]
    assert spy["symbol"] == "SPY"
    assert spy["daily_return_pct"] == pytest.approx((400 / 398 - 1) * 100)
    assert spy["quote"]["fixture"] is True
    assert spy["calculation"]["input_evidence_ids"]
    assert review["news"] == []
    assert any("breadth" in gap for gap in review["gaps"])


def test_news_dedupes_headline_url_and_preserves_dates():
    service = services()
    timestamp = datetime.now(UTC)
    item = NewsItem(
        headline="Company filing",
        source_name="Synthetic unit-test source",
        source_url="https://example.invalid/filing#section",
        published_at=timestamp,
        fetched_at=timestamp,
        symbols=["AAPL"],
        fixture=True,
    )
    duplicate = item.model_copy(
        update={"headline": " company  FILING ", "source_url": "https://example.invalid/filing"}
    )
    service.data.news = lambda: [item, duplicate]
    result = service.news()
    assert len(result["items"]) == 1
    assert datetime.fromisoformat(result["items"][0]["published_at"].replace("Z", "+00:00")) == timestamp
    assert result["items"][0]["symbols"] == ["AAPL"]


def test_fixture_signals_are_honestly_unavailable():
    result = services().signals()
    assert len(result["items"]) == 3
    assert all(row["value"] is None and row["observations"] == [] for row in result["items"])
    assert all(row["status"] == "unavailable" and row["gaps"] for row in result["items"])


def test_live_missing_fred_key():
    result = services(data_mode="live").signals()
    assert all(row["value"] is None and "FRED_API_KEY" in row["gaps"][0] for row in result["items"])


def test_mocked_real_format_macro_observations_and_missing_values():
    service = services(data_mode="live", fred_api_key="test-secret")
    today = datetime.now(UTC).date()

    def handler(request):
        assert request.url.host == "api.stlouisfed.org"
        assert request.url.params["series_id"] in {"DGS10", "FEDFUNDS", "DCOILWTICO"}
        return httpx.Response(
            200,
            json={
                "observations": [
                    {"date": str(today), "value": "."},
                    {"date": str(today + timedelta(days=1)), "value": "100"},
                    {"date": str(today - timedelta(days=1)), "value": "4.1"},
                    {"date": str(today - timedelta(days=2)), "value": "4.0"},
                    {"date": "bad", "value": "inf"},
                ]
            },
        )

    service.data = DataService(
        service.settings, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler)))
    )
    result = service.signals()
    for row in result["items"]:
        assert row["value"] == 4.1
        assert row["observation_date"] == str(today - timedelta(days=1))
        assert row["status"] == "available"
        assert row["stale"] is False
        assert len(row["observations"]) == 2
        assert row["published_at"] is None
        assert "test-secret" not in str(row)
        assert row["source_url"].startswith("https://fred.stlouisfed.org/series/")


def test_fred_failure_is_sanitized_and_not_fabricated():
    service = services(data_mode="live", fred_api_key="test-secret")
    service.data.http = ProviderHTTP(
        httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(403)))
    )
    result = service.signals()
    assert all(row["value"] is None and row["status"] == "unavailable" for row in result["items"])
    assert "test-secret" not in str(result)


def test_all_twenty_industry_templates_are_navigable_and_guided():
    service = services()
    templates = service.industries()
    assert len(templates) == 20
    assert len({template["slug"] for template in templates}) == 20
    for template in templates:
        assert service.industry(template["slug"]) == template
        assert len(template["prompt"]) > 100
        assert any("not a verified sector" in gap for gap in template["gaps"])
    with pytest.raises(KeyError):
        service.industry("../unknown")


@pytest.mark.parametrize("slug,symbol", [("ai-computing", "NVDA"), ("ai-application", "MSFT")])
def test_two_template_selections_reuse_company_research_pipeline(slug, symbol):
    service = services()
    template = service.industry(slug)
    assert symbol in template["symbols"]
    repository = Repository("sqlite:///:memory:")
    try:
        run = new_run(symbol, service.settings)
        # Current acceptance is a representative company case with explicit sector-data gaps.
        run["industry"] = template
        repository.save_run(run)
        result = ResearchOrchestrator(repository, service.data, service.settings).execute(run["run_id"])
        assert result["status"] == "incomplete"
        assert result["symbol"] == symbol
        assert len(result["stages"]) == 6
        assert "SYNTHETIC FIXTURE DATA" in result["report"]
        assert result["industry"]["slug"] == slug
        assert all(stage["status"] == "complete" for stage in result["stages"])
    finally:
        repository.close()


def test_fred_cached_observations_keep_original_network_timestamp():
    service = services(data_mode="live", fred_api_key="test-secret")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "observations": [{"date": str(datetime.now(UTC).date() - timedelta(days=1)), "value": "4.1"}]
            },
        )

    service.data = DataService(
        service.settings, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler)))
    )
    first, second = service.signals(), service.signals()
    assert len(calls) == 3
    for initial, cached in zip(first["items"], second["items"], strict=True):
        assert not initial["cached"] and cached["cached"]
        assert initial["fetched_at"] == cached["fetched_at"]
