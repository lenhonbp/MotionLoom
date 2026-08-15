#!/usr/bin/env python3
"""Deterministically isolate a high-contrast, edge-connected flat background.

This is a narrow recovery utility for generated PNGs where an image provider
painted a dark background despite a transparency request. It flood-fills only
edge-connected pixels within a stated RGB-distance of an observed edge color.
It does not claim the input was provider-native alpha, alter provenance, or
approve an asset. Review the JSON report before using the result in a bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
import zlib
from collections import deque
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_png_reader() -> Any:
    source = ROOT / "scripts" / "asset-consistency.py"
    spec = importlib.util.spec_from_file_location("motionloom_alpha_isolation_png", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load PNG reader: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PNGImage


def median_edge_color(pixels: list[tuple[int, int, int, int]], width: int, height: int) -> tuple[int, int, int]:
    indices = set(range(width)) | {width * (height - 1) + x for x in range(width)}
    indices.update(y * width for y in range(height))
    indices.update(y * width + width - 1 for y in range(height))
    values = [pixels[index] for index in sorted(indices)]
    return tuple(int(median([pixel[channel] for pixel in values])) for channel in range(3))


def distance(pixel: tuple[int, int, int, int], color: tuple[int, int, int]) -> int:
    return sum(abs(pixel[index] - color[index]) for index in range(3))


def isolate(pixels: list[tuple[int, int, int, int]], width: int, height: int, background: tuple[int, int, int], tolerance: int) -> set[int]:
    def matches(index: int) -> bool:
        return pixels[index][3] > 0 and distance(pixels[index], background) <= tolerance
    edges = set(range(width)) | {width * (height - 1) + x for x in range(width)}
    edges.update(y * width for y in range(height))
    edges.update(y * width + width - 1 for y in range(height))
    queue = deque(index for index in edges if matches(index))
    visited = set(queue)
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        for neighbour in (index - 1 if x else None, index + 1 if x + 1 < width else None, index - width if y else None, index + width if y + 1 < height else None):
            if neighbour is not None and neighbour not in visited and matches(neighbour):
                visited.add(neighbour)
                queue.append(neighbour)
    return visited


def png_rgba(width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> bytes:
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for pixel in pixels[y * width : (y + 1) * width]:
            raw.extend(pixel)
    def chunk(kind: bytes, content: bytes) -> bytes:
        return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content) & 0xFFFFFFFF)
    return PNG_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(raw), level=9)) + chunk(b"IEND", b"")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flood-fill a flat edge-connected background into alpha=0")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path, help="Optional JSON evidence report")
    parser.add_argument("--tolerance", type=int, default=24, help="Manhattan RGB distance from edge background; 0-765")
    parser.add_argument("--allow-edge-foreground", action="store_true", help="Permit opaque pixels on the canvas edge; only use for intentionally edge-cropped art")
    args = parser.parse_args(argv)
    if not 0 <= args.tolerance <= 765:
        raise SystemExit("--tolerance must be in 0..765")
    if not args.input.is_file():
        raise SystemExit(f"input is missing: {args.input}")
    if args.output.resolve() == args.input.resolve():
        raise SystemExit("output must differ from input")
    PNGImage = load_png_reader()
    image = PNGImage(args.input)
    pixels = image.rgba()
    background = median_edge_color(pixels, image.width, image.height)
    removed = isolate(pixels, image.width, image.height, background, args.tolerance)
    if not removed:
        raise SystemExit("no edge-connected background pixels matched; do not use a larger tolerance without visual review")
    output_pixels = [(r, g, b, 0 if index in removed else a) for index, (r, g, b, a) in enumerate(pixels)]
    foreground = sum(1 for _, _, _, alpha in output_pixels if alpha > 0)
    if foreground == 0:
        raise SystemExit("isolation would remove all pixels; lower tolerance or provide a different source")
    edge_indices = set(range(image.width)) | {image.width * (image.height - 1) + x for x in range(image.width)}
    edge_indices.update(y * image.width for y in range(image.height))
    edge_indices.update(y * image.width + image.width - 1 for y in range(image.height))
    residual_edge_pixels = sum(1 for index in edge_indices if output_pixels[index][3] > 0)
    if residual_edge_pixels and not args.allow_edge_foreground:
        raise SystemExit(
            f"{residual_edge_pixels} opaque pixel(s) remain at the canvas edge after isolation; "
            "this is likely residual background contamination. Use a cleaner source, or explicitly review and pass --allow-edge-foreground for intentionally cropped art."
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(png_rgba(image.width, image.height, output_pixels))
    report = {
        "contract": "alpha-isolation-report",
        "mode": "edge_connected_flat_background",
        "input": str(args.input),
        "input_sha256": digest(args.input),
        "output": str(args.output),
        "output_sha256": digest(args.output),
        "canvas": {"width": image.width, "height": image.height},
        "observed_edge_background_rgb": list(background),
        "tolerance": args.tolerance,
        "removed_pixels": len(removed),
        "foreground_alpha_pixels": foreground,
        "residual_edge_foreground_pixels": residual_edge_pixels,
        "edge_foreground_allowed": args.allow_edge_foreground,
        "human_review_required": True,
        "production_approved": False,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
