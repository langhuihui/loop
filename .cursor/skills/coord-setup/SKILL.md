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

1. **Check MCP availability** — use the `cursor-ab-coord` MCP tools if they are available in the current Cursor session. If `coord_start` is not available, tell the user to reload MCP configuration or run `./scripts/start.sh` manually.
2. **Start the hub** — call MCP tool `coord_start`.
3. **Give the user the config UI link** from the tool result (`ui_url`, typically `http://127.0.0.1:9900/ui/`). Ask them to open it in a browser.
4. **Tell the user what to do in the UI**:
   - Pick a workflow template (or customize Role A / Role B)
   - Enter the runtime task title, branch, and constraints
   - Click **Generate & apply**
   - Copy the **Session B** prompt first, then **Session A**
5. **Paste order** — Session **B** must be started **before** Session **A**.
6. After the user finishes in the UI, optionally fetch prompts via `coord_prompt` (`role: "B"` then `role: "A"`) if they need them repeated in chat.
7. If the user explicitly wants a no-UI flow, call `coord_quick_setup` with the template/task fields, then use its `paste_order` and `prompts` fields to tell the user exactly what to paste. Pass `lang: "zh"` for Chinese profile and prompts. Use `coord_build_profile` + `coord_setup` only when you need to inspect or adjust the generated profile before applying it.

Do **not** paste long hard-coded prompts. The hub stores the profile; prompts re-anchor with `/snapshot` at runtime.

## MCP tools

| Tool | When |
|------|------|
| `coord_version` | Check local MCP/plugin version without starting the hub |
| `coord_doctor` | Diagnose local files, scripts, hub, UI, and prompt availability |
| `coord_start` | First step — start hub |
| `coord_clear_state` | Clear runtime and persisted state/profile/history/lessons when explicitly requested |
| `coord_quick_setup` | No-UI one-shot setup: start hub, build profile, apply setup |
| `coord_setup_url` | If hub already running, get UI link |
| `coord_status` | Check epoch / turn / stopped |
| `coord_health` | Lightweight hub health check |
| `coord_snapshot` | Re-anchor with state, profile, recent history, lessons, and health in one call |
| `coord_history` | Inspect recent setup/signal/reset events; use `since_id` for incremental reads |
| `coord_lessons` | List or add shared lessons learned during long-running coordination |
| `coord_signal_outcome` | Send a standard signal with validated outcome and summary |
| `coord_build_profile` | Build a profile from template and task fields |
| `coord_templates` | Fetch workflow templates for a no-UI setup |
| `coord_validate_profile` | Validate a generated profile before applying it |
| `coord_setup` | Apply a full profile and return prompts |
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
| MCP tool unavailable | Reload Cursor MCP config, verify `.cursor/mcp.json`, or run `./scripts/start.sh` manually |
| Unsure why setup fails | Run `coord_doctor` and surface its output |
| Hub unreachable | Run `coord_start` or `./scripts/start.sh` |
| No profile / empty prompts | User must click **Generate & apply** in the UI |
| Session not waking | Confirm watcher loop is running in that session's `/loop` prompt |
