#!/usr/bin/env bash
# Reset hub state. Usage: ./scripts/reset.sh "task description" [branch]
set -euo pipefail

HUB_URL="${COORD_HUB_URL:-http://127.0.0.1:9900}"
TASK="${1:-}"
BRANCH="${2:-$(git branch --show-current 2>/dev/null || echo main)}"
MAX_EPOCHS="${COORD_MAX_EPOCHS:-20}"

if [ -z "$TASK" ]; then
  echo "Usage: $0 <task> [branch]" >&2
  exit 1
fi

curl -sf --max-time 5 -X POST "${HUB_URL}/reset" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c "
import json, sys
print(json.dumps({
  'task': sys.argv[1],
  'branch': sys.argv[2],
  'turn': 'A',
  'epoch': 0,
  'max_epochs': int(sys.argv[3]),
}))
" "$TASK" "$BRANCH" "$MAX_EPOCHS")" | python3 -m json.tool

echo "Ready: turn=A, branch=$BRANCH"
