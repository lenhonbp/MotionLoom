#!/usr/bin/env python3
"""Regression suite for MotionLoom's deterministic asset consistency contracts."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "examples/agent-consumer/asset-consistency"
ANALYZER_PATH = ROOT / "scripts/asset-consistency.py"
PREFLIGHT_PATH = ROOT / "scripts/frame-set-preflight.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AC = load_module(ANALYZER_PATH, "asset_consistency")
PREFLIGHT = load_module(PREFLIGHT_PATH, "frame_set_preflight")


def read_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def write_rgba_png(path: Path, width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> None:
    raw = b"".join(b"\x00" + bytes(sum((list(pixel) for pixel in pixels[y * width : (y + 1) * width]), [])) for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b""))


def solid(width: int, height: int, color: tuple[int, int, int, int]) -> list[tuple[int, int, int, int]]:
    return [color] * (width * height)


def test_pass_fixtures() -> None:
    identity = AC.validate_identity(read_json("hero-identity.json"))
    check(identity["ready"], f"identity fixture blocked: {identity}")

    action_set = AC.validate_action_set(read_json("hero-walk-action-set.json"))
    check(action_set["ready"], f"action-set fixture blocked: {action_set}")

    geometry = AC.validate_frame_geometry(read_json("hero-walk-frame-geometry.json"), FIXTURE_ROOT)
    check(geometry["ready"], f"frame geometry fixture blocked: {geometry}")
    check(geometry["metrics"]["frame_count"] == 4, "frame geometry must measure all four frames")

    atlas = AC.validate_atlas(read_json("hero-atlas-contract.json"), FIXTURE_ROOT)
    check(atlas["ready"], f"atlas fixture blocked: {atlas}")
    check(atlas["metrics"]["opaque_pixels_outside_regions"] == 0, "atlas fixture must have no outside pixels")

    layered_map = AC.validate_layered_map(read_json("forest-layered-map.json"), FIXTURE_ROOT)
    check(layered_map["ready"], f"layered-map fixture blocked: {layered_map}")
    check(layered_map["metrics"]["layer_count"] == 3, "layered-map fixture must measure three layers")


def test_identity_and_action_fail_closed() -> None:
    identity = read_json("hero-identity.json")
    identity["derivation"]["origin"] = "unknown"
    result = AC.validate_identity(identity)
    check(not result["ready"] and any(item["code"] == "unknown_origin" for item in result["errors"]), "unknown identity origin must block")

    action_set = read_json("hero-walk-action-set.json")
    del action_set["actions"][0]["loop"]
    result = AC.validate_action_set(action_set)
    check(not result["ready"] and any(item["code"] == "invalid_loop" for item in result["errors"]), "implicit loop policy must block")


def test_frame_contamination_and_pivot_drift() -> None:
    geometry = read_json("hero-walk-frame-geometry.json")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        image = [(0, 0, 0, 0)] * 64
        for y in range(1, 6):
            for x in range(2, 6):
                image[y * 8 + x] = (120, 160, 220, 255)
        image[0] = (255, 0, 0, 255)
        write_rgba_png(root / "contaminated.png", 8, 8, image)
        geometry["frames"] = [copy.deepcopy(geometry["frames"][0])]
        geometry["frames"][0]["image"] = "contaminated.png"
        geometry["frames"][0]["rect"] = {"x": 1, "y": 1, "width": 6, "height": 6}
        geometry["frames"][0]["alpha_bbox"] = {"x": 1, "y": 0, "width": 4, "height": 5}
        geometry["frames"][0]["sha256"] = hashlib.sha256((root / "contaminated.png").read_bytes()).hexdigest()
        result = AC.validate_frame_geometry(geometry, root)
        check(not result["ready"] and any(item["code"] == "frame_contamination" for item in result["errors"]), "opaque pixels outside frame rect must block")

    geometry = read_json("hero-walk-frame-geometry.json")
    geometry["frames"][1]["pivot"]["x"] = 4.5
    result = AC.validate_frame_geometry(geometry, FIXTURE_ROOT)
    check(not result["ready"] and any(item["code"] == "pivot_drift" for item in result["errors"]), "pivot drift must block")


def test_generated_frame_set_preflight() -> None:
    geometry = read_json("hero-walk-frame-geometry.json")
    result = PREFLIGHT.validate(geometry, FIXTURE_ROOT)
    check(result["ready"], f"isolated generated frame fixture must pass preflight: {result}")
    check(result.get("approval") is False, "preflight must never emit approval")

    shared = read_json("hero-walk-frame-geometry.json")
    shared["frames"][1]["image"] = shared["frames"][0]["image"]
    shared["frames"][1]["sha256"] = shared["frames"][0]["sha256"]
    result = PREFLIGHT.validate(shared, FIXTURE_ROOT)
    check(
        not result["ready"] and any(item["code"] == "shared_source_image" for item in result["errors"]),
        "generated multi-frame source must reject a shared pose-sheet image",
    )

    guard = read_json("hero-walk-frame-geometry.json")
    guard["frames"][0]["safe_rect"] = {"x": 2, "y": 1, "width": 4, "height": 5}
    guard["frames"][0]["bleed_margin_px"] = 1
    result = PREFLIGHT.validate(guard, FIXTURE_ROOT)
    check(
        not result["ready"] and any(item["code"] == "guard_band_violation" for item in result["errors"]),
        "generated frame alpha must preserve the declared transparent guard band",
    )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        geometry = read_json("hero-walk-frame-geometry.json")
        geometry["frames"] = [copy.deepcopy(geometry["frames"][0]), copy.deepcopy(geometry["frames"][1])]
        geometry["invariants"]["bbox_drift_tolerance_px"] = 0
        for frame in geometry["frames"]:
            frame["rect"] = {"x": 0, "y": 0, "width": 8, "height": 8}
            frame["safe_rect"] = {"x": 0, "y": 0, "width": 8, "height": 8}
            frame["bleed_margin_px"] = 0

        first_pixels = solid(8, 8, (0, 0, 0, 0))
        for y in range(1, 6):
            for x in range(2, 6):
                first_pixels[y * 8 + x] = (120, 160, 220, 255)
        second_pixels = solid(8, 8, (0, 0, 0, 0))
        for y in range(1, 6):
            for x in range(1, 7):
                second_pixels[y * 8 + x] = (120, 160, 220, 255)
        write_rgba_png(root / "frame-00.png", 8, 8, first_pixels)
        write_rgba_png(root / "frame-01.png", 8, 8, second_pixels)

        geometry["frames"][0]["image"] = "frame-00.png"
        geometry["frames"][0]["alpha_bbox"] = {"x": 2, "y": 1, "width": 4, "height": 5}
        geometry["frames"][0]["sha256"] = hashlib.sha256((root / "frame-00.png").read_bytes()).hexdigest()
        geometry["frames"][1]["image"] = "frame-01.png"
        geometry["frames"][1]["alpha_bbox"] = {"x": 1, "y": 1, "width": 6, "height": 5}
        geometry["frames"][1]["sha256"] = hashlib.sha256((root / "frame-01.png").read_bytes()).hexdigest()

        result = PREFLIGHT.validate(geometry, root)
        check(
            not result["ready"] and any(item["code"] == "bbox_drift" for item in result["errors"]),
            "generated frame apparent-size drift beyond tolerance must block instead of warning",
        )


def test_atlas_overlap_and_contamination() -> None:
    atlas = read_json("hero-atlas-contract.json")
    atlas["regions"][1]["rect"]["x"] = 4
    result = AC.validate_atlas(atlas, FIXTURE_ROOT)
    check(not result["ready"] and any(item["code"] == "region_overlap" for item in result["errors"]), "overlapping atlas regions must block")

    atlas = read_json("hero-atlas-contract.json")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pixels = solid(16, 8, (0, 0, 0, 0))
        for y in range(1, 7):
            for x in list(range(1, 7)) + list(range(9, 15)):
                pixels[y * 16 + x] = (200, 100, 80, 255)
        pixels[0] = (255, 255, 255, 255)
        contaminated = root / "atlas.png"
        write_rgba_png(contaminated, 16, 8, pixels)
        atlas["image"] = str(contaminated)
        result = AC.validate_atlas(atlas, root)
        check(not result["ready"] and any(item["code"] == "atlas_contamination" for item in result["errors"]), "atlas pixels outside regions must block")


def test_layered_map_order_seam_and_bounds() -> None:
    layered_map = read_json("forest-layered-map.json")
    layered_map["layers"][1]["z_index"] = 0
    result = AC.validate_layered_map(layered_map, FIXTURE_ROOT)
    check(not result["ready"] and any(item["code"] == "duplicate_z_index" for item in result["errors"]), "duplicate z-order must block")

    layered_map = read_json("forest-layered-map.json")
    layered_map["layers"][1]["parallax"]["x"] = 0.1
    warning = AC.validate_layered_map(layered_map, FIXTURE_ROOT)
    check(warning["ready"] and any(item["code"] == "parallax_order_drift" for item in warning["warnings"]), "non-monotonic parallax must be visible as a warning")
    blocked = AC.validate_layered_map(layered_map, FIXTURE_ROOT, strict=True)
    check(not blocked["ready"] and any(item["code"] == "parallax_order_drift" for item in blocked["errors"]), "strict parallax drift must block")

    layered_map = read_json("forest-layered-map.json")
    layered_map["camera"]["safe_bounds"] = {"x": 120, "y": 60, "width": 32, "height": 18}
    result = AC.validate_layered_map(layered_map, FIXTURE_ROOT)
    check(not result["ready"] and any(item["code"] == "camera_safe_bounds_outside_world" for item in result["errors"]), "camera safe bounds outside world must block")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pixels = solid(4, 4, (0, 0, 0, 255))
        for y in range(4):
            pixels[y * 4 + 3] = (255, 255, 255, 255)
        seam_image = root / "seam.png"
        write_rgba_png(seam_image, 4, 4, pixels)
        seam_map = read_json("forest-layered-map.json")
        seam_map["layers"] = [copy.deepcopy(seam_map["layers"][0])]
        seam_map["layers"][0]["image"] = str(seam_image)
        result = AC.validate_layered_map(seam_map, root)
        check(not result["ready"] and any(item["code"] == "horizontal_seam" for item in result["errors"]), "tileable horizontal seam must block")


def test_missing_file_and_cli_surface() -> None:
    geometry = read_json("hero-walk-frame-geometry.json")
    geometry["frames"][0]["image"] = "does-not-exist.png"
    result = AC.validate_frame_geometry(geometry, FIXTURE_ROOT)
    check(not result["ready"] and any(item["code"] == "image_unreadable" for item in result["errors"]), "missing image must fail closed")

    cli = subprocess.run([
        "node", str(ROOT / "bin/motionloom.mjs"), "asset-consistency", "validate",
        "--kind", "layered-map", "--input", str(FIXTURE_ROOT / "forest-layered-map.json"),
        "--root", str(FIXTURE_ROOT), "--json",
    ], cwd=ROOT, capture_output=True, text=True)
    data = json.loads(cli.stdout)
    check(cli.returncode == 0 and data.get("ready") is True and data.get("contract") == "layered_map", "CLI must expose the consistency validator")

    preflight_cli = subprocess.run([
        sys.executable, str(PREFLIGHT_PATH),
        "--input", str(FIXTURE_ROOT / "hero-walk-frame-geometry.json"),
        "--root", str(FIXTURE_ROOT), "--json",
    ], cwd=ROOT, capture_output=True, text=True)
    preflight_data = json.loads(preflight_cli.stdout)
    check(
        preflight_cli.returncode == 0 and preflight_data.get("ready") is True and preflight_data.get("approval") is False,
        "generated frame-set preflight CLI must pass isolated fixture without granting approval",
    )


def main() -> int:
    test_pass_fixtures()
    test_identity_and_action_fail_closed()
    test_frame_contamination_and_pivot_drift()
    test_generated_frame_set_preflight()
    test_atlas_overlap_and_contamination()
    test_layered_map_order_seam_and_bounds()
    test_missing_file_and_cli_surface()
    print("asset consistency contract tests: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"asset consistency contract tests: FAIL — {exc}", file=sys.stderr)
        raise
