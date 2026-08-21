#!/usr/bin/env python3
"""Deterministic tests for Dev Lab live-runtime binding helpers."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "review-hook.py"
spec = importlib.util.spec_from_file_location("motionloom_review_hook", MODULE_PATH)
assert spec and spec.loader
review_hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_hook)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def descriptor() -> dict:
    return {
        "schema_version": "1.0",
        "mode": "sprite-sequence",
        "files": ["frames/idle-0.png", "frames/idle-1.png", "frames/attack-0.png"],
        "default_animation": "idle",
        "animations": [
            {"id": "idle", "fps": 8, "frames": ["frames/idle-0.png", "frames/idle-1.png"], "loop": True, "review_required": True},
            {"id": "attack", "fps": 12, "frames": ["frames/attack-0.png"], "loop": False, "review_required": True},
        ],
        "controls": {"play": True, "pause": True, "restart": True, "seek": True, "step": True, "speed": True, "loop": True},
        "viewport": {"canvas_width": 1920, "canvas_height": 1920, "pixel_art": True},
        "review_policy": {"require_all_animations": True},
    }


def build_scene(root: Path) -> Path:
    scene = root / "scene"
    (scene / "frames").mkdir(parents=True)
    for name, content in [("idle-0.png", b"idle-0"), ("idle-1.png", b"idle-1"), ("attack-0.png", b"attack-0")]:
        (scene / "frames" / name).write_bytes(content)
    write_json(scene / "devlab-runtime.json", descriptor())
    return scene


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        scene = build_scene(Path(td))
        first = review_hook.runtime_bundle(scene)
        assert first is not None
        assert first["mode"] == "sprite-sequence"
        assert first["animations"] == ["idle", "attack"]
        assert len(first["bundle_sha256"]) == 64

        second = review_hook.runtime_bundle(scene)
        assert second["bundle_sha256"] == first["bundle_sha256"], "runtime bundle hashing must be deterministic"
        (scene / "frames" / "attack-0.png").write_bytes(b"attack-mutated")
        mutated = review_hook.runtime_bundle(scene)
        assert mutated["bundle_sha256"] != first["bundle_sha256"], "runtime byte drift must invalidate the bundle"

        bad = descriptor()
        bad["files"].append("../escape.png")
        write_json(scene / "devlab-runtime.json", bad)
        try:
            review_hook.runtime_bundle(scene)
            raise AssertionError("path traversal should fail closed")
        except ValueError as exc:
            assert "unsafe" in str(exc) or "inside" in str(exc)

    legacy_raw = "task:scene:context:source:render"
    import hashlib
    expected_legacy = hashlib.sha256(legacy_raw.encode()).hexdigest()[:20]
    actual_legacy = review_hook.candidate_id("task", "scene", "context", "source", "render")
    assert actual_legacy == expected_legacy, "legacy snapshot candidate identity must remain byte-compatible"
    live = review_hook.candidate_id("task", "scene", "context", "source", "render", "f" * 64)
    assert live != actual_legacy, "live runtime bundle must participate in candidate identity"

    print(json.dumps({"status": "pass", "runtime_bundle": "hash-bound", "path_traversal": "blocked", "legacy_candidate_id": "compatible"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
