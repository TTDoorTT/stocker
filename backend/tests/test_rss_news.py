"""Offline checks for RSS filtering, cache persistence, and no implicit AI calls."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.modules.intelligence import rss


def test_parse_english_and_exclude_chinese_or_undated():
    now = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
    xml = f"""<rss><channel>
       <item><title>Chip makers expand AI production</title>
         <link>https://example.org/a?utm_source=x</link><pubDate>{now}</pubDate></item>
       <item><title>芯片行业新闻</title>
         <link>https://example.org/b</link><pubDate>{now}</pubDate></item>
       <item><title>Undated story</title><link>https://example.org/c</link></item>
       </channel></rss>""".encode()
    items = rss.parse_feed(xml, {"hint": "semi", "name": "Example"}, datetime.now(UTC) - timedelta(days=3))
    assert len(items) == 1
    assert items[0]["headline"] == "Chip makers expand AI production"
    assert items[0]["canonical_url"] == "https://example.org/a"


def test_rss_refresh_persists_without_model(monkeypatch, tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path}/rss.db")
    service = rss.RSSNewsService(settings)
    service.config = {
        "industries": [{"key": "ai", "name": "AI / LLMs"}, {"key": "semi", "name": "Semiconductors"}],
        "sources": [{"name": "Example", "hint": "ai", "url": "https://example.org/rss"}],
    }
    now = datetime.now(UTC).isoformat()
    item = {
        "category": "ai",
        "headline": "New model published",
        "source_name": "Example",
        "source_url": "https://example.org/story",
        "canonical_url": "https://example.org/story",
        "published_at": now,
        "summary": "",
    }
    monkeypatch.setattr(rss, "fetch_source", lambda source, cutoff: ([item, item], True))
    monkeypatch.setattr(
        rss, "summarize_captured_headlines", lambda *args: pytest.fail("No model on news fetch")
    )
    service.refresh_worker()
    data = service.feed("ai", schedule=False)
    assert len(data["items"]) == 1
    assert data["sources_ok"] == 1
    assert data["sources_failed"] == 0
    assert service.feed("semi", schedule=False)["items"] == []
    restarted = rss.RSSNewsService(settings)
    assert len(restarted.feed("ai", schedule=False)["items"]) == 1
    with pytest.raises(ValueError, match="Unknown RSS"):
        service.feed("invalid", schedule=False)
