from __future__ import annotations

import unittest

from lib.profile import build_profile
from lib.prompt import build_prompt


class PromptTests(unittest.TestCase):
    def test_english_prompt_trims_hub_url_and_uses_role(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "Implement login", "branch": "main", "constraints": []},
            lang="en",
        )

        prompt = build_prompt("A", profile, "http://127.0.0.1:9900/")

        self.assertIn("You are coord role A (builder)", prompt)
        self.assertIn("http://127.0.0.1:9900/wait/A", prompt)
        self.assertNotIn("http://127.0.0.1:9900//wait/A", prompt)
        self.assertIn("AGENT_LOOP_WAKE_A", prompt)
        self.assertIn("recommended_action=stop", prompt)
        self.assertIn("payload.outcome must be one of progress, blocked, no-op, done", prompt)
        self.assertIn("do not rely on memory", prompt)
        self.assertIn("http://127.0.0.1:9900/snapshot", prompt)
        self.assertIn("Signal example", prompt)
        self.assertIn('"outcome":"progress"', prompt)
        self.assertIn('"target":"B"', prompt)
        self.assertIn('"turn":"B"', prompt)
        self.assertIn('./scripts/signal.sh --dry-run B progress "what changed this round" 1 B', prompt)
        self.assertIn("add --stopped", prompt)
        self.assertIn("http://127.0.0.1:9900/signal", prompt)
        self.assertIn("http://127.0.0.1:9900/lessons", prompt)

    def test_chinese_prompt_uses_localized_role(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "实现登录", "branch": "main", "constraints": []},
            lang="zh",
        )

        prompt = build_prompt("B", profile, "http://127.0.0.1:9900")

        self.assertIn("你是 coord 角色 B（审查者）", prompt)
        self.assertIn("不要依赖记忆", prompt)
        self.assertIn("recommended_action=stop", prompt)
        self.assertIn("payload.outcome 必须是 progress、blocked、no-op、done 之一", prompt)
        self.assertIn("http://127.0.0.1:9900/snapshot", prompt)
        self.assertIn("signal 示例", prompt)
        self.assertIn('"outcome":"progress"', prompt)
        self.assertIn('"target":"A"', prompt)
        self.assertIn('"turn":"A"', prompt)
        self.assertNotIn('"target":"B","epoch":1,"turn":"B"', prompt)
        self.assertIn('./scripts/signal.sh --dry-run A progress "本轮完成内容" 1 A', prompt)
        self.assertIn("加入 --stopped", prompt)
        self.assertIn("POST http://127.0.0.1:9900/signal", prompt)
        self.assertIn("POST http://127.0.0.1:9900/lessons", prompt)
        self.assertIn("http://127.0.0.1:9900/wait/B", prompt)
        self.assertIn("AGENT_LOOP_WAKE_B", prompt)

    def test_invalid_role_is_rejected(self) -> None:
        profile = build_profile(
            "dev-review",
            task={"title": "Implement login", "branch": "main", "constraints": []},
        )

        with self.assertRaisesRegex(ValueError, "role must be A or B"):
            build_prompt("C", profile, "http://127.0.0.1:9900")


if __name__ == "__main__":
    unittest.main()
