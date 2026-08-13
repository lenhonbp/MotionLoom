#!/usr/bin/env python3
"""Cross-platform project analyzer entrypoint.

This replaces the npm CLI's Bash-only analyzer path while preserving the
existing analyzer implementation and refreshing Project Memory when present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.analyzer import analyze  # noqa: E402
from project_memory_loader import refresh_if_present  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a host project and refresh MotionLoom Project Memory.")
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--output")
    parser.add_argument("--init-memory", action="store_true", help="Create .motionloom/project-memory.json if it does not exist")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"project root is not a directory: {root}")
    context_path = Path(args.output).expanduser().resolve() if args.output else root / "project-context.json"
    context = analyze(str(root))
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{context_path} written ({len(json.dumps(context, ensure_ascii=False))} bytes)")
    memory_result = refresh_if_present(root, context_path, initialize=args.init_memory)
    if memory_result:
        print(json.dumps({"project_memory": memory_result}, ensure_ascii=False))
    print("== MotionLoom analysis complete: review assumptions before generating ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
