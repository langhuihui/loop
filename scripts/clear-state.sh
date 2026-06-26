#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${COORD_DATA_DIR:-$ROOT}"

rm -f \
  "$DATA_DIR/.coord-state.json" \
  "$DATA_DIR/.coord-state.json.tmp" \
  "$DATA_DIR/.coord-profile.json" \
  "$DATA_DIR/.coord-profile.json.tmp" \
  "$DATA_DIR/.coord-history.json" \
  "$DATA_DIR/.coord-history.json.tmp" \
  "$DATA_DIR/.coord-lessons.json" \
  "$DATA_DIR/.coord-lessons.json.tmp" \
  "$DATA_DIR/.coord-endpoint.json" \
  "$DATA_DIR/.coord-endpoint.json.tmp"

echo "cleared coord-hub persisted state/profile/history/lessons in $DATA_DIR"
