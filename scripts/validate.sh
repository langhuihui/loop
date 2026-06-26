#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TIMEOUT="${COORD_VALIDATE_TIMEOUT:-20}"

run() {
  local label="$1"
  shift
  echo "==> $label"
  timeout "$TIMEOUT" "$@"
}

cd "$ROOT"

run "python unit tests" python3 -m unittest discover -s tests
run "python syntax" python3 -m py_compile coord-hub.py lib/profile.py lib/prompt.py lib/version.py mcp/server.py scripts/build-profile.py scripts/validate-profile.py
run "hub version" python3 coord-hub.py --version
run "json syntax" python3 - <<'PY'
import json
from pathlib import Path

for path in [
    Path("mcp.json"),
    Path(".cursor/mcp.json"),
    Path(".cursor-plugin/plugin.json"),
    Path("lib/templates.json"),
    Path("lib/templates.zh.json"),
    *sorted(Path("examples").glob("*.json")),
]:
    json.loads(path.read_text(encoding="utf-8"))
PY
run "profile examples" python3 scripts/validate-profile.py examples/setup-dev-review.json
run "profile examples zh" python3 scripts/validate-profile.py examples/setup-dev-review.zh.json
run "profile stdin" bash -c './scripts/build-profile.py "Implement X" | python3 scripts/validate-profile.py - >/dev/null'
run "build profile" bash -c './scripts/build-profile.py "Implement X" --constraint "No server" >/dev/null'
run "apply setup dry run" bash -c './scripts/apply-setup.sh --dry-run examples/setup-dev-review.json >/dev/null'
run "apply setup stdin dry run" bash -c './scripts/build-profile.py "Implement X" | ./scripts/apply-setup.sh --dry-run - >/dev/null'
run "quick setup dry run" bash -c './scripts/quick-setup.sh --dry-run "Implement X" --constraint "No server" >/dev/null'
run "reset max epochs validation" bash -c '! COORD_MAX_EPOCHS=0 ./scripts/reset.sh "Implement X" >/dev/null 2>&1'
run "ui js syntax" node --check ui/js/main.js ui/js/i18n.js
run "website js syntax" node --check website/js/main.js website/js/i18n.js
run "shell syntax" bash -n scripts/_hub-url.sh scripts/start.sh scripts/stop.sh scripts/status.sh scripts/reset.sh scripts/apply-setup.sh scripts/prompts.sh scripts/signal.sh scripts/lessons.sh scripts/snapshot.sh scripts/quick-setup.sh scripts/doctor.sh scripts/clear-state.sh scripts/validate.sh watchers/wait-a.sh watchers/wait-b.sh

echo "All checks passed."
