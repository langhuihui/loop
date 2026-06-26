#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
. "$ROOT/scripts/_hub-url.sh"
HUB_URL="$(coord_resolve_hub_url "$ROOT")"
TIMEOUT="${COORD_STATUS_TIMEOUT:-5}"

snapshot="$(curl -sf --max-time "$TIMEOUT" "${HUB_URL}/snapshot" 2>/dev/null || true)"
if [ -n "$snapshot" ]; then
  printf '%s\n' "$snapshot" | python3 -m json.tool
else
  health="$(curl -sf --max-time "$TIMEOUT" "${HUB_URL}/health" 2>/dev/null || true)"
  if [ -n "$health" ]; then
    printf '%s\n' "$health" | python3 -m json.tool
  else
    curl -sf --max-time "$TIMEOUT" "${HUB_URL}/state" | python3 -m json.tool
  fi
fi
