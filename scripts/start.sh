#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
. "$ROOT/scripts/_hub-url.sh"

HOST="${COORD_HUB_HOST:-127.0.0.1}"
PORT="${COORD_HUB_PORT:-9900}"
DATA_DIR="${COORD_DATA_DIR:-$ROOT}"
mkdir -p "$DATA_DIR"
PID_FILE="${COORD_HUB_PID_FILE:-$DATA_DIR/.coord-hub.pid}"
LOG_FILE="${COORD_HUB_LOG_FILE:-$DATA_DIR/.coord-hub.log}"
ENDPOINT_FILE="$DATA_DIR/.coord-endpoint.json"

if [ -f "$PID_FILE" ]; then
  old_pid=$(cat "$PID_FILE")
  if kill -0 "$old_pid" 2>/dev/null; then
    running_url="$(coord_endpoint_url "$DATA_DIR")"
    echo "coord-hub already running (pid $old_pid) on ${running_url:-unknown}"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if [ "$PORT" = "auto" ]; then
  LAUNCH_PORT=0
else
  LAUNCH_PORT="$PORT"
fi

# Drop a stale endpoint file so we read the freshly-bound port.
rm -f "$ENDPOINT_FILE"

nohup python3 "$ROOT/coord-hub.py" --host "$HOST" --port "$LAUNCH_PORT" >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

ACTUAL_URL=""
for _ in $(seq 1 50); do
  ACTUAL_URL="$(coord_endpoint_url "$DATA_DIR")"
  [ -n "$ACTUAL_URL" ] && break
  sleep 0.1
done

if [ -z "$ACTUAL_URL" ]; then
  echo "coord-hub failed to start; see $LOG_FILE" >&2
  exit 1
fi

if curl -sf --max-time 3 "$ACTUAL_URL/state" >/dev/null; then
  echo "coord-hub started (pid $(cat "$PID_FILE")) → $ACTUAL_URL"
  echo "config UI → $ACTUAL_URL/ui/"
  echo "log: $LOG_FILE"
else
  echo "coord-hub failed to start; see $LOG_FILE" >&2
  exit 1
fi
