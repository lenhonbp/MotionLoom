"""Cross-platform Dev Lab scene/task preparation and local serving helper."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
TASK_ARTIFACTS = (
    "task.json", "browser-review.json", "review.json", "execution-report.json",
    "handoff.json", "quality-report.json", "artifact-manifest.json",
    "issue-register.json", "decision-log.jsonl", "project-memory.json",
    "project-graph.json", "provenance.json", "capability-registry.json",
    "motion-ir.json", "replay-bundle.json", "semantic-lint-report.json",
    "continuity-report.json", "fix-plan.json", "visual-truth.json", "browser-observation.md",
)


def fail(message: str) -> "NoReturn":
    print(f"MotionLoom Dev Lab error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read JSON {path}: {exc}")
    return value if isinstance(value, dict) else {}


def safe_name(value: str, label: str) -> None:
    if not value or value in {".", ".."} or not SAFE_NAME.fullmatch(value):
        fail(f"{label} contains unsafe path characters: {value!r}")


def inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def prepare_scene(root: Path, lab: Path, scene: str, task_dir: Path | None) -> tuple[Path, Path | None, str | None]:
    safe_name(scene, "scene")
    scene_dir = (root / "src" / "output" / scene).resolve()
    if not scene_dir.is_dir():
        fail(f"scene directory not found: {scene_dir}; render the scene first")
    if not (scene_dir / "browser-review.json").is_file():
        fail("browser-review.json is required; run review-hook prepare first")
    lab_root = lab.resolve()
    destination = (lab_root / "public" / "scenes" / scene).resolve()
    if not inside(destination, (lab_root / "public" / "scenes").resolve()):
        fail("scene destination escaped Dev Lab public directory")
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(scene_dir, destination)

    task_destination: Path | None = None
    task_id: str | None = None
    if task_dir is not None:
        task_dir = task_dir.resolve()
        if not inside(task_dir, root.resolve()):
            fail("task bundle must be inside the MotionLoom repository")
        task = read_json(task_dir / "task.json")
        task_id = str(task.get("task_id") or "")
        safe_name(task_id, "task_id")
        task_destination = (lab_root / "public" / "tasks" / task_id).resolve()
        if not inside(task_destination, (lab_root / "public" / "tasks").resolve()):
            fail("task destination escaped Dev Lab public directory")
        if task_destination.exists():
            shutil.rmtree(task_destination)
        task_destination.mkdir(parents=True, exist_ok=True)
        for name in TASK_ARTIFACTS:
            source = task_dir / name
            if source.is_file():
                shutil.copy2(source, task_destination / name)
    return destination, task_destination, task_id


def serve(lab: Path, port: int) -> int:
    if not (lab / "public").is_dir():
        fail(f"Dev Lab public directory not found: {lab / 'public'}")
    print(f"== Dev Lab ready: http://localhost:{port}/ ==")
    return subprocess.run([sys.executable, "-m", "http.server", str(port), "--directory", str(lab / "public")], check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene")
    parser.add_argument("--task-dir")
    parser.add_argument("--lab-dir")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "3300")))
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    package_root = Path(__file__).resolve().parents[1]
    root = Path(os.environ.get("MOTIONLOOM_PROJECT_ROOT") or Path.cwd()).expanduser().resolve()
    lab = Path(args.lab_dir or os.environ.get("MOTIONLOOM_DEV_LAB") or package_root / "dev-lab").expanduser().resolve()
    task_dir = Path(args.task_dir).expanduser().resolve() if args.task_dir else None
    destination, task_destination, task_id = prepare_scene(root, lab, args.scene, task_dir)
    print(f"== Dev Lab scene prepared: {destination} ==")
    if task_destination:
        print(f"== Dev Lab task bundle prepared: {task_destination} (task_id={task_id}) ==")
    if args.prepare_only:
        return 0
    return serve(lab, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
