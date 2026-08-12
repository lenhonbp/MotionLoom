#!/usr/bin/env python3
"""
spec.py — Step 2 of the pipeline: Motion Spec generation & validation.

A motion spec is the signed contract between the understanding step and the
generation step. It binds the animation to the project context, picks the
framework per the selection matrix, and validates that the requested values
stay inside the performance budget (file size, frame count, layer count).

Usage:
    python3 src/core/spec.py generate <category> --duration 0.8 --loop \
        --context project-context.json --output motion-spec.md
    python3 src/core/spec.py validate motion-spec.md
"""

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

FRAMEWORK_MATRIX = {
    "ui-micro": ["framer-motion", "gsap"],
    "loading": ["lottie", "framer-motion", "css"],
    "hero-scene": ["lottie", "gsap", "threejs"],
    "character-body": ["lottie", "spine"],
    "icon-animation": ["lottie", "framer-motion", "css"],
    "scroll-linked": ["gsap", "framer-motion"],
    "data-viz": ["gsap", "framer-motion", "threejs"],
    "3d-scene": ["threejs"],
}

EASING_CANON = {
    "linear", "ease", "ease-in", "ease-out", "ease-in-out",
    "ease-in-sine", "ease-out-sine", "ease-in-out-sine",
    "ease-in-quad", "ease-out-quad", "ease-in-out-quad",
    "ease-in-cubic", "ease-out-cubic", "ease-in-out-cubic",
    "ease-in-expo", "ease-out-expo", "ease-in-out-expo",
    "ease-in-back", "ease-out-back", "ease-in-out-back",
    "spring", "anticipation", "overshoot",
}

PERF_BUDGET = {
    "max_file_kb": 300,          # dotLottie target for UI; 1500 for hero
    "max_layers": 80,
    "max_duration_hero_s": 8,
    "max_duration_ui_s": 2,
    "default_fps": 60,
    "rig_fps": 30,
}


def generate_spec(args) -> dict:
    context = {}
    ctx_path = Path(args.context).resolve() if args.context else None
    if ctx_path and ctx_path.exists():
        try:
            context = json.loads(ctx_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"error: invalid context JSON: {ctx_path}: {exc}")
    elif not args.allow_unbound:
        raise SystemExit(f"error: context not found: {ctx_path}; run analyze first (or pass --allow-unbound explicitly)")

    if args.category not in FRAMEWORK_MATRIX:
        raise SystemExit(f"error: unknown category '{args.category}'; choose one of: {', '.join(FRAMEWORK_MATRIX)}")
    duration = args.duration if args.duration is not None else _default_duration(args.category)
    fps = args.fps or (PERF_BUDGET["rig_fps"] if args.category == "character-body" else PERF_BUDGET["default_fps"])
    total_frames = round(duration * fps)

    stack_pref = (context.get("stack") or {}).get("framework")
    candidates = FRAMEWORK_MATRIX.get(args.category, ["lottie"])
    framework = args.framework or (stack_pref if stack_pref in candidates else candidates[0])

    easing = args.easing or context.get("motion_language", {}).get("recommendation") or "ease-in-out"
    if easing not in EASING_CANON:
        print(f"warning: easing '{easing}' not in canon; defaulting to ease-in-out", file=sys.stderr)
        easing = "ease-in-out"

    brand = context.get("brand", {})
    manifest_motion = ((context.get("manifest_overrides") or {}).get("motion") or {})
    spec = {
        "version": "1.0",
        "category": args.category,
        "framework": framework,
        "duration_s": duration,
        "fps": fps,
        "total_frames": total_frames,
        "loop": _default_loop(args.category) if args.loop is None else args.loop,
        "easing": easing,
        "camera": args.camera or ("push-in" if args.category == "hero-scene" else None),
        "theme": {
            "primary": brand.get("primary"),
            "accent": brand.get("accent"),
        },
        "performance": {
            "max_file_kb": PERF_BUDGET["max_file_kb"],
            "max_layers": PERF_BUDGET["max_layers"],
        },
        "source_binding": context.get("source_authority", ""),
        "context_binding": {
            "name": context.get("name"),
            "project_root": context.get("project_root"),
            "context_sha256": _sha256(ctx_path) if ctx_path and ctx_path.exists() else None,
        },
        "accessibility": {
            "reduced_motion": manifest_motion.get("reduced_motion", "respect-prefers-reduced-motion"),
        },
    }
    if args.interactivity:
        spec["interactivity"] = [i.strip() for i in args.interactivity.split(",")]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(f"motion-spec.json written -> {out}")
    return spec


def _default_duration(category: str) -> float:
    # CLI-first import: works when run directly without PYTHONPATH
    for extra in (".", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        if extra not in sys.path:
            sys.path.insert(0, extra)
    return _load_categories().get(category, {}).get("default_duration_s", 1.0)


def _default_loop(category: str) -> bool:
    return bool(_load_categories().get(category, {}).get("loop", False))


def _load_categories() -> dict:
    try:
        from core.analyzer import CATEGORIES  # noqa
        return CATEGORIES
    except ModuleNotFoundError:
        return {}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_spec(path: str, context_path: str | None = None) -> list:
    issues = []
    try:
        text = Path(path).read_text(encoding="utf-8")
        spec = json.loads(text) if text.strip().startswith("{") else _parse_md_spec(text)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"invalid motion spec: {exc}"]
    if not isinstance(spec, dict):
        return ["motion spec root must be a JSON object"]
    category = spec.get("category")
    framework = spec.get("framework")
    if category not in FRAMEWORK_MATRIX:
        issues.append(f"unknown category '{category}'")
    elif framework not in FRAMEWORK_MATRIX[category]:
        issues.append(f"framework '{framework}' is not allowed for category '{category}'")
    duration = spec.get("duration_s")
    fps = spec.get("fps")
    if not isinstance(duration, (int, float)) or isinstance(duration, bool):
        issues.append("duration_s must be a number")
        duration = 0
    if not isinstance(fps, (int, float)) or isinstance(fps, bool):
        issues.append("fps must be a number")
        fps = 0
    if duration <= 0:
        issues.append("duration_s must be greater than zero")
    if fps <= 0:
        issues.append("fps must be greater than zero")
    if duration > PERF_BUDGET["max_duration_ui_s"] and category not in ("hero-scene", "character-body", "3d-scene"):
        issues.append(f"duration {duration}s exceeds {PERF_BUDGET['max_duration_ui_s']}s budget for {category}")
    if fps not in (30, 60, 120):
        issues.append(f"fps {fps} is non-standard; prefer 30/60/120")
    expected_frames = round(duration * fps)
    if spec.get("total_frames") != expected_frames:
        issues.append(f"total_frames {spec.get('total_frames')} does not equal duration_s × fps ({expected_frames})")
    easing = spec.get("easing")
    if easing not in EASING_CANON:
        issues.append(f"easing '{easing}' not in canonical list")
    if not spec.get("theme", {}).get("primary"):
        issues.append("no brand primary color bound — run analyzer first")
    binding = spec.get("context_binding") or {}
    if not binding.get("name") or not binding.get("project_root") or not binding.get("context_sha256"):
        issues.append("missing context_binding — spec is not bound to a project context")
    if context_path:
        context_file = Path(context_path)
        if not context_file.exists():
            issues.append(f"context file not found: {context_file}")
        elif binding.get("context_sha256") != _sha256(context_file):
            issues.append("context hash mismatch — regenerate motion spec after project analysis changes")
    return issues


def _parse_md_spec(text: str) -> dict:
    def grab(key):
        m = re.search(rf"-\s*\*?{key}\*?\s*[:=]\s*(.+)", text)
        return m.group(1).strip() if m else None
    return {
        "category": grab("category") or "ui-micro",
        "framework": grab("framework") or "lottie",
        "duration_s": float(grab("duration") or 1.0),
        "fps": int(grab("fps") or 60),
        "loop": "true" in (grab("loop") or "false"),
        "easing": grab("easing") or "ease-in-out",
        "theme": {"primary": grab("primary")},
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    g = sub.add_parser("generate")
    g.add_argument("category")
    g.add_argument("--framework")
    g.add_argument("--duration", type=float)
    g.add_argument("--fps", type=int)
    g.add_argument("--loop", action="store_true")
    g.add_argument("--no-loop", dest="loop", action="store_false")
    g.add_argument("--easing")
    g.add_argument("--camera")
    g.add_argument("--interactivity")
    g.add_argument("--context", default="project-context.json")
    g.add_argument("--allow-unbound", action="store_true", help="allow generation without project-context.json (not accepted by quality gate)")
    g.add_argument("--output", default="motion-spec.json")
    g.set_defaults(loop=None)
    v = sub.add_parser("validate")
    v.add_argument("path")
    v.add_argument("--context")
    args = parser.parse_args()
    if args.cmd == "generate":
        generate_spec(args)
    elif args.cmd == "validate":
        issues = validate_spec(args.path, args.context)
        print("PASS — no issues" if not issues else "ISSUES:\n" + "\n".join(f"- {i}" for i in issues))
        sys.exit(1 if issues else 0)


if __name__ == "__main__":
    main()
