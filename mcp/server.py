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
sys.path.insert(0, str(ROOT))

from lib.profile import build_profile, validate_profile  # noqa: E402
from lib.version import VERSION  # noqa: E402

SERVER_VERSION = VERSION
HUB_HOST = os.environ.get("COORD_HUB_HOST", "127.0.0.1")
HUB_PORT = os.environ.get("COORD_HUB_PORT", "9900")
AUTO_PORT = HUB_PORT == "auto"
_url_port = "9900" if AUTO_PORT else HUB_PORT
HUB_URL = os.environ.get("COORD_HUB_URL", f"http://{HUB_HOST}:{_url_port}").rstrip("/")


def default_data_dir() -> str:
    configured = os.environ.get("COORD_DATA_DIR")
    if configured:
        return configured
    if os.environ.get("CURSOR_PLUGIN_ROOT"):
        return str(Path.home() / ".cursor-ab-coord")
    return str(ROOT)


DATA_DIR = default_data_dir()
ENDPOINT_PATH = Path(DATA_DIR) / ".coord-endpoint.json"


def read_endpoint() -> dict[str, Any] | None:
    """Read the running hub's endpoint file, if present."""
    try:
        data = json.loads(ENDPOINT_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if isinstance(data, dict) and data.get("url"):
        return data
    return None


def active_hub_url() -> str:
    """Resolve the hub URL, preferring an explicit override, then discovery."""
    override = os.environ.get("COORD_HUB_URL")
    if override:
        return override.rstrip("/")
    endpoint = read_endpoint()
    if endpoint:
        return str(endpoint["url"]).rstrip("/")
    return HUB_URL


def active_ui_url() -> str:
    return f"{active_hub_url()}/ui/"


def configured_ui_url() -> str:
    """UI URL from static config, used for hub-independent reporting."""
    return f"{HUB_URL}/ui/"


def coord_env() -> dict[str, str]:
    env = {
        **os.environ,
        "COORD_HUB_HOST": HUB_HOST,
        "COORD_HUB_PORT": HUB_PORT,
        "COORD_DATA_DIR": DATA_DIR,
    }
    # With an OS-assigned port, let child scripts discover the real URL from the
    # endpoint file instead of pinning a misleading COORD_HUB_URL.
    if os.environ.get("COORD_HUB_URL") or not AUTO_PORT:
        env["COORD_HUB_URL"] = HUB_URL
    return env

TOOLS: list[dict[str, Any]] = [
    {
        "name": "coord_version",
        "description": "Return local MCP/plugin version without requiring the hub to be running.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_start",
        "description": "Start the local coord hub (coord-hub.py) if not already running.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_doctor",
        "description": "Run local diagnostics for files, scripts, hub connectivity, UI, and prompts.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_quick_setup",
        "description": "Start the hub, build a profile from template/task fields, apply setup, and return prompts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "description": "Template id, e.g. dev-review, test-fix, plan-implement, security-fix.",
                },
                "task": {"type": "string", "description": "Runtime task title."},
                "branch": {"type": "string", "description": "Git branch name."},
                "constraints": {"type": "array", "items": {"type": "string"}},
                "max_epochs": {"type": "integer"},
                "lang": {"type": "string", "enum": ["en", "zh"]},
                "roles": {
                    "type": "object",
                    "description": "Optional full roles override with A and B objects.",
                },
            },
            "required": ["template", "task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_stop",
        "description": "Stop the local coord hub.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_clear_state",
        "description": "Clear hub in-memory and persisted state/profile/history/lessons. Requires confirm=true.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "confirm": {
                    "type": "boolean",
                    "description": "Must be true to clear state.",
                },
            },
            "required": ["confirm"],
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_status",
        "description": "Get current hub coordination state (GET /state).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_health",
        "description": "Get lightweight hub health info (GET /health).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "coord_snapshot",
        "description": "Get a compact re-anchor snapshot with state, profile, recent history, lessons, and health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "history_limit": {"type": "integer"},
                "lessons_limit": {"type": "integer"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_history",
        "description": "Get recent hub coordination events (GET /history).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum events to return, capped by the hub.",
                },
                "since_id": {
                    "type": "integer",
                    "description": "Only return events with id greater than this value.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_lessons",
        "description": "List or add shared lessons for long-running A/B sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "add"]},
                "limit": {
                    "type": "integer",
                    "description": "For action=list, maximum lessons to return.",
                },
                "role": {
                    "type": "string",
                    "enum": ["A", "B"],
                    "description": "For action=add, the role that learned the lesson.",
                },
                "epoch": {
                    "type": "integer",
                    "description": "For action=add, optional coordination epoch.",
                },
                "text": {
                    "type": "string",
                    "description": "For action=add, reusable lesson or pitfall text.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        },
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
        "name": "coord_templates",
        "description": "Get workflow template catalog (GET /templates), optionally localized.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lang": {"type": "string", "enum": ["en", "zh"]},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_setup",
        "description": "Apply a full role profile, reset state, and return generated prompts (POST /setup).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {
                    "type": "object",
                    "description": "Full profile with template, roles, workflow, task, maxEpochs, and lang.",
                },
            },
            "required": ["profile"],
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_build_profile",
        "description": "Build a validated profile from a template and task fields for no-UI setup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "description": "Template id, e.g. dev-review, test-fix, plan-implement, security-fix.",
                },
                "task": {"type": "string", "description": "Runtime task title."},
                "branch": {"type": "string", "description": "Git branch name."},
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Runtime constraints.",
                },
                "max_epochs": {"type": "integer", "description": "Maximum coordination epochs."},
                "lang": {"type": "string", "enum": ["en", "zh"]},
                "roles": {
                    "type": "object",
                    "description": "Optional full roles override with A and B objects.",
                },
            },
            "required": ["template", "task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_validate_profile",
        "description": "Validate a role profile locally before calling coord_setup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {"type": "object", "description": "Profile body to validate."},
            },
            "required": ["profile"],
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
                "payload": {
                    "type": "object",
                    "description": "Signal payload. Include outcome as progress, blocked, no-op, or done when possible.",
                },
                "stopped": {"type": "boolean"},
            },
            "required": ["target", "payload"],
            "additionalProperties": False,
        },
    },
    {
        "name": "coord_signal_outcome",
        "description": "Send a standard signal with a validated outcome and summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "enum": ["A", "B"]},
                "outcome": {"type": "string", "enum": ["progress", "blocked", "no-op", "done"]},
                "summary": {"type": "string"},
                "epoch": {"type": "integer"},
                "turn": {"type": "string", "enum": ["A", "B"]},
                "stopped": {"type": "boolean"},
            },
            "required": ["target", "outcome", "summary"],
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
    base = active_hub_url()
    url = f"{base}{path}"
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
        if isinstance(err.get("errors"), list):
            detail = "; ".join(str(item) for item in err["errors"])
            raise RuntimeError(f"{err.get('error', 'request failed')}: {detail}") from e
        raise RuntimeError(err.get("error", raw or str(e))) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"hub unreachable at {base}: {e}") from e


def tool_result_text(obj: Any) -> dict[str, Any]:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": text}]}


def start_hub() -> dict[str, Any]:
    script = ROOT / "scripts" / "start.sh"
    proc = subprocess.run(
        [str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        env=coord_env(),
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(out.strip() or "coord_start failed")
    return {
        "ok": True,
        "message": out.strip(),
        "ui_url": active_ui_url(),
        "hub_url": active_hub_url(),
        "data_dir": DATA_DIR,
        "state": hub_request("GET", "/state"),
    }


def doctor_result(proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "output": ((proc.stdout or "") + (proc.stderr or "")).strip(),
    }


def run_doctor() -> dict[str, Any]:
    script = ROOT / "scripts" / "doctor.sh"
    proc = subprocess.run(
        [str(script)], cwd=ROOT, capture_output=True, text=True, timeout=15, env=coord_env()
    )
    return doctor_result(proc)


def parse_max_epochs_arg(value: Any) -> int:
    if value is None:
        return 20
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError("max_epochs must be an integer")
    if value < 1:
        raise RuntimeError("max_epochs must be >= 1")
    return value


def parse_nonnegative_int_arg(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"{field} must be an integer")
    if value < 0:
        raise RuntimeError(f"{field} must be >= 0")
    return value


def parse_positive_int_arg(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"{field} must be an integer")
    if value < 1:
        raise RuntimeError(f"{field} must be >= 1")
    return value


def parse_nonempty_string_arg(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise RuntimeError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise RuntimeError(f"{field} is required")
    return text


def parse_role_arg(value: Any, field: str) -> str:
    role = parse_nonempty_string_arg(value, field).upper()
    if role not in ("A", "B"):
        raise RuntimeError(f"{field} must be A or B")
    return role


def build_profile_from_args(arguments: dict[str, Any]) -> dict[str, Any]:
    template_id = parse_nonempty_string_arg(arguments.get("template", ""), "template")
    task_title = parse_nonempty_string_arg(arguments.get("task", ""), "task")

    constraints = arguments.get("constraints") or []
    if not isinstance(constraints, list) or not all(isinstance(item, str) for item in constraints):
        raise RuntimeError("constraints must be an array of strings")

    branch = arguments.get("branch", "main")
    if not isinstance(branch, str):
        raise RuntimeError("branch must be a string")
    branch = branch.strip() or "main"
    lang = arguments.get("lang", "en")
    if not isinstance(lang, str) or lang not in ("en", "zh"):
        raise RuntimeError("lang must be en or zh")

    task = {
        "title": task_title,
        "branch": branch,
        "constraints": constraints,
    }
    max_epochs = parse_max_epochs_arg(arguments.get("max_epochs"))
    roles = arguments.get("roles")
    if roles is not None and not isinstance(roles, dict):
        raise RuntimeError("roles must be an object when provided")

    try:
        return build_profile(
            template_id,
            roles=roles,
            task=task,
            max_epochs=max_epochs,
            lang=lang,
        )
    except KeyError as e:
        raise RuntimeError(str(e)) from e


def build_quick_setup_result(
    start: dict[str, Any], setup: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    roles = profile.get("roles", {})
    task = profile.get("task", {})
    return {
        "ok": True,
        "ui_url": start.get("ui_url", active_ui_url()),
        "paste_order": ["B", "A"],
        "prompts": setup.get("prompts", {}),
        "profile_summary": {
            "template": profile.get("template"),
            "lang": profile.get("lang", "en"),
            "max_epochs": profile.get("maxEpochs"),
            "task": {
                "title": task.get("title"),
                "branch": task.get("branch"),
                "constraints": task.get("constraints", []),
            },
            "roles": {
                "A": roles.get("A", {}).get("name"),
                "B": roles.get("B", {}).get("name"),
            },
        },
        "state": setup.get("state"),
        "setup": setup,
        "start": start,
    }


def build_reset_body(arguments: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if "task" in arguments:
        if not isinstance(arguments["task"], str):
            raise RuntimeError("task must be a string")
        body["task"] = arguments["task"]
    if "branch" in arguments:
        if not isinstance(arguments["branch"], str):
            raise RuntimeError("branch must be a string")
        body["branch"] = arguments["branch"]
    if "max_epochs" in arguments:
        body["max_epochs"] = parse_max_epochs_arg(arguments["max_epochs"])
    return body


def build_signal_body(arguments: dict[str, Any]) -> dict[str, Any]:
    target = parse_role_arg(arguments.get("target", ""), "target")
    payload = arguments.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError("payload must be an object")
    if "outcome" in payload:
        outcome = parse_nonempty_string_arg(payload["outcome"], "payload.outcome")
        if outcome not in ("progress", "blocked", "no-op", "done"):
            raise RuntimeError("payload.outcome must be one of: progress, blocked, no-op, done")

    body: dict[str, Any] = {"target": target, "payload": payload}
    if "epoch" in arguments:
        body["epoch"] = parse_nonnegative_int_arg(arguments["epoch"], "epoch")
    if "turn" in arguments:
        body["turn"] = parse_role_arg(arguments["turn"], "turn")
    if "stopped" in arguments:
        stopped = arguments["stopped"]
        if not isinstance(stopped, bool):
            raise RuntimeError("stopped must be a boolean")
        body["stopped"] = stopped
    return body


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "coord_version":
        return tool_result_text(
            {
                "name": "cursor-ab-coord",
                "version": SERVER_VERSION,
                "ui_url": configured_ui_url(),
                "data_dir": DATA_DIR,
            }
        )

    if name == "coord_start":
        return tool_result_text(start_hub())

    if name == "coord_doctor":
        return tool_result_text(run_doctor())

    if name == "coord_quick_setup":
        start = start_hub()
        profile = build_profile_from_args(arguments)
        errors = validate_profile(profile)
        if errors:
            return tool_result_text({"ok": False, "errors": errors, "profile": profile})
        setup = hub_request("POST", "/setup", profile)
        return tool_result_text(build_quick_setup_result(start, setup, profile))

    if name == "coord_stop":
        script = ROOT / "scripts" / "stop.sh"
        proc = subprocess.run(
            [str(script)], cwd=ROOT, capture_output=True, text=True, timeout=10, env=coord_env()
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return tool_result_text({"ok": proc.returncode == 0, "message": out.strip()})

    if name == "coord_clear_state":
        if arguments.get("confirm") is not True:
            raise RuntimeError("coord_clear_state requires confirm=true")
        try:
            return tool_result_text(hub_request("POST", "/clear", {"confirm": True}))
        except RuntimeError as e:
            if "hub unreachable" not in str(e):
                raise
            script = ROOT / "scripts" / "clear-state.sh"
            proc = subprocess.run(
                [str(script)], cwd=ROOT, capture_output=True, text=True, timeout=10, env=coord_env()
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            return tool_result_text(
                {
                    "ok": proc.returncode == 0,
                    "message": out.strip(),
                    "warning": "hub was unreachable; only persisted state/profile/history/lessons files were cleared",
                }
            )

    if name == "coord_status":
        return tool_result_text(hub_request("GET", "/state"))

    if name == "coord_health":
        return tool_result_text(hub_request("GET", "/health"))

    if name == "coord_snapshot":
        params: list[str] = []
        history_limit = arguments.get("history_limit")
        lessons_limit = arguments.get("lessons_limit")
        if history_limit is not None:
            params.append(f"history_limit={parse_positive_int_arg(history_limit, 'history_limit')}")
        if lessons_limit is not None:
            params.append(f"lessons_limit={parse_positive_int_arg(lessons_limit, 'lessons_limit')}")
        suffix = f"?{'&'.join(params)}" if params else ""
        return tool_result_text(hub_request("GET", f"/snapshot{suffix}"))

    if name == "coord_history":
        params: list[str] = []
        limit = arguments.get("limit")
        since_id = arguments.get("since_id")
        if limit is not None:
            params.append(f"limit={parse_positive_int_arg(limit, 'limit')}")
        if since_id is not None:
            params.append(f"since_id={parse_nonnegative_int_arg(since_id, 'since_id')}")
        suffix = f"?{'&'.join(params)}" if params else ""
        return tool_result_text(hub_request("GET", f"/history{suffix}"))

    if name == "coord_lessons":
        action = parse_nonempty_string_arg(arguments.get("action", ""), "action")
        if action == "list":
            limit = arguments.get("limit")
            suffix = f"?limit={parse_positive_int_arg(limit, 'limit')}" if limit is not None else ""
            return tool_result_text(hub_request("GET", f"/lessons{suffix}"))
        if action == "add":
            role = parse_nonempty_string_arg(arguments.get("role", ""), "role").upper()
            text = parse_nonempty_string_arg(arguments.get("text", ""), "text")
            if role not in ("A", "B"):
                raise RuntimeError("role must be A or B")
            body: dict[str, Any] = {"role": role, "text": text}
            if "epoch" in arguments:
                body["epoch"] = parse_nonnegative_int_arg(arguments["epoch"], "epoch")
            return tool_result_text(hub_request("POST", "/lessons", body))
        raise RuntimeError("action must be list or add")

    if name == "coord_setup_url":
        return tool_result_text({"ui_url": active_ui_url()})

    if name == "coord_reset":
        return tool_result_text(hub_request("POST", "/reset", build_reset_body(arguments or {})))

    if name == "coord_templates":
        lang = arguments.get("lang", "en")
        if not isinstance(lang, str):
            raise RuntimeError("lang must be en or zh")
        if lang not in ("en", "zh"):
            raise RuntimeError("lang must be en or zh")
        suffix = "?lang=zh" if lang == "zh" else ""
        return tool_result_text(hub_request("GET", f"/templates{suffix}"))

    if name == "coord_setup":
        profile = arguments.get("profile")
        if not isinstance(profile, dict):
            raise RuntimeError("coord_setup requires a profile object")
        return tool_result_text(hub_request("POST", "/setup", profile))

    if name == "coord_build_profile":
        profile = build_profile_from_args(arguments)
        errors = validate_profile(profile)
        return tool_result_text({"ok": not errors, "errors": errors, "profile": profile})

    if name == "coord_validate_profile":
        profile = arguments.get("profile")
        if not isinstance(profile, dict):
            raise RuntimeError("coord_validate_profile requires a profile object")
        errors = validate_profile(profile)
        return tool_result_text({"ok": not errors, "errors": errors})

    if name == "coord_signal":
        return tool_result_text(hub_request("POST", "/signal", build_signal_body(arguments)))

    if name == "coord_signal_outcome":
        target = parse_nonempty_string_arg(arguments.get("target", ""), "target").upper()
        outcome = parse_nonempty_string_arg(arguments.get("outcome", ""), "outcome")
        summary = parse_nonempty_string_arg(arguments.get("summary", ""), "summary")
        if target not in ("A", "B"):
            raise RuntimeError("target must be A or B")
        if outcome not in ("progress", "blocked", "no-op", "done"):
            raise RuntimeError("outcome must be one of: progress, blocked, no-op, done")
        body: dict[str, Any] = {
            "target": target,
            "payload": {"outcome": outcome, "summary": summary},
        }
        if "epoch" in arguments:
            body["epoch"] = parse_nonnegative_int_arg(arguments["epoch"], "epoch")
        if "turn" in arguments:
            turn = parse_nonempty_string_arg(arguments["turn"], "turn").upper()
            if turn not in ("A", "B"):
                raise RuntimeError("turn must be A or B")
            body["turn"] = turn
        if "stopped" in arguments:
            stopped = arguments["stopped"]
            if not isinstance(stopped, bool):
                raise RuntimeError("stopped must be a boolean")
            body["stopped"] = stopped
        return tool_result_text(hub_request("POST", "/signal", body))

    if name == "coord_profile":
        if "profile" in arguments:
            profile = arguments["profile"]
            if not isinstance(profile, dict):
                raise RuntimeError("coord_profile profile must be an object")
            return tool_result_text(hub_request("POST", "/profile", profile))
        return tool_result_text(hub_request("GET", "/profile"))

    if name == "coord_prompt":
        role = parse_role_arg(arguments.get("role", ""), "role")
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
                    "serverInfo": {"name": "cursor-ab-coord", "version": SERVER_VERSION},
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
