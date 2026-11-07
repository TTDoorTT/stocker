"""RSS highlights use saved excerpts and diverse publishers."""

from datetime import UTC, datetime, timedelta

from app.core.config import Settings
from app.modules.intelligence import rss


def test_rss_highlights_context_and_diversity(tmp_path, monkeypatch):
    settings = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/news.db",
        llm_model="mock-model",
    )
    service = rss.RSSNewsService(settings)
    now = datetime.now(UTC)

    with rss.closing(service.connect()) as db, db:
        for i in range(29):
            source = "Dominant Publisher" if i < 25 else "Publisher B" if i < 27 else "Publisher C"
            stamp = (now - timedelta(minutes=i)).isoformat()
            db.execute(
                """INSERT INTO rss_articles
                (category, canonical_url, headline, source_name,
                 source_url, published_at, fetched_at, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "ai",
                    f"https://example.org/{i}",
                    f"Headline {i}",
                    source,
                    f"https://example.org/{i}",
                    stamp,
                    stamp,
                    "A" * 700 if i == 0 else f"Description {i}",
                ),
            )

    # Descriptions must not appear in the news-list API.
    listed = service.feed("ai", schedule=False)["items"]
    assert len(listed) == 29
    assert "summary" not in listed[0]

    received = {}

    def fake_summary(payload, evidence, gaps, configured, **kwargs):
        received["evidence"] = evidence
        received["task"] = kwargs["task"]
        return {
            "answer": "Industry highlights (headlines only)\n\n- Example",
            "evidence": evidence,
            "gaps": gaps,
            "mode": "live",
        }

    monkeypatch.setattr(rss, "summarize_captured_headlines", fake_summary)

    result = service.highlights("ai", settings)
    evidence = received["evidence"]

    assert len(evidence) == 20

    publishers = {item["source_name"] for item in evidence}
    assert "Publisher B" in publishers
    assert "Publisher C" in publishers

    assert "Publisher RSS description" in evidence[0]["value"]
    assert "A" * 500 in evidence[0]["value"]
    assert "A" * 501 not in evidence[0]["value"]

    assert "headlines and RSS excerpts" in result["answer"]
    assert "No full articles were retrieved" in received["task"]
