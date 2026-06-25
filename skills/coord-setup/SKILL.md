---
name: coord-setup
description: >-
  Set up A/B Cursor session coordination — start the local hub via MCP, open
  the config UI, and guide the user to copy /loop prompts for Session B then A.
  Use when the user wants coord setup, A/B loops, dev-review coordination, or
  asks to run coord-setup.
---

# coord-setup

Set up two-session coordination for this repo.

## Instructions

1. **Start the hub** — call MCP tool `coord_start`.
2. **Give the user the config UI link** from the tool result (`ui_url`, typically `http://127.0.0.1:9900/ui/`). Ask them to open it in a browser.
3. **Tell the user what to do in the UI**:
   - Pick a workflow template (or customize Role A / Role B)
   - Enter the runtime task title, branch, and constraints
   - Click **Generate & apply**
   - Copy the **Session B** prompt first, then **Session A**
4. **Paste order** — Session **B** must be started **before** Session **A**.
5. After the user finishes in the UI, optionally fetch prompts via `coord_prompt` (`role: "B"` then `role: "A"`) if they need them repeated in chat.

Do **not** paste long hard-coded prompts. The hub stores the profile; prompts read `/profile` and `/state` at runtime.

## MCP tools

| Tool | When |
|------|------|
| `coord_start` | First step — start hub |
| `coord_setup_url` | If hub already running, get UI link |
| `coord_status` | Check epoch / turn / stopped |
| `coord_prompt` | Fetch generated prompt for A or B |
| `coord_stop` | User asks to tear down |

## Examples

User: "Set up A/B coordination for implementing feature X"

1. `coord_start`
2. Reply: "Hub is running. Open http://127.0.0.1:9900/ui/ — set task to 'Implement feature X', click Generate & apply, then paste Session B prompt first, then Session A."

## Performance Notes

- Hub binds `127.0.0.1:9900` by default.
- `coord_start` is idempotent if the hub is already running.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Hub unreachable | Run `coord_start` or `./scripts/start.sh` |
| No profile / empty prompts | User must click **Generate & apply** in the UI |
| Session not waking | Confirm watcher loop is running in that session's `/loop` prompt |
