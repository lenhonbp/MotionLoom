"""Validate task bundles bound to the scenes changed by a commit."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


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


def task_dirs(root: Path, scene: str) -> list[Path]:
    artifacts = root / "artifacts"
    if not artifacts.is_dir() or artifacts.is_symlink():
        return []
    resolved_artifacts = artifacts.resolve()
    matched = []
    for task_path in sorted(artifacts.glob("*/task.json")):
        if has_symlink_component(task_path, root):
            continue
        try:
            if not task_path.resolve().is_relative_to(resolved_artifacts):
                continue
        except (OSError, RuntimeError):
            continue
        task = read_json(task_path)
        if task.get("scene") == scene:
            matched.append(task_path.parent)
    return matched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenes-file", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--require-attestation", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report_script = Path(__file__).resolve().with_name("report.py")
    scenes_file = Path(args.scenes_file)
    scenes = [line.strip() for line in scenes_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not scenes:
        print("No changed scenes; report completeness check skipped.")
        return 0

    missing: list[str] = []
    selected: list[str] = []
    required = (
        "task.json",
        "execution-report.json",
        "artifact-manifest.json",
        "handoff.json",
        "issue-register.json",
        "semantic-lint-report.json",
        "semantic-lint-benchmark.json",
        "continuity-report.json",
        "fix-plan.json",
        "evidence-verifier-report.json",
    )
    if args.require_attestation:
        required = required + ("attestation.json", "trust-policy.json")
    attestation_verifier = Path(__file__).resolve().with_name("attestation-verifier.py")
    for scene in scenes:
        matched = task_dirs(root, scene)
        if not matched:
            missing.append(f"{scene}: no artifacts/<task-id>/task.json bound to scene")
            continue
        complete = [task_dir for task_dir in matched if all((task_dir / name).is_file() for name in required)]
        if not complete:
            missing.append(f"{scene}: incomplete task/report/P1 feedback bundle")
            continue
        passing: list[Path] = []
        for task_dir in complete:
            result = subprocess.run(
                [sys.executable, str(report_script), "check", "--task-dir", str(task_dir), "--root", str(root)],
                cwd=root,
                capture_output=True,
                text=True,
            )
            verification = read_json(task_dir / "evidence-verifier-report.json")
            task = read_json(task_dir / "task.json")
            verifier_ok = (
                verification.get("verified") is True
                and verification.get("approval") is False
                and verification.get("bindings", {}).get("scene") == scene
                and verification.get("bindings", {}).get("task_id") == task.get("task_id")
            )
            attestation_ok = True
            if args.require_attestation:
                attestation_result = subprocess.run(
                    [
                        sys.executable,
                        str(attestation_verifier),
                        "--attestation",
                        str(task_dir / "attestation.json"),
                        "--trust-policy",
                        str(task_dir / "trust-policy.json"),
                        "--expected-task-id",
                        str(task.get("task_id") or ""),
                        "--expected-scene",
                        scene,
                    ],
                    cwd=root,
                    capture_output=True,
                    text=True,
                )
                attestation_doc = read_json(task_dir / "attestation.json")
                verifier_doc = read_json(task_dir / "attestation-verifier-report.json")
                if not verifier_doc:
                    try:
                        verifier_doc = json.loads(attestation_result.stdout)
                    except json.JSONDecodeError:
                        verifier_doc = {}
                attestation_ok = (
                    attestation_result.returncode == 0
                    and verifier_doc.get("verified") is True
                    and verifier_doc.get("approval") is False
                    and attestation_doc.get("approval") is False
                    and verifier_doc.get("bindings", {}).get("scene") == scene
                    and verifier_doc.get("bindings", {}).get("task_id") == task.get("task_id")
                )
            if result.returncode == 0 and verifier_ok and attestation_ok:
                passing.append(task_dir)
        if not passing:
            missing.append(f"{scene}: semantic report check failed")
            continue
        state_rank = {"confirmed": 4, "ready_for_pr": 3, "validated": 2, "review_required": 1}
        ranked = sorted(
            passing,
            key=lambda path: (
                state_rank.get(str(read_json(path / "task.json").get("state")), 0),
                str(read_json(path / "task.json").get("updated_at", "")),
                str(read_json(path / "task.json").get("task_id", "")),
            ),
            reverse=True,
        )
        top_task = read_json(ranked[0] / "task.json")
        top_key = (state_rank.get(str(top_task.get("state")), 0), str(top_task.get("updated_at", "")))
        if sum(
            1
            for path in passing
            if (
                state_rank.get(str(read_json(path / "task.json").get("state")), 0),
                str(read_json(path / "task.json").get("updated_at", "")),
            )
            == top_key
        ) > 1:
            missing.append(f"{scene}: ambiguous passing task bundles share the same state and updated_at")
        else:
            selected.append(f"{scene}={top_task.get('task_id', ranked[0].name)}")

    if missing:
        print("FAIL: report/handoff contract is incomplete:")
        print("\n".join(f" - {item}" for item in missing))
        return 1
    suffix = f" Selected bundles: {', '.join(selected)}." if selected else ""
    print(f"Report contract passed for {len(scenes)} scene(s).{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
