"""Persistent RSS industry highlights; reading the cache never invokes an LLM."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta


class HighlightCache:
    def __init__(self, database_url: str):
        if not database_url.startswith("sqlite:///"):
            raise ValueError("Highlight cache requires the existing SQLite database")
        self.path = database_url[len("sqlite:///") :]

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("""
            CREATE TABLE IF NOT EXISTS rss_highlights_cache (
                category TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                model_id TEXT NOT NULL,
                news_fingerprint TEXT NOT NULL
            )
        """)
        db.commit()
        return db

    @staticmethod
    def _fingerprint(db: sqlite3.Connection, category: str) -> str:
        """Track news content rather than fetch time, so routine refreshes stay fresh."""
        cutoff = (datetime.now(UTC) - timedelta(days=3)).isoformat()
        rows = db.execute(
            """
            SELECT canonical_url, headline, source_name, published_at, summary
            FROM rss_articles
            WHERE category = ? AND published_at >= ?
            ORDER BY published_at DESC, canonical_url ASC
            LIMIT 120
            """,
            (category, cutoff),
        ).fetchall()
        records = [tuple(row) for row in rows]
        encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def fingerprint(self, category: str) -> str:
        with closing(self.connect()) as db:
            return self._fingerprint(db, category)

    def get(self, category: str) -> dict:
        with closing(self.connect()) as db:
            saved = db.execute(
                """
                SELECT result_json, generated_at, model_id, news_fingerprint
                FROM rss_highlights_cache WHERE category = ?
                """,
                (category,),
            ).fetchone()
            if saved is None:
                return {
                    "category": category,
                    "saved": False,
                    "generated_at": None,
                    "model_id": None,
                    "stale": False,
                    "result": None,
                }
            fingerprint = self._fingerprint(db, category)

        return {
            "category": category,
            "saved": True,
            "generated_at": saved["generated_at"],
            "model_id": saved["model_id"],
            "stale": saved["news_fingerprint"] != fingerprint,
            "result": json.loads(saved["result_json"]),
        }

    def save(self, category: str, result: dict, model_id: str, news_fingerprint: str) -> None:
        """Replace the saved result only after the model returns a validated success."""
        if not result.get("answer") or not isinstance(result.get("evidence"), list):
            raise ValueError("Cannot save an invalid highlight response")
        timestamp = datetime.now(UTC).isoformat()
        with closing(self.connect()) as db, db:
            db.execute(
                """
                INSERT INTO rss_highlights_cache
                    (category, result_json, generated_at, model_id, news_fingerprint)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(category) DO UPDATE SET
                    result_json = excluded.result_json,
                    generated_at = excluded.generated_at,
                    model_id = excluded.model_id,
                    news_fingerprint = excluded.news_fingerprint
                """,
                (
                    category,
                    json.dumps(result, ensure_ascii=False),
                    timestamp,
                    model_id,
                    news_fingerprint,
                ),
            )
