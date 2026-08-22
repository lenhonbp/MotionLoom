"""Shared browser-review candidate consistency checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# These fields determine which exact candidate was reviewed. The URL is
# intentionally excluded because a Dev Lab deployment may legitimately use a
# different host/base path while the candidate bytes remain identical.
IDENTITY_FIELDS = (
    "candidate_id",
    "task_id",
    "scene",
    "source_sha256",
    "context_sha256",
    "status",
    "expires_at",
    "runtime_review",
)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def candidate_consistency_errors(
    scene_candidate_path: Path,
    task_candidate_path: Path,
    *,
    expected_task_id: str | None = None,
    expected_scene: str | None = None,
) -> list[str]:
    """Return fail-closed errors for scene/task browser-review divergence."""

    errors: list[str] = []
    if not scene_candidate_path.is_file():
        return ["scene-level browser-review.json is required when a task bundle is used"]
    if not task_candidate_path.is_file():
        return ["task-level browser-review.json is required when a task bundle is used"]

    scene_candidate = read_json(scene_candidate_path)
    task_candidate = read_json(task_candidate_path)
    if not scene_candidate:
        errors.append("scene-level browser-review.json is invalid or empty")
    if not task_candidate:
        errors.append("task-level browser-review.json is invalid or empty")

    for field in IDENTITY_FIELDS:
        if scene_candidate.get(field) != task_candidate.get(field):
            errors.append(f"scene/task browser-review {field} mismatch")

    if expected_task_id is not None and task_candidate.get("task_id") != expected_task_id:
        errors.append("task-level browser-review task_id does not match task.json")
    if expected_scene is not None and task_candidate.get("scene") != expected_scene:
        errors.append("task-level browser-review scene does not match scene directory")

    return errors
