#!/usr/bin/env python3
"""Regression tests for action-scoped frame manifests and separation evidence."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "examples/agent-consumer/asset-consistency/action-sequence/hero-walk-action-manifest.json"
GEOMETRY = ROOT / "examples/agent-consumer/asset-consistency/hero-walk-frame-geometry.json"
ACTION_SCRIPT = ROOT / "scripts/action-separation.py"
PREFLIGHT_SCRIPT = ROOT / "scripts/frame-set-preflight.py"


def run_json(script: Path, *args: str) -> tuple[int, dict]:
    result = subprocess.run([sys.executable, str(script), *args, "--json"], cwd=ROOT, capture_output=True, text=True)
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON from {script}: {result.stdout}\n{result.stderr}") from exc


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="motionloom-action-separation-") as td:
        root = Path(td)
        fixture_root = root / "asset-consistency"
        shutil.copytree(ROOT / "examples/agent-consumer/asset-consistency", fixture_root)
        manifest = fixture_root / "action-sequence/hero-walk-action-manifest.json"
        geometry = fixture_root / "hero-walk-frame-geometry.json"

        code, result = run_json(ACTION_SCRIPT, "validate", "--input", str(manifest), "--root", str(fixture_root))
        check(code == 0 and result.get("ready") is True, f"canonical manifest must pass: {result}")
        check(result.get("metrics", {}).get("envelope_count") == 4, "all frame envelopes must be checked")
        check(result.get("approval") is False, "action separation must never grant approval")

        code, result = run_json(
            PREFLIGHT_SCRIPT,
            "--input", str(geometry), "--root", str(fixture_root), "--action-manifest", str(manifest),
        )
        check(code == 0 and result.get("ready") is True, f"manifest-aware frame preflight must pass: {result}")
        check(result.get("metrics", {}).get("action_manifest", {}).get("passing_action_verifications") == 4, "preflight must expose action verification metrics")

        broken_envelope = fixture_root / "action-sequence/envelopes/walk.01.json"
        envelope = json.loads(broken_envelope.read_text(encoding="utf-8"))
        envelope["action_id"] = "attack"
        broken_envelope.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
        code, result = run_json(ACTION_SCRIPT, "validate", "--input", str(manifest), "--root", str(fixture_root))
        check(code != 0 and any(item.get("code") == "envelope_binding_mismatch" for item in result.get("errors", [])), "cross-action envelope must be blocked")

        restored = json.loads((ROOT / "examples/agent-consumer/asset-consistency/action-sequence/envelopes/walk.01.json").read_text(encoding="utf-8"))
        broken_envelope.write_text(json.dumps(restored, indent=2) + "\n", encoding="utf-8")
        envelope = json.loads(broken_envelope.read_text(encoding="utf-8"))
        envelope["verifier"]["margin"] = 0.05
        broken_envelope.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
        code, result = run_json(ACTION_SCRIPT, "validate", "--input", str(manifest), "--root", str(fixture_root))
        check(code != 0 and any(item.get("code") == "action_confidence_margin" for item in result.get("errors", [])), "ambiguous action margin must quarantine")

        duplicated = json.loads(manifest.read_text(encoding="utf-8"))
        duplicated["frames"][1]["image"] = duplicated["frames"][0]["image"]
        duplicate_path = fixture_root / "action-sequence/duplicate.json"
        duplicate_path.write_text(json.dumps(duplicated, indent=2) + "\n", encoding="utf-8")
        code, result = run_json(ACTION_SCRIPT, "validate", "--input", str(duplicate_path), "--root", str(fixture_root))
        check(code != 0 and any(item.get("code") == "duplicate_frame_image" for item in result.get("errors", [])), "cross-frame image reuse must be blocked")

    print("action separation tests: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"action separation tests: FAIL — {exc}", file=sys.stderr)
        raise
