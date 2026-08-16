#!/usr/bin/env python3
"""Verify MotionLoom runtime evidence without granting approval.

The verifier is intentionally independent from the builder-side quality gate.
It checks local identity, hashes, telemetry shape and optional freshness policy.
Exit 0 means the evidence is internally consistent; it never means approved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
VERIFIER = "motionloom-evidence-verifier/1.0"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_json(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def parse_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def reject_symlink_within_root(root: Path, relative: Path, label: str) -> None:
    """Reject links inside an untrusted root, not symlinked system parents.

    macOS exposes /var as a symlink to /private/var. A fixture rooted in mktemp
    must be valid when the root itself is a real directory, while an evidence
    path must never traverse a symlink at or below that root.
    """
    root = root.absolute()
    if root.is_symlink():
        raise ValueError(f"symlink root is not allowed: {label}")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink path component is not allowed: {label}")


def safe_relative_file(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError(f"{label} must be a non-empty relative path")
    candidate = Path(relative)
    if candidate.is_absolute() or "\x00" in relative:
        raise ValueError(f"{label} must be relative")
    if any(part in ("", ".", "..") for part in candidate.parts):
        raise ValueError(f"{label} contains unsafe path components")
    joined = root / candidate
    reject_symlink_within_root(root, candidate, label)
    resolved_root = root.resolve()
    resolved = joined.resolve(strict=False)
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"{label} escapes its evidence root")
    if not resolved.is_file():
        raise ValueError(f"{label} does not point to an existing file")
    return resolved


def verify(scene_dir: Path, task_dir: Path, runtime_evidence_name: str, max_age_days: float | None) -> dict:
    issues: list[str] = []
    scene_dir = scene_dir.absolute()
    task_dir = task_dir.absolute()
    bindings: dict[str, object] = {
        "scene": scene_dir.name,
        "task_id": "",
        "source_sha256": "",
        "manifest_sha256": "",
        "motion_ir_sha256": "",
        "telemetry_files": [],
    }

    try:
        if not SAFE_NAME.fullmatch(scene_dir.name):
            raise ValueError("scene directory name is unsafe")
        if not SAFE_NAME.fullmatch(task_dir.name):
            raise ValueError("task directory name is unsafe")
        if scene_dir.is_symlink():
            raise ValueError("scene directory symlink is not allowed")
        if task_dir.is_symlink():
            raise ValueError("task directory symlink is not allowed")
        manifest_path = safe_relative_file(scene_dir, "manifest.json", "manifest.json")
        source_manifest = parse_json(manifest_path)
        if not isinstance(source_manifest, dict):
            raise ValueError("manifest.json must contain an object")
        task_path = safe_relative_file(task_dir, "task.json", "task.json")
        task = parse_json(task_path)
        if not isinstance(task, dict) or not str(task.get("task_id") or "").strip():
            raise ValueError("task.json.task_id is required")
        task_id = str(task["task_id"])
        bindings["task_id"] = task_id
        if source_manifest.get("scene") and source_manifest.get("scene") != scene_dir.name:
            issues.append("manifest scene does not match scene directory")
        source_path = safe_relative_file(scene_dir, source_manifest.get("file"), "manifest.file")
        source_sha = sha256_file(source_path)
        manifest_sha = sha256_file(manifest_path)
        motion_ir_path = safe_relative_file(task_dir, "motion-ir.json", "motion-ir.json")
        motion_ir_sha = sha256_file(motion_ir_path)
        bindings.update({
            "source_sha256": source_sha,
            "manifest_sha256": manifest_sha,
            "motion_ir_sha256": motion_ir_sha,
        })

        evidence_path = safe_relative_file(task_dir, runtime_evidence_name, "runtime evidence")
        evidence = parse_json(evidence_path)
        if not isinstance(evidence, dict):
            raise ValueError("runtime evidence must contain an object")
        if evidence.get("mode") != "runtime":
            issues.append("runtime evidence mode must be runtime")
        if evidence.get("status") != "pass":
            issues.append("runtime evidence status must be pass")
        for field, expected in (("scene", scene_dir.name), ("task_id", task_id), ("source_sha256", source_sha), ("manifest_sha256", manifest_sha), ("motion_ir_sha256", motion_ir_sha)):
            if evidence.get(field) != expected:
                issues.append(f"runtime evidence {field} does not match canonical binding")

        generated_at = evidence.get("generated_at")
        if max_age_days is not None:
            try:
                observed_at = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
                if observed_at.tzinfo is None:
                    raise ValueError("generated_at must include timezone")
                age_days = (datetime.now(timezone.utc) - observed_at.astimezone(timezone.utc)).total_seconds() / 86400
                if age_days < -1 / 86400:
                    issues.append("runtime evidence generated_at is in the future")
                elif age_days > max_age_days:
                    issues.append(f"runtime evidence is stale: {age_days:.3f} days > {max_age_days:.3f}")
            except (TypeError, ValueError) as exc:
                issues.append(f"runtime evidence generated_at is invalid: {exc}")

        frameworks = evidence.get("frameworks")
        if not isinstance(frameworks, list) or not frameworks:
            issues.append("runtime evidence frameworks must be a non-empty array")
            frameworks = []
        evidence_root = evidence_path.parent
        for item in frameworks:
            if not isinstance(item, dict):
                issues.append("runtime evidence framework entry must be an object")
                continue
            framework = str(item.get("framework") or "unknown")
            telemetry = item.get("telemetry")
            if not isinstance(telemetry, dict):
                issues.append(f"{framework}: telemetry binding is missing")
                continue
            telemetry_name = telemetry.get("file")
            try:
                telemetry_path = safe_relative_file(evidence_root, telemetry_name, f"{framework}.telemetry.file")
                telemetry_sha = sha256_file(telemetry_path)
                if telemetry.get("sha256") != telemetry_sha:
                    issues.append(f"{framework}: telemetry sha256 mismatch")
                telemetry_doc = parse_json(telemetry_path)
                if not isinstance(telemetry_doc, dict):
                    raise ValueError("telemetry must contain an object")
                for field, expected in (("mode", "runtime-telemetry"), ("scene", scene_dir.name), ("task_id", task_id), ("framework", framework), ("source_sha256", source_sha), ("manifest_sha256", manifest_sha), ("motion_ir_sha256", motion_ir_sha), ("status", "pass")):
                    if telemetry_doc.get(field) != expected:
                        issues.append(f"{framework}: telemetry {field} does not match canonical binding")
                samples = telemetry_doc.get("samples")
                if not isinstance(samples, list) or len(samples) < 3:
                    issues.append(f"{framework}: telemetry requires at least three samples")
                    samples = []
                intervals: list[float] = []
                for index, sample in enumerate(samples):
                    if not isinstance(sample, dict):
                        issues.append(f"{framework}: sample {index} is not an object")
                        continue
                    state = sample.get("state")
                    if not isinstance(state, dict) or sample.get("state_sha256") != sha256_json(state):
                        issues.append(f"{framework}: sample {index} state hash mismatch")
                    values = sample.get("raf_intervals_ms")
                    if not isinstance(values, list) or not values or any(not isinstance(value, (int, float)) or value <= 0 or value > 1000 for value in values):
                        issues.append(f"{framework}: sample {index} has invalid RAF intervals")
                    else:
                        intervals.extend(float(value) for value in values)
                metrics = telemetry_doc.get("metrics")
                if not isinstance(metrics, dict) or metrics.get("sample_count") != len(samples) or metrics.get("raf_interval_count") != len(intervals):
                    issues.append(f"{framework}: telemetry metrics count mismatch")
                if intervals and isinstance(metrics, dict):
                    ordered = sorted(intervals)
                    p95_index = min(len(ordered) - 1, max(0, int(__import__("math").ceil(len(ordered) * 0.95) - 1)))
                    if metrics.get("max_raf_interval_ms") != max(intervals) or metrics.get("p95_raf_interval_ms") != ordered[p95_index]:
                        issues.append(f"{framework}: telemetry aggregate metrics mismatch")
                bindings["telemetry_files"].append(str(telemetry_name))
            except (ValueError, OSError, json.JSONDecodeError) as exc:
                issues.append(f"{framework}: {exc}")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        issues.append(str(exc))

    return {
        "schema_version": "1.0",
        "verifier": VERIFIER,
        "verified": not issues,
        "approval": False,
        "issues": issues,
        "bindings": bindings,
        "policy": {"max_age_days": max_age_days} if max_age_days is not None else {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MotionLoom runtime evidence without granting approval")
    parser.add_argument("--scene-dir", required=True)
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--runtime-evidence", default="runtime-adapters/runtime-evidence.json")
    parser.add_argument("--max-age-days", type=float)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = verify(Path(args.scene_dir), Path(args.task_dir), args.runtime_evidence, args.max_age_days)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
