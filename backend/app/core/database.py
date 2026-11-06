import sqlite3
from pathlib import Path
from threading import RLock


class Database:
    """SQLite v1 lifecycle and serialized transactions shared by feature repositories."""

    def __init__(self, url: str):
        if not url.startswith("sqlite:///"):
            raise ValueError("Only SQLite is supported")
        path = url.removeprefix("sqlite:///")
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, 1):
            self.conn.close()
            raise ValueError("Unsupported database schema version; explicit migration required")
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS positions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL,
          shares REAL NOT NULL, average_cost REAL NOT NULL, currency TEXT NOT NULL);
        PRAGMA user_version=1;
        """)
        self.conn.commit()

    def query(self, sql, params=()):
        with self.lock, self.conn:
            cursor = self.conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
