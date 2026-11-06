import json

from app.core.database import Database


class ResearchRepository:
    def __init__(self, database: Database | str):
        self.database = Database(database) if isinstance(database, str) else database

    def save_run(self, run):
        with self.database.lock, self.database.conn:
            self.database.conn.execute(
                "INSERT OR REPLACE INTO runs VALUES (?, ?)", (run["run_id"], json.dumps(run, allow_nan=False))
            )

    def run(self, run_id):
        with self.database.lock:
            row = self.database.conn.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def runs(self, limit=50, offset=0):
        with self.database.lock:
            return [
                json.loads(row[0])
                for row in self.database.conn.execute(
                    "SELECT payload FROM runs ORDER BY rowid DESC LIMIT ? OFFSET ?", (limit, offset)
                )
            ]

    def event(self, run_id, event):
        with self.database.lock, self.database.conn:
            cursor = self.database.conn.execute(
                "INSERT INTO events(run_id,payload) VALUES (?,?)",
                (run_id, json.dumps(event, allow_nan=False)),
            )
            return cursor.lastrowid

    def events(self, run_id):
        with self.database.lock:
            return [
                dict(json.loads(row["payload"]), id=row["id"])
                for row in self.database.conn.execute(
                    "SELECT id,payload FROM events WHERE run_id=? ORDER BY id", (run_id,)
                )
            ]

    def close(self) -> None:
        self.database.close()
