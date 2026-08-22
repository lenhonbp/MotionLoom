#!/usr/bin/env python3
"""Validate and compose provider-neutral instructions from a MotionLoom Frame Generation Lock.

The lock exists to keep independently generated animation frames on one identity,
canvas and geometry contract before deterministic post-generation preflight. This
tool does not call an image provider, modify assets, grant provenance authority or
mint user approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,95}$")
FRAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


def issue(code: str, message: str, path: str = "") -> dict[str, str]:
    return {"severity": "error", "code": code, "message": message, "path": path}


def load_document(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [issue("invalid_input", str(exc), str(path))]
    if not isinstance(value, dict):
        return None, [issue("invalid_document", "lock root must be an object", str(path))]
    return value, []


def inside(root: Path, value: str) -> tuple[Path | None, dict[str, str] | None]:
    candidate = (root / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, issue("path_escape", f"path escapes lock root: {value}", value)
    return candidate, None


def rect_inside(rect: dict[str, Any], width: int, height: int) -> bool:
    try:
        x, y = int(rect["x"]), int(rect["y"])
        w, h = int(rect["width"]), int(rect["height"])
    except (KeyError, TypeError, ValueError):
        return False
    return x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= width and y + h <= height


def validate(document: dict[str, Any], root: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    required = [
        "schema_version", "lock_id", "asset_identity", "action_id", "reference",
        "canvas", "geometry", "appearance", "source_policy", "frames", "postflight", "trust",
    ]
    for key in required:
        if key not in document:
            errors.append(issue("missing_field", f"required field is missing: {key}", key))

    if document.get("schema_version") not in {"0.1", "0.2"}:
        errors.append(issue("schema_version", "frame generation lock schema_version must be 0.1 or 0.2", "schema_version"))
    enhanced = document.get("schema_version") == "0.2"
    if enhanced:
        if not ID_RE.match(str(document.get("sequence_id", ""))):
            errors.append(issue("invalid_sequence_id", "schema_version 0.2 requires a safe sequence_id", "sequence_id"))
        forbidden = document.get("forbidden_action_ids")
        if not isinstance(forbidden, list) or not forbidden or any(not FRAME_RE.match(str(item)) for item in forbidden):
            errors.append(issue("invalid_forbidden_actions", "schema_version 0.2 requires a non-empty safe forbidden_action_ids array", "forbidden_action_ids"))
        elif str(document.get("action_id")) in {str(item) for item in forbidden}:
            errors.append(issue("expected_action_forbidden", "action_id must not also be forbidden", "forbidden_action_ids"))
        contract = document.get("action_contract") if isinstance(document.get("action_contract"), dict) else {}
        action_manifest = str(document.get("action_manifest", ""))
        if not action_manifest.lower().endswith(".json"):
            errors.append(issue("invalid_action_manifest", "schema_version 0.2 requires a JSON action_manifest path", "action_manifest"))
        else:
            _, manifest_error = inside(root, action_manifest)
            if manifest_error:
                manifest_error["path"] = "action_manifest"
                errors.append(manifest_error)
        for key in ("positive_cues", "negative_cues"):
            values = contract.get(key)
            if not isinstance(values, list) or not values or any(not isinstance(item, str) or not item.strip() for item in values):
                errors.append(issue("invalid_action_contract", f"action_contract.{key} must be a non-empty string array", f"action_contract.{key}"))
    if not ID_RE.match(str(document.get("lock_id", ""))):
        errors.append(issue("invalid_lock_id", "lock_id must use lowercase safe identifier characters", "lock_id"))
    if not FRAME_RE.match(str(document.get("action_id", ""))):
        errors.append(issue("invalid_action_id", "action_id must use lowercase safe identifier characters", "action_id"))

    canvas = document.get("canvas") if isinstance(document.get("canvas"), dict) else {}
    try:
        width, height = int(canvas.get("width", 0)), int(canvas.get("height", 0))
    except (TypeError, ValueError):
        width, height = 0, 0
    if width <= 0 or height <= 0:
        errors.append(issue("invalid_canvas", "canvas width and height must be positive integers", "canvas"))
    if canvas.get("color_space") not in {"srgb", "linear-srgb"}:
        errors.append(issue("invalid_color_space", "unsupported canvas color_space", "canvas.color_space"))
    if canvas.get("alpha_mode") not in {"straight", "premultiplied"}:
        errors.append(issue("invalid_alpha_mode", "unsupported canvas alpha_mode", "canvas.alpha_mode"))

    reference = document.get("reference") if isinstance(document.get("reference"), dict) else {}
    ref_value = str(reference.get("image", ""))
    ref_path, path_error = inside(root, ref_value) if ref_value else (None, issue("missing_reference", "reference.image is required", "reference.image"))
    if path_error:
        errors.append(path_error)
    expected_hash = str(reference.get("sha256", ""))
    if not SHA_RE.match(expected_hash):
        errors.append(issue("invalid_reference_sha256", "reference.sha256 must be 64 lowercase hex characters", "reference.sha256"))
    if ref_path is not None:
        try:
            actual_hash = hashlib.sha256(ref_path.read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(issue("reference_unreadable", str(exc), "reference.image"))
        else:
            if expected_hash and actual_hash != expected_hash:
                errors.append(issue("reference_sha256_mismatch", "reference bytes do not match the locked SHA-256", "reference.sha256"))
    if reference.get("role") not in {"identity_anchor", "accepted_frame_anchor"}:
        errors.append(issue("invalid_reference_role", "reference.role must be identity_anchor or accepted_frame_anchor", "reference.role"))

    geometry = document.get("geometry") if isinstance(document.get("geometry"), dict) else {}
    safe_rect = geometry.get("safe_rect") if isinstance(geometry.get("safe_rect"), dict) else {}
    if width > 0 and height > 0 and not rect_inside(safe_rect, width, height):
        errors.append(issue("invalid_safe_rect", "geometry.safe_rect must fit inside the locked canvas", "geometry.safe_rect"))
    target = geometry.get("target_alpha_bbox") if isinstance(geometry.get("target_alpha_bbox"), dict) else {}
    try:
        target_w, target_h = int(target.get("width", 0)), int(target.get("height", 0))
    except (TypeError, ValueError):
        target_w, target_h = 0, 0
    if target_w <= 0 or target_h <= 0 or (width > 0 and target_w > width) or (height > 0 and target_h > height):
        errors.append(issue("invalid_target_bbox", "target alpha bbox must be positive and fit inside the canvas", "geometry.target_alpha_bbox"))
    try:
        min_padding = int(geometry.get("min_padding_px", -1))
    except (TypeError, ValueError):
        min_padding = -1
    if min_padding < 0:
        errors.append(issue("invalid_padding", "geometry.min_padding_px must be non-negative", "geometry.min_padding_px"))
    tolerances = geometry.get("tolerances") if isinstance(geometry.get("tolerances"), dict) else {}
    for key in ("pivot_px", "footline_px", "bbox_width_px", "bbox_height_px"):
        try:
            value = float(tolerances.get(key, -1))
        except (TypeError, ValueError):
            value = -1
        if value < 0:
            errors.append(issue("invalid_tolerance", f"geometry.tolerances.{key} must be non-negative", f"geometry.tolerances.{key}"))

    source = document.get("source_policy") if isinstance(document.get("source_policy"), dict) else {}
    expected_source = {
        "isolated_frames": True,
        "max_frames_per_image": 1,
        "allow_pose_sheet": False,
        "allow_post_resize": False,
        "reuse_reference": True,
    }
    for key, expected in expected_source.items():
        if source.get(key) != expected:
            errors.append(issue("unsafe_source_policy", f"source_policy.{key} must be {expected!r}", f"source_policy.{key}"))

    appearance = document.get("appearance") if isinstance(document.get("appearance"), dict) else {}
    for key in ("preserve", "forbid"):
        values = appearance.get(key)
        if not isinstance(values, list) or not values or any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(issue("invalid_appearance_rule", f"appearance.{key} must be a non-empty string array", f"appearance.{key}"))
    pixel_art = appearance.get("pixel_art") if isinstance(appearance.get("pixel_art"), dict) else {}
    if pixel_art.get("enabled") is True and pixel_art.get("nearest_neighbor_only") is not True:
        errors.append(issue("unsafe_pixel_art_policy", "pixel-art locks require nearest_neighbor_only=true", "appearance.pixel_art.nearest_neighbor_only"))

    frames = document.get("frames") if isinstance(document.get("frames"), list) else []
    if len(frames) < 2:
        errors.append(issue("insufficient_frames", "a frame generation lock requires at least two frames", "frames"))
    seen_ids: set[str] = set()
    seen_outputs: set[str] = set()
    for index, frame in enumerate(frames):
        prefix = f"frames[{index}]"
        if not isinstance(frame, dict):
            errors.append(issue("invalid_frame", "frame must be an object", prefix))
            continue
        frame_id = str(frame.get("frame_id", ""))
        if not FRAME_RE.match(frame_id):
            errors.append(issue("invalid_frame_id", "frame_id must use lowercase safe identifier characters", f"{prefix}.frame_id"))
        if frame_id in seen_ids:
            errors.append(issue("duplicate_frame_id", f"duplicate frame_id: {frame_id}", f"{prefix}.frame_id"))
        seen_ids.add(frame_id)
        if not str(frame.get("pose", "")).strip():
            errors.append(issue("missing_pose", "frame pose instruction is required", f"{prefix}.pose"))
        output = str(frame.get("output", ""))
        if not output.lower().endswith(".png"):
            errors.append(issue("invalid_output", "frame output must be a PNG path", f"{prefix}.output"))
        if output in seen_outputs:
            errors.append(issue("duplicate_output", f"multiple frames target the same output: {output}", f"{prefix}.output"))
        seen_outputs.add(output)
        _, output_error = inside(root, output) if output else (None, issue("invalid_output", "frame output is required", f"{prefix}.output"))
        if output_error:
            output_error["path"] = f"{prefix}.output"
            errors.append(output_error)

    postflight = document.get("postflight") if isinstance(document.get("postflight"), dict) else {}
    geometry_value = str(postflight.get("frame_geometry", ""))
    _, geometry_error = inside(root, geometry_value) if geometry_value else (None, issue("missing_postflight", "postflight.frame_geometry is required", "postflight.frame_geometry"))
    if geometry_error:
        geometry_error["path"] = "postflight.frame_geometry"
        errors.append(geometry_error)

    trust = document.get("trust") if isinstance(document.get("trust"), dict) else {}
    if trust.get("review_only") is not True or trust.get("approval") is not False:
        errors.append(issue("invalid_trust_boundary", "generation locks must remain review_only with approval=false", "trust"))
    if trust.get("authority") not in {"ai_generated", "ai_assisted", "code_authored", "unknown"}:
        errors.append(issue("invalid_authority", "unsupported trust.authority", "trust.authority"))

    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "contract": "frame_generation_lock",
        "ready": not errors,
        "errors": errors,
        "warnings": [],
        "metrics": {
            "frame_count": len(frames),
            "canvas": {"width": width, "height": height},
            "lock_sha256": hashlib.sha256(canonical).hexdigest(),
            "reference_sha256": expected_hash or None,
            "isolated_frames": source.get("isolated_frames") is True,
        },
        "approval": False,
    }


def find_frame(document: dict[str, Any], frame_id: str) -> dict[str, Any] | None:
    for frame in document.get("frames", []):
        if isinstance(frame, dict) and frame.get("frame_id") == frame_id:
            return frame
    return None


def compose_instruction(document: dict[str, Any], frame: dict[str, Any]) -> str:
    canvas = document["canvas"]
    geometry = document["geometry"]
    appearance = document["appearance"]
    reference = document["reference"]
    target = geometry["target_alpha_bbox"]
    tolerances = geometry["tolerances"]
    safe = geometry["safe_rect"]
    pivot = geometry["pivot"]
    preserve = "; ".join(str(value).strip() for value in appearance["preserve"])
    forbid = "; ".join(str(value).strip() for value in appearance["forbid"])
    pixel_rule = " Use crisp nearest-neighbor pixel edges; do not resample or blur." if appearance.get("pixel_art", {}).get("enabled") else ""
    sequence_clause = f" Sequence {document['sequence_id']} is immutable across this action." if document.get("sequence_id") else ""
    contract = document.get("action_contract") if isinstance(document.get("action_contract"), dict) else {}
    positive_clause = "; ".join(str(item).strip() for item in contract.get("positive_cues", []))
    negative_clause = "; ".join(str(item).strip() for item in contract.get("negative_cues", []))
    action_clause = f" Positive action cues: {positive_clause}. Negative action cues: {negative_clause}. Forbidden competing actions: {', '.join(str(item) for item in document.get('forbidden_action_ids', []))}." if positive_clause and negative_clause else ""
    return (
        f"MotionLoom Frame Generation Lock {document['lock_id']} for action {document['action_id']}.{sequence_clause} "
        f"Use reference image {reference['image']} as the locked {reference['role']} with SHA-256 {reference['sha256']}. "
        f"Generate exactly ONE isolated source frame for {frame['frame_id']}; never create a pose sheet, contact sheet, collage, atlas, or multiple poses in one image. "
        f"Pose: {frame['pose']} "
        f"Canvas is exactly {canvas['width']} × {canvas['height']} pixels, {canvas['color_space']} with {canvas['alpha_mode']} alpha. "
        f"Keep the subject centered near x={geometry['center_x']}; pivot={pivot['x']},{pivot['y']} ({pivot['space']}); footline={geometry['footline_px']} px. "
        f"Keep all opaque pixels inside safe rect x={safe['x']}, y={safe['y']}, width={safe['width']}, height={safe['height']} and preserve at least {geometry['min_padding_px']} px transparent padding. "
        f"Target apparent alpha bounds are approximately {target['width']} × {target['height']} px; do not introduce whole-subject zoom drift beyond ±{tolerances['bbox_width_px']} px width or ±{tolerances['bbox_height_px']} px height, pivot drift beyond ±{tolerances['pivot_px']} px, or footline drift beyond ±{tolerances['footline_px']} px. "
        f"Preserve: {preserve}. Forbid: {forbid}.{pixel_rule} "
        f"Do not mirror, crop from a shared canvas, silently change camera/scale, or resize the generated frame afterward.{action_clause} "
        f"Return/save only the single PNG as {frame['output']}. This is review evidence only; generation success does not imply artist authorship, production eligibility, runtime approval, licence, or user approval."
    )


def compose(document: dict[str, Any], root: Path, frame_id: str | None = None) -> dict[str, Any]:
    validation = validate(document, root)
    if not validation["ready"]:
        return validation
    frames = document["frames"] if frame_id is None else [find_frame(document, frame_id)]
    if frame_id is not None and frames[0] is None:
        return {
            "contract": "frame_generation_lock",
            "ready": False,
            "errors": [issue("unknown_frame", f"frame_id not found in lock: {frame_id}", "frame_id")],
            "warnings": [],
            "metrics": validation["metrics"],
            "approval": False,
        }
    postflight = document["postflight"]["frame_geometry"]
    items = [
        {
            "frame_id": frame["frame_id"],
            "output": frame["output"],
            "instruction": compose_instruction(document, frame),
        }
        for frame in frames
        if isinstance(frame, dict)
    ]
    manifest_flag = f" --action-manifest {document['action_manifest']}" if document.get("action_manifest") else ""
    return {
        "contract": "frame_generation_lock",
        "ready": True,
        "lock_id": document["lock_id"],
        "action_id": document["action_id"],
        "sequence_id": document.get("sequence_id"),
        "forbidden_action_ids": document.get("forbidden_action_ids", []),
        "lock_sha256": validation["metrics"]["lock_sha256"],
        "reference_sha256": validation["metrics"]["reference_sha256"],
        "frames": items,
        "next_gate": f"motionloom frame-set-preflight --input {postflight} --root {root}{manifest_flag} --json",
        "approval": False,
    }


def emit(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if not result.get("ready"):
        print("frame generation lock: FAIL")
        for item in result.get("errors", []):
            print(f"ERROR {item.get('code')}: {item.get('message')}")
        return
    if "frames" not in result:
        print("frame generation lock: PASS")
        return
    for frame in result["frames"]:
        print(frame["instruction"])
        print()
    print(f"Next gate: {result['next_gate']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "compose", "compose-all"):
        command = sub.add_parser(name)
        command.add_argument("--input", required=True, help="frame-generation-lock JSON")
        command.add_argument("--root", default=".", help="project/asset root used to resolve paths")
        command.add_argument("--json", action="store_true", dest="as_json")
        if name == "compose":
            command.add_argument("--frame-id", required=True)
    args = parser.parse_args(argv)
    document, load_errors = load_document(Path(args.input))
    if load_errors or document is None:
        result = {"contract": "frame_generation_lock", "ready": False, "errors": load_errors, "warnings": [], "metrics": {}, "approval": False}
    else:
        root = Path(args.root).resolve()
        if args.command == "validate":
            result = validate(document, root)
        elif args.command == "compose":
            result = compose(document, root, args.frame_id)
        else:
            result = compose(document, root)
    emit(result, args.as_json)
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
