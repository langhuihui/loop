#!/usr/bin/env bash
# Background watcher for Session A — paste into Cursor /loop or run standalone.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
. "$ROOT/scripts/_hub-url.sh"
HUB_URL="$(coord_resolve_hub_url "$ROOT")"
LAST_WAKE_ID=0

while true; do
  resp=$(curl -sf --max-time 3700 "${HUB_URL}/wait/A?since=${LAST_WAKE_ID}" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  next_wake_id=$(printf '%s' "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id", 0))' 2>/dev/null || echo 0)
  if [ "$next_wake_id" -gt "$LAST_WAKE_ID" ] 2>/dev/null; then
    LAST_WAKE_ID="$next_wake_id"
  fi
  echo "AGENT_LOOP_WAKE_DEV {\"hub\":${resp}}"
done
