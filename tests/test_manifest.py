from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_project_and_root_mcp_configs_match(self) -> None:
        root_config = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        project_config = json.loads((ROOT / ".cursor" / "mcp.json").read_text(encoding="utf-8"))

        self.assertEqual(root_config, project_config)
        server = root_config["mcpServers"]["cursor-ab-coord"]
        self.assertEqual(server["command"], "python3")
        self.assertEqual(server["args"], ["mcp/server.py"])

    def test_plugin_manifest_references_existing_safe_logo(self) -> None:
        manifest = json.loads((ROOT / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
        logo = manifest["logo"]

        self.assertEqual(manifest["name"], "cursor-ab-coord")
        self.assertFalse(logo.startswith("/"))
        self.assertNotIn("..", Path(logo).parts)
        self.assertTrue((ROOT / logo).is_file())

    def test_project_skill_matches_plugin_skill_copy(self) -> None:
        plugin_skill = (ROOT / "skills" / "coord-setup" / "SKILL.md").read_text(encoding="utf-8")
        project_skill = (
            ROOT / ".cursor" / "skills" / "coord-setup" / "SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertEqual(plugin_skill, project_skill)


if __name__ == "__main__":
    unittest.main()
