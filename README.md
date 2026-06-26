# cursor-ab-coord

Coordinate two [Cursor](https://cursor.com) chat sessions via a local HTTP hub, MCP tools, and a config UI — then copy generated `/loop` prompts into Session B and A.

```
coord-setup skill  →  MCP coord_start  →  Config UI (:9900/ui)
                                              │
Session A  ◄── POST /signal ──►  Coord Hub  ◄── POST /signal ──►  Session B
       ▲         GET /wait/A                    GET /wait/B              ▲
       └──────────────── /loop watchers ────────────────────────────────┘
```

## Quick start

### 1. Enable MCP (once per machine)

Add to your Cursor MCP config, or use the project file at [`.cursor/mcp.json`](.cursor/mcp.json):

```json
{
  "mcpServers": {
    "cursor-ab-coord": {
      "command": "python3",
      "args": ["mcp/server.py"]
    }
  }
}
```

Run MCP from the **repo root** (or install as a Cursor plugin — see below).

### 2. Run `coord-setup`

In any Cursor chat with this project/plugin enabled, ask:

> Set up A/B coordination

The repo includes `coord-setup` in two places:

- [`.cursor/skills/coord-setup/SKILL.md`](.cursor/skills/coord-setup/SKILL.md) — project skill for direct use in this repo
- [`skills/coord-setup/SKILL.md`](skills/coord-setup/SKILL.md) — plugin skill for packaging/distribution

The agent uses the skill to:

1. Call MCP `coord_start`
2. Give you the config UI link: **http://127.0.0.1:9900/ui/** (the hub root redirects there too)
3. Explain paste order: **Session B first**, then Session A

### 3. Configure in the UI

1. Open http://127.0.0.1:9900/ui/ (or http://127.0.0.1:9900)
2. Pick a workflow template (dev-review, test-fix, …) or edit Role A / B
3. Enter task title, branch, constraints
4. Click **Generate & apply**
5. Copy Session **B** prompt → paste into Cursor Session B
6. Copy Session **A** prompt → paste into Cursor Session A

Prompts are short: agents re-anchor with `GET /snapshot` from the hub at runtime.

The hub persists the latest state/profile/history/lessons in local hidden files (`.coord-state.json`, `.coord-profile.json`, `.coord-history.json`, `.coord-lessons.json`) so the UI can restore your setup after a restart.

## Cursor plugin install

This repository is laid out as a single Cursor plugin: `.cursor-plugin/plugin.json`
declares the plugin, `mcp.json` declares the MCP server, and
`skills/coord-setup/SKILL.md` provides the setup skill. The plugin also includes
`commands/coord-setup.md` as a slash-command entry point.

For local plugin testing, symlink the repo into Cursor's local plugins folder,
then reload Cursor:

```bash
mkdir -p ~/.cursor/plugins/local
ln -s "$(pwd)" ~/.cursor/plugins/local/cursor-ab-coord
```

After reload, enable the plugin from Cursor's Plugins UI and ask for
`coord-setup` in any workspace. When Cursor loads this as a plugin, the MCP
server keeps hub state under `~/.cursor-ab-coord` by default instead of writing
runtime files into Cursor's plugin cache. Override with `COORD_DATA_DIR` if you
want a different location.

### Change the hub port (avoid 9900 conflicts)

The hub binds `127.0.0.1:9900` by default. You can either pin another port or let
the OS pick a free one automatically.

**Auto (recommended when 9900 is taken):** set `COORD_HUB_PORT=auto`. The hub
binds a free port, writes the real `host:port` to `<data_dir>/.coord-endpoint.json`,
and the MCP server and helper scripts discover it from that file — you never pick
a number.

```json
{
  "mcpServers": {
    "cursor-ab-coord": {
      "command": "python3",
      "args": ["mcp/server.py"],
      "env": { "COORD_HUB_PORT": "auto" }
    }
  }
}
```

**Pinned:** set a concrete port; host/URL follow automatically.

```bash
export COORD_HUB_PORT=9931
./scripts/start.sh          # hub starts on 9931
./scripts/status.sh         # discovers 9931 from the endpoint file
```

Generated `/loop` prompts use whatever host:port the UI was opened on, so they
stay consistent with the chosen port. `COORD_HUB_URL` still wins if you need a
fully custom URL.

### Run multiple A/B loops at once

Each hub coordinates exactly one A/B loop (single shared state). To run several
loops in parallel, start one hub per loop, each with its own data directory (and
an auto port so they never collide):

```bash
# Loop 1
COORD_DATA_DIR=~/.coord/loop1 COORD_HUB_PORT=auto ./scripts/start.sh
# Loop 2
COORD_DATA_DIR=~/.coord/loop2 COORD_HUB_PORT=auto ./scripts/start.sh
```

Every helper script honours the same `COORD_DATA_DIR`, so point each loop's
commands at its own directory. State, pid, log, and the endpoint file all live
under that directory, keeping the loops fully isolated.

For Marketplace publishing, keep the repository public, validate locally, then
submit the repository URL at https://cursor.com/marketplace/publish.

## Manual start (without MCP)

```bash
./scripts/start.sh
open http://127.0.0.1:9900
```

Legacy flow with static prompts still works — see [`prompts/`](prompts/).

You can also apply a setup profile directly:

```bash
./scripts/quick-setup.sh "Implement feature X"
./scripts/build-profile.py "Implement feature X" | ./scripts/apply-setup.sh -
./scripts/prompts.sh        # print Session B then Session A prompts
./scripts/prompts.sh A      # print one prompt
./scripts/doctor.sh         # diagnose local setup and hub connectivity
./scripts/apply-setup.sh examples/setup-dev-review.json
./scripts/build-profile.py "Implement feature X" | ./scripts/validate-profile.py -
# validate and preview without contacting the hub
./scripts/quick-setup.sh --dry-run "Implement feature X"
./scripts/build-profile.py "Implement feature X" | ./scripts/apply-setup.sh --dry-run -
```

## Scripts

| Script | Description |
|--------|-------------|
| `./scripts/start.sh` | Start hub on `127.0.0.1:9900` |
| `./scripts/stop.sh` | Stop hub |
| `./scripts/status.sh` | Print hub health (falls back to state for older hubs) |
| `./scripts/build-profile.py <task>` | Generate a `/setup` profile from a template/task |
| `./scripts/apply-setup.sh [--dry-run] [file\|-]` | Validate/preview or apply a `/setup` profile JSON |
| `./scripts/prompts.sh [A\|B\|all]` | Print generated prompts from the active hub profile |
| `./scripts/quick-setup.sh [--dry-run] <task>` | Build/apply a profile and print Session B then A prompts |
| `./scripts/doctor.sh` | Diagnose local files, scripts, hub connectivity, UI, and prompts |
| `./scripts/validate-profile.py <file\|->` | Validate a `/setup` profile JSON without contacting the hub |
| `./scripts/snapshot.sh [--raw]` | Fetch consolidated `/snapshot` context |
| `./scripts/signal.sh [--dry-run] ...` | Send a validated outcome signal |
| `./scripts/lessons.sh list\|add` | List or add shared lessons |
| `./scripts/reset.sh "<task>" [branch]` | Reset epoch & task (legacy) |
| `./scripts/clear-state.sh` | Remove persisted `.coord-*.json` state/profile/history/lessons |

Script timeouts can be tuned with environment variables such as `COORD_APPLY_TIMEOUT`, `COORD_DOCTOR_TIMEOUT`, `COORD_LESSONS_TIMEOUT`, `COORD_PROMPT_TIMEOUT`, `COORD_RESET_TIMEOUT`, `COORD_SIGNAL_TIMEOUT`, `COORD_SNAPSHOT_TIMEOUT`, `COORD_STATUS_TIMEOUT`, and `COORD_VALIDATE_TIMEOUT`.
Runtime state, pid, and log files default to the repository root for direct
script usage. Set `COORD_DATA_DIR` to store them elsewhere; plugin-loaded MCP
defaults this to `~/.cursor-ab-coord`.
Profile file arguments may be absolute paths or paths relative to the repository root.

## MCP tools

| Tool | Description |
|------|-------------|
| `coord_version` | Return MCP/plugin version without requiring the hub |
| `coord_start` | Start hub, return UI URL |
| `coord_doctor` | Run local diagnostics for files, scripts, hub, UI, and prompts |
| `coord_stop` | Stop hub |
| `coord_clear_state` | Clear runtime and persisted state/profile/history/lessons (`confirm: true`) |
| `coord_quick_setup` | Start hub, build profile, apply setup, return prompts |
| `coord_setup_url` | Get config UI URL |
| `coord_status` | `GET /state` |
| `coord_health` | `GET /health` |
| `coord_snapshot` | `GET /snapshot` with state, profile, history, lessons, and health |
| `coord_history` | `GET /history` with optional `limit` / `since_id` |
| `coord_lessons` | List or add shared lessons |
| `coord_reset` | `POST /reset` |
| `coord_build_profile` | Build a profile from template/task inputs |
| `coord_templates` | `GET /templates` |
| `coord_validate_profile` | Local profile validation before setup |
| `coord_setup` | `POST /setup` with a full profile |
| `coord_signal` | `POST /signal` |
| `coord_signal_outcome` | `POST /signal` with validated `payload.outcome` and summary |
| `coord_profile` | `GET` or `POST /profile` |
| `coord_prompt` | `GET /prompt/A` or `/prompt/B` |

The recommended path is still the UI. `coord_quick_setup` exists for fully agent-driven setup when the user explicitly wants to skip the browser UI; it returns `paste_order`, `prompts`, `ui_url`, and a `profile_summary`. Pass `lang: "zh"` for Chinese profiles/prompts. `coord_build_profile`, `coord_templates`, and `coord_validate_profile` are available for advanced customization.

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/state` | Coordination state |
| GET | `/health` | Lightweight health summary, including version |
| GET | `/snapshot` | Consolidated state/profile/history/lessons/health re-anchor context |
| GET | `/profile` | Role profile |
| POST | `/profile` | Save profile (no reset) |
| POST | `/validate-profile` | Validate a profile without saving or resetting state |
| POST | `/setup` | Save profile + reset state + return prompts |
| POST | `/clear` | Clear runtime and persisted state/profile/history/lessons (`{"confirm": true}`) |
| GET | `/templates` | Workflow template catalog (`?lang=zh` for Chinese) |
| GET | `/history` | Recent setup/signal/reset events (`?limit=10&since_id=3`) |
| GET | `/lessons` | Recent shared lessons (`?limit=20`) |
| POST | `/lessons` | Add a shared lesson (`role`, `epoch`, `text`) |
| GET | `/prompt/A` · `/prompt/B` | Generated `/loop` prompt |
| GET | `/wait/A` · `/wait/B` | Long-poll wake |
| POST | `/signal` | Signal target role; include `payload.outcome` (`progress`, `blocked`, `no-op`, `done`) |
| POST | `/reset` | Reset state |
| GET | `/ui/` | Config UI |

## Workflow templates

| Template | Role A | Role B |
|----------|--------|--------|
| `dev-review` | builder | reviewer (fix + commit) |
| `test-fix` | tester | fixer |
| `plan-implement` | architect | implementer |
| `security-fix` | auditor | developer |

Templates live in [`lib/templates.json`](lib/templates.json).
Chinese template overrides live in [`lib/templates.zh.json`](lib/templates.zh.json). The real config UI loads localized templates from `GET /templates?lang=zh`; the `website/` folder remains a static demo site.

## Payload actions (dev-review default)

| `payload.action` | From | Meaning |
|------------------|------|---------|
| `review` | A → B | A finished a slice; B should review |
| `continue_dev` | B → A | B reviewed; A continues |
| `blocked` | B → A | Stop loop; human needed |

## Project layout

```
coord-hub.py          # Hub server
lib/                  # Templates + prompt builder
lib/version.py        # Shared version for hub and MCP server
ui/                   # Config UI (served at /ui/)
mcp/server.py         # MCP stdio server
commands/             # Plugin slash commands
.cursor/mcp.json      # Project MCP config
.cursor/skills/       # Project skills recognized in this repo
skills/coord-setup/   # Plugin skill copy for distribution
website/              # Static marketing / demo site (no hub connection)
```

## Requirements

- Python 3.9+ (stdlib only)
- `curl`
- Cursor with `/loop` support

## Validate

```bash
./scripts/validate.sh
```

Each validation step runs with a timeout. Override with `COORD_VALIDATE_TIMEOUT=<seconds>`.
GitHub Actions runs the same command on push and pull requests.

## License

MIT — see [LICENSE](LICENSE).
