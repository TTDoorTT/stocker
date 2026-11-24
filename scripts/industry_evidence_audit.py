#!/usr/bin/env python3
"""Offline SEC excerpt audit CLI; run from anywhere, no external dependencies."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.intelligence.evidence_audit import (  # noqa: E402
    create_audit,
    summarize_audit,
    verify_local_source,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/review an offline, human-labeled SEC evidence audit")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="Build immutable manifest and editable review CSV")
    prepare.add_argument("--input", type=Path, required=True, help="Live /filing-excerpts JSON file")
    prepare.add_argument("--out", type=Path, required=True, help="Fresh local audit folder")
    prepare.add_argument("--limit", type=int, default=24)
    report = sub.add_parser("report", help="Check evidence integrity and summarize manual labels")
    report.add_argument("--audit", type=Path, required=True)
    report.add_argument("--strict", action="store_true", help="Fail when human review is incomplete")
    verify = sub.add_parser("verify-local", help="Compare excerpt against a locally saved SEC filing")
    verify.add_argument("--audit", type=Path, required=True)
    verify.add_argument("--sample-id", required=True)
    verify.add_argument("--source-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            result = create_audit(payload, args.out, args.limit)
        elif args.command == "report":
            result = summarize_audit(args.audit, strict=args.strict)
        else:
            result = verify_local_source(args.audit, args.sample_id, args.source_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Audit error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
