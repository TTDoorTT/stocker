"""Storage rename preserves SQLite history and private credentials without overwrites."""

import importlib.util
import sqlite3
import stat
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("migrate_storage_names", SCRIPTS / "migrate_storage_names.py")
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def seed(path):
    path.mkdir()
    db = sqlite3.connect(path / "previous.db")
    db.executescript(
        "PRAGMA user_version=1; CREATE TABLE history (id, value); INSERT INTO history VALUES (1, 'synthetic record');"
    )
    db.commit()
    db.close()
    (path / "ai-settings").mkdir()
    (path / "ai-settings" / "config.json").write_text('{"api_key":"synthetic-private-key"}')


def test_storage_copy_preserves_database_secrets_and_source(tmp_path):
    source, target = tmp_path / "old", tmp_path / "new"
    seed(source)
    original = (source / "previous.db").read_bytes()
    migration.migrate(source, target, "previous.db")
    assert (source / "previous.db").read_bytes() == original
    with sqlite3.connect(target / "stocker.db") as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("SELECT * FROM history").fetchall() == [(1, "synthetic record")]
    assert (target / "ai-settings/config.json").read_bytes() == (
        source / "ai-settings/config.json"
    ).read_bytes()
    assert stat.S_IMODE((target / "ai-settings/config.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((target / "ai-settings").stat().st_mode) == 0o700
    assert not (target / "previous.db").exists()


def test_storage_copy_refuses_collisions_and_existing_destination(tmp_path):
    source, target = tmp_path / "old", tmp_path / "new"
    seed(source)
    target.mkdir()
    (target / "keep").write_text("keep")
    with pytest.raises(ValueError, match="Destination must be empty"):
        migration.migrate(source, target, "previous.db")
    assert (target / "keep").read_text() == "keep"
    (source / "stocker.db").write_bytes(b"existing")
    with pytest.raises(ValueError, match="collide"):
        migration.migrate(source, tmp_path / "empty", "previous.db")


def test_storage_copy_refuses_overlapping_paths_and_symlinks(tmp_path):
    source = tmp_path / "old"
    seed(source)
    with pytest.raises(ValueError, match="separate"):
        migration.migrate(source, source / "child", "previous.db")
    (source / "link").symlink_to(source / "previous.db")
    with pytest.raises(ValueError, match="Symlinks"):
        migration.migrate(source, tmp_path / "new", "previous.db")
