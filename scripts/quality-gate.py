#!/usr/bin/env python3
"""Acceptance gate for a scene in src/output.

This gate is intentionally stricter than the exploratory Dev Lab: it requires
one project context, a JSON motion spec bound to that context, a manifest,
runtime snapshots (not placeholders), and a completed checklist.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from core.spec import validate_spec  # noqa: E402


def _load_validator():
    path = ROOT / "scripts" / "validate-lottie.py"
    loader = importlib.util.spec_from_file_location("validate_lottie", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}")


def validate_scene(scene_dir: Path, context_path: Path) -> list[str]:
    issues = []
    manifest_path = scene_dir / "manifest.json"
    spec_path = scene_dir / "motion-spec.json"
    if not manifest_path.exists():
        issues.append("missing manifest.json")
        return issues
    if not spec_path.exists():
        issues.append("missing motion-spec.json; markdown specs cannot prove context binding")
        return issues
    if not context_path.exists():
        issues.append(f"missing project context: {context_path}")
        return issues
    try:
        manifest = _json(manifest_path)
        spec = _json(spec_path)
    except ValueError as exc:
        return [str(exc)]

    issues.extend(validate_spec(str(spec_path), str(context_path)))
    context = _json(context_path)
    if spec.get("context_binding", {}).get("name") != context.get("name"):
        issues.append("spec context name does not match project-context.json")
    if spec.get("theme", {}).get("primary") != (context.get("brand") or {}).get("primary"):
        issues.append("spec primary color does not match project-context.json")
    if manifest.get("framework") and manifest["framework"] != spec.get("framework"):
        issues.append("manifest.framework does not match motion-spec.framework")
    if manifest.get("category") and manifest["category"] != spec.get("category"):
        issues.append("manifest.category does not match motion-spec.category")
    if not spec.get("source_binding"):
        issues.append("motion spec has no source_binding")
    if not (spec.get("accessibility") or {}).get("reduced_motion"):
        issues.append("motion spec has no reduced-motion policy")

    checks = manifest.get("checks")
    if not isinstance(checks, list) or not checks:
        issues.append("manifest.checks must contain the Dev Lab quality checklist")
    else:
        failed = [c.get("id", "unnamed") for c in checks if c.get("pass") is not True]
        if failed:
            issues.append(f"Dev Lab checklist has failing/unconfirmed checks: {', '.join(failed)}")

    snapshot_dir = scene_dir / "snapshot"
    required = [snapshot_dir / f"frame-{p:02d}.png" for p in (0, 50, 100)]
    for frame in required:
        if not frame.is_file() or frame.stat().st_size == 0:
            issues.append(f"missing snapshot frame: {frame.name}")
    meta_path = snapshot_dir / ".render-meta.json"
    if not meta_path.exists():
        issues.append("missing snapshot/.render-meta.json")
    else:
        try:
            meta = _json(meta_path)
            if meta.get("mode") != "runtime":
                issues.append("snapshot evidence is not runtime-rendered (placeholder is rejected)")
            if meta.get("scene") != scene_dir.name:
                issues.append("snapshot metadata scene mismatch")
        except ValueError as exc:
            issues.append(str(exc))

    source = manifest.get("file")
    if not source:
        issues.append("manifest.file is required")
    else:
        source_path = (scene_dir / source).resolve()
        if not source_path.is_file() or scene_dir.resolve() not in source_path.parents:
            issues.append("manifest.file must point to an existing file inside the scene directory")
        elif spec.get("framework") in ("lottie", "dotlottie") and source_path.suffix in (".json", ".lottie"):
            validator = _load_validator()
            issues.extend(validator.validate(source_path, spec, int(spec.get("performance", {}).get("max_layers", 80))))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scene")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--context", default="project-context.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    context = Path(args.context)
    if not context.is_absolute():
        context = root / context
    output_root = root / "src" / "output"
    scenes = [root / "src" / "output" / args.scene] if args.scene else sorted(p for p in output_root.iterdir() if p.is_dir()) if output_root.exists() else []
    if not scenes:
        print("QUALITY GATE: no scene outputs found")
        return 0
    failed = False
    for scene_dir in scenes:
        issues = validate_scene(scene_dir, context)
        if issues:
            failed = True
            print(f"REJECTED {scene_dir.name}:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"ACCEPTED {scene_dir.name}: context + spec + runtime snapshots + checklist")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
