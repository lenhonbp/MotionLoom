"""Cross-platform runtime telemetry capture for MotionLoom.

This is the platform-neutral replacement for capture-runtime-telemetry.sh.
It intentionally shells out only to the repository's npm runtime:test script,
using pathlib and subprocess APIs that work on Ubuntu, macOS and Windows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


SCENE_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture and verify runtime telemetry")
    parser.add_argument("scene")
    parser.add_argument("task_dir")
    parser.add_argument("--max-age-days", type=int, default=1)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"capture-runtime-telemetry: invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"capture-runtime-telemetry: expected object in {path}")
    return value


def main() -> int:
    args = parse_args()
    if not SCENE_RE.fullmatch(args.scene):
        print(f"capture-runtime-telemetry: unsafe scene identifier: {args.scene}", file=sys.stderr)
        return 2
    if args.max_age_days < 0:
        print("capture-runtime-telemetry: --max-age-days must be non-negative", file=sys.stderr)
        return 2

    package_root = Path(__file__).resolve().parents[1]
    root = Path(os.environ.get("MOTIONLOOM_PROJECT_ROOT") or Path.cwd()).expanduser().resolve()
    task_dir = Path(args.task_dir).expanduser()
    task_dir = task_dir.resolve() if task_dir.is_absolute() else (root / task_dir).resolve()
    try:
        task_dir.relative_to(root)
    except ValueError:
        print("capture-runtime-telemetry: task directory must remain inside the project root", file=sys.stderr)
        return 2
    scene_dir = (root / "src" / "output" / args.scene).resolve()
    manifest_path = scene_dir / "manifest.json"
    task_path = task_dir / "task.json"
    if not manifest_path.is_file() or not task_path.is_file():
        print("capture-runtime-telemetry: missing scene manifest or task.json", file=sys.stderr)
        return 2

    manifest = load_json(manifest_path)
    task = load_json(task_path)
    source = manifest.get("file")
    task_id = task.get("task_id")
    if not isinstance(source, str) or not source or Path(source).is_absolute() or ".." in Path(source).parts:
        print("capture-runtime-telemetry: manifest.file must be a safe relative path", file=sys.stderr)
        return 2
    if not isinstance(task_id, str) or not task_id:
        print("capture-runtime-telemetry: task.json.task_id is required", file=sys.stderr)
        return 2

    source_path = (scene_dir / source).resolve()
    if scene_dir not in source_path.parents or not source_path.is_file():
        print("capture-runtime-telemetry: manifest source must remain inside scene directory", file=sys.stderr)
        return 2

    output_dir = task_dir / "runtime-adapters"
    env = os.environ.copy()
    env.update(
        {
            "RUNTIME_EVIDENCE_DIR": str(output_dir),
            "RUNTIME_SCENE": args.scene,
            "RUNTIME_TASK_ID": task_id,
            "RUNTIME_SOURCE_PATH": str(source_path),
            "RUNTIME_MANIFEST_PATH": str(manifest_path),
            "RUNTIME_MOTION_IR_PATH": str(task_dir / "motion-ir.json"),
            "MOTIONLOOM_RUNTIME_OUTPUT_ROOT": str(root),
        }
    )
    node = shutil.which("node") or ("node.exe" if os.name == "nt" else "node")
    runtime = subprocess.run(
        [node, str(package_root / "scripts" / "runtime-adapters.mjs")],
        cwd=root,
        env=env,
        check=False,
    )
    if runtime.returncode != 0:
        return runtime.returncode

    verifier = subprocess.run(
        [
            sys.executable,
            str(package_root / "scripts" / "evidence-verifier.py"),
            "--scene-dir",
            str(scene_dir),
            "--task-dir",
            str(task_dir),
            "--runtime-evidence",
            "runtime-adapters/runtime-evidence.json",
            "--max-age-days",
            str(args.max_age_days),
            "--output",
            str(task_dir / "evidence-verifier-report.json"),
        ],
        cwd=root,
        check=False,
    )
    return verifier.returncode


if __name__ == "__main__":
    raise SystemExit(main())
