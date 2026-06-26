from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

_TEMPLATES_PATH = Path(__file__).resolve().parent / "templates.json"
_TEMPLATES_ZH_PATH = Path(__file__).resolve().parent / "templates.zh.json"


def require_supported_lang(lang: Any) -> str:
    if not isinstance(lang, str) or lang not in ("en", "zh"):
        raise ValueError("lang must be en or zh")
    return lang


def load_templates() -> dict[str, Any]:
    with _TEMPLATES_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def load_template_overrides(lang: str) -> dict[str, Any]:
    lang = require_supported_lang(lang)
    if lang != "zh":
        return {}
    try:
        with _TEMPLATES_ZH_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def template_ids() -> list[str]:
    return list(load_templates().keys())


def load_templates_for_lang(lang: str = "en") -> dict[str, Any]:
    lang = require_supported_lang(lang)
    return {template_id: get_template(template_id, lang=lang) for template_id in template_ids()}


def get_template(template_id: str, *, lang: str = "en") -> dict[str, Any]:
    lang = require_supported_lang(lang)
    templates = load_templates()
    if template_id not in templates:
        raise KeyError(f"unknown template: {template_id}")
    template = templates[template_id]
    override = load_template_overrides(lang).get(template_id, {})
    return deep_merge(template, override)


def build_profile(
    template_id: str,
    *,
    roles: dict[str, Any] | None = None,
    task: dict[str, Any] | None = None,
    max_epochs: int = 20,
    lang: str = "en",
) -> dict[str, Any]:
    lang = require_supported_lang(lang)
    base = get_template(template_id, lang=lang)
    profile: dict[str, Any] = {
        "template": template_id,
        "roles": deepcopy(roles or base["roles"]),
        "workflow": deepcopy(base["workflow"]),
        "task": deepcopy(task or base["task"]),
        "maxEpochs": max_epochs,
        "lang": lang,
    }
    return profile


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _require_nonempty_string(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{field} must be a string")
        return
    if not value.strip():
        errors.append(f"{field} is required")


def _require_role(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{field} must be A or B")
        return
    if value.upper() not in ("A", "B"):
        errors.append(f"{field} must be A or B")


def validate_profile(profile: dict[str, Any]) -> list[str]:
    """Return validation errors for a profile body accepted by /profile and /setup."""
    errors: list[str] = []

    if not isinstance(profile, dict):
        return ["profile must be an object"]

    template = profile.get("template")
    if template is not None and not isinstance(template, str):
        errors.append("template must be a string")

    roles = profile.get("roles")
    if not isinstance(roles, dict):
        errors.append("roles must be an object")
    else:
        for role in ("A", "B"):
            value = roles.get(role)
            if not isinstance(value, dict):
                errors.append(f"roles.{role} must be an object")
                continue

            for field in ("name", "goal", "wakeSentinel"):
                _require_nonempty_string(value.get(field, ""), f"roles.{role}.{field}", errors)

            for field in ("responsibilities", "forbidden"):
                if field in value and not _is_string_list(value[field]):
                    errors.append(f"roles.{role}.{field} must be an array of strings")

    workflow = profile.get("workflow")
    if not isinstance(workflow, dict):
        errors.append("workflow must be an object")
    else:
        _require_role(workflow.get("initialTurn", "A"), "workflow.initialTurn", errors)

        transitions = workflow.get("transitions", [])
        if not isinstance(transitions, list):
            errors.append("workflow.transitions must be an array")
        else:
            for idx, transition in enumerate(transitions):
                if not isinstance(transition, dict):
                    errors.append(f"workflow.transitions[{idx}] must be an object")
                    continue
                for field in ("from", "to"):
                    _require_role(
                        transition.get(field, ""),
                        f"workflow.transitions[{idx}].{field}",
                        errors,
                    )
                _require_nonempty_string(
                    transition.get("action", ""),
                    f"workflow.transitions[{idx}].action",
                    errors,
                )
                if "stop" in transition and not isinstance(transition["stop"], bool):
                    errors.append(f"workflow.transitions[{idx}].stop must be a boolean")

    task = profile.get("task")
    if not isinstance(task, dict):
        errors.append("task must be an object")
    else:
        _require_nonempty_string(task.get("title", ""), "task.title", errors)
        if "branch" in task and not isinstance(task["branch"], str):
            errors.append("task.branch must be a string")
        if "constraints" in task and not _is_string_list(task["constraints"]):
            errors.append("task.constraints must be an array of strings")

    max_epochs = profile.get("maxEpochs", 20)
    if not isinstance(max_epochs, int) or isinstance(max_epochs, bool):
        errors.append("maxEpochs must be an integer")
    elif max_epochs < 1:
        errors.append("maxEpochs must be >= 1")

    lang = profile.get("lang", "en")
    if lang not in ("en", "zh"):
        errors.append("lang must be en or zh")

    return errors


def apply_setup_to_state(profile: dict[str, Any]) -> dict[str, Any]:
    """Map profile to hub /reset body fields."""
    errors = validate_profile(profile)
    if errors:
        raise ValueError("; ".join(errors))

    task = profile["task"]
    workflow = profile["workflow"]
    branch = task.get("branch", "main")
    initial_turn = workflow.get("initialTurn", "A")
    return {
        "task": task["title"],
        "branch": branch,
        "turn": initial_turn.upper(),
        "epoch": 0,
        "max_epochs": profile.get("maxEpochs", 20),
        "stopped": False,
        "stagnation_count": 0,
        "recommended_action": "continue",
        "terminal_reason": "none",
    }
