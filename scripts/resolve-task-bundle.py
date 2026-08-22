#!/usr/bin/env python3
"""Resolve one safe artifact task bundle bound to a scene identity.

The resolver intentionally does not infer a task path from a scene slug. A
bundle is eligible only when its direct ``artifacts/<task-id>/task.json``
declares the requested scene and remains inside the repository artifacts root.
Multiple matching bundles are rejected rather than ranked implicitly. A task bundle with a browser-review candidate that conflicts with the canonical scene candidate is not eligible; the later quality/review gates still report that divergence when the bundle is checked directly.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SAFE_SCENE = re.compile(r"^[A-Za-z0-9._-]+$")


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def has_symlink_component(path: Path, root: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        if current == root:
            return False
        if current == current.parent:
            return True
        current = current.parent


def resolve_task_dirs(root: Path, scene: str) -> list[Path]:
    artifacts = root / "artifacts"
    if not artifacts.is_dir() or artifacts.is_symlink():
        return []
    resolved_artifacts = artifacts.resolve()
    scene_candidate = read_json(root / "src" / "output" / scene / "browser-review.json")
    matches: list[Path] = []
    for task_path in sorted(artifacts.glob("*/task.json")):
        if has_symlink_component(task_path, root):
            continue
        try:
            if not task_path.resolve().is_relative_to(resolved_artifacts):
                continue
        except (OSError, RuntimeError):
            continue
        task = read_json(task_path)
        if task.get("scene") != scene:
            continue
        task_candidate = read_json(task_path.parent / "browser-review.json")
        if scene_candidate and task_candidate:
            identity_fields = ("candidate_id", "task_id", "scene", "source_sha256", "context_sha256", "expires_at")
            if any(scene_candidate.get(field) != task_candidate.get(field) for field in identity_fields):
                continue
        matches.append(task_path.parent)
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    if not SAFE_SCENE.fullmatch(args.scene) or args.scene in {".", ".."}:
        print("FAIL: unsafe scene identifier", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    matches = resolve_task_dirs(root, args.scene)
    if not matches:
        print(f"FAIL: no safe task bundle bound to scene: {args.scene}", file=sys.stderr)
        return 3
    if len(matches) != 1:
        joined = ", ".join(str(path.relative_to(root)) for path in matches)
        print(f"FAIL: ambiguous task bundles bound to scene {args.scene}: {joined}", file=sys.stderr)
        return 4
    print(matches[0].relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
