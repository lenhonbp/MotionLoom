#!/usr/bin/env python3
"""Dogfood MotionLoom's published multi-frame contract from an isolated consumer project.

This creates a deterministic 12-frame transparent PNG sequence, drives the public
Frame Generation Lock and frame-set preflight through an installed MotionLoom
package, and records positive/negative evidence. It is contract evidence only;
it does not represent AI image quality, artist authorship, production approval,
runtime approval, or user approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import zlib
from pathlib import Path
from typing import Any


WIDTH = 64
HEIGHT = 64
ALPHA_BBOX = {"x": 18, "y": 10, "width": 28, "height": 41}
SAFE_RECT = {"x": 8, "y": 6, "width": 48, "height": 50}
PIVOT = {"x": 32, "y": 54, "space": "pixels"}
FOOTLINE = 51
FRAME_COUNT = 12


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def write_png(path: Path, phase: int) -> None:
    """Write a small connected pixel-art scout proxy with stable outer alpha bounds."""
    rgba = bytearray(WIDTH * HEIGHT * 4)

    def pixel(x: int, y: int, color: tuple[int, int, int, int]) -> None:
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            raise ValueError((x, y))
        index = (y * WIDTH + x) * 4
        rgba[index:index + 4] = bytes(color)

    def rect(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int, int]) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                pixel(x, y, color)

    cream = (244, 223, 180, 255)
    orange = (255, 122, 11, 255)
    dark = (23, 27, 37, 255)
    cyan = (8, 215, 239, 255)

    # Stable silhouette anchors lock exact x/y extrema across every frame.
    rect(24, 10, 39, 19, cream)
    rect(27, 20, 36, 36, cream)
    rect(21, 22, 26, 27, orange)
    rect(37, 22, 42, 27, orange)
    rect(28, 13, 35, 17, dark)
    rect(29, 14, 30, 16, cyan)
    rect(33, 14, 34, 16, cyan)

    # Outer extrema are deliberate, connected through arms/legs, and never drift.
    arm_shift = (-2, -1, 0, 1, 2, 1, 0, -1, -2, -1, 0, 1)[phase]
    rect(18, 25 + max(arm_shift, 0), 23, 31 + max(arm_shift, 0), dark)
    rect(40, 25 + max(-arm_shift, 0), 45, 31 + max(-arm_shift, 0), dark)
    rect(22, 27, 27, 29, dark)
    rect(36, 27, 41, 29, dark)

    stride = (-3, -2, -1, 0, 1, 2, 3, 2, 1, 0, -1, -2)[phase]
    left_x = 26 + stride
    right_x = 35 - stride
    rect(28, 35, 31, 39, dark)
    rect(33, 35, 36, 39, dark)
    rect(min(28, left_x), 39, max(31, left_x + 3), 46, cream)
    rect(min(33, right_x), 39, max(36, right_x + 3), 46, cream)
    rect(18, 47, 31, 50, dark)
    rect(32, 47, 45, 50, dark)

    # Phase marker keeps hashes distinct without changing geometry.
    marker_x = 28 + (phase % 8)
    pixel(marker_x, 33, orange)

    raw = bytearray()
    for y in range(HEIGHT):
        raw.append(0)
        start = y * WIDTH * 4
        raw.extend(rgba[start:start + WIDTH * 4])

    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
    payload += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_json(command: list[str], *, expect_success: bool = True) -> tuple[int, dict[str, Any], str]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"command did not emit JSON: {' '.join(command)}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        ) from exc
    if expect_success and completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}\n{completed.stderr}"
        )
    return completed.returncode, payload, completed.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motionloom-root", required=True, help="installed motionloom package root")
    parser.add_argument("--out", required=True, help="evidence/output directory")
    parser.add_argument("--expected-version", required=True, help="published MotionLoom version expected in the consumer")
    args = parser.parse_args()

    package_root = Path(args.motionloom_root).resolve()
    out_root = Path(args.out).resolve()
    consumer_root = out_root / "consumer-project"
    assets_root = consumer_root / "motion-assets"
    frames_root = assets_root / "generated"
    reference_root = assets_root / "reference"
    out_root.mkdir(parents=True, exist_ok=True)
    if consumer_root.exists():
        shutil.rmtree(consumer_root)
    frames_root.mkdir(parents=True, exist_ok=True)
    reference_root.mkdir(parents=True, exist_ok=True)

    package = json.loads((package_root / "package.json").read_text(encoding="utf-8"))
    package_version = str(package.get("version", ""))
    if package_version != args.expected_version:
        raise RuntimeError(f"consumer dogfood requires published motionloom@{args.expected_version}, got {package_version!r}")
    cli = package_root / "bin" / "motionloom.mjs"
    for required in [
        cli,
        package_root / "scripts" / "frame-generation-lock.py",
        package_root / "scripts" / "frame-set-preflight.py",
        package_root / "schemas" / "frame-generation-lock.schema.json",
    ]:
        if not required.is_file():
            raise RuntimeError(f"published package is missing required frame-generation asset: {required}")

    reference = reference_root / "scout-run-anchor.png"
    write_png(reference, 0)
    frames: list[dict[str, Any]] = []
    geometry_frames: list[dict[str, Any]] = []
    pose_names = [
        "contact-right",
        "down-right",
        "passing-right",
        "up-right",
        "flight-right",
        "settle-right",
        "contact-left",
        "down-left",
        "passing-left",
        "up-left",
        "flight-left",
        "settle-left",
    ]
    for index, pose in enumerate(pose_names):
        frame_id = f"run.{index:02d}"
        relative = Path("generated") / f"scout-run-{index:02d}.png"
        target = assets_root / relative
        write_png(target, index)
        frames.append({
            "frame_id": frame_id,
            "pose": f"12-frame run cycle {pose}; preserve the locked camera, scale, pivot and shared footline.",
            "output": str(relative).replace("\\", "/"),
        })
        geometry_frames.append({
            "frame_id": frame_id,
            "image": str(relative).replace("\\", "/"),
            "rect": {"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT},
            "alpha_bbox": ALPHA_BBOX,
            "pivot": PIVOT,
            "footline_px": FOOTLINE,
            "safe_rect": SAFE_RECT,
            "bleed_margin_px": 2,
            "sha256": sha256(target),
        })

    lock = {
        "schema_version": "0.1",
        "lock_id": "published-consumer-scout-run-12-v1",
        "asset_identity": "consumer/scout-v3-dogfood",
        "action_id": "run-12",
        "reference": {
            "image": "reference/scout-run-anchor.png",
            "sha256": sha256(reference),
            "role": "accepted_frame_anchor",
        },
        "canvas": {"width": WIDTH, "height": HEIGHT, "color_space": "srgb", "alpha_mode": "straight"},
        "geometry": {
            "center_x": 32,
            "pivot": PIVOT,
            "footline_px": FOOTLINE,
            "safe_rect": SAFE_RECT,
            "min_padding_px": 6,
            "target_alpha_bbox": {"width": ALPHA_BBOX["width"], "height": ALPHA_BBOX["height"]},
            "tolerances": {"pivot_px": 0, "footline_px": 0, "bbox_width_px": 0, "bbox_height_px": 0},
        },
        "appearance": {
            "preserve": [
                "same scout identity and connected silhouette",
                "same left-to-right camera and apparent scale",
                "same cream, orange, dark and cyan pixel-art palette",
            ],
            "forbid": [
                "second pose, contact sheet, collage or neighboring frame residue",
                "background, crop, mirror, camera drift or post-generation resize",
            ],
            "pixel_art": {"enabled": True, "nearest_neighbor_only": True},
        },
        "source_policy": {
            "isolated_frames": True,
            "max_frames_per_image": 1,
            "allow_pose_sheet": False,
            "allow_post_resize": False,
            "reuse_reference": True,
        },
        "frames": frames,
        "postflight": {"frame_geometry": "frame-geometry.json"},
        "trust": {"authority": "ai_generated", "review_only": True, "approval": False},
    }
    geometry = {
        "schema_version": "0.1",
        "asset_identity": "consumer/scout-v3-dogfood",
        "canvas": {"width": WIDTH, "height": HEIGHT, "color_space": "srgb", "alpha_mode": "straight"},
        "invariants": {
            "pivot_tolerance_px": 0,
            "footline_tolerance_px": 0,
            "bbox_drift_tolerance_px": 0,
            "min_alpha_pixels": 1,
            "allow_external_opaque_pixels": False,
        },
        "frames": geometry_frames,
    }
    lock_path = assets_root / "frame-generation-lock.json"
    geometry_path = assets_root / "frame-geometry.json"
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    geometry_path.write_text(json.dumps(geometry, indent=2) + "\n", encoding="utf-8")

    base = ["node", str(cli)]
    _, validation, _ = run_json(base + [
        "frame-generation-lock", "validate", "--input", str(lock_path), "--root", str(assets_root), "--json",
    ])
    if validation.get("ready") is not True or validation.get("approval") is not False:
        raise RuntimeError(f"frame-generation-lock validation did not pass safely: {validation}")
    if validation.get("metrics", {}).get("frame_count") != FRAME_COUNT:
        raise RuntimeError(f"lock frame count mismatch: {validation}")

    _, composed, _ = run_json(base + [
        "frame-generation-lock", "compose-all", "--input", str(lock_path), "--root", str(assets_root), "--json",
    ])
    composed_frames = composed.get("frames", [])
    if composed.get("ready") is not True or composed.get("approval") is not False or len(composed_frames) != FRAME_COUNT:
        raise RuntimeError(f"compose-all failed consumer contract: {composed}")
    outputs = [item.get("output") for item in composed_frames]
    if len(set(outputs)) != FRAME_COUNT:
        raise RuntimeError(f"compose-all reused output paths: {outputs}")
    for item in composed_frames:
        instruction = str(item.get("instruction", ""))
        if "exactly ONE isolated source frame" not in instruction or "never create a pose sheet" not in instruction:
            raise RuntimeError(f"composed instruction lost source-isolation policy: {item}")
        if str(item.get("output")) not in instruction:
            raise RuntimeError(f"composed instruction does not bind its unique output: {item}")

    _, preflight, _ = run_json(base + [
        "frame-set-preflight", "--input", str(geometry_path), "--root", str(assets_root), "--json",
    ])
    if preflight.get("ready") is not True or preflight.get("approval") is not False:
        raise RuntimeError(f"12-frame preflight failed: {preflight}")
    metrics = preflight.get("metrics", {})
    if metrics.get("unique_source_images") != FRAME_COUNT:
        raise RuntimeError(f"preflight did not observe 12 unique source images: {metrics}")

    # Negative probe: simulate the original failure mode by reusing a neighboring source image.
    bad_geometry = json.loads(json.dumps(geometry))
    bad_geometry["frames"][6]["image"] = bad_geometry["frames"][5]["image"]
    bad_geometry["frames"][6]["sha256"] = bad_geometry["frames"][5]["sha256"]
    bad_path = assets_root / "frame-geometry-shared-source-negative.json"
    bad_path.write_text(json.dumps(bad_geometry, indent=2) + "\n", encoding="utf-8")
    code, bad_result, _ = run_json(base + [
        "frame-set-preflight", "--input", str(bad_path), "--root", str(assets_root), "--json",
    ], expect_success=False)
    bad_codes = {item.get("code") for item in bad_result.get("errors", []) if isinstance(item, dict)}
    if code == 0 or bad_result.get("ready") is not False or "shared_source_image" not in bad_codes:
        raise RuntimeError(f"shared-source negative probe was not blocked: {bad_result}")

    report = {
        "status": "pass",
        "consumer_kind": "isolated-published-package-dogfood",
        "motionloom_version": package_version,
        "action": "run-12",
        "frame_count": FRAME_COUNT,
        "unique_source_images": metrics.get("unique_source_images"),
        "lock_ready": validation.get("ready"),
        "compose_all_ready": composed.get("ready"),
        "preflight_ready": preflight.get("ready"),
        "shared_source_negative_probe": "blocked",
        "shared_source_error_code": "shared_source_image",
        "approval": False,
        "authority": "ai_generated",
        "evidence_boundary": "Deterministic synthetic consumer evidence only; not visual-quality, artist, production, runtime, licence, or user approval evidence.",
        "consumer_root": str(consumer_root),
        "assets_root": str(assets_root),
    }
    (out_root / "consumer-dogfood-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
