"""Offline tests for persistent, per-category RSS highlight results."""

from contextlib import closing
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.intelligence.service import IntelligenceService
from app.modules.market_data.service import DataService
from app.modules.research.errors import ModelError


def make_services(tmp_path):
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/stocker.db",
        llm_model="mock-model",
    )
    intel = IntelligenceService(DataService(settings), settings)
    with closing(intel.rss_collector.connect()) as db, db:
        stamp = datetime.now(UTC).isoformat()
        db.execute(
            """
            INSERT INTO rss_articles
                (category, canonical_url, headline, source_name,
                 source_url, published_at, fetched_at, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ai",
                "https://example.org/1",
                "AI industry story",
                "Test Publisher",
                "https://example.org/1",
                stamp,
                stamp,
                "Publisher description",
            ),
        )
    return settings, intel


def fake_result(answer: str) -> dict:
    return {
        "answer": answer,
        "evidence": [{"evidence_id": "ev-test", "source_url": "https://example.org/1"}],
        "gaps": ["Full articles were not retrieved"],
        "mode": "live",
    }


def test_saved_highlights_survive_restart_and_mark_changes_stale(tmp_path, monkeypatch):
    settings, intel = make_services(tmp_path)
    requested = []

    def summarize(category, config):
        requested.append((category, config.llm_model))
        return fake_result("Initial AI highlights")

    monkeypatch.setattr(intel.rss_collector, "highlights", summarize)

    assert intel.rss_saved_highlights("ai")["saved"] is False
    assert requested == []  # GET/reading cache never invokes LLM
    assert intel.rss_highlights("ai")["answer"] == "Initial AI highlights"
    assert requested == [("ai", "mock-model")]

    restarted = IntelligenceService(DataService(settings), settings)
    saved = restarted.rss_saved_highlights("ai")
    assert saved["saved"] and not saved["stale"]
    assert saved["result"]["answer"] == "Initial AI highlights"
    assert saved["model_id"] == "mock-model"
    assert saved["generated_at"]
    assert restarted.rss_saved_highlights("semi")["saved"] is False
    assert requested == [("ai", "mock-model")]

    with closing(restarted.rss_collector.connect()) as db, db:
        stamp = datetime.now(UTC).isoformat()
        db.execute(
            """
            INSERT INTO rss_articles
                (category, canonical_url, headline, source_name,
                 source_url, published_at, fetched_at, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "ai",
                "https://example.org/2",
                "New AI industry story",
                "Second Publisher",
                "https://example.org/2",
                stamp,
                stamp,
                "New publisher excerpt",
            ),
        )
    assert restarted.rss_saved_highlights("ai")["stale"] is True

    def fail(category, config):
        raise ModelError("Test model failure")

    monkeypatch.setattr(restarted.rss_collector, "highlights", fail)
    with pytest.raises(ModelError, match="Test model failure"):
        restarted.rss_highlights("ai")
    assert restarted.rss_saved_highlights("ai")["result"]["answer"] == "Initial AI highlights"

    monkeypatch.setattr(
        restarted.rss_collector, "highlights", lambda category, config: fake_result("New AI highlights")
    )
    restarted.rss_highlights("ai")
    current = restarted.rss_saved_highlights("ai")
    assert current["result"]["answer"] == "New AI highlights"
    assert current["stale"] is False


def test_saved_highlights_get_endpoint_is_read_only(tmp_path, monkeypatch):
    settings, _ = make_services(tmp_path)

    # Any LLM invocation from GET should fail the test immediately.
    def forbidden(*args, **kwargs):
        raise AssertionError("GET must not call a model")

    monkeypatch.setattr("app.modules.intelligence.rss.RSSNewsService.highlights", forbidden)
    with TestClient(create_app(settings)) as client:
        read = client.get("/api/intelligence/rss/highlights?category=ai")
        assert read.status_code == 200
        assert read.json()["saved"] is False
        assert client.get("/api/intelligence/rss/highlights?category=invalid").status_code == 422
