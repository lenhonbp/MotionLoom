"""Regression tests for scene/task browser-review candidate consistency."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_json(command: list[str], cwd: Path) -> tuple[int, dict]:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"raw": result.stdout, "stderr": result.stderr}
    return result.returncode, payload


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="motionloom-candidate-consistency-") as td:
        root = Path(td)
        scene_dir = root / "src/output/browser-review-smoke"
        task_dir = root / "artifacts/browser-review-smoke-task"
        scene_dir.parent.mkdir(parents=True)
        task_dir.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "src/output/browser-review-smoke", scene_dir)
        shutil.copytree(ROOT / "artifacts/browser-review-smoke-task", task_dir)

        scene_candidate_path = scene_dir / "browser-review.json"
        task_candidate_path = task_dir / "browser-review.json"
        scene_candidate = json.loads(scene_candidate_path.read_text(encoding="utf-8"))
        task_candidate = json.loads(task_candidate_path.read_text(encoding="utf-8"))

        # Deliberately introduce a foreign task candidate. The new contract
        # must reject it before any approval/PR decision.
        task_candidate["candidate_id"] = "foreign-candidate"
        task_candidate_path.write_text(json.dumps(task_candidate, indent=2) + "\n", encoding="utf-8")
        assert scene_candidate.get("candidate_id") != task_candidate.get("candidate_id")

        context_path = task_dir / "project-context.json"
        quality_command = [
            sys.executable,
            str(ROOT / "scripts/quality-gate.py"),
            "--root",
            str(root),
            "--scene",
            "browser-review-smoke",
            "--context",
            str(context_path),
            "--task-dir",
            str(task_dir),
            "--require-browser-review",
        ]
        quality_rc, quality_payload = run_json(quality_command, ROOT)
        quality_errors = " ".join(quality_payload.get("errors", [])) or quality_payload.get("raw", "")
        assert quality_rc != 0, quality_payload
        assert "scene/task browser-review candidate_id mismatch" in quality_errors, quality_payload

        # Align both candidate files completely, then make only expiry stale.
        expired_candidate = dict(task_candidate)
        expired_candidate["expires_at"] = "2020-01-01T00:00:00Z"
        scene_candidate_path.write_text(json.dumps(expired_candidate, indent=2) + "\n", encoding="utf-8")
        task_candidate_path.write_text(json.dumps(expired_candidate, indent=2) + "\n", encoding="utf-8")
        quality_rc, quality_payload = run_json(quality_command, ROOT)
        quality_errors = " ".join(quality_payload.get("errors", [])) or quality_payload.get("raw", "")
        assert quality_rc != 0, quality_payload
        assert "browser review candidate has expired" in quality_errors, quality_payload

        # Restore the canonical scene fixture, then introduce a foreign task
        # candidate and verify review-hook exposes the same failure.
        canonical_candidate = json.loads((ROOT / "src/output/browser-review-smoke/browser-review.json").read_text())
        scene_candidate_path.write_text(json.dumps(canonical_candidate, indent=2) + "\n", encoding="utf-8")
        foreign_task_candidate = dict(canonical_candidate)
        foreign_task_candidate["candidate_id"] = "foreign-candidate"
        task_candidate_path.write_text(json.dumps(foreign_task_candidate, indent=2) + "\n", encoding="utf-8")
        review_command = [
            sys.executable,
            str(ROOT / "scripts/review-hook.py"),
            "validate",
            "--task-dir",
            str(task_dir),
            "--root",
            str(root),
            "--require-approved",
        ]
        review_rc, review_payload = run_json(review_command, ROOT)
        review_errors = " ".join(review_payload.get("errors", []))
        assert review_rc != 0, review_payload
        assert "scene/task browser-review candidate_id mismatch" in review_errors, review_payload

    print("browser review consistency tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
