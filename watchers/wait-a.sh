#!/usr/bin/env bash
# Background watcher for Session A — paste into Cursor /loop or run standalone.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
. "$ROOT/scripts/_hub-url.sh"
HUB_URL="$(coord_resolve_hub_url "$ROOT")"

while true; do
  resp=$(curl -sf --max-time 3700 "${HUB_URL}/wait/A" 2>/dev/null || echo "")
  [ -z "$resp" ] && continue
  echo "AGENT_LOOP_WAKE_DEV {\"hub\":${resp}}"
done
