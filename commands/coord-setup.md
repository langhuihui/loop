---
name: coord-setup
description: Start A/B Cursor session coordination with the local hub and setup UI.
---

# Coord Setup

Set up A/B Cursor session coordination for the current workspace.

Use the `coord-setup` skill. Start the local hub with the `cursor-ab-coord`
MCP tool `coord_start`, return the setup UI URL, and guide the user to copy the
generated Session B prompt first, then Session A.

If MCP tools are unavailable, tell the user to enable or reload the
`cursor-ab-coord` plugin/MCP server instead of pasting long hard-coded prompts.
