#!/usr/bin/env python3
"""
MotionLoom confirm-to-PR entrypoint.

Style contract: review-first and side-effect explicit. OPEN_PR defaults to 0;
this module preserves the guarded shell workflow while using pathlib and
subprocess argument arrays so it works on Ubuntu, macOS and Windows.
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


def run(repo: Path, args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=repo,
        check=True,
        text=True,
        capture_output=capture,
    )


def git_output(repo: Path, args: list[str]) -> str:
    return run(repo, ["git", *args], capture=True).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and commit a reviewed MotionLoom scene")
    parser.add_argument("scene")
    parser.add_argument("title", nargs="?", default=None)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--context", default=None)
    parser.add_argument("--task-dir", default=None)
    parser.add_argument("--open-pr", action="store_true", help="Push and open a PR; default is local-only")
    args = parser.parse_args()

    if not SCENE_RE.fullmatch(args.scene) or args.scene in {".", ".."}:
        parser.error("scene id contains unsafe branch/path characters")

    repo = Path(args.repo).expanduser().resolve() if args.repo else Path(__file__).resolve().parents[1]
    scene_dir = repo / "src" / "output" / args.scene
    if not scene_dir.is_dir():
        print(f"error: scene directory not found: {scene_dir}", file=sys.stderr)
        return 1

    try:
        top_level = Path(git_output(repo, ["rev-parse", "--show-toplevel"])).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"error: repository is not a Git clone: {exc}", file=sys.stderr)
        return 1
    if top_level != repo:
        print(f"error: --repo must be the Git repository root ({top_level})", file=sys.stderr)
        return 1

    if not args.task_dir:
        print("error: --task-dir is required; user review must be persisted before PR", file=sys.stderr)
        return 1
    task_dir = Path(args.task_dir).expanduser()
    if not task_dir.is_absolute():
        task_dir = repo / task_dir
    task_dir = task_dir.resolve()
    try:
        task_dir.relative_to(repo)
    except ValueError:
        print("error: task directory must be inside the repository", file=sys.stderr)
        return 1

    task_path = task_dir / "task.json"
    try:
        task_data = json.loads(task_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read task.json: {exc}", file=sys.stderr)
        return 1
    if task_data.get("scene") != args.scene:
        print("error: task.json scene does not match requested scene", file=sys.stderr)
        return 1

    python = os.environ.get("MOTIONLOOM_PYTHON") or ("python" if os.name == "nt" else "python3")
    quality_args = [
        str(repo / "scripts" / "quality-gate.py"),
        "--scene", args.scene,
        "--context", args.context or str(repo / "project-context.json"),
        "--task-dir", str(task_dir),
        "--require-browser-review",
        "--require-visual-truth",
    ]
    print("== running context-bound quality gate ==")
    run(repo, [python, *quality_args])
    run(repo, [python, str(repo / "scripts" / "review-hook.py"), "validate", "--task-dir", str(task_dir), "--require-approved"])
    run(repo, [python, str(repo / "scripts" / "report.py"), "check", "--task-dir", str(task_dir)])

    branch = f"fix/{args.scene}"
    try:
        run(repo, ["git", "checkout", "-b", branch])
    except subprocess.CalledProcessError:
        run(repo, ["git", "checkout", branch])

    task_rel = task_dir.relative_to(repo)
    run(repo, ["git", "add", str(Path("src") / "output" / args.scene), str(task_rel)])
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo).returncode
    if staged == 0:
        print("error: no staged scene changes to commit", file=sys.stderr)
        return 1

    title = args.title or f"animation: scene '{args.scene}' (verified in Dev Lab)"
    commit_message = (
        f"feat(animation): scene '{args.scene}' — proven in Dev Lab\n\n"
        f"- motion-spec signed (see src/output/{args.scene}/motion-spec.json)\n"
        f"- snapshot frames: 0/50/100% in src/output/{args.scene}/snapshot/\n"
        "- context-bound quality gate: passed\n"
        f"- brand tokens bound from {args.context or 'project-context.json'}"
    )
    run(repo, ["git", "commit", "-m", commit_message])

    if not args.open_pr and os.environ.get("OPEN_PR") != "1":
        print(f"== committed to {branch} — OPEN_PR=0, push/open PR manually ==")
        return 0

    if shutil.which("gh") is None:
        print(f"== committed to {branch} — install gh CLI to open the PR ==")
        print(f"   git push origin {branch}")
        return 0

    run(repo, ["git", "push", "-u", "origin", branch])
    body = (
        f"## Scene: {args.scene}\n\n"
        "Verified in the Dev Lab (checklist + snapshot diffs attached).\n"
        "Framework, duration, easing, reduced-motion policy and theme tokens per the signed motion spec.\n\n"
        "### Snapshots\n| 0% | 50% | 100% |\n|---|---|---|\n"
        "| `snapshot/frame-00.png` | `snapshot/frame-50.png` | `snapshot/frame-100.png` |\n\n"
        "Ready to review — comment fixes in the Dev Lab or approve to merge."
    )
    run(repo, ["gh", "pr", "create", "--title", title, "--body", body])
    print(f"== PR opened for scene: {args.scene} ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
