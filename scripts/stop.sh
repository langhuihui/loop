#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="${COORD_HUB_PID_FILE:-$ROOT/.coord-hub.pid}"
HOST="${COORD_HUB_HOST:-127.0.0.1}"
PORT="${COORD_HUB_PORT:-9900}"

if [ ! -f "$PID_FILE" ]; then
  pattern="$ROOT/coord-hub.py --host $HOST --port $PORT"
  pid="$(pgrep -f "$pattern" 2>/dev/null | head -n 1 || true)"
  if [ -z "$pid" ]; then
    echo "coord-hub not running (no pid file)"
    exit 0
  fi
  kill "$pid"
  echo "stopped coord-hub (pid $pid, discovered by command match)"
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
