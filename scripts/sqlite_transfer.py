"""Import a verified SQLite snapshot into a new path; never overwrite a database.

Run with services stopped, mounting the source read-only. Prints no records.
"""
import os
import sqlite3
import sys
from pathlib import Path

from backup_local_state import snapshot


def main():
    source, target = (Path(value).resolve() for value in sys.argv[1:])
    os.umask(0o077)
    if not source.is_file():
        raise SystemExit('Source snapshot does not exist')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive reservation prevents accidental replacement of existing history.
    with target.open('xb'):
        pass
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src, sqlite3.connect(target) as dst:
        before = snapshot(src)
        if before['integrity'] != ['ok'] or before['user_version'] != 1:
            raise SystemExit('Source is not an integrity-verified schema v1 snapshot')
        src.backup(dst)
        if snapshot(dst) != before:
            raise SystemExit('Imported database does not match source')
    print('SQLite import verified: schema, integrity, table counts and all row fingerprints match')


if __name__ == '__main__':
    main()
