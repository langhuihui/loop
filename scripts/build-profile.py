#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.profile import build_profile, template_ids, validate_profile  # noqa: E402


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("must be a positive integer") from e
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a coord-hub /setup profile JSON")
    parser.add_argument("task", help="runtime task title")
    parser.add_argument("--template", default="dev-review", choices=template_ids())
    parser.add_argument("--branch", default="main")
    parser.add_argument("--constraint", action="append", default=[], help="runtime constraint")
    parser.add_argument("--max-epochs", type=positive_int, default=20)
    parser.add_argument("--lang", choices=("en", "zh"), default="en")
    args = parser.parse_args()

    profile = build_profile(
        args.template,
        task={
            "title": args.task,
            "branch": args.branch,
            "constraints": args.constraint,
        },
        max_epochs=args.max_epochs,
        lang=args.lang,
    )
    errors = validate_profile(profile)
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(json.dumps(profile, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
