#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${COORD_HUB_HOST:-127.0.0.1}"
PORT="${COORD_HUB_PORT:-9900}"
PID_FILE="${COORD_HUB_PID_FILE:-$ROOT/.coord-hub.pid}"
LOG_FILE="${COORD_HUB_LOG_FILE:-$ROOT/.coord-hub.log}"

if [ -f "$PID_FILE" ]; then
  old_pid=$(cat "$PID_FILE")
  if kill -0 "$old_pid" 2>/dev/null; then
    echo "coord-hub already running (pid $old_pid) on http://${HOST}:${PORT}"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

nohup python3 "$ROOT/coord-hub.py" --host "$HOST" --port "$PORT" >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
sleep 0.5

if curl -sf --max-time 3 "http://${HOST}:${PORT}/state" >/dev/null; then
  echo "coord-hub started (pid $(cat "$PID_FILE")) → http://${HOST}:${PORT}"
  echo "log: $LOG_FILE"
else
  echo "coord-hub failed to start; see $LOG_FILE" >&2
  exit 1
fi
