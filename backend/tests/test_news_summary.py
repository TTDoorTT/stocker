"""Offline tests of on-demand headline summaries; no actual model output is claimed."""

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from app.agents.client import ModelError
from app.contracts.market import NewsItem
from app.core.config import Settings
from app.modules.market_data.errors import DataUnavailable
from app.services.news_summary import summarize_news


def news_item(**updates):
    values = {
        "headline": "Company announces earnings release",
        "source_name": "Example licensed feed",
        "source_url": "https://news.example/company-earnings",
        "published_at": datetime(2025, 1, 1, tzinfo=UTC),
        "fetched_at": datetime(2025, 1, 2, tzinfo=UTC),
        "symbols": ["AAPL"],
        "cached": True,
    }
    return NewsItem(**(values | updates))


def configured(**updates):
    return Settings(_env_file=None, **({"data_mode": "live", "llm_model": "mock-model"} | updates))


def model_stub(monkeypatch, mutate=None):
    calls = []

    class StubModel:
        def __init__(self, settings):
            pass

        def complete(self, stage, context, schema, tools):
            captured = tools.call("get_company_data", {})
            identifiers = [item["evidence_id"] for item in captured["evidence"]]
            calls.append({"stage": stage, "context": context, "captured": captured})
            output = {
                "stage": "report",
                "summary": "The captured headline announces an earnings release.",
                "executive_summary": "Details remain limited to the original headline.",
                "claims": [
                    {
                        "text": "An earnings announcement appears in the supplied feed.",
                        "evidence_ids": identifiers,
                        "calculation_ids": [],
                    }
                ],
                "evidence_ids": identifiers,
                "calculation_ids": [],
                "gaps": [],
            }
            if mutate:
                mutate(output)
            return output

    monkeypatch.setattr("app.services.news_summary.ModelClient", StubModel)
    return calls


def test_headline_summary_is_on_demand_cited_and_preserves_source_metadata(monkeypatch):
    calls = model_stub(monkeypatch)
    data = Mock()
    item = news_item()
    data.news.return_value = [item, item]  # duplicate source headlines do not expand context
    result = summarize_news(data, configured(), "aapl")
    data.news.assert_called_once_with("AAPL")
    assert len(calls) == 1 and calls[0]["stage"] == "report"
    assert len(result["evidence"]) == 1
    evidence = result["evidence"][0]
    assert evidence["field"] == "headline"
    assert evidence["value"] == item.headline
    assert evidence["source_url"] == item.source_url
    assert evidence["cached"] is True
    assert datetime.fromisoformat(evidence["published_at"].replace("Z", "+00:00")) == item.published_at
    assert datetime.fromisoformat(evidence["fetched_at"].replace("Z", "+00:00")) == item.fetched_at
    assert evidence["evidence_id"] in result["answer"]
    assert "Headline-only" in result["answer"]
    assert any("full article contents" in gap for gap in result["gaps"])
    assert calls[0]["captured"]["facts"] == []
    assert "No full article content was supplied" in calls[0]["context"]["task"]
    # This service only uses read tools and the model; it never launches the research pipeline.
    assert set(calls[0]["captured"]) == {"symbol", "mode", "profile", "evidence", "facts", "news", "gaps"}


@pytest.mark.parametrize("settings", [configured(data_mode="fixtures"), configured(llm_model="")])
def test_missing_or_fixture_configuration_prevents_data_and_model_calls(monkeypatch, settings):
    model = Mock(side_effect=AssertionError("Model must not be created"))
    monkeypatch.setattr("app.services.news_summary.ModelClient", model)
    data = Mock()
    with pytest.raises(ModelError):
        summarize_news(data, settings)
    data.news.assert_not_called()
    model.assert_not_called()


def test_empty_news_prevents_model_call(monkeypatch):
    model = Mock(side_effect=AssertionError("No source, no summary"))
    monkeypatch.setattr("app.services.news_summary.ModelClient", model)
    data = Mock()
    data.news.return_value = []
    with pytest.raises(DataUnavailable, match="No sourced live headlines"):
        summarize_news(data, configured())
    model.assert_not_called()


@pytest.mark.parametrize("bad_item", [news_item(fixture=True), news_item(source_url="fixture:synthetic")])
def test_fixture_headlines_never_become_live_ai_evidence(monkeypatch, bad_item):
    model = Mock(side_effect=AssertionError("Fixture source must not reach model"))
    monkeypatch.setattr("app.services.news_summary.ModelClient", model)
    data = Mock()
    data.news.return_value = [bad_item]
    with pytest.raises(DataUnavailable):
        summarize_news(data, configured())
    model.assert_not_called()


@pytest.mark.parametrize(
    "mutate,error",
    [
        (lambda result: result["claims"][0].update(text="Revenue increased by 25 percent."), "Numeric prose"),
        (
            lambda result: result["claims"][0].update(value=25, unit="%", reference_id="unknown"),
            "Numeric claim",
        ),
        (lambda result: result.update(evidence_ids=["unknown"]), "Unknown evidence"),
        (lambda result: result.update(claims=[]), "requires at least one"),
    ],
)
def test_invalid_model_claims_are_rejected_before_publication(monkeypatch, mutate, error):
    model_stub(monkeypatch, mutate)
    data = Mock()
    data.news.return_value = [news_item()]
    with pytest.raises(ValueError, match=error):
        summarize_news(data, configured())


def test_context_is_capped_and_symbols_derive_from_source_tags(monkeypatch):
    calls = model_stub(monkeypatch)
    data = Mock()
    data.news.return_value = [
        news_item(headline=f"Company headline {index}", source_url=f"https://news.example/{index}")
        for index in range(20)
    ]
    result = summarize_news(data, configured())
    assert len(result["evidence"]) == 12
    assert all(item["symbol"] == "AAPL" for item in result["evidence"])
    assert len(calls) == 1
