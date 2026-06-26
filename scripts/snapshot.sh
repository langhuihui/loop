#!/usr/bin/env bash
set -euo pipefail

HUB_URL="${COORD_HUB_URL:-http://127.0.0.1:9900}"
TIMEOUT="${COORD_SNAPSHOT_TIMEOUT:-5}"
HISTORY_LIMIT=""
LESSONS_LIMIT=""
RAW=false

usage() {
  cat >&2 <<'EOF'
Usage:
  scripts/snapshot.sh [--history-limit N] [--lessons-limit N] [--raw]
EOF
}

require_positive_int() {
  local value="$1"
  local name="$2"
  if ! [[ "$value" =~ ^[0-9]+$ ]] || [ "$value" -lt 1 ]; then
    echo "$name must be a positive integer" >&2
    exit 2
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --history-limit)
      if [ "$#" -lt 2 ]; then
        usage
        exit 2
      fi
      require_positive_int "$2" "history limit"
      HISTORY_LIMIT="$2"
      shift 2
      ;;
    --lessons-limit)
      if [ "$#" -lt 2 ]; then
        usage
        exit 2
      fi
      require_positive_int "$2" "lessons limit"
      LESSONS_LIMIT="$2"
      shift 2
      ;;
    --raw)
      RAW=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

query=""
if [ -n "$HISTORY_LIMIT" ]; then
  query="history_limit=$HISTORY_LIMIT"
fi
if [ -n "$LESSONS_LIMIT" ]; then
  if [ -n "$query" ]; then
    query="$query&"
  fi
  query="${query}lessons_limit=$LESSONS_LIMIT"
fi

url="${HUB_URL}/snapshot"
if [ -n "$query" ]; then
  url="${url}?${query}"
fi

body="$(curl -sf --max-time "$TIMEOUT" "$url")"
if [ "$RAW" = true ]; then
  printf '%s\n' "$body"
else
  printf '%s\n' "$body" | python3 -m json.tool
fi
