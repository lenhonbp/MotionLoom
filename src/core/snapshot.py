#!/usr/bin/env python3
"""
snapshot.py — Step 5 support: render deterministic PNG snapshots of a scene.

For code-based scenes (GSAP / Framer Motion) it drives a headless Chromium
via the Dev Lab snapshot harness; for Lottie files it renders frames with
the dotlottie runtime in Node. Output lands in src/output/<scene>/snapshot/
as `frame-00.png`, `frame-50.png`, `frame-100.png` so visual diffs and PR
reviews are bit-exact reproducible.

Usage:
    python3 src/core/snapshot.py render <scene> --scene-dir src/output/<scene> --progress 0,50,100
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _fallback_placeholder_frames(scene_dir: Path, progress: list[int], framework: str) -> None:
    """Deterministic placeholder frames when the headless harness is not installed.
    Frames embed the scene id, progress and framework so diffs still detect change."""
    from PIL import Image, ImageDraw

    out = scene_dir / "snapshot"
    out.mkdir(parents=True, exist_ok=True)
    color = {"lottie": (245, 158, 11), "gsap": (59, 130, 246), "framer-motion": (34, 197, 94)}.get(
        framework, (140, 140, 160))
    for p in progress:
        img = Image.new("RGB", (320, 200), (20, 18, 26))
        d = ImageDraw.Draw(img)
        d.rectangle([40, 60, 40 + int(2.4 * p), 100], fill=color)
        d.text((20, 150), f"{scene_dir.name} @{p}% [{framework}] placeholder", fill=(200, 200, 210))
        img.save(out / f"frame-{p:02d}.png")
    (out / ".render-meta.json").write_text(json.dumps({
        "mode": "placeholder", "scene": scene_dir.name, "framework": framework,
        "progress": progress,
    }, indent=2) + "\n", encoding="utf-8")


def _write_render_meta(scene_dir: Path, scene: str, framework: str, progress: list[int], mode: str) -> None:
    out = scene_dir / "snapshot"
    out.mkdir(parents=True, exist_ok=True)
    (out / ".render-meta.json").write_text(json.dumps({
        "mode": mode, "scene": scene, "framework": framework, "progress": progress,
    }, indent=2) + "\n", encoding="utf-8")


def render_snapshots(scene: str, scene_dir: Path, progress: list[int], allow_placeholder: bool = False) -> dict:
    if not scene_dir.is_dir():
        raise SystemExit(f"error: scene directory not found: {scene_dir}")
    if any(p < 0 or p > 100 for p in progress):
        raise SystemExit("error: progress values must be between 0 and 100")
    manifest_path = scene_dir / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"error: scene manifest missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: invalid scene manifest: {exc}")

    framework = manifest.get("framework", "unknown")
    src = manifest.get("file", "")
    if not framework or framework == "unknown":
        raise SystemExit("error: manifest.framework is required")
    shots = []

    if framework in ("lottie", "dotlottie") and src.endswith((".lottie", ".json")):
        # Node path using @napi-rs/canvas + dotlottie (see scripts/render-node.mjs)
        runner = Path(__file__).parent.parent.parent / "scripts" / "render-node.mjs"
        source_path = (scene_dir / src).resolve()
        if not source_path.is_file() or scene_dir.resolve() not in source_path.parents:
            raise SystemExit(f"error: manifest.file must point to a file inside the scene directory: {src}")
        (scene_dir / "snapshot").mkdir(parents=True, exist_ok=True)
        for p in progress:
            out_png = scene_dir / "snapshot" / f"frame-{p:02d}.png"
            env = {**os.environ, "FRAME_PCT": str(p), "SRC": str(source_path), "OUT": str(out_png)}
            subprocess.run(["node", str(runner)], env=env, check=True,
                           capture_output=True)
            shots.append(str(out_png))
        _write_render_meta(scene_dir, scene, framework, progress, "runtime")
    else:
        # Headless Chromium via Dev Lab snapshot harness
        lab = Path(__file__).parent.parent.parent / "dev-lab"
        harness = lab / "scripts" / "snapshot.mjs"
        try:
            subprocess.run(
                ["node", str(harness), "--scene", scene,
                 "--progress", ",".join(map(str, progress)), "--out", str(scene_dir / "snapshot")],
                cwd=lab, check=True, capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            if not allow_placeholder:
                detail = getattr(exc, "stderr", b"")
                if isinstance(detail, bytes):
                    detail = detail.decode(errors="replace")
                raise SystemExit(
                    "error: runtime snapshot failed; start the Dev Lab and install its renderer "
                    f"dependencies before accepting this scene. {detail[-500:]}"
                )
            print("warn: runtime harness unavailable; writing explicitly marked placeholder frames", file=sys.stderr)
            _fallback_placeholder_frames(scene_dir, progress, framework)
        shots = sorted(str(p) for p in (scene_dir / "snapshot").glob("frame-*.png"))

    return {"scene": scene, "framework": framework, "shots": shots}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["render"])
    parser.add_argument("scene")
    parser.add_argument("--scene-dir", required=True)
    parser.add_argument("--progress", default="0,50,100")
    parser.add_argument("--allow-placeholder", action="store_true", help="diagnostic only; quality gate rejects these frames")
    args = parser.parse_args()
    result = render_snapshots(args.scene, Path(args.scene_dir), [int(x) for x in args.progress.split(",")], args.allow_placeholder)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
