#!/usr/bin/env python3
"""Regression tests for Visual Truth provenance and review semantics."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/visual-truth.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    source = ROOT / "src/output/browser-review-smoke/animation.json"
    manifest = ROOT / "src/output/browser-review-smoke/manifest.json"
    baseline = ROOT / "src/output/browser-review-smoke/snapshot/frame-00.png"
    candidate = ROOT / "src/output/browser-review-smoke/snapshot/frame-100.png"
    runtime = ROOT / "artifacts/browser-review-smoke-task/runtime-adapters/runtime-evidence.json"
    motion_ir = ROOT / "artifacts/browser-review-smoke-task/motion-ir.json"
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="motionloom-visual-truth-") as td:
        output = Path(td) / "visual-truth.json"
        command = [
            sys.executable, str(SCRIPT), "build", "--root", str(ROOT), "--scene", "browser-review-smoke",
            "--baseline", str(baseline), "--candidate", str(candidate), "--source", str(source),
            "--manifest", str(manifest), "--runtime-evidence", str(runtime), "--motion-ir", str(motion_ir),
            "--task-id", "browser-review-smoke-task", "--output", str(output),
        ]
        built = subprocess.run(command, capture_output=True, text=True)
        if built.returncode != 0:
            errors.append(f"visual truth build failed: {built.stdout}{built.stderr}")
        else:
            report = json.loads(output.read_text(encoding="utf-8"))
            if report.get("status") != "review_required":
                errors.append("different real runtime frames must require review")
            if report.get("review_boundary", {}).get("approval") is not False:
                errors.append("visual truth build inferred approval")
            validate = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", "--root", str(ROOT), "--input", str(output),
                 "--scene", "browser-review-smoke", "--task-id", "browser-review-smoke-task",
                 "--source-sha256", digest(source), "--manifest-sha256", digest(manifest),
                 "--motion-ir-sha256", digest(motion_ir)],
                capture_output=True, text=True,
            )
            if validate.returncode != 0:
                errors.append(f"fresh visual truth validation failed: {validate.stdout}{validate.stderr}")
            stale = json.loads(output.read_text(encoding="utf-8"))
            stale["provenance"]["source_sha256"] = "0" * 64
            output.write_text(json.dumps(stale, indent=2) + "\n", encoding="utf-8")
            stale_result = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", "--root", str(ROOT), "--input", str(output),
                 "--source-sha256", digest(source)], capture_output=True, text=True,
            )
            if stale_result.returncode == 0 or "source_sha256" not in stale_result.stdout:
                errors.append("stale source binding was not rejected")
    # Keep this test explicit about the schema file being part of the package.
    schema = json.loads((ROOT / "schemas/visual-truth.schema.json").read_text(encoding="utf-8"))
    if schema.get("properties", {}).get("review_boundary", {}).get("properties", {}).get("approval", {}).get("const") is not False:
        errors.append("visual truth schema does not force approval=false")
    if errors:
        print("visual truth contract tests: FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("visual truth contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
