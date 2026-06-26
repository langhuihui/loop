#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=false

if [ "${1:-}" = "--dry-run" ] || [ "${1:-}" = "-n" ]; then
  DRY_RUN=true
  shift
fi

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 [--dry-run|-n] <task> [build-profile-options]" >&2
  echo 'Example: ./scripts/quick-setup.sh "Implement feature X" --lang zh --constraint "No server"' >&2
  exit 2
fi

if [ "$DRY_RUN" = true ]; then
  "$ROOT/scripts/build-profile.py" "$@" | "$ROOT/scripts/apply-setup.sh" --dry-run -
  exit 0
fi

echo "==> Build and apply profile"
"$ROOT/scripts/build-profile.py" "$@" | "$ROOT/scripts/apply-setup.sh" - >/dev/null

echo "==> Generated prompts"
"$ROOT/scripts/prompts.sh"
