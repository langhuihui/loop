#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

rm -f \
  "$ROOT/.coord-state.json" \
  "$ROOT/.coord-state.json.tmp" \
  "$ROOT/.coord-profile.json" \
  "$ROOT/.coord-profile.json.tmp" \
  "$ROOT/.coord-history.json" \
  "$ROOT/.coord-history.json.tmp" \
  "$ROOT/.coord-lessons.json" \
  "$ROOT/.coord-lessons.json.tmp"

echo "cleared coord-hub persisted state/profile/history/lessons"
