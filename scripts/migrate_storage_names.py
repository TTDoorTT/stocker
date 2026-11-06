"""Copy a stopped installation's data into empty private storage, verifying every file.

Run in a container with the source mounted read-only and destination writable.
The source is retained. SQLite uses verified backup, including committed WAL data.
"""

import argparse
import hashlib
import os
import shutil
import sqlite3
from pathlib import Path

from backup_local_state import snapshot


def migrate(source: Path, target: Path, source_database: str, target_database: str = "stocker.db"):
    source, target = source.resolve(), target.resolve()
    for name in (source_database, target_database):
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("Database names must be plain filenames")
    if source == target or source in target.parents or target in source.parents:
        raise ValueError("Source and destination must be separate directories")
    if not source.is_dir() or not (source / source_database).is_file():
        raise ValueError("Source storage and selected database must exist")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("Destination must be empty; existing storage is never overwritten")
    paths = sorted(source.rglob("*"))
    if any(path.is_symlink() for path in paths):
        raise ValueError("Symlinks are not supported in private storage")
    if source_database != target_database and (source / target_database).exists():
        raise ValueError("Renamed database would collide with another source file")
    os.umask(0o077)
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.chmod(0o700)
    copied = 0
    for path in paths:
        relative = path.relative_to(source)
        if path.is_dir():
            (target / relative).mkdir(parents=True, exist_ok=True, mode=0o700)
            (target / relative).chmod(0o700)
            continue
        # SQLite backups capture committed WAL content; do not copy transient sidecars.
        if path.name.endswith(("-wal", "-shm", "-journal")):
            continue
        if relative == Path(source_database):
            relative = Path(target_database)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open("rb") as stream:
            sqlite_file = stream.read(16) == b"SQLite format 3\x00"
        if sqlite_file:
            with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as src:
                before = snapshot(src)
                if before["integrity"] != ["ok"] or before["user_version"] != 1:
                    raise ValueError("Source database integrity/schema verification failed")
                with destination.open("xb"):
                    pass
                with sqlite3.connect(destination) as dst:
                    src.backup(dst)
                    if snapshot(dst) != before:
                        raise ValueError("Database verification failed")
        else:
            with path.open("rb") as src, destination.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            if (
                hashlib.sha256(path.read_bytes()).digest()
                != hashlib.sha256(destination.read_bytes()).digest()
            ):
                raise ValueError("File verification failed")
        destination.chmod(0o600)
        copied += 1
    print(f"Storage copy verified: {copied} files; source retained, secrets not displayed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--source-database", required=True)
    parser.add_argument("--target-database", default="stocker.db")
    args = parser.parse_args()
    migrate(args.source, args.target, args.source_database, args.target_database)


if __name__ == "__main__":
    main()
