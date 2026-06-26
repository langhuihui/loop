from __future__ import annotations

import unittest

from lib.profile import (
    apply_setup_to_state,
    build_profile,
    load_template_overrides,
    load_templates,
    load_templates_for_lang,
    require_supported_lang,
    validate_profile,
)


class ProfileTests(unittest.TestCase):
    def test_build_profile_uses_chinese_template_overrides(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "实现登录", "branch": "main", "constraints": ["不要启动服务器"]},
            lang="zh",
        )

        self.assertEqual(profile["roles"]["A"]["name"], "开发者")
        self.assertEqual(profile["roles"]["B"]["name"], "审查者")
        self.assertEqual(profile["roles"]["A"]["wakeSentinel"], "AGENT_LOOP_WAKE_A")
        self.assertEqual(profile["task"]["title"], "实现登录")
        self.assertEqual(profile["lang"], "zh")

    def test_load_templates_for_lang_preserves_workflow(self) -> None:
        templates = load_templates_for_lang("zh")

        dev_review = templates["dev-review"]
        self.assertEqual(dev_review["roles"]["A"]["name"], "开发者")
        self.assertEqual(dev_review["workflow"]["initialTurn"], "A")
        self.assertEqual(dev_review["workflow"]["transitions"][0]["action"], "review")

    def test_template_language_helpers_reject_unsupported_lang(self) -> None:
        self.assertEqual(require_supported_lang("en"), "en")
        self.assertEqual(require_supported_lang("zh"), "zh")
        for value in ("fr", "", 1):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "lang must be en or zh"):
                    require_supported_lang(value)
        with self.assertRaisesRegex(ValueError, "lang must be en or zh"):
            load_template_overrides("fr")
        with self.assertRaisesRegex(ValueError, "lang must be en or zh"):
            load_templates_for_lang("fr")
        with self.assertRaisesRegex(ValueError, "lang must be en or zh"):
            build_profile("dev-review", task={"title": "x"}, lang="fr")

    def test_chinese_overrides_cover_all_templates_and_roles(self) -> None:
        templates = load_templates()
        zh_overrides = load_template_overrides("zh")

        self.assertEqual(set(templates), set(zh_overrides))
        for template_id, template in templates.items():
            override = zh_overrides[template_id]
            self.assertEqual(set(template["roles"]), set(override["roles"]))
            self.assertIn("task", override)
            self.assertIn("title", override["task"])
            self.assertIn("constraints", override["task"])
            for role in ("A", "B"):
                self.assertIn("name", override["roles"][role])
                self.assertIn("goal", override["roles"][role])
                self.assertIn("responsibilities", override["roles"][role])
                self.assertIn("forbidden", override["roles"][role])

    def test_validate_profile_rejects_missing_sections(self) -> None:
        errors = validate_profile({})

        self.assertIn("roles must be an object", errors)
        self.assertIn("workflow must be an object", errors)
        self.assertIn("task must be an object", errors)

    def test_validate_profile_accepts_generated_profile(self) -> None:
        profile = build_profile(
            "test-fix",
            task={"title": "Add tests", "branch": "main", "constraints": []},
        )

        self.assertEqual(validate_profile(profile), [])

    def test_validate_profile_requires_wake_sentinel(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "Implement feature", "branch": "main", "constraints": []},
        )
        profile["roles"]["A"].pop("wakeSentinel")
        profile["roles"]["B"]["wakeSentinel"] = " "

        errors = validate_profile(profile)

        self.assertIn("roles.A.wakeSentinel is required", errors)
        self.assertIn("roles.B.wakeSentinel is required", errors)

    def test_validate_profile_rejects_non_string_required_text_fields(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "Implement feature", "branch": "main", "constraints": []},
        )
        profile["roles"]["A"]["name"] = 123
        profile["workflow"]["transitions"][0]["action"] = 123
        profile["task"]["title"] = 123

        errors = validate_profile(profile)

        self.assertIn("roles.A.name must be a string", errors)
        self.assertIn("workflow.transitions[0].action must be a string", errors)
        self.assertIn("task.title must be a string", errors)

    def test_validate_profile_rejects_invalid_workflow_roles(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "Implement feature", "branch": "main", "constraints": []},
        )
        profile["workflow"]["initialTurn"] = 1
        profile["workflow"]["transitions"][0]["from"] = "C"
        profile["workflow"]["transitions"][0]["to"] = 2

        errors = validate_profile(profile)

        self.assertIn("workflow.initialTurn must be A or B", errors)
        self.assertIn("workflow.transitions[0].from must be A or B", errors)
        self.assertIn("workflow.transitions[0].to must be A or B", errors)

    def test_validate_profile_requires_boolean_transition_stop(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "Implement feature", "branch": "main", "constraints": []},
        )
        profile["workflow"]["transitions"][0]["stop"] = "true"

        errors = validate_profile(profile)

        self.assertIn("workflow.transitions[0].stop must be a boolean", errors)

    def test_validate_profile_requires_integer_max_epochs(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "Implement feature", "branch": "main", "constraints": []},
        )

        for value in (1.5, "20", True):
            with self.subTest(value=value):
                profile["maxEpochs"] = value
                self.assertIn("maxEpochs must be an integer", validate_profile(profile))

    def test_apply_setup_to_state_maps_runtime_fields(self) -> None:
        profile = build_profile(
            "plan-implement",
            task={"title": "Build endpoint", "branch": "feature/api", "constraints": []},
            max_epochs=7,
        )

        state = apply_setup_to_state(profile)
        self.assertEqual(state["task"], "Build endpoint")
        self.assertEqual(state["branch"], "feature/api")
        self.assertEqual(state["turn"], "A")
        self.assertEqual(state["max_epochs"], 7)
        self.assertFalse(state["stopped"])
        self.assertEqual(state["stagnation_count"], 0)
        self.assertEqual(state["recommended_action"], "continue")
        self.assertEqual(state["terminal_reason"], "none")

    def test_apply_setup_to_state_rejects_invalid_profile(self) -> None:
        profile = build_profile(
            "plan-implement",
            task={"title": "Build endpoint", "branch": "feature/api", "constraints": []},
        )
        profile["maxEpochs"] = "20"

        with self.assertRaisesRegex(ValueError, "maxEpochs must be an integer"):
            apply_setup_to_state(profile)


if __name__ == "__main__":
    unittest.main()
