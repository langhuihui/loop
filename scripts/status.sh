#!/usr/bin/env bash
set -euo pipefail

HUB_URL="${COORD_HUB_URL:-http://127.0.0.1:9900}"

curl -sf --max-time 5 "${HUB_URL}/state" | python3 -m json.tool
