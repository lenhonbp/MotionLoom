from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ISOLATOR = ROOT / "scripts" / "isolate-alpha-background.py"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_png(path: Path, contamination: bool = False) -> None:
    width = height = 8
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            if 2 <= x <= 5 and 2 <= y <= 5:
                color = (244, 124, 21, 255)
            elif contamination and x == width - 1 and y == 3:
                color = (180, 24, 180, 255)
            else:
                color = (29, 32, 32, 255)
            raw.extend(color)
    def chunk(kind: bytes, content: bytes) -> bytes:
        return struct.pack(">I", len(content)) + kind + content + struct.pack(">I", zlib.crc32(kind + content) & 0xFFFFFFFF)
    payload = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    path.write_bytes(payload)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source, output, report = root / "source.png", root / "isolated.png", root / "report.json"
        write_png(source)
        result = subprocess.run([sys.executable, str(ISOLATOR), str(source), str(output), "--report", str(report), "--tolerance", "24"], capture_output=True, text=True)
        check(result.returncode == 0, result.stderr or result.stdout)
        data = json.loads(report.read_text())
        check(data["removed_pixels"] == 48 and data["foreground_alpha_pixels"] == 16, "isolator must remove only the edge-connected flat background")
        check(data["residual_edge_foreground_pixels"] == 0 and data["human_review_required"] is True and data["production_approved"] is False, "isolation must preserve review/approval boundary")

        contaminated = root / "contaminated.png"
        write_png(contaminated, contamination=True)
        rejected = subprocess.run([sys.executable, str(ISOLATOR), str(contaminated), str(root / "rejected.png"), "--tolerance", "24"], capture_output=True, text=True)
        check(rejected.returncode != 0 and "residual background contamination" in (rejected.stderr + rejected.stdout), "edge contamination must fail closed")
    print("alpha isolation tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
