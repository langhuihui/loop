#!/usr/bin/env bash
# Background watcher for Session A — paste into Cursor /loop or run standalone.
set -euo pipefail

HUB_URL="${COORD_HUB_URL:-http://127.0.0.1:9900}"

while true; do
  resp=$(curl -sf --max-time 3700 "${HUB_URL}/wait/A" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "AGENT_LOOP_WAKE_DEV {\"hub\":${resp}}"
done
