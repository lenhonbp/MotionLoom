#!/usr/bin/env python3
"""Deterministic checks for Dev Lab state-machine candidate binding."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "review-hook.py"
spec = importlib.util.spec_from_file_location("motionloom_review_hook_state_machine", MODULE_PATH)
assert spec and spec.loader
review_hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_hook)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def runtime_descriptor(include_machine: bool) -> dict:
    files = ["frames/idle.png", "frames/run.png"]
    if include_machine:
        files.append("devlab-state-machine.json")
    return {
        "schema_version": "1.0",
        "mode": "sprite-sequence",
        "files": files,
        "default_animation": "idle",
        "animations": [
            {"id": "idle", "fps": 8, "frames": ["frames/idle.png"], "loop": True, "review_required": True},
            {"id": "run", "fps": 8, "frames": ["frames/run.png"], "loop": True, "review_required": True},
        ],
        "controls": {"play": True, "pause": True, "restart": True, "seek": True, "step": True, "speed": True, "loop": True},
        "review_policy": {"require_all_animations": True},
    }


def machine(label: str = "Start run") -> dict:
    return {
        "schema_version": "1.0",
        "initial_state": "idle",
        "states": [
            {"id": "idle", "label": "Idle", "animation": "idle"},
            {"id": "run", "label": "Run", "animation": "run"},
        ],
        "transitions": [
            {
                "id": "start-run",
                "label": label,
                "from": "idle",
                "to": "run",
                "trigger": "move",
                "mode": "select-animation",
                "review_required": True,
            }
        ],
        "sequences": [],
        "review_policy": {"require_all_transitions": True, "require_all_sequences": False},
    }


def build_scene(root: Path, include_machine: bool) -> Path:
    scene = root / ("bound" if include_machine else "unbound")
    (scene / "frames").mkdir(parents=True)
    (scene / "frames" / "idle.png").write_bytes(b"idle")
    (scene / "frames" / "run.png").write_bytes(b"run")
    write_json(scene / "devlab-runtime.json", runtime_descriptor(include_machine))
    write_json(scene / "devlab-state-machine.json", machine())
    return scene


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        bound = build_scene(root, True)
        first = review_hook.runtime_bundle(bound)
        assert first is not None
        write_json(bound / "devlab-state-machine.json", machine("Changed transition label"))
        second = review_hook.runtime_bundle(bound)
        assert second["bundle_sha256"] != first["bundle_sha256"], "hash-bound state-machine drift must invalidate the candidate runtime bundle"

        unbound = build_scene(root, False)
        first_unbound = review_hook.runtime_bundle(unbound)
        write_json(unbound / "devlab-state-machine.json", machine("Unbound byte drift"))
        second_unbound = review_hook.runtime_bundle(unbound)
        assert second_unbound["bundle_sha256"] == first_unbound["bundle_sha256"], "undeclared state-machine bytes must not influence candidate identity"

    print(json.dumps({
        "status": "pass",
        "state_machine": "hash-bound-when-declared",
        "unbound_state_machine": "ignored-by-bundle",
        "approval": "user_only",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
