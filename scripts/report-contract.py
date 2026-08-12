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


def task_dirs(root: Path, scene: str) -> list[Path]:
    artifacts = root / "artifacts"
    if not artifacts.is_dir():
        return []
    matched = []
    for task_path in sorted(artifacts.glob("*/task.json")):
        task = read_json(task_path)
        if task.get("scene") == scene:
            matched.append(task_path.parent)
    return matched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenes-file", required=True)
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report_script = Path(__file__).resolve().with_name("report.py")
    scenes_file = Path(args.scenes_file)
    scenes = [line.strip() for line in scenes_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not scenes:
        print("No changed scenes; report completeness check skipped.")
        return 0

    missing: list[str] = []
    required = ("task.json", "execution-report.json", "artifact-manifest.json", "handoff.json", "issue-register.json")
    for scene in scenes:
        matched = task_dirs(root, scene)
        if not matched:
            missing.append(f"{scene}: no artifacts/<task-id>/task.json bound to scene")
            continue
        complete = [task_dir for task_dir in matched if all((task_dir / name).is_file() for name in required)]
        if not complete:
            missing.append(f"{scene}: incomplete task/execution-report/artifact-manifest/handoff/issue-register bundle")
            continue
        checked = False
        for task_dir in complete:
            result = subprocess.run(
                [sys.executable, str(report_script), "check", "--task-dir", str(task_dir)],
                cwd=root,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                checked = True
                break
        if not checked:
            missing.append(f"{scene}: semantic report check failed")

    if missing:
        print("FAIL: report/handoff contract is incomplete:")
        print("\n".join(f" - {item}" for item in missing))
        return 1
    print(f"Report contract passed for {len(scenes)} scene(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
