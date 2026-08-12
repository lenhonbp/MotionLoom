#!/usr/bin/env python3
"""Create or refresh the required source_binding in a scene manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KINDS = {"project", "library", "generated", "fixture", "remote"}


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    bind = sub.add_parser("bind-source")
    bind.add_argument("--scene", required=True)
    bind.add_argument("--source", required=True)
    bind.add_argument("--kind", required=True, choices=sorted(KINDS))
    bind.add_argument("--authority", required=True)
    bind.add_argument("--license", required=True)
    bind.add_argument("--source-url")
    bind.add_argument("--attribution", default="")
    bind.add_argument("--manifest", default="manifest.json")
    args = parser.parse_args()

    scene_dir = (ROOT / "src" / "output" / args.scene).resolve()
    manifest_path = scene_dir / args.manifest
    source_path = (scene_dir / args.source).resolve()
    if not scene_dir.is_dir():
        raise SystemExit(f"scene directory not found: {scene_dir}")
    if not manifest_path.is_file():
        raise SystemExit(f"manifest not found: {manifest_path}")
    if not source_path.is_file() or scene_dir not in source_path.parents:
        raise SystemExit("source must be an existing file inside the scene directory")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    relative_source = source_path.relative_to(scene_dir).as_posix()
    manifest["file"] = relative_source
    binding = {
        "kind": args.kind,
        "source_path": relative_source,
        "authority": args.authority,
        "license": args.license,
        "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    }
    if args.source_url:
        binding["source_url"] = args.source_url
    if args.attribution:
        binding["attribution"] = args.attribution
    manifest["source_binding"] = binding
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "source_binding": binding}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
