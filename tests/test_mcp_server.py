from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import mcp.server as mcp_server
from lib.version import VERSION
from mcp.server import (
    SERVER_VERSION,
    TOOLS,
    build_profile_from_args,
    build_quick_setup_result,
    build_reset_body,
    build_signal_body,
    doctor_result,
    parse_max_epochs_arg,
    parse_nonnegative_int_arg,
    parse_nonempty_string_arg,
    parse_positive_int_arg,
    parse_role_arg,
    run_tool,
)


class McpServerTests(unittest.TestCase):
    def test_server_version_matches_plugin_manifest(self) -> None:
        manifest_path = Path(__file__).resolve().parents[1] / ".cursor-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(SERVER_VERSION, manifest["version"])
        self.assertEqual(VERSION, manifest["version"])

    def test_tool_catalog_contains_no_ui_helpers(self) -> None:
        names = {tool["name"] for tool in TOOLS}

        self.assertIn("coord_version", names)
        self.assertIn("coord_doctor", names)
        self.assertIn("coord_quick_setup", names)
        self.assertIn("coord_build_profile", names)
        self.assertIn("coord_validate_profile", names)
        self.assertIn("coord_health", names)
        self.assertIn("coord_snapshot", names)
        self.assertIn("coord_history", names)
        self.assertIn("coord_lessons", names)
        self.assertIn("coord_signal_outcome", names)
        self.assertIn("coord_clear_state", names)

    def test_build_profile_from_args_supports_chinese(self) -> None:
        profile = build_profile_from_args(
            {
                "template": "dev-review",
                "task": "实现登录",
                "branch": "main",
                "constraints": ["不要启动服务器"],
                "lang": "zh",
            }
        )

        self.assertEqual(profile["roles"]["A"]["name"], "开发者")
        self.assertEqual(profile["task"]["title"], "实现登录")
        self.assertEqual(profile["lang"], "zh")

    def test_coord_version_does_not_require_hub(self) -> None:
        result = run_tool("coord_version", {})
        payload = json.loads(result["content"][0]["text"])

        self.assertEqual(payload["name"], "cursor-ab-coord")
        self.assertEqual(payload["version"], VERSION)
        self.assertEqual(payload["ui_url"], "http://127.0.0.1:9900/ui/")
        self.assertEqual(payload["data_dir"], str(mcp_server.DATA_DIR))

    def test_default_data_dir_avoids_plugin_cache_when_installed(self) -> None:
        with patch.dict(os.environ, {"CURSOR_PLUGIN_ROOT": "/tmp/plugin"}, clear=True):
            self.assertEqual(mcp_server.default_data_dir(), str(Path.home() / ".cursor-ab-coord"))

    def test_coord_env_passes_data_dir_to_scripts(self) -> None:
        env = mcp_server.coord_env()

        self.assertEqual(env["COORD_DATA_DIR"], str(mcp_server.DATA_DIR))
        self.assertEqual(env["COORD_HUB_HOST"], "127.0.0.1")
        self.assertEqual(env["COORD_HUB_PORT"], "9900")
        self.assertEqual(env["COORD_HUB_URL"], mcp_server.HUB_URL)

    def test_hub_url_follows_custom_port_without_explicit_url(self) -> None:
        import importlib

        try:
            with patch.dict(os.environ, {"COORD_HUB_PORT": "9931"}, clear=True):
                reloaded = importlib.reload(mcp_server)
                self.assertEqual(reloaded.HUB_PORT, "9931")
                self.assertEqual(reloaded.HUB_URL, "http://127.0.0.1:9931")
                self.assertEqual(reloaded.coord_env()["COORD_HUB_URL"], "http://127.0.0.1:9931")
        finally:
            importlib.reload(mcp_server)

    def test_explicit_hub_url_overrides_derived_port(self) -> None:
        import importlib

        try:
            with patch.dict(
                os.environ,
                {"COORD_HUB_PORT": "9931", "COORD_HUB_URL": "http://127.0.0.1:9999"},
                clear=True,
            ):
                reloaded = importlib.reload(mcp_server)
                self.assertEqual(reloaded.HUB_URL, "http://127.0.0.1:9999")
        finally:
            importlib.reload(mcp_server)

    def test_active_hub_url_prefers_endpoint_file(self) -> None:
        endpoint = mcp_server.ENDPOINT_PATH
        existed = endpoint.exists()
        backup = endpoint.read_text(encoding="utf-8") if existed else None
        try:
            endpoint.write_text(
                json.dumps({"host": "127.0.0.1", "port": 9942, "url": "http://127.0.0.1:9942"}),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(mcp_server.active_hub_url(), "http://127.0.0.1:9942")
                self.assertEqual(mcp_server.active_ui_url(), "http://127.0.0.1:9942/ui/")
        finally:
            if backup is not None:
                endpoint.write_text(backup, encoding="utf-8")
            else:
                endpoint.unlink(missing_ok=True)

    def test_explicit_url_beats_endpoint_file(self) -> None:
        endpoint = mcp_server.ENDPOINT_PATH
        existed = endpoint.exists()
        backup = endpoint.read_text(encoding="utf-8") if existed else None
        try:
            endpoint.write_text(
                json.dumps({"url": "http://127.0.0.1:9942"}), encoding="utf-8"
            )
            with patch.dict(os.environ, {"COORD_HUB_URL": "http://127.0.0.1:9999"}, clear=True):
                self.assertEqual(mcp_server.active_hub_url(), "http://127.0.0.1:9999")
        finally:
            if backup is not None:
                endpoint.write_text(backup, encoding="utf-8")
            else:
                endpoint.unlink(missing_ok=True)

    def test_coord_env_omits_url_under_auto_port(self) -> None:
        import importlib

        try:
            with patch.dict(os.environ, {"COORD_HUB_PORT": "auto"}, clear=True):
                reloaded = importlib.reload(mcp_server)
                self.assertTrue(reloaded.AUTO_PORT)
                self.assertEqual(reloaded.HUB_URL, "http://127.0.0.1:9900")
                self.assertNotIn("COORD_HUB_URL", reloaded.coord_env())
        finally:
            importlib.reload(mcp_server)

    def test_build_profile_from_args_rejects_bad_constraints(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "constraints must be an array of strings"):
            build_profile_from_args(
                {
                    "template": "dev-review",
                    "task": "Implement login",
                    "constraints": ["ok", 1],
                }
            )

    def test_build_profile_from_args_rejects_bad_strings(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "template must be a string"):
            build_profile_from_args({"template": 1, "task": "Implement login"})
        with self.assertRaisesRegex(RuntimeError, "task is required"):
            build_profile_from_args({"template": "dev-review", "task": " "})
        with self.assertRaisesRegex(RuntimeError, "branch must be a string"):
            build_profile_from_args({"template": "dev-review", "task": "Implement login", "branch": 123})
        with self.assertRaisesRegex(RuntimeError, "lang must be en or zh"):
            build_profile_from_args({"template": "dev-review", "task": "Implement login", "lang": "fr"})
        with self.assertRaisesRegex(RuntimeError, "lang must be en or zh"):
            build_profile_from_args({"template": "dev-review", "task": "Implement login", "lang": 1})

    def test_parse_max_epochs_arg_requires_positive_integer(self) -> None:
        self.assertEqual(parse_max_epochs_arg(None), 20)
        self.assertEqual(parse_max_epochs_arg(3), 3)

        for value, message in (
            (True, "max_epochs must be an integer"),
            (1.5, "max_epochs must be an integer"),
            ("20", "max_epochs must be an integer"),
            (0, "max_epochs must be >= 1"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, message):
                    parse_max_epochs_arg(value)

    def test_parse_nonnegative_int_arg_requires_integer(self) -> None:
        self.assertEqual(parse_nonnegative_int_arg(0, "epoch"), 0)
        self.assertEqual(parse_nonnegative_int_arg(3, "epoch"), 3)

        for value, message in (
            (True, "epoch must be an integer"),
            (1.5, "epoch must be an integer"),
            ("2", "epoch must be an integer"),
            (-1, "epoch must be >= 0"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, message):
                    parse_nonnegative_int_arg(value, "epoch")

    def test_parse_positive_int_arg_requires_positive_integer(self) -> None:
        self.assertEqual(parse_positive_int_arg(1, "limit"), 1)
        self.assertEqual(parse_positive_int_arg(3, "limit"), 3)

        for value, message in (
            (True, "limit must be an integer"),
            (1.5, "limit must be an integer"),
            ("2", "limit must be an integer"),
            (0, "limit must be >= 1"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, message):
                    parse_positive_int_arg(value, "limit")

    def test_parse_nonempty_string_arg_requires_string(self) -> None:
        self.assertEqual(parse_nonempty_string_arg("  ok  ", "summary"), "ok")

        for value, message in (
            (1, "summary must be a string"),
            (["ok"], "summary must be a string"),
            (" ", "summary is required"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, message):
                    parse_nonempty_string_arg(value, "summary")

    def test_parse_role_arg_accepts_only_a_or_b(self) -> None:
        self.assertEqual(parse_role_arg("a", "role"), "A")
        self.assertEqual(parse_role_arg("B", "role"), "B")
        for value in ("C", 1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(RuntimeError, "role must"):
                    parse_role_arg(value, "role")
        with self.assertRaisesRegex(RuntimeError, "role is required"):
            parse_role_arg("", "role")

    def test_coord_validate_profile_tool_reports_errors(self) -> None:
        result = run_tool("coord_validate_profile", {"profile": {}})
        payload = json.loads(result["content"][0]["text"])

        self.assertFalse(payload["ok"])
        self.assertIn("roles must be an object", payload["errors"])

    def test_doctor_result_preserves_output_on_failure(self) -> None:
        proc = subprocess.CompletedProcess(
            args=["doctor"],
            returncode=1,
            stdout="fail hub unreachable\n",
            stderr="warn start it\n",
        )
        result = doctor_result(proc)

        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], 1)
        self.assertIn("fail hub unreachable", result["output"])
        self.assertIn("warn start it", result["output"])

    def test_quick_setup_result_is_agent_friendly(self) -> None:
        profile = build_profile_from_args(
            {
                "template": "dev-review",
                "task": "Implement login",
                "branch": "feature/login",
                "constraints": ["No server"],
            }
        )
        result = build_quick_setup_result(
            {"ok": True, "ui_url": "http://127.0.0.1:9900/ui/"},
            {
                "ok": True,
                "state": {"epoch": 0, "turn": "A"},
                "prompts": {"A": "prompt A", "B": "prompt B"},
            },
            profile,
        )

        self.assertEqual(result["ui_url"], "http://127.0.0.1:9900/ui/")
        self.assertEqual(result["paste_order"], ["B", "A"])
        self.assertEqual(result["prompts"]["B"], "prompt B")
        self.assertEqual(result["profile_summary"]["task"]["branch"], "feature/login")
        self.assertEqual(result["profile_summary"]["roles"]["A"], profile["roles"]["A"]["name"])

    def test_build_reset_body_validates_optional_fields(self) -> None:
        self.assertEqual(
            build_reset_body({"task": "Ship feature", "branch": "main", "max_epochs": 3}),
            {"task": "Ship feature", "branch": "main", "max_epochs": 3},
        )

        for args, message in (
            ({"task": 1}, "task must be a string"),
            ({"branch": 1}, "branch must be a string"),
            ({"max_epochs": "3"}, "max_epochs must be an integer"),
        ):
            with self.subTest(args=args):
                with self.assertRaisesRegex(RuntimeError, message):
                    build_reset_body(args)

    def test_coord_clear_state_requires_confirmation(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "confirm=true"):
            run_tool("coord_clear_state", {"confirm": False})

    def test_coord_clear_state_fallback_warning_includes_lessons(self) -> None:
        text = (Path(__file__).resolve().parents[1] / "mcp" / "server.py").read_text(encoding="utf-8")

        self.assertIn("persisted state/profile/history/lessons files", text)

    def test_coord_reset_uses_validated_body(self) -> None:
        calls: list[tuple[str, str, dict[str, object] | None]] = []
        original = mcp_server.hub_request

        def fake_hub_request(
            method: str, path: str, body: dict[str, object] | None = None
        ) -> dict[str, object]:
            calls.append((method, path, body))
            return {"ok": True}

        mcp_server.hub_request = fake_hub_request
        try:
            result = run_tool(
                "coord_reset",
                {"task": "Ship feature", "branch": "feature/ship", "max_epochs": 4},
            )
        finally:
            mcp_server.hub_request = original

        self.assertEqual(
            calls,
            [
                (
                    "POST",
                    "/reset",
                    {"task": "Ship feature", "branch": "feature/ship", "max_epochs": 4},
                )
            ],
        )
        self.assertTrue(json.loads(result["content"][0]["text"])["ok"])

    def test_build_signal_body_validates_fields(self) -> None:
        self.assertEqual(
            build_signal_body(
                {
                    "target": "b",
                    "payload": {"outcome": "progress", "summary": "Moved forward"},
                    "epoch": 2,
                    "turn": "a",
                    "stopped": False,
                }
            ),
            {
                "target": "B",
                "payload": {"outcome": "progress", "summary": "Moved forward"},
                "epoch": 2,
                "turn": "A",
                "stopped": False,
            },
        )
        self.assertEqual(
            build_signal_body({"target": "A", "payload": {"custom": 1}}),
            {"target": "A", "payload": {"custom": 1}},
        )
        for args, message in (
            ({"target": "A", "payload": "bad"}, "payload must be an object"),
            ({"target": "A", "payload": {"outcome": "maybe"}}, "payload.outcome must be one of"),
            ({"target": "A", "payload": {"outcome": 1}}, "payload.outcome must be a string"),
            ({"target": "A", "payload": {}, "epoch": "2"}, "epoch must be an integer"),
            ({"target": "A", "payload": {}, "turn": "C"}, "turn must be A or B"),
            ({"target": "A", "payload": {}, "stopped": "false"}, "stopped must be a boolean"),
        ):
            with self.subTest(args=args):
                with self.assertRaisesRegex(RuntimeError, message):
                    build_signal_body(args)

    def test_coord_signal_validates_before_posting(self) -> None:
        calls: list[tuple[str, str, dict[str, object] | None]] = []
        original = mcp_server.hub_request

        def fake_hub_request(
            method: str, path: str, body: dict[str, object] | None = None
        ) -> dict[str, object]:
            calls.append((method, path, body))
            return {"ok": True}

        mcp_server.hub_request = fake_hub_request
        try:
            result = run_tool(
                "coord_signal",
                {"target": "b", "payload": {"outcome": "done", "summary": "Finished"}, "stopped": True},
            )
        finally:
            mcp_server.hub_request = original

        self.assertEqual(
            calls,
            [
                (
                    "POST",
                    "/signal",
                    {"target": "B", "payload": {"outcome": "done", "summary": "Finished"}, "stopped": True},
                )
            ],
        )
        self.assertTrue(json.loads(result["content"][0]["text"])["ok"])

    def test_coord_lessons_lists_and_adds_via_hub(self) -> None:
        calls: list[tuple[str, str, dict[str, object] | None]] = []
        original = mcp_server.hub_request

        def fake_hub_request(
            method: str, path: str, body: dict[str, object] | None = None
        ) -> dict[str, object]:
            calls.append((method, path, body))
            return {"ok": True, "path": path}

        mcp_server.hub_request = fake_hub_request
        try:
            list_result = run_tool("coord_lessons", {"action": "list", "limit": 3})
            add_result = run_tool(
                "coord_lessons",
                {"action": "add", "role": "a", "epoch": 2, "text": "Reuse fast checks"},
            )
        finally:
            mcp_server.hub_request = original

        self.assertEqual(calls[0], ("GET", "/lessons?limit=3", None))
        self.assertEqual(
            calls[1],
            ("POST", "/lessons", {"role": "A", "text": "Reuse fast checks", "epoch": 2}),
        )
        self.assertEqual(json.loads(list_result["content"][0]["text"])["path"], "/lessons?limit=3")
        self.assertEqual(json.loads(add_result["content"][0]["text"])["path"], "/lessons")

    def test_coord_lessons_validates_add_args(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "role must be A or B"):
            run_tool("coord_lessons", {"action": "add", "role": "C", "text": "bad"})
        with self.assertRaisesRegex(RuntimeError, "text is required"):
            run_tool("coord_lessons", {"action": "add", "role": "A", "text": " "})
        with self.assertRaisesRegex(RuntimeError, "text must be a string"):
            run_tool("coord_lessons", {"action": "add", "role": "A", "text": 123})
        with self.assertRaisesRegex(RuntimeError, "action must be a string"):
            run_tool("coord_lessons", {"action": 1})
        with self.assertRaisesRegex(RuntimeError, "epoch must be an integer"):
            run_tool("coord_lessons", {"action": "add", "role": "A", "text": "x", "epoch": "2"})
        with self.assertRaisesRegex(RuntimeError, "limit must be an integer"):
            run_tool("coord_lessons", {"action": "list", "limit": "2"})

    def test_coord_snapshot_passes_limits_to_hub(self) -> None:
        calls: list[tuple[str, str, dict[str, object] | None]] = []
        original = mcp_server.hub_request

        def fake_hub_request(
            method: str, path: str, body: dict[str, object] | None = None
        ) -> dict[str, object]:
            calls.append((method, path, body))
            return {"ok": True, "path": path}

        mcp_server.hub_request = fake_hub_request
        try:
            result = run_tool(
                "coord_snapshot",
                {"history_limit": 4, "lessons_limit": 7},
            )
        finally:
            mcp_server.hub_request = original

        self.assertEqual(calls, [("GET", "/snapshot?history_limit=4&lessons_limit=7", None)])
        self.assertEqual(
            json.loads(result["content"][0]["text"])["path"],
            "/snapshot?history_limit=4&lessons_limit=7",
        )

    def test_coord_snapshot_and_history_validate_integer_params(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "history_limit must be an integer"):
            run_tool("coord_snapshot", {"history_limit": "4"})
        with self.assertRaisesRegex(RuntimeError, "lessons_limit must be >= 1"):
            run_tool("coord_snapshot", {"lessons_limit": 0})
        with self.assertRaisesRegex(RuntimeError, "limit must be an integer"):
            run_tool("coord_history", {"limit": "10"})
        with self.assertRaisesRegex(RuntimeError, "since_id must be an integer"):
            run_tool("coord_history", {"since_id": "1"})

    def test_coord_signal_outcome_builds_standard_payload(self) -> None:
        calls: list[tuple[str, str, dict[str, object] | None]] = []
        original = mcp_server.hub_request

        def fake_hub_request(
            method: str, path: str, body: dict[str, object] | None = None
        ) -> dict[str, object]:
            calls.append((method, path, body))
            return {"ok": True}

        mcp_server.hub_request = fake_hub_request
        try:
            result = run_tool(
                "coord_signal_outcome",
                {
                    "target": "b",
                    "outcome": "progress",
                    "summary": "Implemented feature",
                    "epoch": 3,
                    "turn": "b",
                    "stopped": False,
                },
            )
        finally:
            mcp_server.hub_request = original

        self.assertEqual(
            calls,
            [
                (
                    "POST",
                    "/signal",
                    {
                        "target": "B",
                        "payload": {"outcome": "progress", "summary": "Implemented feature"},
                        "epoch": 3,
                        "turn": "B",
                        "stopped": False,
                    },
                )
            ],
        )
        self.assertTrue(json.loads(result["content"][0]["text"])["ok"])

    def test_coord_signal_outcome_validates_required_fields(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "outcome must be one of"):
            run_tool("coord_signal_outcome", {"target": "A", "outcome": "maybe", "summary": "bad"})
        with self.assertRaisesRegex(RuntimeError, "summary is required"):
            run_tool("coord_signal_outcome", {"target": "A", "outcome": "progress", "summary": ""})
        with self.assertRaisesRegex(RuntimeError, "summary must be a string"):
            run_tool("coord_signal_outcome", {"target": "A", "outcome": "progress", "summary": 123})
        with self.assertRaisesRegex(RuntimeError, "target must be a string"):
            run_tool("coord_signal_outcome", {"target": 1, "outcome": "progress", "summary": "bad"})
        with self.assertRaisesRegex(RuntimeError, "turn must be A or B"):
            run_tool(
                "coord_signal_outcome",
                {"target": "A", "outcome": "progress", "summary": "bad", "turn": "C"},
            )
        with self.assertRaisesRegex(RuntimeError, "stopped must be a boolean"):
            run_tool(
                "coord_signal_outcome",
                {"target": "A", "outcome": "progress", "summary": "bad", "stopped": "false"},
            )
        with self.assertRaisesRegex(RuntimeError, "epoch must be an integer"):
            run_tool(
                "coord_signal_outcome",
                {"target": "A", "outcome": "progress", "summary": "bad", "epoch": "2"},
            )

    def test_coord_profile_posts_when_profile_key_is_present(self) -> None:
        calls: list[tuple[str, str, dict[str, object] | None]] = []
        original = mcp_server.hub_request

        def fake_hub_request(
            method: str, path: str, body: dict[str, object] | None = None
        ) -> dict[str, object]:
            calls.append((method, path, body))
            return {"ok": True, "path": path}

        mcp_server.hub_request = fake_hub_request
        try:
            get_result = run_tool("coord_profile", {})
            post_result = run_tool("coord_profile", {"profile": {}})
        finally:
            mcp_server.hub_request = original

        self.assertEqual(calls[0], ("GET", "/profile", None))
        self.assertEqual(calls[1], ("POST", "/profile", {}))
        self.assertEqual(json.loads(get_result["content"][0]["text"])["path"], "/profile")
        self.assertEqual(json.loads(post_result["content"][0]["text"])["path"], "/profile")

    def test_coord_profile_rejects_non_object_profile(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "profile must be an object"):
            run_tool("coord_profile", {"profile": []})

    def test_coord_prompt_validates_role_locally(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "role must be A or B"):
            run_tool("coord_prompt", {"role": "C"})
        with self.assertRaisesRegex(RuntimeError, "role must be a string"):
            run_tool("coord_prompt", {"role": 1})

    def test_coord_templates_validates_lang_locally(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "lang must be en or zh"):
            run_tool("coord_templates", {"lang": "fr"})
        with self.assertRaisesRegex(RuntimeError, "lang must be en or zh"):
            run_tool("coord_templates", {"lang": 1})


if __name__ == "__main__":
    unittest.main()
