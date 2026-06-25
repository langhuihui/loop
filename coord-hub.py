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
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.profile import apply_setup_to_state, load_templates_for_lang, validate_profile  # noqa: E402
from lib.prompt import build_prompt  # noqa: E402
from lib.version import VERSION  # noqa: E402

UI_DIR = ROOT / "ui"
STATE_PATH = ROOT / ".coord-state.json"
PROFILE_PATH = ROOT / ".coord-profile.json"
HISTORY_PATH = ROOT / ".coord-history.json"
LESSONS_PATH = ROOT / ".coord-lessons.json"
MAX_HISTORY = 50
MAX_LESSONS = 100
VALID_OUTCOMES = {"progress", "blocked", "no-op", "done"}
STAGNATION_OUTCOMES = {"blocked", "no-op"}
STAGNATION_LIMIT = 3
CONSISTENCY_FIELDS = ("epoch", "turn", "stopped")

lock = threading.Lock()
DEFAULT_STATE: dict[str, Any] = {
    "epoch": 0,
    "turn": "A",
    "task": "",
    "branch": "",
    "verdict": None,
    "max_epochs": 20,
    "stopped": False,
    "stagnation_count": 0,
    "recommended_action": "continue",
    "terminal_reason": "none",
}
state: dict[str, Any] = dict(DEFAULT_STATE)

profile: dict[str, Any] | None = None
history: list[dict[str, Any]] = []
next_history_id = 1
lessons: list[dict[str, Any]] = []
next_lesson_id = 1

waiters: dict[str, list[tuple[threading.Event, int]]] = {"A": [], "B": []}
pending: dict[str, tuple[int, dict[str, Any]] | None] = {"A": None, "B": None}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def parse_json_body(raw: bytes) -> dict[str, Any]:
    try:
        body = json.loads(raw or b"{}")
    except json.JSONDecodeError as e:
        raise ValueError("request body must be valid JSON") from e
    if not isinstance(body, dict):
        raise ValueError("request body must be a JSON object")
    return body


def save_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_persisted() -> None:
    global next_history_id, next_lesson_id, profile

    saved_state = load_json(STATE_PATH)
    if isinstance(saved_state, dict):
        state.update({k: saved_state[k] for k in DEFAULT_STATE if k in saved_state})

    saved_profile = load_json(PROFILE_PATH)
    if isinstance(saved_profile, dict) and "roles" in saved_profile:
        profile = saved_profile

    saved_history = load_json(HISTORY_PATH)
    if isinstance(saved_history, list):
        history[:] = saved_history[-MAX_HISTORY:]
        existing_ids = [
            item.get("id")
            for item in history
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        ]
        next_history_id = (max(existing_ids) + 1) if existing_ids else 1

    saved_lessons = load_json(LESSONS_PATH)
    if isinstance(saved_lessons, list):
        lessons[:] = saved_lessons[-MAX_LESSONS:]
        existing_lesson_ids = [
            item.get("id")
            for item in lessons
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        ]
        next_lesson_id = (max(existing_lesson_ids) + 1) if existing_lesson_ids else 1


def persist_state(snapshot: dict[str, Any] | None = None) -> None:
    save_json(STATE_PATH, snapshot or state)


def persist_profile(snapshot: dict[str, Any]) -> None:
    save_json(PROFILE_PATH, snapshot)


def persist_history() -> None:
    save_json(HISTORY_PATH, history[-MAX_HISTORY:])


def persist_lessons() -> None:
    save_json(LESSONS_PATH, lessons[-MAX_LESSONS:])


def remove_persisted_files() -> None:
    for path in (
        STATE_PATH,
        STATE_PATH.with_suffix(STATE_PATH.suffix + ".tmp"),
        PROFILE_PATH,
        PROFILE_PATH.with_suffix(PROFILE_PATH.suffix + ".tmp"),
        HISTORY_PATH,
        HISTORY_PATH.with_suffix(HISTORY_PATH.suffix + ".tmp"),
        LESSONS_PATH,
        LESSONS_PATH.with_suffix(LESSONS_PATH.suffix + ".tmp"),
    ):
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def notify_role(role: str, epoch: int, payload: dict[str, Any]) -> None:
    with lock:
        pending[role] = (epoch, payload)
        for ev, _ in waiters.get(role, []):
            ev.set()


def wake_waiters_locked() -> None:
    for role_waiters in waiters.values():
        for ev, _ in role_waiters:
            ev.set()


def append_history(event: str, data: dict[str, Any]) -> None:
    global next_history_id
    with lock:
        history.append(
            {
                "id": next_history_id,
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": event,
                **data,
            }
        )
        next_history_id += 1
        if len(history) > MAX_HISTORY:
            del history[: len(history) - MAX_HISTORY]
        persist_history()


def append_lesson(role: str, text: str, epoch: int | None) -> dict[str, Any]:
    global next_lesson_id
    with lock:
        lesson = {
            "id": next_lesson_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "epoch": epoch,
            "text": text,
        }
        lessons.append(lesson)
        next_lesson_id += 1
        if len(lessons) > MAX_LESSONS:
            del lessons[: len(lessons) - MAX_LESSONS]
        persist_lessons()
        return dict(lesson)


def hub_base_url(handler: BaseHTTPRequestHandler) -> str:
    host = handler.headers.get("Host", "127.0.0.1:9900")
    return f"http://{host}"


def profile_validation_result(body: dict[str, Any]) -> dict[str, Any]:
    errors = validate_profile(body)
    return {"ok": not errors, "errors": errors}


def parse_positive_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    if value < 1:
        raise ValueError(f"{field} must be >= 1")
    return value


def parse_nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    if value < 0:
        raise ValueError(f"{field} must be >= 0")
    return value


def parse_query_positive_int(raw: str, field: str, default: int, cap: int | None = None) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as e:
        raise ValueError(f"{field} must be an integer") from e
    value = parse_positive_int(value, field)
    return min(value, cap) if cap is not None else value


def parse_query_nonnegative_int(raw: str, field: str, default: int) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as e:
        raise ValueError(f"{field} must be an integer") from e
    return parse_nonnegative_int(value, field)


def parse_optional_string(body: dict[str, Any], field: str, default: str = "") -> str:
    if field not in body:
        return default
    value = body[field]
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def parse_lang(value: Any) -> str:
    if not isinstance(value, str) or value not in ("en", "zh"):
        raise ValueError("lang must be en or zh")
    return value


def parse_role(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be A or B")
    role = value.upper()
    if role not in ("A", "B"):
        raise ValueError(f"{field} must be A or B")
    return role


def parse_outcome(value: Any) -> str:
    if not isinstance(value, str) or value not in VALID_OUTCOMES:
        allowed = ", ".join(sorted(VALID_OUTCOMES))
        raise ValueError(f"payload.outcome must be one of: {allowed}")
    return value


def parse_signal_body(
    body: dict[str, Any],
) -> tuple[str, int | None, str | None, dict[str, Any], bool | None]:
    target = parse_role(body.get("target", ""), "target")
    epoch = parse_nonnegative_int(body["epoch"], "epoch") if "epoch" in body else None
    turn = parse_role(body["turn"], "turn") if "turn" in body else None
    payload = body.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    payload = dict(payload)
    if "outcome" in payload:
        payload["outcome"] = parse_outcome(payload["outcome"])
    stopped = body.get("stopped") if "stopped" in body else None
    if stopped is not None and not isinstance(stopped, bool):
        raise ValueError("stopped must be a boolean")
    return target, epoch, turn, payload, stopped


def parse_lesson_body(body: dict[str, Any]) -> tuple[str, str, int | None]:
    if "role" not in body:
        raise ValueError("role must be A or B")
    role = parse_role(body["role"], "role")
    text = body.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text is required")
    epoch = parse_nonnegative_int(body["epoch"], "epoch") if "epoch" in body else None
    return role, text.strip(), epoch


def update_stagnation_state(payload: dict[str, Any]) -> None:
    outcome = payload.get("outcome")
    if outcome == "done":
        state["stagnation_count"] = 0
        state["stopped"] = True
        state["recommended_action"] = "stop"
        state["terminal_reason"] = "done"
        return

    if outcome == "progress":
        state["stagnation_count"] = 0
        state["recommended_action"] = "continue"
        state["terminal_reason"] = "none"
        return

    if outcome in STAGNATION_OUTCOMES:
        state["stagnation_count"] = int(state.get("stagnation_count", 0)) + 1
        if state["stagnation_count"] >= STAGNATION_LIMIT:
            state["recommended_action"] = "stop"
            state["terminal_reason"] = "stagnation"
            state["stopped"] = True
        else:
            state["recommended_action"] = "continue"
            state["terminal_reason"] = "none"


def latest_history_state() -> dict[str, Any] | None:
    for item in reversed(history):
        snapshot = item.get("state") if isinstance(item, dict) else None
        if isinstance(snapshot, dict):
            return snapshot
    return None


def latest_signal_event() -> dict[str, Any] | None:
    for item in reversed(history):
        if isinstance(item, dict) and item.get("event") == "signal":
            return item
    return None


def history_item_outcome(item: dict[str, Any]) -> str | None:
    outcome = item.get("outcome")
    if outcome in VALID_OUTCOMES:
        return str(outcome)
    payload = item.get("payload")
    if isinstance(payload, dict) and payload.get("outcome") in VALID_OUTCOMES:
        return str(payload["outcome"])
    return None


def health_warnings() -> list[str]:
    warnings: list[str] = []
    snapshot = latest_history_state()
    if snapshot is not None:
        for field in CONSISTENCY_FIELDS:
            if state.get(field) != snapshot.get(field):
                warnings.append(
                    f"state.{field}={state.get(field)!r} differs from latest history state "
                    f"{snapshot.get(field)!r}"
                )

    if int(state.get("stagnation_count", 0)) >= STAGNATION_LIMIT and not state.get("stopped"):
        warnings.append("stagnation_count reached limit but stopped is false")
    if state.get("stopped") and state.get("recommended_action") != "stop":
        warnings.append("state is stopped but recommended_action is not stop")
    latest_signal = latest_signal_event()
    latest_outcome = history_item_outcome(latest_signal) if latest_signal is not None else None
    if latest_signal is not None and latest_outcome is None:
        warnings.append("latest signal is missing a valid outcome")
    if latest_outcome == "done" and not state.get("stopped"):
        warnings.append("latest signal outcome is done but stopped is false")
    return warnings


def outcome_counts() -> dict[str, int]:
    counts = {outcome: 0 for outcome in sorted(VALID_OUTCOMES)}
    for item in history:
        if not isinstance(item, dict) or item.get("event") != "signal":
            continue
        outcome = history_item_outcome(item)
        if outcome in counts:
            counts[outcome] += 1
    return counts


def state_response_body() -> dict[str, Any]:
    body = dict(state)
    body["pending"] = {
        k: {"epoch": v[0], "payload": v[1]} if v else None
        for k, v in pending.items()
    }
    body["has_profile"] = profile is not None
    return body


def snapshot_response_body(history_limit: int = 10, lessons_limit: int = 20) -> dict[str, Any]:
    warnings = health_warnings()
    return {
        "ok": True,
        "version": VERSION,
        "state": state_response_body(),
        "profile": dict(profile) if profile is not None else None,
        "history": list(history[-max(1, min(history_limit, MAX_HISTORY)) :]),
        "lessons": list(lessons[-max(1, min(lessons_limit, MAX_LESSONS)) :]),
        "health": {
            "warnings": warnings,
            "outcome_counts": outcome_counts(),
            "history_size": len(history),
            "lessons_size": len(lessons),
            "next_history_id": next_history_id,
            "next_lesson_id": next_lesson_id,
        },
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[coord-hub] {self.address_string()} {fmt % args}")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self._redirect("/ui/")
            return

        if path == "/state":
            with lock:
                body = state_response_body()
            self._json(200, body)
            return

        if path == "/health":
            with lock:
                warnings = health_warnings()
                body = {
                    "ok": True,
                    "version": VERSION,
                    "epoch": state["epoch"],
                    "turn": state["turn"],
                    "stopped": state["stopped"],
                    "has_profile": profile is not None,
                    "history_size": len(history),
                    "next_history_id": next_history_id,
                    "lessons_size": len(lessons),
                    "outcome_counts": outcome_counts(),
                    "warnings": warnings,
                    "ui_path": "/ui/",
                }
            self._json(200, body)
            return

        if path == "/snapshot":
            with lock:
                history_limit_raw = (query.get("history_limit") or [""])[0]
                lessons_limit_raw = (query.get("lessons_limit") or [""])[0]
                try:
                    history_limit = parse_query_positive_int(history_limit_raw, "history_limit", 10, MAX_HISTORY)
                    lessons_limit = parse_query_positive_int(lessons_limit_raw, "lessons_limit", 20, MAX_LESSONS)
                except ValueError as e:
                    self._json(400, {"error": str(e)})
                    return
                body = snapshot_response_body(history_limit, lessons_limit)
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
            try:
                lang = parse_lang((query.get("lang") or ["en"])[0])
            except ValueError as e:
                self._json(400, {"error": str(e)})
                return
            self._json(200, load_templates_for_lang(lang))
            return

        if path == "/history":
            with lock:
                limit_raw = (query.get("limit") or [""])[0]
                since_id_raw = (query.get("since_id") or [""])[0]
                try:
                    limit = parse_query_positive_int(limit_raw, "limit", MAX_HISTORY, MAX_HISTORY)
                    since_id = parse_query_nonnegative_int(since_id_raw, "since_id", 0)
                except ValueError as e:
                    self._json(400, {"error": str(e)})
                    return
                events = [
                    item
                    for item in history
                    if not isinstance(item.get("id"), int) or item["id"] > since_id
                ]
                self._json(200, {"history": events[-limit:]})
            return

        if path == "/lessons":
            with lock:
                limit_raw = (query.get("limit") or [""])[0]
                try:
                    limit = parse_query_positive_int(limit_raw, "limit", MAX_LESSONS, MAX_LESSONS)
                except ValueError as e:
                    self._json(400, {"error": str(e)})
                    return
                self._json(200, {"lessons": list(lessons[-limit:])})
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
        global next_history_id, next_lesson_id, profile
        path = urlparse(self.path).path
        try:
            body = self._read_json()
        except ValueError as e:
            self._json(400, {"error": str(e)})
            return

        if path == "/clear":
            if body.get("confirm") is not True:
                self._json(400, {"error": "confirm must be true"})
                return
            with lock:
                state.clear()
                state.update(DEFAULT_STATE)
                profile = None
                history.clear()
                next_history_id = 1
                lessons.clear()
                next_lesson_id = 1
                pending["A"] = None
                pending["B"] = None
                wake_waiters_locked()
                snap = dict(state)
            remove_persisted_files()
            self._json(200, {"ok": True, "state": snap, "has_profile": False})
            return

        if path == "/signal":
            try:
                target, new_epoch, new_turn, payload, stopped = parse_signal_body(body)
            except ValueError as e:
                self._json(400, {"error": str(e)})
                return

            with lock:
                if new_epoch is not None:
                    state["epoch"] = new_epoch
                if new_turn is not None:
                    state["turn"] = new_turn
                if "verdict" in body:
                    state["verdict"] = body["verdict"]
                if stopped is True:
                    state["stopped"] = True
                    state["recommended_action"] = "stop"
                    state["terminal_reason"] = "stopped"
                else:
                    update_stagnation_state(payload)
                snap = dict(state)

            persist_state(snap)
            append_history(
                "signal",
                {"target": target, "outcome": payload.get("outcome"), "payload": payload, "state": snap},
            )
            notify_role(target, snap["epoch"], payload)
            self._json(200, {"ok": True, "state": snap})
            return

        if path == "/lessons":
            try:
                role, text, epoch = parse_lesson_body(body)
            except ValueError as e:
                self._json(400, {"error": str(e)})
                return
            lesson = append_lesson(role, text, epoch)
            append_history("lesson", {"lesson": lesson})
            self._json(200, {"ok": True, "lesson": lesson})
            return

        if path == "/profile":
            result = profile_validation_result(body)
            if not result["ok"]:
                self._json(400, {"error": "invalid profile body", **result})
                return
            with lock:
                profile = body
            persist_profile(body)
            append_history("profile", {"template": body.get("template")})
            self._json(200, {"ok": True, "profile": body})
            return

        if path == "/setup":
            result = profile_validation_result(body)
            if not result["ok"]:
                self._json(400, {"error": "invalid profile body", **result})
                return
            reset_fields = apply_setup_to_state(body)
            with lock:
                profile = body
                state.update(reset_fields)
                pending["A"] = None
                pending["B"] = None
                wake_waiters_locked()
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

        if path == "/validate-profile":
            result = profile_validation_result(body)
            code = 200 if result["ok"] else 400
            self._json(code, result)
            return

        if path == "/reset":
            try:
                epoch = parse_nonnegative_int(body.get("epoch", 0), "epoch")
                turn = parse_role(body.get("turn", "A"), "turn")
                max_epochs = parse_positive_int(body.get("max_epochs", 20), "max_epochs")
                task = parse_optional_string(body, "task")
                branch = parse_optional_string(body, "branch")
            except ValueError as e:
                self._json(400, {"error": str(e)})
                return

            with lock:
                state.update(
                    {
                        "epoch": epoch,
                        "turn": turn,
                        "task": task,
                        "branch": branch,
                        "verdict": None,
                        "max_epochs": max_epochs,
                        "stopped": False,
                        "stagnation_count": 0,
                        "recommended_action": "continue",
                        "terminal_reason": "none",
                    }
                )
                pending["A"] = None
                pending["B"] = None
                wake_waiters_locked()
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
        return parse_json_body(raw)

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

    def _redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self._cors_headers()
        self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description="A/B coord hub for Cursor loops")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9900)
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args()

    if args.version:
        print(VERSION)
        return

    load_persisted()
    server = ThreadedHTTPServer((args.host, args.port), Handler)
    print(f"[coord-hub] listening on http://{args.host}:{args.port}")
    print(f"[coord-hub] config UI → http://{args.host}:{args.port}/ui/")
    server.serve_forever()


if __name__ == "__main__":
    main()
