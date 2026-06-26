from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lib.profile import validate_profile


ROOT = Path(__file__).resolve().parents[1]


class ExamplesTests(unittest.TestCase):
    def test_all_examples_are_valid_json(self) -> None:
        for path in sorted((ROOT / "examples").glob("*.json")):
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_setup_examples_are_valid_profiles(self) -> None:
        for path in sorted((ROOT / "examples").glob("setup-*.json")):
            with self.subTest(path=path.name):
                body = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_profile(body), [])

    def test_validate_profile_script_accepts_setup_example(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate-profile.py"),
                str(ROOT / "examples" / "setup-dev-review.json"),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        self.assertEqual(proc.stdout.strip(), "profile ok")

    def test_validate_profile_script_resolves_repo_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate-profile.py"),
                    "examples/setup-dev-review.json",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
                cwd=tmp,
            )

        self.assertEqual(proc.stdout.strip(), "profile ok")

    def test_validate_profile_script_accepts_stdin(self) -> None:
        profile = (ROOT / "examples" / "setup-dev-review.json").read_text(encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate-profile.py"),
                "-",
            ],
            input=profile,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd="/",
        )

        self.assertEqual(proc.stdout.strip(), "profile ok")

    def test_apply_setup_dry_run_does_not_require_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "apply-setup.sh"),
                "--dry-run",
                "examples/setup-dev-review.json",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd="/",
        )

        body = json.loads(proc.stdout)
        self.assertEqual(body["template"], "dev-review")
        self.assertEqual(body["task"]["title"], "Implement feature X")

    def test_apply_setup_dry_run_accepts_stdin(self) -> None:
        build = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build-profile.py"),
                "Pipe profile",
                "--constraint",
                "No server",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd="/",
        )
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "apply-setup.sh"),
                "--dry-run",
                "-",
            ],
            input=build.stdout,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd="/",
        )

        body = json.loads(proc.stdout)
        self.assertEqual(body["task"]["title"], "Pipe profile")
        self.assertEqual(body["task"]["constraints"], ["No server"])

    def test_quick_setup_dry_run_does_not_require_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "quick-setup.sh"),
                "--dry-run",
                "Preview profile",
                "--constraint",
                "No server",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd="/",
        )

        body = json.loads(proc.stdout)
        self.assertEqual(body["task"]["title"], "Preview profile")
        self.assertEqual(body["task"]["constraints"], ["No server"])

    def test_lessons_script_rejects_invalid_role_without_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "lessons.sh"),
                "add",
                "C",
                "Should fail before curl",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("role must be A or B", proc.stderr)

    def test_lessons_script_rejects_empty_text_without_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "lessons.sh"),
                "add",
                "A",
                "",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("text is required", proc.stderr)

    def test_signal_script_rejects_invalid_outcome_without_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "signal.sh"),
                "A",
                "maybe",
                "Should fail before curl",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("outcome must be one of", proc.stderr)

    def test_signal_script_rejects_invalid_roles_without_hub(self) -> None:
        bad_target = subprocess.run(
            [
                str(ROOT / "scripts" / "signal.sh"),
                "C",
                "progress",
                "Should fail before curl",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )
        bad_turn = subprocess.run(
            [
                str(ROOT / "scripts" / "signal.sh"),
                "A",
                "progress",
                "Should fail before curl",
                "1",
                "C",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(bad_target.returncode, 2)
        self.assertIn("target must be A or B", bad_target.stderr)
        self.assertEqual(bad_turn.returncode, 2)
        self.assertIn("turn must be A or B", bad_turn.stderr)

    def test_signal_script_dry_run_outputs_payload_without_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "signal.sh"),
                "--dry-run",
                "--stopped",
                "b",
                "progress",
                "Built endpoint",
                "3",
                "b",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd="/",
        )

        body = json.loads(proc.stdout)
        self.assertEqual(body["target"], "B")
        self.assertEqual(body["epoch"], 3)
        self.assertEqual(body["turn"], "B")
        self.assertTrue(body["stopped"])
        self.assertEqual(body["payload"]["outcome"], "progress")
        self.assertEqual(body["payload"]["summary"], "Built endpoint")

    def test_snapshot_script_rejects_invalid_limit_without_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "snapshot.sh"),
                "--history-limit",
                "bad",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("history limit must be a positive integer", proc.stderr)

    def test_lessons_script_rejects_invalid_limit_without_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "lessons.sh"),
                "list",
                "0",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("limit must be a positive integer", proc.stderr)

    def test_prompts_script_rejects_invalid_role_without_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "prompts.sh"),
                "C",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("Usage:", proc.stderr)

    def test_reset_script_rejects_missing_task_without_hub(self) -> None:
        proc = subprocess.run(
            [
                str(ROOT / "scripts" / "reset.sh"),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("Usage:", proc.stderr)

    def test_doctor_checks_snapshot_and_lessons_helpers(self) -> None:
        text = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")

        self.assertIn('require_executable "scripts/signal.sh"', text)
        self.assertIn('require_executable "scripts/lessons.sh"', text)
        self.assertIn('require_executable "scripts/snapshot.sh"', text)
        self.assertIn('require_executable "scripts/build-profile.py"', text)
        self.assertIn('require_executable "scripts/validate-profile.py"', text)
        self.assertIn('require_executable "scripts/clear-state.sh"', text)
        self.assertIn("$HUB_URL/lessons", text)
        self.assertIn("$HUB_URL/snapshot", text)
        self.assertIn("outcome_counts", text)
        self.assertIn("outcomes $outcome_summary", text)

    def test_status_prefers_snapshot_with_health_fallback(self) -> None:
        text = (ROOT / "scripts" / "status.sh").read_text(encoding="utf-8")

        self.assertIn("${HUB_URL}/snapshot", text)
        self.assertIn("${HUB_URL}/health", text)
        self.assertIn("${HUB_URL}/state", text)
        self.assertLess(text.index("${HUB_URL}/snapshot"), text.index("${HUB_URL}/health"))

    def test_readme_documents_snapshot_lessons_and_outcomes(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("`coord_snapshot`", text)
        self.assertIn("`coord_lessons`", text)
        self.assertIn("`coord_signal_outcome`", text)
        self.assertIn("GET | `/snapshot`", text)
        self.assertIn("GET | `/lessons`", text)
        self.assertIn("POST | `/lessons`", text)
        self.assertIn("`payload.outcome`", text)

    def test_readme_documents_new_helper_scripts(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("`./scripts/snapshot.sh [--raw]`", text)
        self.assertIn("`./scripts/signal.sh [--dry-run] ...`", text)
        self.assertIn("`./scripts/lessons.sh list\\|add`", text)
        self.assertIn("COORD_SNAPSHOT_TIMEOUT", text)
        self.assertIn("COORD_SIGNAL_TIMEOUT", text)
        self.assertIn("COORD_LESSONS_TIMEOUT", text)

    def test_clear_state_script_removes_lessons_files(self) -> None:
        script = (ROOT / "scripts" / "clear-state.sh").read_text(encoding="utf-8")

        self.assertIn(".coord-lessons.json", script)
        self.assertIn(".coord-lessons.json.tmp", script)
        self.assertIn("state/profile/history/lessons", script)

    def test_docs_describe_clear_state_lessons_scope(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        mcp_server = (ROOT / "mcp" / "server.py").read_text(encoding="utf-8")

        self.assertIn("state/profile/history/lessons", readme)
        self.assertIn("state/profile/history/lessons", mcp_server)
        for path in (
            ROOT / "skills" / "coord-setup" / "SKILL.md",
            ROOT / ".cursor" / "skills" / "coord-setup" / "SKILL.md",
        ):
            self.assertIn("state/profile/history/lessons", path.read_text(encoding="utf-8"))

    def test_static_website_prompt_uses_snapshot_protocol(self) -> None:
        text = (ROOT / "website" / "js" / "main.js").read_text(encoding="utf-8")

        self.assertIn("/snapshot", text)
        self.assertIn("payload.outcome must be one of progress, blocked, no-op, done", text)
        self.assertIn("/lessons", text)
        self.assertNotIn("curl -s ${hubUrl}/profile", text)
        self.assertNotIn("curl -s ${hubUrl}/state", text)

    def test_static_website_describes_setup_endpoint(self) -> None:
        text = (ROOT / "website" / "js" / "i18n.js").read_text(encoding="utf-8")

        self.assertIn("Profile JSON (POST /setup)", text)
        self.assertIn("Profile JSON（POST /setup）", text)
        self.assertNotIn("POST /profile", text)
        self.assertIn("<code>/snapshot</code>", text)
        self.assertNotIn("Agents read <code>/profile</code> and <code>/state</code>", text)

    def test_coord_setup_skills_describe_snapshot_runtime(self) -> None:
        for path in (
            ROOT / "skills" / "coord-setup" / "SKILL.md",
            ROOT / ".cursor" / "skills" / "coord-setup" / "SKILL.md",
        ):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("prompts re-anchor with `/snapshot`", text)
                self.assertNotIn("prompts read `/profile` and `/state`", text)

    def test_build_profile_script_outputs_valid_chinese_profile(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build-profile.py"),
                "实现登录",
                "--lang",
                "zh",
                "--constraint",
                "不要启动服务器",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            cwd="/",
        )

        body = json.loads(proc.stdout)
        self.assertEqual(body["roles"]["A"]["name"], "开发者")
        self.assertEqual(body["task"]["title"], "实现登录")
        self.assertEqual(validate_profile(body), [])

    def test_build_profile_script_rejects_non_positive_max_epochs(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build-profile.py"),
                "Implement feature",
                "--max-epochs",
                "0",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
        )

        self.assertEqual(proc.returncode, 2)
        self.assertIn("must be a positive integer", proc.stderr)


if __name__ == "__main__":
    unittest.main()
