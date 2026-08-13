#!/usr/bin/env python3
"""
MotionLoom render entrypoint.

Style contract: evidence-first, explicit runtime mode and no hidden approval
side effects. This is the cross-platform equivalent of render.sh and delegates
to the canonical Python snapshot renderer without requiring Bash.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


SCENE_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render MotionLoom runtime snapshots")
    parser.add_argument("scene")
    parser.add_argument("--repo", default=None, help="Repository root; defaults to the script parent")
    parser.add_argument("--progress", default="0,50,100")
    parser.add_argument("--allow-placeholder", action="store_true")
    args = parser.parse_args()

    if not SCENE_RE.fullmatch(args.scene):
        parser.error("scene id contains unsafe path characters")

    repo = Path(args.repo).expanduser().resolve() if args.repo else Path(__file__).resolve().parents[1]
    scene_dir = repo / "src" / "output" / args.scene
    if not scene_dir.is_dir():
        print(f"error: scene directory not found: {scene_dir}", file=sys.stderr)
        return 1

    try:
        progress = [int(value) for value in args.progress.split(",") if value.strip()]
    except ValueError:
        print("error: progress must be a comma-separated list of integers", file=sys.stderr)
        return 1

    if not progress or any(value < 0 or value > 100 for value in progress):
        print("error: progress values must be between 0 and 100", file=sys.stderr)
        return 1

    # Import by path-independent package layout. The repository root is added
    # only for this process; no cwd or shell-specific import assumptions.
    sys.path.insert(0, str(repo))
    from src.core.snapshot import render_snapshots  # pylint: disable=import-outside-toplevel

    result = render_snapshots(
        args.scene,
        scene_dir,
        progress,
        allow_placeholder=args.allow_placeholder or os.environ.get("ALLOW_PLACEHOLDER") == "1",
    )
    print(__import__("json").dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
