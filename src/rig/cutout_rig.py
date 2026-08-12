#!/usr/bin/env python3
"""
cutout_rig.py — Body rigging engine for cutout character animation.

Builds a skeletal hierarchy from an authoritative flat SVG and emits
frame-interpolated pose keyframes suitable for
Lottie export or direct GSAP/CSS playback.

Hierarchy convention (parent-first rotation order):
    root (hip)
      spine -> chest -> head
      L-shoulder -> L-upper-arm -> L-forearm -> L-hand
      R-shoulder -> R-upper-arm -> R-forearm -> R-hand
      L-hip -> L-thigh -> L-shin -> L-foot
      R-hip -> R-thigh -> R-shin -> R-foot

Usage:
    python3 src/rig/cutout_rig.py build --input assets/library/avatar-base.svg --output rigged-avatar.svg
    python3 src/rig/cutout_rig.py pose rigged-avatar.svg --pose idle --duration 1.5 --fps 30 --out idle.json
"""

import argparse
import json
import math
import re
import uuid
from pathlib import Path

BONES = [
    "hip", "spine", "chest", "head",
    "l_shoulder", "l_upper_arm", "l_forearm", "l_hand",
    "r_shoulder", "r_upper_arm", "r_forearm", "r_hand",
    "l_hip", "l_thigh", "l_shin", "l_foot",
    "r_hip", "r_thigh", "r_shin", "r_foot",
]

# Default pose: degrees relative to parent (T-pose-ish standing)
DEFAULT_POSE = {
    "hip": 0, "spine": 0, "chest": 0, "head": 0,
    "l_shoulder": 10, "l_upper_arm": -8, "l_forearm": -12, "l_hand": 0,
    "r_shoulder": -10, "r_upper_arm": 8, "r_forearm": 12, "r_hand": 0,
    "l_hip": 0, "l_thigh": 2, "l_shin": -1, "l_foot": 0,
    "r_hip": 0, "r_thigh": -2, "r_shin": 1, "r_foot": 0,
}

# Preset motion clips: per-bone (start, end) offsets in degrees, additive to DEFAULT_POSE
CLIPS = {
    "idle": {
        "head": (-3, 3), "chest": (-1, 1), "l_upper_arm": (4, 4),
        "r_upper_arm": (-4, -4), "spine": (-1, 1),
    },
    "walk": {
        "l_thigh": (18, -18), "r_thigh": (-18, 18),
        "l_shin": (-22, 10), "r_shin": (10, -22),
        "l_upper_arm": (-24, 24), "r_upper_arm": (24, -24),
        "spine": (-3, 3), "head": (2, -2),
    },
    "wave": {
        "r_upper_arm": (-110, -110), "r_forearm": (10, 50),
        "r_hand": (0, 25), "chest": (0, 4), "head": (0, -6),
    },
    "nod": {"head": (0, 14)},
    "bounce": {"hip": (0, 6), "spine": (-2, 2), "l_upper_arm": (6, -6), "r_upper_arm": (-6, 6)},
}

EASE_IN_OUT = lambda t: t * t * (3 - 2 * t)  # smoothstep


def svg_group(bone: str, children_svg: str, pivot: str, shape: str) -> str:
    """Wrap a bone in a <g> with data-bone attribute and transform-origin pivot."""
    return (
        f'<g data-bone="{bone}" style="transform-origin:{pivot}" '
        f'transform="rotate({DEFAULT_POSE[bone]:.1f} 0 0)">{shape}{children_svg}</g>'
    )


def build_rig(args) -> str:
    if not args.input:
        if not args.allow_placeholder:
            raise SystemExit("error: --input authoritative SVG is required; use --allow-placeholder only for local prototyping")
        flat = _default_avatar_svg()
    elif not Path(args.input).exists():
        raise SystemExit(f"error: SVG asset not found: {args.input}")
    else:
        flat = Path(args.input).read_text(encoding="utf-8")

    # Prefer explicit data-part names; positional assignment is only a
    # compatibility fallback for legacy source art without names.
    parts = _split_svg_parts(flat)
    assigned = {name: shape for name, shape in parts if name}
    if not assigned:
        assigned = dict(zip(BONES, [shape for _, shape in parts]))

    def hierarchy(bone: str) -> str:
        kids = {
            "hip": ["spine", "l_hip", "r_hip"],
            "spine": ["chest"],
            "chest": ["head", "l_shoulder", "r_shoulder"],
            "l_shoulder": ["l_upper_arm"], "l_upper_arm": ["l_forearm"], "l_forearm": ["l_hand"],
            "r_shoulder": ["r_upper_arm"], "r_upper_arm": ["r_forearm"], "r_forearm": ["r_hand"],
            "l_hip": ["l_thigh"], "l_thigh": ["l_shin"], "l_shin": ["l_foot"],
            "r_hip": ["r_thigh"], "r_thigh": ["r_shin"], "r_shin": ["r_foot"],
        }
        children = "".join(hierarchy(c) for c in kids.get(bone, []))
        shape = assigned.get(bone, "")
        pivot = f"{args.pivot_x}px {args.pivot_y}px"
        return svg_group(bone, children, pivot, shape)

    inner = hierarchy("hip")
    doc = flat if "<g data-bone=" in flat else f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {args.width} {args.height}">
<g id="rig" data-rig="cutout-v1">{inner}</g></svg>'''
    out = Path(args.output)
    out.write_text(doc, encoding="utf-8")
    print(f"rigged avatar written -> {out} ({len(BONES)} bones)")
    return str(out)


def _split_svg_parts(svg_text: str) -> list:
    """Extract `(data-part, SVG fragment)` without changing the source geometry."""
    named = []
    # Covers self-closing primitives and named groups. It intentionally does
    # not claim arbitrary unlabelled nested geometry as a body part.
    pattern = re.compile(
        r'(<g\b[^>]*data-part=["\']([^"\']+)["\'][^>]*>.*?</g>|'
        r'<(?:path|circle|ellipse|rect|polygon)\b[^>]*data-part=["\']([^"\']+)["\'][^>]*/>)',
        re.S,
    )
    for match in pattern.finditer(svg_text):
        named.append((match.group(2) or match.group(3), match.group(1)))
    if named:
        return named
    legacy = re.findall(
        r'(<g\b[^>]*>.*?</g>|<(?:path|circle|ellipse|rect|polygon)\b[^>]*/>)',
        svg_text,
        re.S,
    )
    return [(None, fragment) for fragment in legacy]


def _default_avatar_svg() -> str:
    return f"""<!-- cutout avatar base — replace with authoritative art from assets/library/ -->
<circle data-part="head" cx="250" cy="90" r="42" fill="#2d2d3a"/>
<rect data-part="chest" x="208" y="140" width="84" height="96" rx="22" fill="#2d2d3a"/>
<rect data-part="l_upper_arm" x="178" y="148" width="26" height="78" rx="13" fill="#45455a"/>
<rect data-part="r_upper_arm" x="296" y="148" width="26" height="78" rx="13" fill="#45455a"/>
<rect data-part="l_forearm" x="176" y="228" width="22" height="70" rx="11" fill="#45455a"/>
<rect data-part="r_forearm" x="302" y="228" width="22" height="70" rx="11" fill="#45455a"/>
<rect data-part="l_thigh" x="216" y="238" width="30" height="84" rx="15" fill="#37374a"/>
<rect data-part="r_thigh" x="254" y="238" width="30" height="84" rx="15" fill="#37374a"/>
<rect data-part="l_shin" x="218" y="324" width="26" height="80" rx="13" fill="#37374a"/>
<rect data-part="r_shin" x="256" y="324" width="26" height="80" rx="13" fill="#37374a"/>
<ellipse data-part="l_foot" cx="231" cy="408" rx="24" ry="10" fill="#1f1f2e"/>
<ellipse data-part="r_foot" cx="269" cy="408" rx="24" ry="10" fill="#1f1f2e"/>"""


def pose(args) -> dict:
    rig = Path(args.rig).read_text(encoding="utf-8")
    clip = CLIPS.get(args.pose) or _parse_clip_file(args.pose)
    fps = args.fps or 30
    duration = args.duration or 1.5
    frames = max(2, round(duration * fps))

    keyframes = []
    for i in range(frames):
        t = EASE_IN_OUT(i / (frames - 1)) if frames > 1 else 0
        # ping-pong: forward half then back
        tt = 1 - abs(1 - 2 * (i / max(1, frames - 1)))
        pose_frame = dict(DEFAULT_POSE)
        for bone, (a, b) in clip.items():
            pose_frame[bone] = DEFAULT_POSE.get(bone, 0) + (a + (b - a) * tt)
        keyframes.append({"frame": i, "time_s": round(i / fps, 3), "angles": pose_frame})

    out = Path(args.out)
    out.write_text(json.dumps({
        "rig": str(args.rig), "clip": args.pose, "fps": fps,
        "duration_s": duration, "frames": len(keyframes), "keyframes": keyframes,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"pose clip written -> {out} ({len(keyframes)} frames)")
    return {"file": str(out), "frames": len(keyframes)}


def _parse_clip_file(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    b = sub.add_parser("build")
    b.add_argument("--input")
    b.add_argument("--output", default="rigged-avatar.svg")
    b.add_argument("--pivot-x", default=0)
    b.add_argument("--pivot-y", default=0)
    b.add_argument("--width", default=500)
    b.add_argument("--height", default=450)
    p = sub.add_parser("pose")
    p.add_argument("rig")
    p.add_argument("--pose", required=True)
    p.add_argument("--duration", type=float)
    p.add_argument("--fps", type=int)
    p.add_argument("--out", default="clip.json")
    b.add_argument("--allow-placeholder", action="store_true", help="allow generated geometric avatar for local prototyping only")
    args = parser.parse_args()
    if args.cmd == "build":
        build_rig(args)
    elif args.cmd == "pose":
        pose(args)


if __name__ == "__main__":
    main()
