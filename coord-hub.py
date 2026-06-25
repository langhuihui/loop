#!/usr/bin/env python3
"""A/B session coordination hub for Cursor /loop cross-session wake.

Usage:
  python3 coord-hub.py [--port 9900] [--host 127.0.0.1]

Endpoints:
  GET  /state              — current hub state
  GET  /wait/<A|B>         — long-poll until a message for that role arrives
  POST /signal             — enqueue message for target role
  POST /reset              — reset state (optional task/branch in body)
  GET  /profile            — current role profile
  POST /profile            — save profile (no state reset)
  POST /setup              — save profile and reset coordination state
  GET  /templates          — workflow template catalog
  GET  /prompt/A|B         — generated /loop prompt for role
  GET  /ui/                — config UI (static files)
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.profile import apply_setup_to_state, load_templates  # noqa: E402
from lib.prompt import build_prompt  # noqa: E402

UI_DIR = ROOT / "ui"
STATE_PATH = ROOT / ".coord-state.json"
PROFILE_PATH = ROOT / ".coord-profile.json"
HISTORY_PATH = ROOT / ".coord-history.json"
MAX_HISTORY = 50

lock = threading.Lock()
DEFAULT_STATE: dict[str, Any] = {
    "epoch": 0,
    "turn": "A",
    "task": "",
    "branch": "",
    "verdict": None,
    "max_epochs": 20,
    "stopped": False,
}
state: dict[str, Any] = dict(DEFAULT_STATE)

profile: dict[str, Any] | None = None
history: list[dict[str, Any]] = []

waiters: dict[str, list[tuple[threading.Event, int]]] = {"A": [], "B": []}
pending: dict[str, tuple[int, dict[str, Any]] | None] = {"A": None, "B": None}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_persisted() -> None:
    global profile

    saved_state = load_json(STATE_PATH)
    if isinstance(saved_state, dict):
        state.update({k: saved_state[k] for k in DEFAULT_STATE if k in saved_state})

    saved_profile = load_json(PROFILE_PATH)
    if isinstance(saved_profile, dict) and "roles" in saved_profile:
        profile = saved_profile

    saved_history = load_json(HISTORY_PATH)
    if isinstance(saved_history, list):
        history[:] = saved_history[-MAX_HISTORY:]


def persist_state(snapshot: dict[str, Any] | None = None) -> None:
    save_json(STATE_PATH, snapshot or state)


def persist_profile(snapshot: dict[str, Any]) -> None:
    save_json(PROFILE_PATH, snapshot)


def persist_history() -> None:
    save_json(HISTORY_PATH, history[-MAX_HISTORY:])


def notify_role(role: str, epoch: int, payload: dict[str, Any]) -> None:
    with lock:
        pending[role] = (epoch, payload)
        for ev, _ in waiters.get(role, []):
            ev.set()


def append_history(event: str, data: dict[str, Any]) -> None:
    with lock:
        history.append({"event": event, **data})
        if len(history) > MAX_HISTORY:
            del history[: len(history) - MAX_HISTORY]
        persist_history()


def hub_base_url(handler: BaseHTTPRequestHandler) -> str:
    host = handler.headers.get("Host", "127.0.0.1:9900")
    return f"http://{host}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[coord-hub] {self.address_string()} {fmt % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/state":
            with lock:
                body = dict(state)
                body["pending"] = {
                    k: {"epoch": v[0], "payload": v[1]} if v else None
                    for k, v in pending.items()
                }
                body["has_profile"] = profile is not None
            self._json(200, body)
            return

        if path == "/profile":
            with lock:
                if profile is None:
                    self._json(404, {"error": "no profile configured"})
                    return
                self._json(200, dict(profile))
            return

        if path == "/templates":
            self._json(200, load_templates())
            return

        if path == "/history":
            with lock:
                self._json(200, {"history": list(history)})
            return

        if path in ("/prompt/A", "/prompt/B"):
            role = path.rsplit("/", 1)[-1]
            with lock:
                if profile is None:
                    self._json(400, {"error": "profile not configured; POST /setup first"})
                    return
                p = dict(profile)
            text = build_prompt(role, p, hub_base_url(self))
            self._json(200, {"role": role, "prompt": text})
            return

        if path == "/ui" or path.startswith("/ui/"):
            self._serve_ui(path)
            return

        if path.startswith("/wait/"):
            role = path.rsplit("/", 1)[-1].upper()
            if role not in ("A", "B"):
                self._json(400, {"error": "role must be A or B"})
                return

            ev = threading.Event()
            with lock:
                if pending[role] is not None:
                    epoch, payload = pending[role]
                    pending[role] = None
                    self._json(200, {"epoch": epoch, "payload": payload})
                    return
                waiters[role].append((ev, state["epoch"]))

            ev.wait(timeout=3600)
            with lock:
                waiters[role] = [(e, ep) for e, ep in waiters[role] if e is not ev]
                if pending[role] is not None:
                    epoch, payload = pending[role]
                    pending[role] = None
                    self._json(200, {"epoch": epoch, "payload": payload})
                    return

            self._json(204, {})
            return

        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        global profile
        path = urlparse(self.path).path
        body = self._read_json()

        if path == "/signal":
            target = str(body.get("target", "")).upper()
            if target not in ("A", "B"):
                self._json(400, {"error": "target must be A or B"})
                return

            payload = body.get("payload") or {}
            with lock:
                if "epoch" in body:
                    state["epoch"] = int(body["epoch"])
                if "turn" in body:
                    state["turn"] = str(body["turn"]).upper()
                if "verdict" in body:
                    state["verdict"] = body["verdict"]
                if body.get("stopped") is True:
                    state["stopped"] = True
                snap = dict(state)

            persist_state(snap)
            append_history("signal", {"target": target, "payload": payload, "state": snap})
            notify_role(target, snap["epoch"], payload)
            self._json(200, {"ok": True, "state": snap})
            return

        if path == "/profile":
            if not isinstance(body, dict) or "roles" not in body:
                self._json(400, {"error": "invalid profile body"})
                return
            with lock:
                profile = body
            persist_profile(body)
            append_history("profile", {"template": body.get("template")})
            self._json(200, {"ok": True, "profile": body})
            return

        if path == "/setup":
            if not isinstance(body, dict) or "roles" not in body:
                self._json(400, {"error": "invalid profile body"})
                return
            reset_fields = apply_setup_to_state(body)
            with lock:
                profile = body
                state.update(reset_fields)
                pending["A"] = None
                pending["B"] = None
                snap = dict(state)
            persist_profile(body)
            persist_state(snap)
            append_history("setup", {"template": body.get("template"), "state": snap})
            prompts = {
                "A": build_prompt("A", body, hub_base_url(self)),
                "B": build_prompt("B", body, hub_base_url(self)),
            }
            self._json(200, {"ok": True, "state": snap, "profile": body, "prompts": prompts})
            return

        if path == "/reset":
            with lock:
                state.update(
                    {
                        "epoch": int(body.get("epoch", 0)),
                        "turn": str(body.get("turn", "A")).upper(),
                        "task": str(body.get("task", "")),
                        "branch": str(body.get("branch", "")),
                        "verdict": None,
                        "max_epochs": int(body.get("max_epochs", 20)),
                        "stopped": False,
                    }
                )
                pending["A"] = None
                pending["B"] = None
                snap = dict(state)
            persist_state(snap)
            append_history("reset", {"state": snap})
            self._json(200, {"ok": True, "state": snap})
            return

        self._json(404, {"error": "not found"})

    def _serve_ui(self, path: str) -> None:
        if not UI_DIR.is_dir():
            self._json(503, {"error": "ui directory missing"})
            return

        rel = path[len("/ui") :].lstrip("/")
        if rel == "":
            rel = "index.html"

        file_path = (UI_DIR / rel).resolve()
        if not str(file_path).startswith(str(UI_DIR.resolve())):
            self._json(403, {"error": "forbidden"})
            return
        if not file_path.is_file():
            self._json(404, {"error": "not found"})
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        content_type = content_type or "application/octet-stream"
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, obj: dict[str, Any]) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description="A/B coord hub for Cursor loops")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9900)
    args = parser.parse_args()

    load_persisted()
    server = ThreadedHTTPServer((args.host, args.port), Handler)
    print(f"[coord-hub] listening on http://{args.host}:{args.port}")
    print(f"[coord-hub] config UI → http://{args.host}:{args.port}/ui/")
    server.serve_forever()


if __name__ == "__main__":
    main()
