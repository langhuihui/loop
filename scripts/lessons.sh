#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
. "$ROOT/scripts/_hub-url.sh"
HUB_URL="$(coord_resolve_hub_url "$ROOT")"
TIMEOUT="${COORD_LESSONS_TIMEOUT:-5}"
CMD="${1:-list}"

usage() {
  cat >&2 <<'EOF'
Usage:
  scripts/lessons.sh [list [limit]]
  scripts/lessons.sh add <A|B> <text> [epoch]
EOF
}

print_lessons() {
  python3 -c '
import json
import sys

body = json.load(sys.stdin)
items = body.get("lessons", [])
if not items:
    print("(no lessons)")
    raise SystemExit(0)

for item in items:
    role = item.get("role") or "-"
    epoch = item.get("epoch")
    epoch_text = "-" if epoch is None else str(epoch)
    lesson_id = item.get("id")
    text = item.get("text", "")
    print(f"#{lesson_id} [{role} epoch {epoch_text}] {text}")
'
}

require_positive_int() {
  local value="$1"
  local name="$2"
  if ! [[ "$value" =~ ^[0-9]+$ ]] || [ "$value" -lt 1 ]; then
    echo "$name must be a positive integer" >&2
    exit 2
  fi
}

case "$CMD" in
  list)
    limit="${2:-20}"
    require_positive_int "$limit" "limit"
    curl -sf --max-time "$TIMEOUT" "${HUB_URL}/lessons?limit=${limit}" | print_lessons
    ;;
  add)
    if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
      usage
      exit 2
    fi
    role="$2"
    text="$3"
    epoch="${4:-}"
    role_upper="$(printf '%s' "$role" | tr '[:lower:]' '[:upper:]')"
    case "$role_upper" in
      A|B) role="$role_upper" ;;
      *)
        echo "role must be A or B" >&2
        exit 2
        ;;
    esac
    if [ -n "$epoch" ] && ! [[ "$epoch" =~ ^[0-9]+$ ]]; then
      echo "epoch must be a non-negative integer" >&2
      exit 2
    fi
    if [ -z "$text" ]; then
      echo "text is required" >&2
      exit 2
    fi
    body="$(ROLE="$role" TEXT="$text" EPOCH="$epoch" python3 -c '
import json
import os

body = {"role": os.environ["ROLE"], "text": os.environ["TEXT"]}
epoch = os.environ.get("EPOCH", "")
if epoch:
    body["epoch"] = int(epoch)
print(json.dumps(body))
')"
    curl -sf --max-time "$TIMEOUT" \
      -H "Content-Type: application/json" \
      -d "$body" \
      "${HUB_URL}/lessons" | python3 -c '
import json
import sys

body = json.load(sys.stdin)
lesson = body["lesson"]
print(f"saved lesson #{lesson[\"id\"]}")
'
    ;;
  *)
    usage
    exit 2
    ;;
esac
