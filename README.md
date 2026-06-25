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

In any Cursor chat in this repo, ask:

> Set up A/B coordination

The agent uses the [`coord-setup`](skills/coord-setup/SKILL.md) skill to:

1. Call MCP `coord_start`
2. Give you the config UI link: **http://127.0.0.1:9900/ui/**
3. Explain paste order: **Session B first**, then Session A

### 3. Configure in the UI

1. Open http://127.0.0.1:9900/ui/
2. Pick a workflow template (dev-review, test-fix, …) or edit Role A / B
3. Enter task title, branch, constraints
4. Click **Generate & apply**
5. Copy Session **B** prompt → paste into Cursor Session B
6. Copy Session **A** prompt → paste into Cursor Session A

Prompts are short: agents read `GET /profile` and `GET /state` from the hub at runtime.

The hub persists the latest state/profile/history in local hidden files (`.coord-state.json`, `.coord-profile.json`, `.coord-history.json`) so the UI can restore your setup after a restart.

## Manual start (without MCP)

```bash
./scripts/start.sh
open http://127.0.0.1:9900/ui/
```

Legacy flow with static prompts still works — see [`prompts/`](prompts/).

## Scripts

| Script | Description |
|--------|-------------|
| `./scripts/start.sh` | Start hub on `127.0.0.1:9900` |
| `./scripts/stop.sh` | Stop hub |
| `./scripts/status.sh` | Print hub state |
| `./scripts/reset.sh "<task>" [branch]` | Reset epoch & task (legacy) |

## MCP tools

| Tool | Description |
|------|-------------|
| `coord_start` | Start hub, return UI URL |
| `coord_stop` | Stop hub |
| `coord_setup_url` | Get config UI URL |
| `coord_status` | `GET /state` |
| `coord_reset` | `POST /reset` |
| `coord_signal` | `POST /signal` |
| `coord_profile` | `GET` or `POST /profile` |
| `coord_prompt` | `GET /prompt/A` or `/prompt/B` |

## HTTP API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/state` | Coordination state |
| GET | `/profile` | Role profile |
| POST | `/profile` | Save profile (no reset) |
| POST | `/setup` | Save profile + reset state + return prompts |
| GET | `/templates` | Workflow template catalog |
| GET | `/prompt/A` · `/prompt/B` | Generated `/loop` prompt |
| GET | `/wait/A` · `/wait/B` | Long-poll wake |
| POST | `/signal` | Signal target role |
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
ui/                   # Config UI (served at /ui/)
mcp/server.py         # MCP stdio server
skills/coord-setup/   # Cursor skill
website/              # Static marketing / demo site (no hub connection)
```

## Requirements

- Python 3.9+ (stdlib only)
- `curl`
- Cursor with `/loop` support

## License

MIT — see [LICENSE](LICENSE).
