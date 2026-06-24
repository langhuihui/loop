#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="${COORD_HUB_PID_FILE:-$ROOT/.coord-hub.pid}"

if [ ! -f "$PID_FILE" ]; then
  echo "coord-hub not running (no pid file)"
  exit 0
fi

pid=$(cat "$PID_FILE")
if kill -0 "$pid" 2>/dev/null; then
  kill "$pid"
  echo "stopped coord-hub (pid $pid)"
else
  echo "coord-hub not running (stale pid $pid)"
fi
rm -f "$PID_FILE"
