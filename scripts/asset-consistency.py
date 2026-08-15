#!/usr/bin/env python3
"""
MotionLoom Asset Consistency Compiler.

Style: Timeline Desk — deterministic measurements first, explicit evidence
second, heuristic warnings last. This tool never grants provenance authority,
production eligibility or human approval.

The analyzer intentionally uses only the Python standard library. It reads
uncompressed PNG pixels, validates contract geometry, emits machine-readable
evidence, and exits non-zero for deterministic contract violations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    path: str = ""


class PNGError(ValueError):
    pass


class PNGImage:
    """Small deterministic PNG reader for the formats needed by contracts."""

    def __init__(self, path: Path):
        self.path = path
        self.width = 0
        self.height = 0
        self.bit_depth = 0
        self.color_type = 0
        self._rows: list[bytes] = []
        self._rgba_cache: list[tuple[int, int, int, int]] | None = None
        self._palette = b""
        self._transparency = b""
        self._read()

    def _read(self) -> None:
        data = self.path.read_bytes()
        if not data.startswith(PNG_SIGNATURE):
            raise PNGError(f"not a PNG file: {self.path}")
        offset = len(PNG_SIGNATURE)
        idat = bytearray()
        interlace = 0
        while offset < len(data):
            if offset + 12 > len(data):
                raise PNGError(f"truncated PNG chunk: {self.path}")
            length = struct.unpack(">I", data[offset : offset + 4])[0]
            chunk_type = data[offset + 4 : offset + 8]
            start = offset + 8
            end = start + length
            if end + 4 > len(data):
                raise PNGError(f"truncated PNG data: {self.path}")
            payload = data[start:end]
            offset = end + 4
            if chunk_type == b"IHDR":
                if length != 13:
                    raise PNGError("invalid IHDR length")
                self.width, self.height, self.bit_depth, self.color_type, compression, filtering, interlace = struct.unpack(
                    ">IIBBBBB", payload
                )
                if compression != 0 or filtering != 0 or interlace != 0:
                    raise PNGError("only non-interlaced baseline PNG is supported")
                if self.bit_depth != 8 or self.color_type not in (0, 2, 3, 4, 6):
                    raise PNGError("only 8-bit grayscale/RGB/RGBA PNG is supported")
            elif chunk_type == b"IDAT":
                idat.extend(payload)
            elif chunk_type == b"PLTE":
                self._palette = payload
            elif chunk_type == b"tRNS":
                self._transparency = payload
            elif chunk_type == b"IEND":
                break
        if not self.width or not self.height or not idat:
            raise PNGError(f"PNG is missing IHDR or IDAT: {self.path}")
        raw = zlib.decompress(bytes(idat))
        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[self.color_type]
        stride = self.width * channels
        expected = self.height * (stride + 1)
        if len(raw) != expected:
            raise PNGError(f"unexpected decompressed PNG length for {self.path}")
        rows: list[bytes] = []
        previous = bytearray(stride)
        cursor = 0
        for _ in range(self.height):
            filter_type = raw[cursor]
            cursor += 1
            filtered = bytearray(raw[cursor : cursor + stride])
            cursor += stride
            current = bytearray(stride)
            for i, value in enumerate(filtered):
                left = current[i - channels] if i >= channels else 0
                up = previous[i]
                up_left = previous[i - channels] if i >= channels else 0
                if filter_type == 0:
                    result = value
                elif filter_type == 1:
                    result = (value + left) & 0xFF
                elif filter_type == 2:
                    result = (value + up) & 0xFF
                elif filter_type == 3:
                    result = (value + ((left + up) // 2)) & 0xFF
                elif filter_type == 4:
                    result = (value + _paeth(left, up, up_left)) & 0xFF
                else:
                    raise PNGError(f"unsupported PNG filter type {filter_type}")
                current[i] = result
            rows.append(bytes(current))
            previous = current
        self._rows = rows

    def rgba(self) -> list[tuple[int, int, int, int]]:
        if self._rgba_cache is not None:
            return self._rgba_cache
        result: list[tuple[int, int, int, int]] = []
        for row in self._rows:
            if self.color_type == 6:
                result.extend(tuple(row[i : i + 4]) for i in range(0, len(row), 4))
            elif self.color_type == 4:
                result.extend((v, v, v, row[i + 1]) for i, v in enumerate(row[::2]))
            elif self.color_type == 2:
                result.extend((row[i], row[i + 1], row[i + 2], 255) for i in range(0, len(row), 3))
            elif self.color_type == 3:
                if len(self._palette) % 3 != 0:
                    raise PNGError(f"invalid PNG palette: {self.path}")
                for palette_index in row:
                    offset = palette_index * 3
                    if offset + 2 >= len(self._palette):
                        raise PNGError(f"PNG palette index out of range: {self.path}")
                    alpha = self._transparency[palette_index] if palette_index < len(self._transparency) else 255
                    result.append((self._palette[offset], self._palette[offset + 1], self._palette[offset + 2], alpha))
            else:
                result.extend((v, v, v, 255) for v in row)
        self._rgba_cache = result
        return result

    def alpha_bbox(self, threshold: int = 1, rect: dict[str, Any] | None = None) -> dict[str, int] | None:
        bounds = _normalise_rect(rect, self.width, self.height) if rect else {"x": 0, "y": 0, "width": self.width, "height": self.height}
        pixels = self.rgba()
        min_x, min_y = self.width, self.height
        max_x, max_y = -1, -1
        for y in range(bounds["y"], bounds["y"] + bounds["height"]):
            for x in range(bounds["x"], bounds["x"] + bounds["width"]):
                if pixels[y * self.width + x][3] >= threshold:
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x), max(max_y, y)
        if max_x < 0:
            return None
        return {"x": min_x, "y": min_y, "width": max_x - min_x + 1, "height": max_y - min_y + 1}

    def alpha_count(self, threshold: int = 1, rect: dict[str, Any] | None = None) -> int:
        bounds = _normalise_rect(rect, self.width, self.height) if rect else {"x": 0, "y": 0, "width": self.width, "height": self.height}
        pixels = self.rgba()
        return sum(
            1
            for y in range(bounds["y"], bounds["y"] + bounds["height"])
            for x in range(bounds["x"], bounds["x"] + bounds["width"])
            if pixels[y * self.width + x][3] >= threshold
        )

    def opaque_outside(self, rect: dict[str, Any], threshold: int = 1) -> int:
        bounds = _normalise_rect(rect, self.width, self.height)
        pixels = self.rgba()
        return sum(
            1
            for y in range(self.height)
            for x in range(self.width)
            if pixels[y * self.width + x][3] >= threshold
            and not (bounds["x"] <= x < bounds["x"] + bounds["width"] and bounds["y"] <= y < bounds["y"] + bounds["height"])
        )

    def edge_difference(self, axis: str) -> float:
        pixels = self.rgba()
        if axis == "x":
            pairs = ((pixels[y * self.width], pixels[y * self.width + self.width - 1]) for y in range(self.height))
        else:
            pairs = ((pixels[x], pixels[(self.height - 1) * self.width + x]) for x in range(self.width))
        differences = [sum(abs(a[i] - b[i]) for i in range(4)) / (4 * 255) for a, b in pairs]
        return sum(differences) / len(differences) if differences else 0.0


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def _normalise_rect(value: dict[str, Any] | None, width: int, height: int) -> dict[str, int]:
    value = value or {"x": 0, "y": 0, "width": width, "height": height}
    return {key: int(value[key]) for key in ("x", "y", "width", "height")}


def _rect_inside(rect: dict[str, int], width: int, height: int) -> bool:
    return rect["x"] >= 0 and rect["y"] >= 0 and rect["width"] > 0 and rect["height"] > 0 and rect["x"] + rect["width"] <= width and rect["y"] + rect["height"] <= height


def _rect_overlap(a: dict[str, int], b: dict[str, int]) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def _close(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def _load_document(path: Path) -> tuple[dict[str, Any] | None, list[Issue]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [Issue("error", "invalid_json", str(exc), str(path))]
    if not isinstance(value, dict):
        return None, [Issue("error", "invalid_document", "contract root must be an object", str(path))]
    return value, []


def _required(document: dict[str, Any], keys: Iterable[str]) -> list[Issue]:
    return [Issue("error", "missing_field", f"required field is missing: {key}", key) for key in keys if key not in document]


def _resolve(root: Path, path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else root / path


def validate_identity(document: dict[str, Any]) -> dict[str, Any]:
    issues = _required(document, ("schema_version", "asset_id", "asset_kind", "identity", "derivation"))
    if document.get("schema_version") != "0.1":
        issues.append(Issue("error", "schema_version", "asset identity schema_version must be 0.1", "schema_version"))
    identity = document.get("identity") if isinstance(document.get("identity"), dict) else {}
    derivation = document.get("derivation") if isinstance(document.get("derivation"), dict) else {}
    issues.extend(_required(identity, ("subject_id", "reference_hashes", "camera", "coordinate_system", "scale", "pivot", "palette_lock")))
    issues.extend(_required(derivation, ("origin", "source_refs")))
    generator = derivation.get("generator") if isinstance(derivation.get("generator"), dict) else {}
    origin = derivation.get("origin")
    if origin not in {"ai_generated", "ai_assisted", "ai_assisted_human_reviewed", "artist_authored", "code_authored", "unknown"}:
        issues.append(Issue("error", "invalid_origin", "asset origin is not a supported provenance tier", "derivation.origin"))
    if origin in {"ai_generated", "ai_assisted", "ai_assisted_human_reviewed"}:
        issues.extend(_required(generator, ("model", "task_id", "prompt_hash")))
    if origin == "unknown":
        issues.append(Issue("error", "unknown_origin", "unknown asset origin is blocked", "derivation.origin"))
    return _result("asset_identity", issues, {"asset_id": document.get("asset_id"), "origin": derivation.get("origin")})


def validate_action_set(document: dict[str, Any]) -> dict[str, Any]:
    issues = _required(document, ("schema_version", "asset_identity", "actions", "invariants"))
    if document.get("schema_version") != "0.1":
        issues.append(Issue("error", "schema_version", "action set schema_version must be 0.1", "schema_version"))
    actions = document.get("actions") if isinstance(document.get("actions"), list) else []
    seen: set[str] = set()
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            issues.append(Issue("error", "invalid_action", "action must be an object", f"actions[{index}]"))
            continue
        action_id = action.get("action_id")
        if action_id in seen:
            issues.append(Issue("error", "duplicate_action", f"duplicate action_id: {action_id}", f"actions[{index}].action_id"))
        seen.add(str(action_id))
        if not action.get("frames"):
            issues.append(Issue("error", "empty_action", "action must contain at least one frame", f"actions[{index}].frames"))
        elif not isinstance(action.get("frames"), list) or any(not isinstance(frame, str) or not frame for frame in action["frames"]):
            issues.append(Issue("error", "invalid_frames", "frames must be a non-empty array of paths", f"actions[{index}].frames"))
        if not isinstance(action.get("fps"), (int, float)) or action.get("fps", 0) <= 0:
            issues.append(Issue("error", "invalid_fps", "fps must be greater than zero", f"actions[{index}].fps"))
        if not isinstance(action.get("loop"), bool):
            issues.append(Issue("error", "invalid_loop", "loop must be an explicit boolean", f"actions[{index}].loop"))
    return _result("action_set", issues, {"action_count": len(actions), "asset_identity": document.get("asset_identity")})


def validate_frame_geometry(document: dict[str, Any], root: Path) -> dict[str, Any]:
    issues = _required(document, ("schema_version", "asset_identity", "canvas", "invariants", "frames"))
    if document.get("schema_version") != "0.1":
        issues.append(Issue("error", "schema_version", "frame geometry schema_version must be 0.1", "schema_version"))
    canvas = document.get("canvas") if isinstance(document.get("canvas"), dict) else {}
    invariants = document.get("invariants") if isinstance(document.get("invariants"), dict) else {}
    frames = document.get("frames") if isinstance(document.get("frames"), list) else []
    width, height = int(canvas.get("width", 0) or 0), int(canvas.get("height", 0) or 0)
    pivot_tolerance = float(invariants.get("pivot_tolerance_px", 0) or 0)
    footline_tolerance = float(invariants.get("footline_tolerance_px", 0) or 0)
    bbox_tolerance = float(invariants.get("bbox_drift_tolerance_px", 0) or 0)
    min_alpha = int(invariants.get("min_alpha_pixels", 1) or 1)
    measurements: list[dict[str, Any]] = []
    base_pivot: tuple[float, float] | None = None
    base_footline: float | None = None
    base_bbox: dict[str, int] | None = None
    for index, frame in enumerate(frames):
        path_prefix = f"frames[{index}]"
        if not isinstance(frame, dict):
            issues.append(Issue("error", "invalid_frame", "frame must be an object", path_prefix))
            continue
        image_path = _resolve(root, str(frame.get("image", "")))
        try:
            image = PNGImage(image_path)
        except (OSError, PNGError, ValueError) as exc:
            issues.append(Issue("error", "image_unreadable", str(exc), f"{path_prefix}.image"))
            continue
        rect = _normalise_rect(frame.get("rect"), image.width, image.height)
        if not _rect_inside(rect, image.width, image.height):
            issues.append(Issue("error", "rect_out_of_bounds", "frame rect is outside the image", f"{path_prefix}.rect"))
            continue
        if width != image.width or height != image.height:
            issues.append(Issue("error", "canvas_size_mismatch", f"image is {image.width}x{image.height}, contract canvas is {width}x{height}", f"{path_prefix}.image"))
        bbox_global = image.alpha_bbox(1, rect)
        alpha_pixels = image.alpha_count(1, rect)
        if alpha_pixels < min_alpha:
            issues.append(Issue("error", "too_few_alpha_pixels", f"frame has {alpha_pixels} alpha pixels, minimum is {min_alpha}", path_prefix))
        if not bbox_global:
            issues.append(Issue("error", "empty_alpha_bbox", "frame has no visible pixels", f"{path_prefix}.alpha_bbox"))
            continue
        bbox = {"x": bbox_global["x"] - rect["x"], "y": bbox_global["y"] - rect["y"], "width": bbox_global["width"], "height": bbox_global["height"]}
        declared_bbox = frame.get("alpha_bbox")
        if isinstance(declared_bbox, dict) and bbox != _normalise_rect(declared_bbox, rect["width"], rect["height"]):
            issues.append(Issue("error", "alpha_bbox_mismatch", f"measured {bbox} does not match declared {declared_bbox}", f"{path_prefix}.alpha_bbox"))
        if not invariants.get("allow_external_opaque_pixels", False):
            outside = image.opaque_outside(rect)
            if outside:
                issues.append(Issue("error", "frame_contamination", f"{outside} opaque pixels exist outside the declared frame rect", f"{path_prefix}.rect"))
        actual_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
        if frame.get("sha256") != actual_hash:
            issues.append(Issue("error", "sha256_mismatch", "declared frame hash does not match file", f"{path_prefix}.sha256"))
        pivot = frame.get("pivot") if isinstance(frame.get("pivot"), dict) else {}
        px, py = float(pivot.get("x", 0)), float(pivot.get("y", 0))
        if pivot.get("space") == "normalized":
            px, py = px * width, py * height
        footline = float(frame.get("footline_px", 0))
        if base_pivot is None:
            base_pivot, base_footline, base_bbox = (px, py), footline, bbox
        else:
            if not (_close(px, base_pivot[0], pivot_tolerance) and _close(py, base_pivot[1], pivot_tolerance)):
                issues.append(Issue("error", "pivot_drift", f"pivot drift exceeds {pivot_tolerance}px", path_prefix))
            if not _close(footline, base_footline, footline_tolerance):
                issues.append(Issue("error", "footline_drift", f"footline drift exceeds {footline_tolerance}px", path_prefix))
            if abs(bbox["width"] - base_bbox["width"]) > bbox_tolerance or abs(bbox["height"] - base_bbox["height"]) > bbox_tolerance:
                issues.append(Issue("warning", "bbox_drift", f"bbox size drift exceeds {bbox_tolerance}px", path_prefix))
        safe_rect = frame.get("safe_rect")
        if isinstance(safe_rect, dict) and not _rect_inside(_normalise_rect(safe_rect, rect["width"], rect["height"]), rect["width"], rect["height"]):
            issues.append(Issue("error", "safe_rect_out_of_bounds", "safe rect must fit inside frame rect", f"{path_prefix}.safe_rect"))
        measurements.append({"frame_id": frame.get("frame_id"), "image": str(image_path), "width": image.width, "height": image.height, "alpha_pixels": alpha_pixels, "alpha_bbox": bbox, "sha256": actual_hash})
    return _result("frame_geometry", issues, {"frame_count": len(measurements), "canvas": {"width": width, "height": height}, "measurements": measurements})


def validate_atlas(document: dict[str, Any], root: Path) -> dict[str, Any]:
    issues = _required(document, ("schema_version", "image", "allow_rotation", "padding_px", "extrude_px", "regions"))
    if document.get("schema_version") != "0.1":
        issues.append(Issue("error", "schema_version", "atlas schema_version must be 0.1", "schema_version"))
    if document.get("allow_rotation") is not False:
        issues.append(Issue("error", "rotation_not_allowed", "atlas rotation must be explicitly false", "allow_rotation"))
    image_path = _resolve(root, str(document.get("image", "")))
    try:
        image = PNGImage(image_path)
    except (OSError, PNGError, ValueError) as exc:
        return _result("atlas", issues + [Issue("error", "image_unreadable", str(exc), "image")], {})
    regions = document.get("regions") if isinstance(document.get("regions"), list) else []
    rects: list[tuple[str, dict[str, int]]] = []
    for index, region in enumerate(regions):
        if not isinstance(region, dict):
            issues.append(Issue("error", "invalid_region", "region must be an object", f"regions[{index}]"))
            continue
        rect = _normalise_rect(region.get("rect"), image.width, image.height)
        region_id = str(region.get("region_id", index))
        if not _rect_inside(rect, image.width, image.height):
            issues.append(Issue("error", "region_out_of_bounds", "atlas region is outside the image", f"regions[{index}].rect"))
        for prior_id, prior_rect in rects:
            if _rect_overlap(rect, prior_rect):
                issues.append(Issue("error", "region_overlap", f"region {region_id} overlaps {prior_id}", f"regions[{index}].rect"))
        rects.append((region_id, rect))
    outside = 0
    if document.get("require_transparent_outside_regions", False) and rects:
        pixels = image.rgba()
        outside = sum(
            1
            for y in range(image.height)
            for x in range(image.width)
            if pixels[y * image.width + x][3] > 0
            and not any(r["x"] <= x < r["x"] + r["width"] and r["y"] <= y < r["y"] + r["height"] for _, r in rects)
        )
        if outside:
            issues.append(Issue("error", "atlas_contamination", f"{outside} opaque pixels exist outside atlas regions", "regions"))
    return _result("atlas", issues, {"image": str(image_path), "width": image.width, "height": image.height, "region_count": len(rects), "opaque_pixels_outside_regions": outside})


def _contains(outer: dict[str, float], inner: dict[str, float]) -> bool:
    return inner["x"] >= outer["x"] and inner["y"] >= outer["y"] and inner["x"] + inner["width"] <= outer["x"] + outer["width"] and inner["y"] + inner["height"] <= outer["y"] + outer["height"]


def validate_layered_map(document: dict[str, Any], root: Path, strict: bool = False) -> dict[str, Any]:
    issues = _required(document, ("schema_version", "map_id", "coordinate_system", "world_bounds", "camera", "layers"))
    if document.get("schema_version") != "0.1":
        issues.append(Issue("error", "schema_version", "layered map schema_version must be 0.1", "schema_version"))
    world = document.get("world_bounds") if isinstance(document.get("world_bounds"), dict) else {}
    camera = document.get("camera") if isinstance(document.get("camera"), dict) else {}
    safe = camera.get("safe_bounds") if isinstance(camera.get("safe_bounds"), dict) else {}
    if world and safe and not _contains({k: float(world.get(k, 0)) for k in ("x", "y", "width", "height")}, {k: float(safe.get(k, 0)) for k in ("x", "y", "width", "height")}):
        issues.append(Issue("error", "camera_safe_bounds_outside_world", "camera safe bounds must fit inside map world bounds", "camera.safe_bounds"))
    layers = document.get("layers") if isinstance(document.get("layers"), list) else []
    ids: set[str] = set()
    z_values: set[int] = set()
    ordered: list[tuple[int, float, str]] = []
    layer_metrics: list[dict[str, Any]] = []
    seam_tolerance = float(camera.get("seam_tolerance", 0.08) or 0.08)
    for index, layer in enumerate(layers):
        path_prefix = f"layers[{index}]"
        if not isinstance(layer, dict):
            issues.append(Issue("error", "invalid_layer", "layer must be an object", path_prefix))
            continue
        layer_id = str(layer.get("layer_id", ""))
        z_index = int(layer.get("z_index", 0))
        if layer_id in ids:
            issues.append(Issue("error", "duplicate_layer_id", f"duplicate layer_id: {layer_id}", f"{path_prefix}.layer_id"))
        if z_index in z_values:
            issues.append(Issue("error", "duplicate_z_index", f"duplicate z_index: {z_index}", f"{path_prefix}.z_index"))
        ids.add(layer_id)
        z_values.add(z_index)
        parallax = layer.get("parallax") if isinstance(layer.get("parallax"), dict) else {}
        px, py = float(parallax.get("x", -1)), float(parallax.get("y", -1))
        if px < 0 or py < 0:
            issues.append(Issue("error", "invalid_parallax", "parallax factors must be non-negative", f"{path_prefix}.parallax"))
        ordered.append((z_index, px, layer_id))
        layer_world = layer.get("world_bounds") if isinstance(layer.get("world_bounds"), dict) else {}
        layer_safe = layer.get("camera_safe_bounds") if isinstance(layer.get("camera_safe_bounds"), dict) else {}
        if layer_world and layer_safe and not _contains({k: float(layer_world.get(k, 0)) for k in ("x", "y", "width", "height")}, {k: float(layer_safe.get(k, 0)) for k in ("x", "y", "width", "height")}):
            issues.append(Issue("error", "layer_safe_bounds_outside_world", "layer camera safe bounds must fit inside layer world bounds", f"{path_prefix}.camera_safe_bounds"))
        image_path = _resolve(root, str(layer.get("image", "")))
        metric: dict[str, Any] = {"layer_id": layer_id, "z_index": z_index, "parallax": {"x": px, "y": py}, "image": str(image_path)}
        try:
            image = PNGImage(image_path)
            metric.update({"width": image.width, "height": image.height})
            tileable = layer.get("tileable") if isinstance(layer.get("tileable"), dict) else {}
            if tileable.get("x") and image.edge_difference("x") > seam_tolerance:
                issues.append(Issue("error", "horizontal_seam", f"tileable x edge difference exceeds {seam_tolerance}", f"{path_prefix}.image"))
            if tileable.get("y") and image.edge_difference("y") > seam_tolerance:
                issues.append(Issue("error", "vertical_seam", f"tileable y edge difference exceeds {seam_tolerance}", f"{path_prefix}.image"))
            metric["edge_difference"] = {"x": image.edge_difference("x"), "y": image.edge_difference("y")}
        except (OSError, PNGError, ValueError) as exc:
            issues.append(Issue("error", "image_unreadable", str(exc), f"{path_prefix}.image"))
        layer_metrics.append(metric)
    ordered.sort()
    previous_parallax: float | None = None
    for z_index, parallax, layer_id in ordered:
        if previous_parallax is not None and parallax < previous_parallax:
            issue = Issue("error" if strict else "warning", "parallax_order_drift", f"parallax decreases at layer {layer_id}; verify intentional depth ordering", f"layers[{layer_id}].parallax")
            issues.append(issue)
        previous_parallax = parallax
    return _result("layered_map", issues, {"map_id": document.get("map_id"), "layer_count": len(layer_metrics), "layers": layer_metrics})


def _result(kind: str, issues: list[Issue], metrics: dict[str, Any]) -> dict[str, Any]:
    errors = [asdict(issue) for issue in issues if issue.severity == "error"]
    warnings = [asdict(issue) for issue in issues if issue.severity == "warning"]
    return {"contract": kind, "status": "blocked" if errors else "pass", "ready": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def run(kind: str, document: dict[str, Any], root: Path, strict: bool) -> dict[str, Any]:
    if kind == "identity":
        return validate_identity(document)
    if kind == "action-set":
        return validate_action_set(document)
    if kind == "frame-geometry":
        return validate_frame_geometry(document, root)
    if kind == "atlas":
        return validate_atlas(document, root)
    if kind == "layered-map":
        return validate_layered_map(document, root, strict)
    return _result("unknown", [Issue("error", "unknown_kind", f"unsupported consistency kind: {kind}", "kind")], {})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate deterministic MotionLoom asset consistency contracts")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "analyze", "report"):
        command_parser = sub.add_parser(command)
        command_parser.add_argument("--kind", choices=("identity", "action-set", "frame-geometry", "atlas", "layered-map"), required=True)
        command_parser.add_argument("--input", required=True, type=Path)
        command_parser.add_argument("--root", type=Path, default=Path("."))
        command_parser.add_argument("--output", type=Path)
        command_parser.add_argument("--strict", action="store_true")
        command_parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    document, load_issues = _load_document(args.input)
    result = _result("document", load_issues, {}) if document is None else run(args.kind, document, args.root.resolve(), args.strict)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.json or args.command != "report":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"{result['contract']}: {result['status']} ({len(result['errors'])} errors, {len(result['warnings'])} warnings)")
        for issue in result["errors"] + result["warnings"]:
            print(f"- {issue['severity']}: {issue['code']}: {issue['message']}")
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
