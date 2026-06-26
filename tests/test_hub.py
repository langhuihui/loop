from __future__ import annotations

import io
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType

from lib.version import VERSION


def load_hub_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "coord-hub.py"
    spec = importlib.util.spec_from_file_location("coord_hub_for_tests", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_handler(hub: ModuleType, path: str, body: bytes = b"") -> object:
    handler = object.__new__(hub.Handler)
    handler.path = path
    handler.headers = {"Content-Length": str(len(body))}
    handler.rfile = io.BytesIO(body)
    handler.responses = []
    handler._json = lambda code, obj: handler.responses.append((code, obj))
    return handler


class HubTests(unittest.TestCase):
    def test_cli_version_prints_shared_version(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "coord-hub.py"), "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        self.assertEqual(proc.stdout.strip(), VERSION)

    def test_hub_uses_shared_version(self) -> None:
        hub = load_hub_module()

        self.assertEqual(hub.VERSION, VERSION)

    def test_profile_validation_result_reports_errors(self) -> None:
        hub = load_hub_module()

        result = hub.profile_validation_result({})

        self.assertFalse(result["ok"])
        self.assertIn("roles must be an object", result["errors"])

    def test_parse_json_body_requires_valid_object(self) -> None:
        hub = load_hub_module()

        self.assertEqual(hub.parse_json_body(b""), {})
        self.assertEqual(hub.parse_json_body(b'{"ok": true}'), {"ok": True})
        for raw, message in (
            (b"{", "request body must be valid JSON"),
            (b"[]", "request body must be a JSON object"),
            (b"null", "request body must be a JSON object"),
        ):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, message):
                    hub.parse_json_body(raw)

    def test_parse_positive_int_rejects_ambiguous_values(self) -> None:
        hub = load_hub_module()

        self.assertEqual(hub.parse_positive_int(3, "max_epochs"), 3)
        for value, message in (
            (True, "max_epochs must be an integer"),
            (1.5, "max_epochs must be an integer"),
            ("20", "max_epochs must be an integer"),
            (0, "max_epochs must be >= 1"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, message):
                    hub.parse_positive_int(value, "max_epochs")

    def test_parse_nonnegative_int_rejects_ambiguous_values(self) -> None:
        hub = load_hub_module()

        self.assertEqual(hub.parse_nonnegative_int(0, "epoch"), 0)
        self.assertEqual(hub.parse_nonnegative_int(3, "epoch"), 3)
        for value, message in (
            (True, "epoch must be an integer"),
            (1.5, "epoch must be an integer"),
            ("2", "epoch must be an integer"),
            (-1, "epoch must be >= 0"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, message):
                    hub.parse_nonnegative_int(value, "epoch")

    def test_parse_query_int_helpers_validate_strings(self) -> None:
        hub = load_hub_module()

        self.assertEqual(hub.parse_query_positive_int("", "limit", 10), 10)
        self.assertEqual(hub.parse_query_positive_int("3", "limit", 10), 3)
        self.assertEqual(hub.parse_query_positive_int("999", "limit", 10, cap=50), 50)
        self.assertEqual(hub.parse_query_nonnegative_int("", "since_id", 0), 0)
        self.assertEqual(hub.parse_query_nonnegative_int("0", "since_id", 3), 0)
        for parser, raw, field, message in (
            (hub.parse_query_positive_int, "abc", "limit", "limit must be an integer"),
            (hub.parse_query_positive_int, "0", "limit", "limit must be >= 1"),
            (hub.parse_query_nonnegative_int, "abc", "since_id", "since_id must be an integer"),
            (hub.parse_query_nonnegative_int, "-1", "since_id", "since_id must be >= 0"),
        ):
            with self.subTest(raw=raw, field=field):
                with self.assertRaisesRegex(ValueError, message):
                    parser(raw, field, 1)

    def test_parse_optional_string_rejects_non_strings(self) -> None:
        hub = load_hub_module()

        self.assertEqual(hub.parse_optional_string({}, "task"), "")
        self.assertEqual(hub.parse_optional_string({}, "branch", "main"), "main")
        self.assertEqual(hub.parse_optional_string({"task": "Ship feature"}, "task"), "Ship feature")
        with self.assertRaisesRegex(ValueError, "task must be a string"):
            hub.parse_optional_string({"task": 123}, "task")

    def test_parse_lang_accepts_only_supported_languages(self) -> None:
        hub = load_hub_module()

        self.assertEqual(hub.parse_lang("en"), "en")
        self.assertEqual(hub.parse_lang("zh"), "zh")
        for value in ("fr", "", 1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "lang must be en or zh"):
                    hub.parse_lang(value)

    def test_parse_role_accepts_only_a_or_b(self) -> None:
        hub = load_hub_module()

        self.assertEqual(hub.parse_role("a", "turn"), "A")
        self.assertEqual(hub.parse_role("B", "turn"), "B")
        for value in ("C", "", 1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "turn must be A or B"):
                    hub.parse_role(value, "turn")

    def test_parse_signal_body_validates_state_fields(self) -> None:
        hub = load_hub_module()
        body = {
            "target": "b",
            "epoch": 2,
            "turn": "a",
            "payload": {"action": "review", "outcome": "progress"},
            "stopped": True,
        }

        target, epoch, turn, payload, stopped = hub.parse_signal_body(body)
        self.assertEqual(target, "B")
        self.assertEqual(epoch, 2)
        self.assertEqual(turn, "A")
        self.assertEqual(payload, {"action": "review", "outcome": "progress"})
        self.assertTrue(stopped)
        self.assertIsNot(payload, body["payload"])

        for body, message in (
            ({"target": "C", "payload": {}}, "target must be A or B"),
            ({"target": "A", "epoch": "2", "payload": {}}, "epoch must be an integer"),
            ({"target": "A", "turn": "C", "payload": {}}, "turn must be A or B"),
            ({"target": "A"}, "payload must be an object"),
            ({"target": "A", "payload": None}, "payload must be an object"),
            ({"target": "A", "payload": "bad"}, "payload must be an object"),
            (
                {"target": "A", "payload": {"outcome": "maybe"}},
                "payload.outcome must be one of",
            ),
            ({"target": "A", "payload": {}, "stopped": "true"}, "stopped must be a boolean"),
        ):
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, message):
                    hub.parse_signal_body(body)

    def test_parse_lesson_body_validates_fields(self) -> None:
        hub = load_hub_module()

        role, text, epoch = hub.parse_lesson_body(
            {"role": "a", "text": " Reuse the fast validation path. ", "epoch": 4}
        )

        self.assertEqual(role, "A")
        self.assertEqual(text, "Reuse the fast validation path.")
        self.assertEqual(epoch, 4)

        for body, message in (
            ({"text": "lesson"}, "role must be A or B"),
            ({"role": "C", "text": "lesson"}, "role must be A or B"),
            ({"role": "A", "text": ""}, "text is required"),
            ({"role": "A", "text": "lesson", "epoch": "4"}, "epoch must be an integer"),
        ):
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, message):
                    hub.parse_lesson_body(body)

    def test_update_stagnation_state_stops_after_repeated_no_progress(self) -> None:
        hub = load_hub_module()
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)

        hub.update_stagnation_state({"outcome": "no-op"})
        hub.update_stagnation_state({"outcome": "blocked"})

        self.assertFalse(hub.state["stopped"])
        self.assertEqual(hub.state["stagnation_count"], 2)
        self.assertEqual(hub.state["recommended_action"], "continue")

        hub.update_stagnation_state({"outcome": "no-op"})

        self.assertTrue(hub.state["stopped"])
        self.assertEqual(hub.state["stagnation_count"], 3)
        self.assertEqual(hub.state["recommended_action"], "stop")
        self.assertEqual(hub.state["terminal_reason"], "stagnation")

    def test_progress_outcome_resets_stagnation_state(self) -> None:
        hub = load_hub_module()
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)
        hub.state["stagnation_count"] = 2

        hub.update_stagnation_state({"outcome": "progress"})

        self.assertFalse(hub.state["stopped"])
        self.assertEqual(hub.state["stagnation_count"], 0)
        self.assertEqual(hub.state["recommended_action"], "continue")
        self.assertEqual(hub.state["terminal_reason"], "none")

    def test_done_outcome_stops_state(self) -> None:
        hub = load_hub_module()
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)
        hub.state["stagnation_count"] = 2

        hub.update_stagnation_state({"outcome": "done"})

        self.assertTrue(hub.state["stopped"])
        self.assertEqual(hub.state["stagnation_count"], 0)
        self.assertEqual(hub.state["recommended_action"], "stop")
        self.assertEqual(hub.state["terminal_reason"], "done")

    def test_wake_waiters_locked_sets_all_waiter_events(self) -> None:
        hub = load_hub_module()
        ev_a = hub.threading.Event()
        ev_b = hub.threading.Event()
        hub.waiters["A"] = [(ev_a, 1)]
        hub.waiters["B"] = [(ev_b, 2)]

        hub.wake_waiters_locked()

        self.assertTrue(ev_a.is_set())
        self.assertTrue(ev_b.is_set())

    def test_health_warnings_detect_state_history_drift(self) -> None:
        hub = load_hub_module()
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)
        hub.state["epoch"] = 3
        hub.history.clear()
        hub.history.append({"event": "signal", "state": {"epoch": 2, "turn": "A", "stopped": False}})

        warnings = hub.health_warnings()

        self.assertEqual(hub.latest_history_state(), {"epoch": 2, "turn": "A", "stopped": False})
        self.assertTrue(any("state.epoch=3 differs" in warning for warning in warnings))

    def test_health_warnings_detect_inconsistent_stop_state(self) -> None:
        hub = load_hub_module()
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)
        hub.history.clear()
        hub.state["stagnation_count"] = hub.STAGNATION_LIMIT

        warnings = hub.health_warnings()

        self.assertIn("stagnation_count reached limit but stopped is false", warnings)

        hub.state["stagnation_count"] = 0
        hub.state["stopped"] = True

        warnings = hub.health_warnings()

        self.assertIn("state is stopped but recommended_action is not stop", warnings)

    def test_health_warnings_detect_latest_signal_without_outcome(self) -> None:
        hub = load_hub_module()
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)
        hub.history.clear()
        hub.history.extend(
            [
                {"event": "signal", "outcome": "progress"},
                {"event": "signal", "payload": {"summary": "missing outcome"}},
            ]
        )

        warnings = hub.health_warnings()

        self.assertIn("latest signal is missing a valid outcome", warnings)

        hub.history.append({"event": "signal", "outcome": "done"})
        warnings = hub.health_warnings()

        self.assertNotIn("latest signal is missing a valid outcome", warnings)

        hub.history.append({"event": "signal", "payload": {"outcome": "progress"}})
        warnings = hub.health_warnings()

        self.assertNotIn("latest signal is missing a valid outcome", warnings)

    def test_health_warnings_detect_done_without_stopped(self) -> None:
        hub = load_hub_module()
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)
        hub.history.clear()
        hub.history.append({"event": "signal", "outcome": "done"})

        warnings = hub.health_warnings()

        self.assertIn("latest signal outcome is done but stopped is false", warnings)

        hub.state["stopped"] = True
        hub.state["recommended_action"] = "stop"
        warnings = hub.health_warnings()

        self.assertNotIn("latest signal outcome is done but stopped is false", warnings)

    def test_outcome_counts_summarizes_signal_history(self) -> None:
        hub = load_hub_module()
        hub.history.clear()
        hub.history.extend(
            [
                {"event": "setup"},
                {"event": "signal", "outcome": "progress"},
                {"event": "signal", "outcome": "blocked"},
                {"event": "signal", "outcome": "blocked"},
                {"event": "signal", "payload": {"outcome": "done"}},
                {"event": "signal", "outcome": "unknown"},
                {"event": "signal", "payload": {}},
            ]
        )

        counts = hub.outcome_counts()

        self.assertEqual(counts["progress"], 1)
        self.assertEqual(counts["blocked"], 2)
        self.assertEqual(counts["done"], 1)
        self.assertEqual(counts["no-op"], 0)

    def test_snapshot_response_body_combines_runtime_context(self) -> None:
        hub = load_hub_module()
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)
        hub.state["epoch"] = 5
        hub.profile = {"template": "dev-review", "roles": {}}
        hub.history.clear()
        hub.history.extend(
            [
                {"id": 1, "event": "setup", "state": {"epoch": 0, "turn": "A", "stopped": False}},
                {
                    "id": 2,
                    "event": "signal",
                    "outcome": "progress",
                    "state": {"epoch": 5, "turn": "B", "stopped": False},
                },
            ]
        )
        hub.lessons.clear()
        hub.lessons.extend(
            [
                {"id": 1, "role": "A", "epoch": 1, "text": "old"},
                {"id": 2, "role": "B", "epoch": 5, "text": "new"},
            ]
        )

        body = hub.snapshot_response_body(history_limit=1, lessons_limit=1)

        self.assertTrue(body["ok"])
        self.assertEqual(body["state"]["epoch"], 5)
        self.assertTrue(body["state"]["has_profile"])
        self.assertEqual(body["profile"]["template"], "dev-review")
        self.assertEqual([item["id"] for item in body["history"]], [2])
        self.assertEqual([item["id"] for item in body["lessons"]], [2])
        self.assertEqual(body["health"]["history_size"], 2)
        self.assertEqual(body["health"]["lessons_size"], 2)
        self.assertEqual(body["health"]["outcome_counts"]["progress"], 1)

    def test_append_lesson_adds_id_timestamp_and_trims_limit(self) -> None:
        hub = load_hub_module()
        hub.persist_lessons = lambda: None
        hub.lessons.clear()
        hub.next_lesson_id = 1

        first = hub.append_lesson("A", "first", 0)
        for idx in range(hub.MAX_LESSONS + 1):
            hub.append_lesson("B", f"lesson {idx}", idx)

        self.assertEqual(first["id"], 1)
        self.assertIn("ts", first)
        self.assertEqual(first["role"], "A")
        self.assertEqual(first["epoch"], 0)
        self.assertEqual(first["text"], "first")
        self.assertEqual(len(hub.lessons), hub.MAX_LESSONS)
        self.assertEqual(hub.next_lesson_id, hub.MAX_LESSONS + 3)

    def test_append_history_adds_id_and_timestamp(self) -> None:
        hub = load_hub_module()
        hub.persist_history = lambda: None
        hub.history.clear()
        hub.next_history_id = 1

        hub.append_history("setup", {"template": "dev-review"})
        hub.append_history("signal", {"target": "B"})

        self.assertEqual(hub.history[0]["id"], 1)
        self.assertEqual(hub.history[0]["event"], "setup")
        self.assertIn("ts", hub.history[0])
        self.assertEqual(hub.history[1]["id"], 2)
        self.assertEqual(hub.next_history_id, 3)

    def test_redirect_helper_sends_302_location(self) -> None:
        hub = load_hub_module()
        handler = object.__new__(hub.Handler)
        calls: list[tuple[str, object, object | None]] = []

        handler.send_response = lambda code: calls.append(("response", code, None))
        handler.send_header = lambda name, value: calls.append(("header", name, value))
        handler._cors_headers = lambda: calls.append(("cors", None, None))
        handler.end_headers = lambda: calls.append(("end", None, None))

        handler._redirect("/ui/")

        self.assertIn(("response", 302, None), calls)
        self.assertIn(("header", "Location", "/ui/"), calls)
        self.assertIn(("header", "Content-Length", "0"), calls)
        self.assertIn(("cors", None, None), calls)
        self.assertIn(("end", None, None), calls)

    def test_handler_rejects_invalid_post_json(self) -> None:
        hub = load_hub_module()
        handler = make_handler(hub, "/signal", b"{")

        hub.Handler.do_POST(handler)

        self.assertEqual(handler.responses, [(400, {"error": "request body must be valid JSON"})])

    def test_handler_rejects_invalid_snapshot_query(self) -> None:
        hub = load_hub_module()
        handler = make_handler(hub, "/snapshot?history_limit=0")

        hub.Handler.do_GET(handler)

        self.assertEqual(handler.responses, [(400, {"error": "history_limit must be >= 1"})])

    def test_handler_rejects_invalid_templates_lang(self) -> None:
        hub = load_hub_module()
        handler = make_handler(hub, "/templates?lang=fr")

        hub.Handler.do_GET(handler)

        self.assertEqual(handler.responses, [(400, {"error": "lang must be en or zh"})])

    def test_handler_rejects_invalid_history_since_id(self) -> None:
        hub = load_hub_module()
        handler = make_handler(hub, "/history?since_id=-1")

        hub.Handler.do_GET(handler)

        self.assertEqual(handler.responses, [(400, {"error": "since_id must be >= 0"})])

    def test_handler_rejects_lesson_without_role(self) -> None:
        hub = load_hub_module()
        body = json.dumps({"text": "remember this"}).encode()
        handler = make_handler(hub, "/lessons", body)

        hub.Handler.do_POST(handler)

        self.assertEqual(handler.responses, [(400, {"error": "role must be A or B"})])

    def test_handler_clear_resets_lessons_and_ids(self) -> None:
        hub = load_hub_module()
        hub.remove_persisted_files = lambda: None
        hub.state.clear()
        hub.state.update(hub.DEFAULT_STATE)
        hub.state["epoch"] = 3
        hub.profile = {"template": "dev-review", "roles": {}}
        hub.history[:] = [{"id": 1, "event": "setup"}]
        hub.lessons[:] = [{"id": 1, "role": "A", "text": "old", "epoch": 1}]
        hub.next_history_id = 2
        hub.next_lesson_id = 2
        hub.pending["A"] = (3, {"outcome": "progress"})
        hub.pending["B"] = (3, {"outcome": "blocked"})
        body = json.dumps({"confirm": True}).encode()
        handler = make_handler(hub, "/clear", body)

        hub.Handler.do_POST(handler)

        self.assertEqual(handler.responses[0][0], 200)
        self.assertEqual(hub.lessons, [])
        self.assertEqual(hub.next_lesson_id, 1)
        self.assertEqual(hub.history, [])
        self.assertEqual(hub.next_history_id, 1)
        self.assertIsNone(hub.profile)
        self.assertIsNone(hub.pending["A"])
        self.assertIsNone(hub.pending["B"])


if __name__ == "__main__":
    unittest.main()
