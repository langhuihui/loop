#!/usr/bin/env python3
"""A/B session coordination hub for Cursor /loop cross-session wake.

Usage:
  python3 coord-hub.py [--port 9900] [--host 127.0.0.1]

Endpoints:
  GET  /state              — current hub state
  GET  /wait/<A|B>         — long-poll until a message for that role arrives
  POST /signal             — enqueue message for target role
  POST /reset              — reset state (optional task/branch in body)
"""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import urlparse

lock = threading.Lock()
state: dict[str, Any] = {
    "epoch": 0,
    "turn": "A",
    "task": "",
    "branch": "",
    "verdict": None,
    "max_epochs": 20,
    "stopped": False,
}

waiters: dict[str, list[tuple[threading.Event, int]]] = {"A": [], "B": []}
pending: dict[str, tuple[int, dict[str, Any]] | None] = {"A": None, "B": None}


def notify_role(role: str, epoch: int, payload: dict[str, Any]) -> None:
    with lock:
        pending[role] = (epoch, payload)
        for ev, _ in waiters.get(role, []):
            ev.set()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[coord-hub] {self.address_string()} {fmt % args}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/state":
            with lock:
                body = dict(state)
                body["pending"] = {
                    k: {"epoch": v[0], "payload": v[1]} if v else None
                    for k, v in pending.items()
                }
            self._json(200, body)
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

            woke = ev.wait(timeout=3600)
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

            notify_role(target, state["epoch"], payload)
            self._json(200, {"ok": True, "state": dict(state)})
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
            self._json(200, {"ok": True, "state": dict(state)})
            return

        self._json(404, {"error": "not found"})

    def _read_json(self) -> dict[str, Any]:
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    def _json(self, code: int, obj: dict[str, Any]) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description="A/B coord hub for Cursor loops")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9900)
    args = parser.parse_args()

    server = ThreadedHTTPServer((args.host, args.port), Handler)
    print(f"[coord-hub] listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
