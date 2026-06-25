from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

_TEMPLATES_PATH = Path(__file__).resolve().parent / "templates.json"


def load_templates() -> dict[str, Any]:
    with _TEMPLATES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def template_ids() -> list[str]:
    return list(load_templates().keys())


def get_template(template_id: str) -> dict[str, Any]:
    templates = load_templates()
    if template_id not in templates:
        raise KeyError(f"unknown template: {template_id}")
    return deepcopy(templates[template_id])


def build_profile(
    template_id: str,
    *,
    roles: dict[str, Any] | None = None,
    task: dict[str, Any] | None = None,
    max_epochs: int = 20,
    lang: str = "en",
) -> dict[str, Any]:
    base = get_template(template_id)
    profile: dict[str, Any] = {
        "template": template_id,
        "roles": deepcopy(roles or base["roles"]),
        "workflow": deepcopy(base["workflow"]),
        "task": deepcopy(task or base["task"]),
        "maxEpochs": max_epochs,
        "lang": lang,
    }
    return profile


def apply_setup_to_state(profile: dict[str, Any]) -> dict[str, Any]:
    """Map profile to hub /reset body fields."""
    task = profile.get("task") or {}
    workflow = profile.get("workflow") or {}
    return {
        "task": str(task.get("title", "")),
        "branch": str(task.get("branch", "main")),
        "turn": str(workflow.get("initialTurn", "A")).upper(),
        "epoch": 0,
        "max_epochs": int(profile.get("maxEpochs", 20)),
        "stopped": False,
    }
