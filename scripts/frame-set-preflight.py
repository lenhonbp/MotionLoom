#!/usr/bin/env python3
"""Fail-closed preflight for Agent-generated multi-frame source assets.

This wrapper reuses MotionLoom's deterministic frame-geometry measurements, then
adds generation-time rules that are intentionally stricter than a generic asset
inspection: source frames must be isolated canvases, scale drift is blocking,
and the measured alpha bounds must preserve the declared transparent guard band.

It never grants provenance authority, artistic approval or production approval.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ASSET_CONSISTENCY = ROOT / "scripts" / "asset-consistency.py"
ACTION_SEPARATION = ROOT / "scripts" / "action-separation.py"


def load_action_separation():
    spec = importlib.util.spec_from_file_location("motionloom_action_separation", ACTION_SEPARATION)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load action-separation.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_asset_consistency():
    spec = importlib.util.spec_from_file_location("motionloom_asset_consistency", ASSET_CONSISTENCY)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load asset-consistency.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AC = load_asset_consistency()
AS = load_action_separation()


def _error(code: str, message: str, path: str = "") -> dict[str, str]:
    return {"severity": "error", "code": code, "message": message, "path": path}


def _normalise_rect(value: dict[str, Any]) -> dict[str, int]:
    return {key: int(value[key]) for key in ("x", "y", "width", "height")}


def _contains(outer: dict[str, int], inner: dict[str, int]) -> bool:
    return (
        inner["x"] >= outer["x"]
        and inner["y"] >= outer["y"]
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"]
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"]
    )


def _shrink(rect: dict[str, int], margin: int) -> dict[str, int] | None:
    width = rect["width"] - 2 * margin
    height = rect["height"] - 2 * margin
    if width <= 0 or height <= 0:
        return None
    return {
        "x": rect["x"] + margin,
        "y": rect["y"] + margin,
        "width": width,
        "height": height,
    }


def validate(
    document: dict[str, Any],
    root: Path,
    allow_shared_source: bool = False,
    action_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = AC.validate_frame_geometry(document, root)
    errors = list(base.get("errors", []))
    warnings = list(base.get("warnings", []))
    frames = document.get("frames") if isinstance(document.get("frames"), list) else []
    canvas = document.get("canvas") if isinstance(document.get("canvas"), dict) else {}
    canvas_width = int(canvas.get("width", 0) or 0)
    canvas_height = int(canvas.get("height", 0) or 0)

    measurements_by_id = {
        str(item.get("frame_id")): item
        for item in base.get("metrics", {}).get("measurements", [])
        if isinstance(item, dict)
    }

    seen_images: dict[str, int] = {}
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        prefix = f"frames[{index}]"
        image_value = str(frame.get("image", ""))
        if image_value:
            if image_value in seen_images and not allow_shared_source:
                errors.append(
                    _error(
                        "shared_source_image",
                        f"generated source frame reuses image {image_value!r}; use one isolated image per source frame",
                        f"{prefix}.image",
                    )
                )
            seen_images[image_value] = index

        rect = frame.get("rect") if isinstance(frame.get("rect"), dict) else None
        if rect and canvas_width > 0 and canvas_height > 0 and not allow_shared_source:
            expected = {"x": 0, "y": 0, "width": canvas_width, "height": canvas_height}
            try:
                actual = _normalise_rect(rect)
            except (KeyError, TypeError, ValueError):
                actual = {}
            if actual != expected:
                errors.append(
                    _error(
                        "non_isolated_source",
                        f"generated source frame rect must own the full {canvas_width}x{canvas_height} canvas before atlas packing",
                        f"{prefix}.rect",
                    )
                )

        frame_id = str(frame.get("frame_id", ""))
        measurement = measurements_by_id.get(frame_id)
        safe_rect_value = frame.get("safe_rect") if isinstance(frame.get("safe_rect"), dict) else None
        if measurement and safe_rect_value:
            try:
                safe_rect = _normalise_rect(safe_rect_value)
                bbox = _normalise_rect(measurement["alpha_bbox"])
                margin = int(frame.get("bleed_margin_px", 0) or 0)
                guarded = _shrink(safe_rect, margin)
            except (KeyError, TypeError, ValueError):
                guarded = None
                bbox = None
            if guarded is None:
                errors.append(
                    _error(
                        "invalid_guard_band",
                        "safe_rect is too small for the declared bleed_margin_px",
                        f"{prefix}.bleed_margin_px",
                    )
                )
            elif bbox is not None and not _contains(guarded, bbox):
                errors.append(
                    _error(
                        "guard_band_violation",
                        f"measured alpha bbox {bbox} leaves less than {frame.get('bleed_margin_px', 0)}px inside safe_rect {safe_rect}",
                        f"{prefix}.safe_rect",
                    )
                )

    action_result = None
    if action_manifest is not None:
        action_result = AS.validate_manifest(action_manifest, root)
        errors.extend(action_result.get("errors", []))
        warnings.extend(action_result.get("warnings", []))

    remaining_warnings: list[dict[str, Any]] = []
    for item in warnings:
        if isinstance(item, dict) and item.get("code") == "bbox_drift":
            promoted = dict(item)
            promoted["severity"] = "error"
            promoted["message"] = f"{promoted.get('message', 'bbox drift exceeds tolerance')}; generated frame scale drift blocks preflight"
            errors.append(promoted)
        else:
            remaining_warnings.append(item)

    return {
        "contract": "generated_frame_set_preflight",
        "ready": not errors,
        "errors": errors,
        "warnings": remaining_warnings,
        "metrics": {
            **base.get("metrics", {}),
            "isolated_source_required": not allow_shared_source,
            "unique_source_images": len(seen_images),
            "action_manifest": action_result.get("metrics") if action_result else None,
        },
        "approval": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="frame-geometry contract JSON")
    parser.add_argument("--root", default=".", help="root used to resolve frame paths")
    parser.add_argument("--allow-shared-source", action="store_true", help="for imported/shared canvases only; not recommended for generated source frames")
    parser.add_argument("--action-manifest", help="action-sequence manifest; validates frame envelopes and action separation")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    try:
        document = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "contract": "generated_frame_set_preflight",
            "ready": False,
            "errors": [_error("invalid_input", str(exc), args.input)],
            "warnings": [],
            "metrics": {},
            "approval": False,
        }
    else:
        if not isinstance(document, dict):
            result = {
                "contract": "generated_frame_set_preflight",
                "ready": False,
                "errors": [_error("invalid_input", "contract root must be an object", args.input)],
                "warnings": [],
                "metrics": {},
                "approval": False,
            }
        else:
            action_manifest = None
            if args.action_manifest:
                try:
                    action_manifest = json.loads(Path(args.action_manifest).read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    result = {
                        "contract": "generated_frame_set_preflight",
                        "ready": False,
                        "errors": [_error("invalid_action_manifest", str(exc), args.action_manifest)],
                        "warnings": [],
                        "metrics": {},
                        "approval": False,
                    }
                    action_manifest = None
                if action_manifest is not None and not isinstance(action_manifest, dict):
                    result = {
                        "contract": "generated_frame_set_preflight",
                        "ready": False,
                        "errors": [_error("invalid_action_manifest", "action manifest root must be an object", args.action_manifest)],
                        "warnings": [],
                        "metrics": {},
                        "approval": False,
                    }
                    action_manifest = None
            if action_manifest is not None or not args.action_manifest:
                result = validate(document, Path(args.root).resolve(), args.allow_shared_source, action_manifest)

    if args.as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"generated frame-set preflight: {'PASS' if result['ready'] else 'FAIL'}")
        for item in result.get("errors", []):
            print(f"ERROR {item.get('code')}: {item.get('message')}")
        for item in result.get("warnings", []):
            print(f"WARN  {item.get('code')}: {item.get('message')}")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
