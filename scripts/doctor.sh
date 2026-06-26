#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HUB_URL="${COORD_HUB_URL:-http://127.0.0.1:9900}"
TIMEOUT="${COORD_DOCTOR_TIMEOUT:-3}"
FAILS=0
WARNS=0

ok() {
  printf 'ok   %s\n' "$1"
}

warn() {
  WARNS=$((WARNS + 1))
  printf 'warn %s\n' "$1"
}

fail() {
  FAILS=$((FAILS + 1))
  printf 'fail %s\n' "$1"
}

require_file() {
  if [ -f "$ROOT/$1" ]; then
    ok "$1 exists"
  else
    fail "$1 missing"
  fi
}

require_executable() {
  if [ -x "$ROOT/$1" ]; then
    ok "$1 executable"
  else
    fail "$1 not executable"
  fi
}

probe_json() {
  local url="$1"
  curl -sf --max-time "$TIMEOUT" "$url" 2>/dev/null || true
}

cd "$ROOT"

echo "Coord doctor"
echo "root: $ROOT"
echo "hub:  $HUB_URL"
echo

if command -v python3 >/dev/null 2>&1; then
  ok "python3 available"
else
  fail "python3 missing"
fi

if command -v curl >/dev/null 2>&1; then
  ok "curl available"
else
  fail "curl missing"
fi

require_file ".cursor-plugin/plugin.json"
require_file "mcp.json"
require_file ".cursor/mcp.json"
require_file "skills/coord-setup/SKILL.md"
require_file ".cursor/skills/coord-setup/SKILL.md"
require_executable "scripts/start.sh"
require_executable "scripts/stop.sh"
require_executable "scripts/build-profile.py"
require_executable "scripts/validate-profile.py"
require_executable "scripts/apply-setup.sh"
require_executable "scripts/prompts.sh"
require_executable "scripts/signal.sh"
require_executable "scripts/lessons.sh"
require_executable "scripts/quick-setup.sh"
require_executable "scripts/snapshot.sh"
require_executable "scripts/clear-state.sh"

if version="$(python3 coord-hub.py --version 2>/dev/null)"; then
  ok "coord-hub.py version $version"
else
  fail "coord-hub.py --version failed"
fi

if ./scripts/validate-profile.py examples/setup-dev-review.json >/dev/null 2>&1; then
  ok "example setup profile valid"
else
  fail "example setup profile invalid"
fi

health="$(probe_json "$HUB_URL/health")"
if [ -n "$health" ]; then
  ok "hub health reachable"
  printf '%s\n' "$health" | python3 -m json.tool 2>/dev/null || warn "hub health returned non-json"
  while IFS= read -r health_warning; do
    [ -n "$health_warning" ] && warn "hub health: $health_warning"
  done < <(printf '%s\n' "$health" | python3 -c 'import json, sys
try:
    body = json.load(sys.stdin)
except json.JSONDecodeError:
    raise SystemExit(0)
for warning in body.get("warnings", []):
    print(warning)
' 2>/dev/null)
  outcome_summary="$(printf '%s\n' "$health" | python3 -c 'import json, sys
try:
    counts = json.load(sys.stdin).get("outcome_counts", {})
except json.JSONDecodeError:
    raise SystemExit(0)
parts = [f"{key}={counts.get(key, 0)}" for key in ("progress", "blocked", "no-op", "done")]
print(" ".join(parts))
' 2>/dev/null || true)"
  [ -n "$outcome_summary" ] && ok "outcomes $outcome_summary"

  if curl -sf --max-time "$TIMEOUT" "$HUB_URL/ui/" >/dev/null 2>&1; then
    ok "UI reachable at $HUB_URL/ui/"
  else
    fail "UI not reachable at $HUB_URL/ui/"
  fi

  state="$(probe_json "$HUB_URL/state")"
  if [ -n "$state" ]; then
    if snapshot="$(probe_json "$HUB_URL/snapshot")" && [ -n "$snapshot" ]; then
      ok "hub snapshot reachable"
    else
      fail "hub snapshot unreachable"
    fi

    if lessons="$(probe_json "$HUB_URL/lessons")" && [ -n "$lessons" ]; then
      ok "hub lessons reachable"
    else
      fail "hub lessons unreachable"
    fi

    if printf '%s\n' "$state" | python3 -c 'import json, sys; raise SystemExit(0 if json.load(sys.stdin).get("has_profile") else 1)' 2>/dev/null; then
      ok "active profile configured"
      for role in B A; do
        if prompt="$(probe_json "$HUB_URL/prompt/$role")" && [ -n "$prompt" ]; then
          ok "prompt $role available"
        else
          fail "prompt $role unavailable"
        fi
      done
    else
      warn "no active profile; run setup via UI or ./scripts/apply-setup.sh"
    fi
  else
    fail "hub state unreachable"
  fi
else
  fail "hub health unreachable at $HUB_URL"
  warn "start it with ./scripts/start.sh, or set COORD_HUB_URL for a custom hub"
fi

echo
echo "Result: $FAILS failure(s), $WARNS warning(s)"

if [ "$FAILS" -gt 0 ]; then
  exit 1
fi
