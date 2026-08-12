#!/usr/bin/env python3
"""
analyzer.py — Step 1 of the MotionLoom pipeline: Project Understanding.

Reads a project repository (package.json, tailwind config, design tokens,
existing animation files, README) and emits `project-context.json`:
the single source of truth that all later steps (plan, source, generate)
must bind to. The agent is required to ground every generated animation
in this context, never in assumptions.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Category taxonomy — maps a user request to an animation class
# ---------------------------------------------------------------------------
CATEGORIES = {
    "ui-micro": {
        "description": "Buttons, toggles, loaders, hover/focus states, feedback toasts",
        "framework": "framer-motion",
        "default_duration_s": 0.3,
        "fps": 60,
        "loop": False,
    },
    "loading": {
        "description": "Spinners, skeletons, progress indicators",
        "framework": "lottie",
        "default_duration_s": 1.0,
        "fps": 60,
        "loop": True,
    },
    "hero-scene": {
        "description": "Full-viewport marketing scenes with camera motion",
        "framework": "lottie",
        "default_duration_s": 3.5,
        "fps": 60,
        "loop": True,
    },
    "character-body": {
        "description": "Avatar/character with skeleton rig: idle, walk, emote",
        "framework": "lottie",
        "default_duration_s": 1.5,
        "fps": 30,
        "loop": True,
    },
    "icon-animation": {
        "description": "Animated icons, path-draw reveals, state glyphs",
        "framework": "lottie",
        "default_duration_s": 0.8,
        "fps": 60,
        "loop": False,
    },
    "scroll-linked": {
        "description": "Parallax, progress-bound reveals, pin animations",
        "framework": "gsap",
        "default_duration_s": 1.0,
        "fps": 60,
        "loop": False,
    },
    "data-viz": {
        "description": "Chart transitions, counting numbers, graph builds",
        "framework": "gsap",
        "default_duration_s": 1.2,
        "fps": 60,
        "loop": False,
    },
    "3d-scene": {
        "description": "WebGL/Three.js scenes, model turntables, shaders",
        "framework": "threejs",
        "default_duration_s": 5.0,
        "fps": 60,
        "loop": True,
    },
}


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def detect_stack(project_root: Path, pkg: dict | None) -> dict:
    stack = {"framework": None, "react": False, "vue": False, "react_native": False, "native_web": False}
    deps = set()
    if pkg:
        deps.update(pkg.get("dependencies", {}).keys())
        deps.update(pkg.get("devDependencies", {}).keys())
    stack["react"] = bool({"react", "next", "framer-motion"} & deps)
    stack["vue"] = bool({"vue", "nuxt"} & deps)
    stack["react_native"] = bool({"react-native"} & deps)
    stack["native_web"] = bool({"lottie-web", "dotlottie-web", "gsap", "animejs"} & deps)
    if "framer-motion" in deps:
        stack["framework"] = "framer-motion"
    elif "gsap" in deps:
        stack["framework"] = "gsap"
    elif "dotlottie-web" in deps or "lottie-web" in deps or "@lottiefiles/react-lottie-player" in deps:
        stack["framework"] = "lottie"
    elif "three" in deps:
        stack["framework"] = "threejs"
    elif stack["react"]:
        stack["framework"] = "framer-motion"
    else:
        stack["framework"] = "gsap"
    return stack


def extract_brand_tokens(project_root: Path) -> dict:
    tokens = {"primary": None, "accent": None, "palette": [], "fonts": []}
    # Tailwind config
    for candidate in ["tailwind.config.js", "tailwind.config.ts", "tailwind.config.mjs"]:
        p = project_root / candidate
        if p.exists():
            text = p.read_text(encoding="utf-8")
            for m in re.finditer(r"primary:\s*['\"](#[0-9a-fA-F]{3,8})['\"]", text):
                tokens["primary"] = m.group(1).upper()
            for m in re.finditer(r"accent:\s*['\"](#[0-9a-fA-F]{3,8})['\"]", text):
                tokens["accent"] = m.group(1).upper()
    # package.json theme / CSS variables
    css_vars = {}
    css_files = list(project_root.rglob("*.css")) + list(project_root.rglob("*.scss"))
    for f in css_files[:20]:
        text = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{3,8})", text):
            css_vars[m.group(1)] = m.group(2).upper()
    for key in ("color-primary", "primary", "brand", "--primary"):
        if key in css_vars:
            tokens["primary"] = tokens["primary"] or css_vars[key]
    return tokens


def detect_motion_language(project_root: Path) -> dict:
    """Gather existing easing/duration conventions from the project."""
    easings = set()
    durations = set()
    for pattern in ("*.ts", "*.tsx", "*.js", "*.jsx", "*.css"):
        for f in project_root.rglob(pattern):
            if "node_modules" in f.parts:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if len(text) > 200_000:
                continue
            easings.update(re.findall(r"ease(in-out|in|out|linear)?", text))
            durations.update(re.findall(r"(?:duration|time)[^;]{0,20}?:\s*['\"]?([\d.]+(?:s|ms))", text, re.I))
    return {
        "easings_used": sorted(easings)[:10],
        "duration_patterns": sorted(durations)[:10],
        "recommendation": "ease-in-out" if "in-out" in easings else "ease-out",
    }


def find_existing_animations(project_root: Path) -> list:
    found = []
    for ext in ("*.lottie", "*.json", "*.riv"):
        for f in project_root.rglob(ext):
            rel = str(f.relative_to(project_root))
            if "node_modules" in rel or ".git" in rel:
                continue
            if ext == "*.json":
                text = f.read_text(encoding="utf-8", errors="ignore")[:200]
                if '"v"' not in text and "anim" not in text.lower():
                    continue
            found.append(rel)
            if len(found) >= 15:
                return found
    return found


def analyze(project_root: str) -> dict:
    root = Path(project_root).resolve()
    pkg = read_json(root / "package.json")
    manifest = read_json(root / "project-manifest.json")
    readme = (root / "README.md").read_text(encoding="utf-8", errors="ignore")[:3000] if (root / "README.md").exists() else ""

    brand = extract_brand_tokens(root)
    # project-manifest.json is the explicit project contract and therefore
    # overrides inferred values from Tailwind/CSS when both are present.
    manifest_brand = (manifest or {}).get("brand") or {}
    for key in ("primary", "accent"):
        if manifest_brand.get(key):
            brand[key] = str(manifest_brand[key]).upper()
    context = {
        "schema_version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "project_root": str(root),
        "name": (pkg or {}).get("name") or root.name,
        "description": (manifest or {}).get("description") or (pkg or {}).get("description") or "",
        "stack": detect_stack(root, pkg),
        "brand": brand,
        "motion_language": detect_motion_language(root),
        "existing_animations": find_existing_animations(root),
        "manifest_overrides": manifest or {},
        "source_authority": "project-manifest.json then assets/library/, never invented geometry",
    }
    return context


def main():
    parser = argparse.ArgumentParser(description="Analyze a host project and emit its binding context.")
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--output", help="Context path; defaults to <project_root>/project-context.json")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    if not root.is_dir():
        parser.error(f"project root is not a directory: {root}")
    ctx = analyze(str(root))
    out = Path(args.output).resolve() if args.output else root / "project-context.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ctx, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{out} written ({len(json.dumps(ctx))} bytes)")
    print(json.dumps(ctx, indent=2))


if __name__ == "__main__":
    main()
