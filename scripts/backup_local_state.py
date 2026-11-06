"""Back up ignored local state outside Git without displaying credentials or records.

Run with backend/.venv/bin/python scripts/backup_local_state.py DESTINATION.
DESTINATION must be outside the repository; copies are private to the current user.
"""

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import Settings  # noqa: E402


def snapshot(connection):
    tables = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    return {
        "integrity": [row[0] for row in connection.execute("PRAGMA integrity_check")],
        "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
        "tables": {
            table: {
                "count": connection.execute(
                    'SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"'
                ).fetchone()[0],
                "sha256": hashlib.sha256(
                    json.dumps(
                        sorted(
                            (
                                json.dumps(row, default=str, separators=(",", ":"))
                                for row in connection.execute(
                                    'SELECT * FROM "' + table.replace('"', '""') + '"'
                                ).fetchall()
                            )
                        )
                    ).encode()
                ).hexdigest(),
            }
            for table in tables
        },
    }


def main():
    destination = Path(sys.argv[1]).expanduser().resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise SystemExit("Backup destination must be outside the repository")
    os.umask(0o077)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    settings = Settings()
    if not settings.database_url.startswith("sqlite:///"):
        raise SystemExit("Only SQLite is supported")
    configured = Path(settings.database_url.removeprefix("sqlite:///"))
    if not configured.is_absolute():
        configured = ROOT / "backend" / configured
    candidates = {configured.resolve()}
    candidates.update(
        path.resolve()
        for path in ROOT.rglob("*")
        if path.suffix in {".db", ".sqlite3"}
        and not any(part in path.parts for part in ("references", "node_modules", ".venv", ".browser-cache"))
    )
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configured_native_database": str(configured),
        "databases": [],
    }
    env = ROOT / ".env"
    if env.exists():
        shutil.copyfile(env, destination / "root.env")
        manifest["env_sha256"] = hashlib.sha256(env.read_bytes()).hexdigest()
    for index, source in enumerate(sorted(candidates)):
        if not source.exists():
            manifest["databases"].append({"source": str(source), "exists": False})
            continue
        target = destination / f"{index:02d}-{source.name}"
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src:
            with sqlite3.connect(target) as dst:
                src.backup(dst)
                state = snapshot(dst)
        if state["integrity"] != ["ok"]:
            raise SystemExit("Backup integrity verification failed")
        manifest["databases"].append({"source": str(source), "backup": target.name, **state})
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Private backup verified: {destination}; {len(manifest['databases'])} database paths recorded")


if __name__ == "__main__":
    main()
