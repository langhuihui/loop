# shellcheck shell=bash
# Shared coord hub URL resolution with endpoint discovery.
# Source this file, then call coord_resolve_hub_url "<data_dir>".

# Print the running hub URL from the endpoint file, or empty if absent.
coord_endpoint_url() {
  local data_dir="$1"
  local ep="$data_dir/.coord-endpoint.json"
  [ -f "$ep" ] || return 0
  python3 -c '
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    url = data.get("url", "")
    if url:
        print(str(url).rstrip("/"))
except Exception:
    pass
' "$ep" 2>/dev/null
}

# Resolve the hub URL with precedence:
#   1. explicit COORD_HUB_URL
#   2. endpoint file under the data dir (a running hub)
#   3. COORD_HUB_HOST/COORD_HUB_PORT (auto -> default 9900)
coord_resolve_hub_url() {
  local data_dir="${COORD_DATA_DIR:-$1}"
  if [ -n "${COORD_HUB_URL:-}" ]; then
    printf '%s' "${COORD_HUB_URL%/}"
    return 0
  fi
  local discovered
  discovered="$(coord_endpoint_url "$data_dir")"
  if [ -n "$discovered" ]; then
    printf '%s' "$discovered"
    return 0
  fi
  local host="${COORD_HUB_HOST:-127.0.0.1}"
  local port="${COORD_HUB_PORT:-9900}"
  [ "$port" = "auto" ] && port=9900
  printf 'http://%s:%s' "$host" "$port"
}
