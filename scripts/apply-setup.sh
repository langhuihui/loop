#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
. "$ROOT/scripts/_hub-url.sh"
HUB_URL="$(coord_resolve_hub_url "$ROOT")"
TIMEOUT="${COORD_APPLY_TIMEOUT:-5}"
DRY_RUN=false
TMP_PROFILE=""

cleanup() {
  if [ -n "$TMP_PROFILE" ]; then
    rm -f "$TMP_PROFILE"
  fi
}
trap cleanup EXIT

if [ "${1:-}" = "--dry-run" ] || [ "${1:-}" = "-n" ]; then
  DRY_RUN=true
  shift
fi

PROFILE_FILE="${1:-$ROOT/examples/setup-dev-review.json}"

if [ "$PROFILE_FILE" = "-" ]; then
  TMP_PROFILE="$(mktemp "${TMPDIR:-/tmp}/coord-profile.XXXXXX.json")"
  cat > "$TMP_PROFILE"
  PROFILE_FILE="$TMP_PROFILE"
elif [ ! -f "$PROFILE_FILE" ] && [[ "$PROFILE_FILE" != /* ]]; then
  PROFILE_FILE="$ROOT/$PROFILE_FILE"
fi

if [ ! -f "$PROFILE_FILE" ]; then
  echo "profile file not found: $PROFILE_FILE" >&2
  echo "Usage: $0 [--dry-run|-n] [profile-json-file|-]" >&2
  exit 1
fi

python3 "$ROOT/scripts/validate-profile.py" "$PROFILE_FILE" >/dev/null

if [ "$DRY_RUN" = true ]; then
  python3 -m json.tool "$PROFILE_FILE"
  exit 0
fi

curl -sf --max-time "$TIMEOUT" -X POST "${HUB_URL}/setup" \
  -H 'Content-Type: application/json' \
  -d @"$PROFILE_FILE" | python3 -m json.tool
