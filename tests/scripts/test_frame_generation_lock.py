#!/usr/bin/env python3
"""Regression tests for MotionLoom's provider-neutral Frame Generation Lock."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples/agent-consumer/frame-generation-lock/hero-walk-lock.json"
SCRIPT = ROOT / "scripts/frame-generation-lock.py"
ASSET_ROOT = ROOT / "examples/agent-consumer"


def run(*args: str) -> tuple[int, dict]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON output: {result.stdout}\n{result.stderr}") from exc
    return result.returncode, payload


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_variant(document: dict, directory: Path, name: str = "lock.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


def base_schema_version() -> str:
    return json.loads(FIXTURE.read_text(encoding="utf-8")).get("schema_version", "")


def test_valid_lock_and_compose() -> None:
    code, result = run("validate", "--input", str(FIXTURE), "--root", str(ASSET_ROOT))
    check(code == 0 and result.get("ready") is True, f"valid lock should pass: {result}")
    check(result.get("approval") is False, "lock validation must preserve approval=false")
    check(result.get("metrics", {}).get("frame_count") == 4, "fixture must expose four frames")
    check(base_schema_version() == "0.2", "canonical lock fixture must exercise enhanced schema 0.2")

    code, result = run(
        "compose", "--input", str(FIXTURE), "--root", str(ASSET_ROOT), "--frame-id", "walk.01"
    )
    check(code == 0 and result.get("ready") is True, f"compose should pass: {result}")
    frames = result.get("frames", [])
    check(len(frames) == 1 and frames[0].get("frame_id") == "walk.01", "compose must select one exact frame")
    instruction = frames[0].get("instruction", "")
    check("exactly ONE isolated source frame" in instruction, "composer must forbid multi-pose source generation")
    check("8 × 8" in instruction, "composer must bind exact canvas dimensions")
    check("Contact" not in instruction and "Passing:" in instruction, "composer must use the selected pose only")
    check("do not introduce whole-subject zoom drift" in instruction, "composer must bind apparent-size tolerance")
    check("approval" in instruction.lower(), "composer must preserve review-only trust boundary")
    check("frame-set-preflight" in result.get("next_gate", ""), "composer must point to deterministic postflight")
    check("--action-manifest" in result.get("next_gate", ""), "enhanced composer must point to manifest-aware postflight")
    check("hero-walk-v1" in instruction and "Forbidden competing actions" in instruction, "composer must bind sequence and action-separation cues")

    code, result = run("compose-all", "--input", str(FIXTURE), "--root", str(ASSET_ROOT))
    check(code == 0 and len(result.get("frames", [])) == 4, "compose-all must emit one instruction per locked frame")
    outputs = [frame["output"] for frame in result["frames"]]
    check(len(outputs) == len(set(outputs)), "composed outputs must remain unique")


def test_fail_closed_variants() -> None:
    base = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        bad_hash = copy.deepcopy(base)
        bad_hash["reference"]["sha256"] = "0" * 64
        path = write_variant(bad_hash, tmp, "bad-hash.json")
        code, result = run("validate", "--input", str(path), "--root", str(ASSET_ROOT))
        check(code != 0 and any(item.get("code") == "reference_sha256_mismatch" for item in result.get("errors", [])), "stale reference hash must block")

        shared_output = copy.deepcopy(base)
        shared_output["frames"][1]["output"] = shared_output["frames"][0]["output"]
        path = write_variant(shared_output, tmp, "shared-output.json")
        code, result = run("validate", "--input", str(path), "--root", str(ASSET_ROOT))
        check(code != 0 and any(item.get("code") == "duplicate_output" for item in result.get("errors", [])), "multiple frames targeting one PNG must block")

        pose_sheet = copy.deepcopy(base)
        pose_sheet["source_policy"]["allow_pose_sheet"] = True
        path = write_variant(pose_sheet, tmp, "pose-sheet.json")
        code, result = run("validate", "--input", str(path), "--root", str(ASSET_ROOT))
        check(code != 0 and any(item.get("code") == "unsafe_source_policy" for item in result.get("errors", [])), "pose-sheet generation policy must block")

        escape = copy.deepcopy(base)
        escape["frames"][0]["output"] = "../../escape.png"
        path = write_variant(escape, tmp, "escape.json")
        code, result = run("validate", "--input", str(path), "--root", str(ASSET_ROOT))
        check(code != 0 and any(item.get("code") == "path_escape" for item in result.get("errors", [])), "output path escape must block")

        post_resize = copy.deepcopy(base)
        post_resize["source_policy"]["allow_post_resize"] = True
        path = write_variant(post_resize, tmp, "post-resize.json")
        code, result = run("validate", "--input", str(path), "--root", str(ASSET_ROOT))
        check(code != 0 and any(item.get("code") == "unsafe_source_policy" for item in result.get("errors", [])), "post-generation resize must block")


def main() -> int:
    test_valid_lock_and_compose()
    test_fail_closed_variants()
    print("frame generation lock tests: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"frame generation lock tests: FAIL — {exc}", file=sys.stderr)
        raise
