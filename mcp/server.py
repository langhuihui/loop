#!/usr/bin/env python3
"""Stdlib-only MCP stdio server for cursor-ab-coord hub control."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HUB_URL = os.environ.get("COORD_HUB_URL", "http://127.0.0.1:9900").rstrip("/")
HUB_HOST = os.environ.get("COORD_HUB_HOST", "127.0.0.1")
HUB_PORT = os.environ.get("COORD_HUB_PORT", "9900")

TOOLS: list[dict[str, Any]] = [
    {
        "name": "coord_start",
        "description": "Start the local coord hub (coord-hub.py) if not already running.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_stop",
        "description": "Stop the local coord hub.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_status",
        "description": "Get current hub coordination state (GET /state).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_setup_url",
        "description": "Return the config UI URL for the running hub.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_reset",
        "description": "Reset hub epoch/task/branch (POST /reset).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "branch": {"type": "string"},
                "max_epochs": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_signal",
        "description": "Send a signal to role A or B (POST /signal).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "enum": ["A", "B"]},
                "epoch": {"type": "integer"},
                "turn": {"type": "string", "enum": ["A", "B"]},
                "payload": {"type": "object"},
                "stopped": {"type": "boolean"},
            },
            "required": ["target", "payload"],
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_profile",
        "description": "Get or set the role profile (GET/POST /profile).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {"type": "object", "description": "If set, POST profile to hub."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_prompt",
        "description": "Get generated /loop prompt for role A or B.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "enum": ["A", "B"]},
            },
            "required": ["role"],
            "additionalProperties": False,
        },
    },
]


def hub_request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{HUB_URL}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            err = json.loads(raw)
        except json.JSONDecodeError:
            err = {"error": raw or str(e)}
        raise RuntimeError(err.get("error", raw or str(e))) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"hub unreachable at {HUB_URL}: {e}") from e


def tool_result_text(obj: Any) -> dict[str, Any]:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "coord_start":
        script = ROOT / "scripts" / "start.sh"
        proc = subprocess.run(
            [str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "COORD_HUB_HOST": HUB_HOST, "COORD_HUB_PORT": HUB_PORT},
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError(out.strip() or "coord_start failed")
        return tool_result_text(
            {
                "ok": True,
                "message": out.strip(),
                "ui_url": f"http://{HUB_HOST}:{HUB_PORT}/ui/",
                "state": hub_request("GET", "/state"),
            }
        )

    if name == "coord_stop":
        script = ROOT / "scripts" / "stop.sh"
        proc = subprocess.run([str(script)], cwd=ROOT, capture_output=True, text=True, timeout=10)
        out = (proc.stdout or "") + (proc.stderr or "")
        return tool_result_text({"ok": proc.returncode == 0, "message": out.strip()})

    if name == "coord_status":
        return tool_result_text(hub_request("GET", "/state"))

    if name == "coord_setup_url":
        return tool_result_text({"ui_url": f"http://{HUB_HOST}:{HUB_PORT}/ui/"})

    if name == "coord_reset":
        return tool_result_text(hub_request("POST", "/reset", arguments or {}))

    if name == "coord_signal":
        return tool_result_text(hub_request("POST", "/signal", arguments))

    if name == "coord_profile":
        if arguments.get("profile"):
            return tool_result_text(hub_request("POST", "/profile", arguments["profile"]))
        return tool_result_text(hub_request("GET", "/profile"))

    if name == "coord_prompt":
        role = str(arguments.get("role", "")).upper()
        return tool_result_text(hub_request("GET", f"/prompt/{role}"))

    raise RuntimeError(f"unknown tool: {name}")


def send(msg: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(msg: dict[str, Any]) -> None:
    method = msg.get("method")
    msg_id = msg.get("id")

    if method == "initialize":
        send(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "cursor-ab-coord", "version": "0.2.0"},
                },
            }
        )
        return

    if method == "notifications/initialized":
        return

    if method == "tools/list":
        send({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}})
        return

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            result = run_tool(name, arguments)
            send({"jsonrpc": "2.0", "id": msg_id, "result": result})
        except Exception as e:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": str(e)}],
                        "isError": True,
                    },
                }
            )
        return

    if msg_id is not None:
        send(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        )


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        handle(msg)


if __name__ == "__main__":
    main()
