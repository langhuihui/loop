#!/usr/bin/env bash
set -euo pipefail

HUB_URL="${COORD_HUB_URL:-http://127.0.0.1:9900}"
TIMEOUT="${COORD_SIGNAL_TIMEOUT:-5}"
DRY_RUN=false
STOPPED=false

usage() {
  cat >&2 <<'EOF'
Usage:
  scripts/signal.sh [--dry-run] [--stopped] <target A|B> <progress|blocked|no-op|done> <summary> [epoch] [turn A|B]
EOF
}

upper_role() {
  printf '%s' "$1" | tr '[:lower:]' '[:upper:]'
}

require_nonnegative_int() {
  local value="$1"
  local name="$2"
  if ! [[ "$value" =~ ^[0-9]+$ ]]; then
    echo "$name must be a non-negative integer" >&2
    exit 2
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --stopped)
      STOPPED=true
      shift
      ;;
    *)
      break
      ;;
  esac
done

if [ "$#" -lt 3 ] || [ "$#" -gt 5 ]; then
  usage
  exit 2
fi

TARGET="$(upper_role "$1")"
OUTCOME="$2"
SUMMARY="$3"
EPOCH="${4:-}"
TURN="${5:-}"

case "$TARGET" in
  A|B) ;;
  *)
    echo "target must be A or B" >&2
    exit 2
    ;;
esac

case "$OUTCOME" in
  progress|blocked|no-op|done) ;;
  *)
    echo "outcome must be one of: progress, blocked, no-op, done" >&2
    exit 2
    ;;
esac

if [ -z "$SUMMARY" ]; then
  echo "summary is required" >&2
  exit 2
fi

if [ -n "$EPOCH" ]; then
  require_nonnegative_int "$EPOCH" "epoch"
fi

if [ -n "$TURN" ]; then
  TURN="$(upper_role "$TURN")"
  case "$TURN" in
    A|B) ;;
    *)
      echo "turn must be A or B" >&2
      exit 2
      ;;
  esac
fi

body="$(TARGET="$TARGET" OUTCOME="$OUTCOME" SUMMARY="$SUMMARY" EPOCH="$EPOCH" TURN="$TURN" STOPPED="$STOPPED" python3 -c '
import json
import os

body = {
    "target": os.environ["TARGET"],
    "payload": {
        "outcome": os.environ["OUTCOME"],
        "summary": os.environ["SUMMARY"],
    },
}
epoch = os.environ.get("EPOCH", "")
turn = os.environ.get("TURN", "")
if epoch:
    body["epoch"] = int(epoch)
if turn:
    body["turn"] = turn
if os.environ.get("STOPPED") == "true":
    body["stopped"] = True
print(json.dumps(body))
')"

if [ "$DRY_RUN" = true ]; then
  printf '%s\n' "$body" | python3 -m json.tool
  exit 0
fi

curl -sf --max-time "$TIMEOUT" \
  -H "Content-Type: application/json" \
  -d "$body" \
  "${HUB_URL}/signal" | python3 -m json.tool
