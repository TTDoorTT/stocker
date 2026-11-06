import json
import sqlite3
from pathlib import Path
from threading import RLock


class Repository:
    """Schema v1: JSON run snapshots plus independent, ordered event records."""

    def __init__(self, url: str):
        if not url.startswith('sqlite:///'):
            raise ValueError('Only SQLite is supported')
        path = url.removeprefix('sqlite:///')
        if path != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        version = self.conn.execute('PRAGMA user_version').fetchone()[0]
        if version not in (0, 1):
            self.conn.close()
            raise ValueError('Unsupported database schema version; explicit migration required')
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS watchlist (symbol TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS positions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL,
          shares REAL NOT NULL, average_cost REAL NOT NULL, currency TEXT NOT NULL);
        PRAGMA user_version=1;
        ''')
        self.conn.commit()

    def save_run(self, run):
        with self.lock, self.conn:
            self.conn.execute('INSERT OR REPLACE INTO runs VALUES (?, ?)',
                              (run['run_id'], json.dumps(run, allow_nan=False)))

    def run(self, run_id):
        with self.lock:
            row = self.conn.execute('SELECT payload FROM runs WHERE id=?', (run_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def runs(self, limit=50, offset=0):
        with self.lock:
            return [json.loads(row[0]) for row in self.conn.execute(
                'SELECT payload FROM runs ORDER BY rowid DESC LIMIT ? OFFSET ?', (limit, offset))]

    def event(self, run_id, event):
        with self.lock, self.conn:
            cursor = self.conn.execute('INSERT INTO events(run_id,payload) VALUES (?,?)',
                                       (run_id, json.dumps(event, allow_nan=False)))
            return cursor.lastrowid

    def events(self, run_id):
        with self.lock:
            return [dict(json.loads(row['payload']), id=row['id']) for row in self.conn.execute(
                'SELECT id,payload FROM events WHERE run_id=? ORDER BY id', (run_id,))]

    def query(self, sql, params=()):
        with self.lock, self.conn:
            cursor = self.conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
