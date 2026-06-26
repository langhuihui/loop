#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.profile import validate_profile  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <profile-json-file|->", file=sys.stderr)
        return 2

    try:
        if sys.argv[1] == "-":
            raw = sys.stdin.read()
        else:
            path = Path(sys.argv[1])
            if not path.is_file() and not path.is_absolute():
                path = ROOT / path
            raw = path.read_text(encoding="utf-8")
        profile = json.loads(raw)
    except FileNotFoundError:
        print(f"profile file not found: {path}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"invalid json: {e}", file=sys.stderr)
        return 1

    errors = validate_profile(profile)
    if errors:
        print("invalid profile:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("profile ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
