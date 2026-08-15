from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts" / "build-ai-pilot.py"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_png(path: Path, alpha: bool, offset: int = 0, contamination: bool = False) -> None:
    """Write one compact, non-interlaced 4x4 PNG without third-party libraries."""
    width = height = 4
    channels = 4 if alpha else 3
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            visible = (x == 1 + offset and y in {1, 2}) or (contamination and x == 3 and y == 1)
            rows.extend((244, 124, 21))
            if alpha:
                rows.append(255 if visible else 0)
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    color_type = 6 if alpha else 2
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))


def build(root: Path, sources: dict[str, Path], output: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, str(BUILDER),
            "--idle", str(sources["idle"]),
            "--contact-right", str(sources["contact-right"]),
            "--passing", str(sources["passing"]),
            "--contact-left", str(sources["contact-left"]),
            "--root", str(root),
            "--output", output,
            "--generated-at", "2026-08-15T00:00:00Z",
            "--overwrite",
        ],
        capture_output=True,
        text=True,
    )


def main() -> int:
    output = ".motionloom/pilots/test-ai-pilot-builder"
    workspace = ROOT / output
    shutil.rmtree(workspace, ignore_errors=True)
    with tempfile.TemporaryDirectory() as td:
        source_dir = Path(td)
        sources: dict[str, Path] = {}
        for index, frame_id in enumerate(("idle", "contact-right", "passing", "contact-left")):
            source = source_dir / f"{frame_id}.png"
            write_png(source, alpha=True, offset=index % 2)
            sources[frame_id] = source
        result = build(ROOT, sources, output)
        check(result.returncode == 0, result.stderr or result.stdout)
        provenance = json.loads((workspace / "provenance.json").read_text())
        candidate = json.loads((workspace / "candidate.json").read_text())
        evidence = json.loads((workspace / "devlab-pilot-evidence.json").read_text())
        check(provenance["authority"] == "ai_generated" and provenance["readiness"] == "runtime_ready", "builder must preserve AI authority/readiness")
        check("human_approval" not in provenance and candidate["runtime"]["review_required"] is True, "builder must not self-approve a candidate")
        check(evidence["state"] == "review_required" and evidence["production_approved"] is False, "Dev Lab evidence must retain review boundary")
        intake = subprocess.run(
            [sys.executable, str(ROOT / "scripts/artifact-intake.py"), "intake", "--root", str(ROOT), "--registry", str(ROOT / "artifact-adapter-registry.json"), "--controls", str(workspace / "controls.json"), "--receipt", str(workspace / "receipt.json"), "--export-manifest", str(workspace / "export.json"), "--json"],
            capture_output=True,
            text=True,
        )
        intake_data = json.loads(intake.stdout)
        check(intake.returncode == 0 and intake_data["status"] == "review_required", intake.stderr or intake.stdout)
        runtime = subprocess.run(
            [sys.executable, str(ROOT / "scripts/runtime-candidate.py"), "validate", "--root", str(ROOT), "--input", str(workspace / "candidate.json"), "--json"],
            capture_output=True,
            text=True,
        )
        runtime_data = json.loads(runtime.stdout)
        check(runtime.returncode == 0 and runtime_data["status"] == "review_required" and runtime_data["runtime_verified"] is False, runtime.stderr or runtime.stdout)

        opaque = source_dir / "opaque.png"
        write_png(opaque, alpha=False)
        rejected = build(ROOT, {key: opaque for key in sources}, ".motionloom/pilots/test-ai-pilot-opaque")
        check(rejected.returncode != 0 and "has no alpha channel" in (rejected.stderr + rejected.stdout), "RGB checkered source must be rejected as non-alpha")

        contaminated = source_dir / "contaminated.png"
        write_png(contaminated, alpha=True, contamination=True)
        rejected = build(ROOT, {key: contaminated for key in sources}, ".motionloom/pilots/test-ai-pilot-contaminated")
        check(rejected.returncode != 0 and "clean padding" in (rejected.stderr + rejected.stdout), "detached canvas-edge contamination must be rejected")
    shutil.rmtree(workspace, ignore_errors=True)
    shutil.rmtree(ROOT / ".motionloom/pilots/test-ai-pilot-opaque", ignore_errors=True)
    shutil.rmtree(ROOT / ".motionloom/pilots/test-ai-pilot-contaminated", ignore_errors=True)
    print("AI pilot builder tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
