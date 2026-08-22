from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "asset-adapt.mjs"
SOURCE = ROOT / "examples/agent-consumer/asset-consistency/assets/hero-frame-00.png"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        output = root / "padded.png"
        report = root / "adaptation.json"
        result = subprocess.run([
            "node", str(SCRIPT), "pad", "--input", str(SOURCE), "--output", str(output),
            "--width", "16", "--height", "16", "--scale", "1", "--anchor", "center",
            "--report", str(report), "--json",
        ], capture_output=True, text=True)
        check(result.returncode == 0, result.stderr)
        doc = json.loads(report.read_text())
        check(doc["approval"] is False and doc["production_approved"] is False, "adaptation cannot grant approval")
        check(doc["source"]["canvas"] == [8, 8] and doc["output"]["canvas"] == [16, 16], "adaptation must bind source/output geometry")
        check(doc["transform"]["crop"] is False and doc["transform"]["stretch"] is False, "crop/stretch must remain false")
        check(doc["transform"]["interpolation"] == "nearest-neighbour", "pixel art must use nearest-neighbour")
        check(output.is_file() and output.stat().st_size > 0, "adapter must emit target PNG")

        blocked = subprocess.run([
            "node", str(SCRIPT), "pad", "--input", str(SOURCE), "--output", str(root / "blocked.png"),
            "--width", "4", "--height", "4", "--json",
        ], capture_output=True, text=True)
        check(blocked.returncode != 0 and "crop is forbidden" in blocked.stderr, "oversized source must fail closed")
    print("asset adaptation contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
