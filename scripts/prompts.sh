#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
. "$ROOT/scripts/_hub-url.sh"
HUB_URL="$(coord_resolve_hub_url "$ROOT")"
TIMEOUT="${COORD_PROMPT_TIMEOUT:-5}"
ROLE="${1:-all}"
ROLE_UPPER="$(printf '%s' "$ROLE" | tr '[:lower:]' '[:upper:]')"

print_prompt() {
  local role="$1"
  curl -sf --max-time "$TIMEOUT" "${HUB_URL}/prompt/${role}" | python3 -c '
import json
import sys

body = json.load(sys.stdin)
print(body["prompt"])
'
}

case "$ROLE_UPPER" in
  A|B)
    print_prompt "$ROLE_UPPER"
    ;;
  ALL)
    echo "===== Session B ====="
    print_prompt "B"
    echo
    echo "===== Session A ====="
    print_prompt "A"
    ;;
  *)
    echo "Usage: $0 [A|B|all]" >&2
    exit 2
    ;;
esac
