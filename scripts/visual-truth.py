#!/usr/bin/env python3
"""Build and validate MotionLoom's provenance-bound visual truth contract.

The contract is deliberately a review aid, not an approval engine. It compares
real rendered PNG frames, records image dimensions and SHA-256 digests, emits a
small deterministic perceptual summary, and keeps user approval false until a
separate browser review artifact records a human decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "1.0"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SHA256_RE = 64


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(path: Path) -> str:
    return sha256(path)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def png_dimensions(path: Path) -> tuple[int, int]:
    """Read PNG dimensions without requiring Pillow or a system image tool."""
    with path.open("rb") as handle:
        if handle.read(8) != PNG_SIGNATURE:
            raise ValueError(f"not a PNG file: {path}")
        length = struct.unpack(">I", handle.read(4))[0]
        chunk = handle.read(4)
        if chunk != b"IHDR" or length < 8:
            raise ValueError(f"PNG has no IHDR: {path}")
        width, height = struct.unpack(">II", handle.read(8))
        if width <= 0 or height <= 0:
            raise ValueError(f"PNG dimensions are invalid: {path}")
        return width, height


def relpath(path: Path, root: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        raise ValueError(f"path must be inside repository root: {path}")


def display_path(path: Path, root: Path) -> str:
    """Render an output path without weakening repository-bound evidence paths."""
    try:
        return relpath(path, root)
    except ValueError:
        return path.resolve().as_posix()


def frame_record(path: Path, root: Path, role: str, percent: int) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"{role} frame is missing or empty: {path}")
    width, height = png_dimensions(path)
    return {
        "role": role,
        "percent": percent,
        "path": relpath(path, root),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "width": width,
        "height": height,
    }


def perceptual_summary(baseline: dict, candidate: dict) -> dict:
    """Return a conservative perceptual signal based on byte identity.

    A byte-identical PNG is a strong deterministic equality signal. A changed
    PNG is intentionally reported as `review_required`, not as a failed quality
    judgment, because visual acceptability is a user/runtime review decision.
    """
    same_dimensions = (baseline["width"], baseline["height"]) == (candidate["width"], candidate["height"])
    identical = baseline["sha256"] == candidate["sha256"]
    return {
        "metric": "sha256-image-identity",
        "method": "PNG metadata plus byte identity; no visual approval inferred",
        "same_dimensions": same_dimensions,
        "byte_identical": identical,
        "changed": not identical or not same_dimensions,
        "distance": 0.0 if identical and same_dimensions else 1.0,
        "threshold": 0.0,
        "interpretation": "equal" if identical and same_dimensions else "review_required",
    }


def build(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    output = Path(args.output)
    if not output.is_absolute():
        output = (root / output).resolve()
    scene = str(args.scene)
    if not scene or scene in {".", ".."} or "/" in scene or "\\" in scene:
        print("visual-truth: unsafe scene identifier", file=sys.stderr)
        return 2
    try:
        baseline = Path(args.baseline)
        candidate = Path(args.candidate)
        if not baseline.is_absolute():
            baseline = (root / baseline).resolve()
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        source = Path(args.source)
        manifest = Path(args.manifest)
        runtime_evidence = Path(args.runtime_evidence) if args.runtime_evidence else None
        motion_ir = Path(args.motion_ir) if args.motion_ir else None
        for value in (source, manifest, runtime_evidence, motion_ir):
            if value is not None and not value.is_absolute():
                value = (root / value).resolve()
        # Rebind optional paths after the loop because Path is immutable.
        if args.runtime_evidence:
            runtime_evidence = (root / args.runtime_evidence).resolve() if not Path(args.runtime_evidence).is_absolute() else Path(args.runtime_evidence).resolve()
        if args.motion_ir:
            motion_ir = (root / args.motion_ir).resolve() if not Path(args.motion_ir).is_absolute() else Path(args.motion_ir).resolve()
        source = (root / args.source).resolve() if not Path(args.source).is_absolute() else Path(args.source).resolve()
        manifest = (root / args.manifest).resolve() if not Path(args.manifest).is_absolute() else Path(args.manifest).resolve()
        baseline_record = frame_record(baseline, root, "baseline", args.percent)
        candidate_record = frame_record(candidate, root, "candidate", args.percent)
        manifest_data = load_json(manifest)
        if not source.is_file() or not manifest.is_file():
            raise ValueError("source and manifest must exist")
        runtime_data = load_json(runtime_evidence) if runtime_evidence else None
        motion_data = load_json(motion_ir) if motion_ir else None
        source_hash = sha256(source)
        manifest_hash = sha256(manifest)
        motion_hash = sha256(motion_ir) if motion_ir else None
        runtime_hash = sha256(runtime_evidence) if runtime_evidence else None
        if manifest_data.get("file") and not str(manifest_data["file"]).strip():
            raise ValueError("manifest.file must be non-empty")
        if runtime_data is not None:
            if runtime_data.get("status") != "pass":
                raise ValueError("runtime evidence status must be pass")
            if args.task_id and runtime_data.get("task_id") not in {None, args.task_id}:
                raise ValueError("runtime evidence task_id does not match requested task")
            if runtime_data.get("scene") not in {None, scene}:
                raise ValueError("runtime evidence scene does not match requested scene")
        comparison = perceptual_summary(baseline_record, candidate_record)
        changed_regions = []
        if comparison["changed"]:
            changed_regions.append({
                "id": "full-frame",
                "label": "Full rendered frame",
                "reason": "Baseline and candidate PNG identities differ; inspect the exact candidate in Dev Lab.",
                "severity": "review",
                "evidence": [baseline_record["path"], candidate_record["path"]],
            })
        report = {
            "schema_version": SCHEMA_VERSION,
            "contract": "motionloom-visual-truth",
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "review_required" if comparison["changed"] else "pass",
            "scene": scene,
            "task_id": args.task_id or None,
            "frames": {
                "baseline": baseline_record,
                "candidate": candidate_record,
            },
            "comparison": comparison,
            "regions": changed_regions,
            "provenance": {
                "source_path": relpath(source, root),
                "source_sha256": source_hash,
                "manifest_path": relpath(manifest, root),
                "manifest_sha256": manifest_hash,
                "runtime_evidence_path": relpath(runtime_evidence, root) if runtime_evidence else None,
                "runtime_evidence_sha256": runtime_hash,
                "motion_ir_path": relpath(motion_ir, root) if motion_ir else None,
                "motion_ir_sha256": motion_hash,
                "runtime_status": runtime_data.get("status") if runtime_data else None,
                "motion_ir_schema_version": motion_data.get("schema_version") if motion_data else None,
            },
            "review_boundary": {
                "approval": False,
                "user_review_required": True,
                "decision": "pending",
                "pr_side_effects": "explicit-confirmation",
            },
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"visual-truth: {exc}", file=sys.stderr)
        return 1


def validate_report(path: Path, root: Path | None = None, expected_scene: str | None = None, expected_task_id: str | None = None, expected_source_sha256: str | None = None, expected_manifest_sha256: str | None = None, expected_motion_ir_sha256: str | None = None) -> list[str]:
    root = (root or path.parent).resolve()
    errors: list[str] = []
    try:
        data = load_json(path)
    except ValueError as exc:
        return [str(exc)]
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append("visual truth schema_version must be 1.0")
    if data.get("contract") != "motionloom-visual-truth":
        errors.append("visual truth contract identifier is invalid")
    if data.get("status") not in {"pass", "review_required"}:
        errors.append("visual truth status must be pass or review_required")
    if expected_scene and data.get("scene") != expected_scene:
        errors.append("visual truth scene does not match requested scene")
    if expected_task_id and data.get("task_id") != expected_task_id:
        errors.append("visual truth task_id does not match task bundle")
    boundary = data.get("review_boundary")
    if not isinstance(boundary, dict) or boundary.get("approval") is not False or boundary.get("user_review_required") is not True:
        errors.append("visual truth must preserve approval=false and user_review_required=true")
    frames = data.get("frames")
    if not isinstance(frames, dict) or not isinstance(frames.get("baseline"), dict) or not isinstance(frames.get("candidate"), dict):
        errors.append("visual truth must contain baseline and candidate frame records")
    else:
        for role in ("baseline", "candidate"):
            frame = frames[role]
            if frame.get("role") != role or not isinstance(frame.get("sha256"), str) or len(frame.get("sha256", "")) != SHA256_RE:
                errors.append(f"visual truth {role} frame hash is invalid")
            frame_path = root / str(frame.get("path", ""))
            try:
                if not frame_path.is_file() or sha256(frame_path) != frame.get("sha256"):
                    errors.append(f"visual truth {role} frame hash/path binding is stale")
                elif png_dimensions(frame_path) != (frame.get("width"), frame.get("height")):
                    errors.append(f"visual truth {role} frame dimensions are stale")
            except (OSError, ValueError):
                errors.append(f"visual truth {role} frame is not a readable PNG")
    provenance = data.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("visual truth provenance is required")
    else:
        for label, expected in (("source_sha256", expected_source_sha256), ("manifest_sha256", expected_manifest_sha256), ("motion_ir_sha256", expected_motion_ir_sha256)):
            if expected and provenance.get(label) != expected:
                errors.append(f"visual truth {label} does not match current artifact")
        for label in ("source_path", "manifest_path"):
            path_value = provenance.get(label)
            if not isinstance(path_value, str) or Path(path_value).is_absolute() or ".." in Path(path_value).parts:
                errors.append(f"visual truth {label} must be a safe repository-relative path")
    comparison = data.get("comparison")
    if not isinstance(comparison, dict) or comparison.get("interpretation") not in {"equal", "review_required"}:
        errors.append("visual truth comparison interpretation is invalid")
    return errors


def validate(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    path = Path(args.input)
    if not path.is_absolute():
        path = (root / path).resolve()
    errors = validate_report(path, root, args.scene, args.task_id, args.source_sha256, args.manifest_sha256, args.motion_ir_sha256)
    result = {"status": "pass" if not errors else "fail", "path": display_path(path, root), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--root", default=".")
    build_parser.add_argument("--scene", required=True)
    build_parser.add_argument("--baseline", required=True)
    build_parser.add_argument("--candidate", required=True)
    build_parser.add_argument("--percent", type=int, default=100)
    build_parser.add_argument("--source", required=True)
    build_parser.add_argument("--manifest", required=True)
    build_parser.add_argument("--runtime-evidence")
    build_parser.add_argument("--motion-ir")
    build_parser.add_argument("--task-id")
    build_parser.add_argument("--output", required=True)
    build_parser.set_defaults(func=build)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--root", default=".")
    validate_parser.add_argument("--input", required=True)
    validate_parser.add_argument("--scene")
    validate_parser.add_argument("--task-id")
    validate_parser.add_argument("--source-sha256")
    validate_parser.add_argument("--manifest-sha256")
    validate_parser.add_argument("--motion-ir-sha256")
    validate_parser.set_defaults(func=validate)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
