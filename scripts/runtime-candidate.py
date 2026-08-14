#!/usr/bin/env python3
"""MotionLoom control-to-runtime candidate bridge.

This contract links a provider-neutral Artifact Intake bundle to the existing
identity/action/frame/atlas/map contracts. It is deterministic, standard
library only, and intentionally reports runtime-test readiness rather than any
form of production approval or user review outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SAFE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$)).+")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
KINDS = {"asset_identity": "identity", "action_set": "action-set", "frame_geometry": "frame-geometry", "atlas": "atlas", "layered_map": "layered-map"}
PROFILE_REQUIREMENTS = {
    "image": {"asset_identity"},
    "frame_sequence": {"asset_identity", "action_set", "frame_geometry"},
    "sprite_atlas": {"asset_identity", "action_set", "frame_geometry", "atlas"},
    "layered_map": {"asset_identity", "layered_map"},
    "video": {"asset_identity", "action_set"},
    "rigged_2d": {"asset_identity", "action_set"},
    "rigged_3d": {"asset_identity", "action_set"},
}


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    path: str = ""


def issue(issues: list[Issue], code: str, message: str, path: str = "", severity: str = "error") -> None:
    issues.append(Issue(severity, code, message, path))


def safe(value: Any) -> bool:
    return isinstance(value, str) and "\\" not in value and bool(SAFE.fullmatch(value))


def resolve(root: Path, value: Any) -> Path | None:
    if not safe(value):
        return None
    raw = root / str(value)
    try:
        path = raw.resolve()
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path if not raw.is_symlink() and path.is_file() else None


def load_json(path: Path, issues: list[Issue], label: str) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issue(issues, "invalid_json", f"{label}: {exc}", str(path))
        return None
    if not isinstance(value, dict):
        issue(issues, "invalid_document", f"{label} root must be an object", str(path))
        return None
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def required(document: dict[str, Any], fields: tuple[str, ...], prefix: str, issues: list[Issue]) -> None:
    for field in fields:
        if field not in document:
            issue(issues, "missing_field", f"{prefix}.{field} is required", f"{prefix}.{field}")


def valid_datetime(value: Any) -> bool:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def resolve_group(root: Path, document: dict[str, Any], key: str, fields: tuple[str, ...], issues: list[Issue]) -> dict[str, Path]:
    group = document.get(key) if isinstance(document.get(key), dict) else {}
    required(group, fields, key, issues)
    resolved: dict[str, Path] = {}
    for field in fields:
        path = resolve(root, group.get(field))
        if path is None:
            issue(issues, "missing_or_unsafe_ref", f"{key}.{field} must be an existing safe relative file", f"{key}.{field}")
        else:
            resolved[field] = path
    return resolved


def validate_runtime_evidence(path: Path, issues: list[Issue]) -> bool:
    evidence = load_json(path, issues, "runtime evidence")
    if evidence is None:
        return False
    if evidence.get("mode") != "runtime" or evidence.get("status") != "pass":
        issue(issues, "runtime_evidence_not_pass", "runtime evidence must record mode=runtime and status=pass", "runtime.runtime_evidence_ref")
        return False
    frameworks = evidence.get("frameworks")
    if not isinstance(frameworks, list) or not frameworks or any(item.get("status") != "pass" or item.get("ready") is not True for item in frameworks if isinstance(item, dict)):
        issue(issues, "runtime_framework_not_ready", "runtime evidence requires at least one ready passing framework", "runtime.runtime_evidence_ref")
        return False
    return True


def validate_candidate(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    issues: list[Issue] = []
    candidate_path = args.input.resolve()
    candidate = load_json(candidate_path, issues, "runtime candidate")
    if candidate is None:
        return result(None, issues, {}, None, False)
    required(candidate, ("schema_version", "candidate_id", "asset_id", "created_at", "artifact_intake", "consistency", "runtime"), "candidate", issues)
    if candidate.get("schema_version") != "0.1":
        issue(issues, "schema_version", "candidate.schema_version must be 0.1", "candidate.schema_version")
    if not isinstance(candidate.get("candidate_id"), str) or len(candidate["candidate_id"]) < 3:
        issue(issues, "invalid_candidate_id", "candidate_id must be a non-empty stable ID", "candidate.candidate_id")
    if not isinstance(candidate.get("asset_id"), str) or not candidate["asset_id"].strip():
        issue(issues, "invalid_asset_id", "asset_id must be non-empty", "candidate.asset_id")
    if not valid_datetime(candidate.get("created_at")):
        issue(issues, "invalid_datetime", "created_at must be ISO-8601", "candidate.created_at")
    intake_paths = resolve_group(root, candidate, "artifact_intake", ("registry", "receipt", "controls", "export_manifest"), issues)
    consistency_paths = resolve_group(root, candidate, "consistency", ("asset_identity", "action_set"), issues)
    consistency_group = candidate.get("consistency") if isinstance(candidate.get("consistency"), dict) else {}
    for name in ("frame_geometry", "atlas", "layered_map"):
        if name in consistency_group:
            path = resolve(root, consistency_group.get(name))
            if path is None:
                issue(issues, "missing_or_unsafe_ref", f"consistency.{name} must be an existing safe relative file", f"consistency.{name}")
            else:
                consistency_paths[name] = path
    runtime = candidate.get("runtime") if isinstance(candidate.get("runtime"), dict) else {}
    if runtime.get("review_required") is not True:
        issue(issues, "review_required", "runtime.review_required must be true; candidate evidence cannot replace human review", "runtime.review_required")
    if runtime.get("target") not in {"sprite", "canvas", "lottie", "dotlottie", "rive", "gsap", "framer-motion", "spine", "three"}:
        issue(issues, "invalid_runtime_target", "runtime.target is unsupported", "runtime.target")

    intake_result: dict[str, Any] | None = None
    controls: dict[str, Any] | None = None
    export: dict[str, Any] | None = None
    if len(intake_paths) == 4:
        try:
            intake = load_module("motionloom_artifact_intake_bridge", ROOT / "scripts" / "artifact-intake.py")
            # Intake strictness evaluates provider adapter authority. Candidate strictness
            # evaluates actual runtime evidence below; a static intake adapter must not be
            # promoted, but it can feed a separately tested runtime candidate.
            intake_result = intake.evaluate_bundle(argparse.Namespace(root=root, registry=intake_paths["registry"], receipt=intake_paths["receipt"], controls=intake_paths["controls"], export_manifest=intake_paths["export_manifest"], strict=False))
            for entry in intake_result.get("errors", []):
                issue(issues, f"intake_{entry.get('code', 'error')}", entry.get("message", "artifact intake error"), entry.get("path", "artifact_intake"))
            controls = load_json(intake_paths["controls"], issues, "control track")
            export = load_json(intake_paths["export_manifest"], issues, "export manifest")
            receipt = load_json(intake_paths["receipt"], issues, "generation receipt")
            for label, document in (("receipt", receipt), ("controls", controls), ("export", export)):
                if document is not None and document.get("asset_id", document.get("asset", {}).get("id")) != candidate.get("asset_id"):
                    issue(issues, "asset_id_mismatch", f"candidate.asset_id must match {label} asset ID", f"{label}.asset_id")
        except (OSError, ValueError, AttributeError, KeyError, TypeError, RuntimeError) as exc:
            issue(issues, "artifact_intake_unavailable", str(exc), "artifact_intake")

    consistency_results: dict[str, Any] = {}
    try:
        analyzer = load_module("motionloom_asset_consistency_bridge", ROOT / "scripts" / "asset-consistency.py")
        for name, path in consistency_paths.items():
            document = load_json(path, issues, f"consistency {name}")
            if document is None:
                continue
            check = analyzer.run(KINDS[name], document, path.parent.resolve(), args.strict)
            consistency_results[name] = check
            for entry in check.get("errors", []):
                issue(issues, f"consistency_{entry.get('code', 'error')}", entry.get("message", "consistency error"), f"consistency.{name}")
            if name in {"asset_identity", "action_set", "frame_geometry"} and document.get("asset_id", document.get("asset_identity")) != candidate.get("asset_id"):
                issue(issues, "consistency_asset_id_mismatch", f"candidate.asset_id must match consistency.{name}", f"consistency.{name}")
    except (OSError, ValueError, AttributeError, KeyError, TypeError, RuntimeError) as exc:
        issue(issues, "consistency_unavailable", str(exc), "consistency")

    profile = ((controls or {}).get("output_profile") or {}).get("kind")
    for name in PROFILE_REQUIREMENTS.get(str(profile), set()):
        if name not in consistency_paths:
            issue(issues, "missing_profile_contract", f"{profile} requires consistency.{name}", f"consistency.{name}")
    if profile not in PROFILE_REQUIREMENTS:
        issue(issues, "unknown_output_profile", "control output_profile.kind is unsupported for runtime bridging", "controls.output_profile.kind")

    output_paths: dict[Path, dict[str, Any]] = {}
    for entry in ((export or {}).get("outputs") or []):
        if isinstance(entry, dict):
            path = resolve(root, entry.get("path"))
            if path is not None:
                output_paths[path] = entry
    action = consistency_results.get("action_set", {}).get("metrics", {}).get("actions", [])
    action_doc = load_json(consistency_paths["action_set"], issues, "action set") if "action_set" in consistency_paths else None
    action_frames: list[Path] = []
    if isinstance(action_doc, dict):
        for item in action_doc.get("actions", []):
            if isinstance(item, dict):
                action_frames.extend((consistency_paths["action_set"].parent / str(frame)).resolve() for frame in item.get("frames", []) if safe(frame))
        profile_data = (controls or {}).get("output_profile") or {}
        expected_count = profile_data.get("expected_frame_count")
        if profile in {"frame_sequence", "sprite_atlas"} and isinstance(expected_count, int) and len(action_frames) != expected_count:
            issue(issues, "frame_count_mismatch", "control expected_frame_count must match action-set frame count", "controls.output_profile.expected_frame_count")
        if profile in {"frame_sequence", "sprite_atlas"}:
            for frame in action_frames:
                if frame not in output_paths:
                    issue(issues, "unexported_action_frame", f"action frame is not hash-bound in export manifest: {frame.name}", "export_manifest.outputs")
    geometry_doc = load_json(consistency_paths["frame_geometry"], issues, "frame geometry") if "frame_geometry" in consistency_paths else None
    if isinstance(geometry_doc, dict):
        for frame in geometry_doc.get("frames", []):
            if isinstance(frame, dict) and safe(frame.get("image")):
                path = (consistency_paths["frame_geometry"].parent / str(frame["image"])).resolve()
                export_entry = output_paths.get(path)
                if export_entry is None:
                    issue(issues, "unexported_geometry_frame", f"geometry frame is not hash-bound in export manifest: {path.name}", "export_manifest.outputs")
                elif not isinstance(frame.get("sha256"), str) or frame.get("sha256") != export_entry.get("sha256") or digest(path) != frame.get("sha256"):
                    issue(issues, "frame_hash_mismatch", f"geometry/export hash mismatch: {path.name}", "frame_geometry.frames")

    runtime_verified = False
    if "runtime_evidence_ref" in runtime:
        evidence_path = resolve(root, runtime.get("runtime_evidence_ref"))
        if evidence_path is None:
            issue(issues, "missing_or_unsafe_runtime_evidence", "runtime.runtime_evidence_ref must be an existing safe relative file", "runtime.runtime_evidence_ref")
        else:
            runtime_verified = validate_runtime_evidence(evidence_path, issues)
    if args.strict and not runtime_verified:
        issue(issues, "runtime_evidence_required", "strict runtime candidate validation requires passing runtime evidence", "runtime.runtime_evidence_ref")
    return result(candidate, issues, consistency_results, intake_result, runtime_verified)


def result(candidate: dict[str, Any] | None, issues: list[Issue], consistency: dict[str, Any], intake: dict[str, Any] | None, runtime_verified: bool) -> dict[str, Any]:
    errors = [asdict(item) for item in issues if item.severity == "error"]
    warnings = [asdict(item) for item in issues if item.severity == "warning"]
    ready = not errors
    return {
        "contract": "runtime-candidate",
        "status": "blocked" if errors else "review_required",
        "runtime_test_ready": ready,
        "runtime_verified": runtime_verified,
        "review_required": True,
        "production_eligible": False,
        "production_approved": False,
        "candidate_id": (candidate or {}).get("candidate_id"),
        "asset_id": (candidate or {}).get("asset_id"),
        "intake": {"status": (intake or {}).get("status"), "adapter": (intake or {}).get("adapter")},
        "consistency": {name: {"status": value.get("status"), "ready": value.get("ready")} for name, value in consistency.items()},
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind MotionLoom artifact intake and consistency evidence into a runtime-test candidate")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "report"):
        item = sub.add_parser(command)
        item.add_argument("--input", required=True, type=Path)
        item.add_argument("--root", type=Path, default=Path("."))
        item.add_argument("--strict", action="store_true")
        item.add_argument("--output", type=Path)
        item.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = validate_candidate(args)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.command == "validate" or args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"runtime-candidate: {payload['status']} ({len(payload['errors'])} errors, {len(payload['warnings'])} warnings)")
        for entry in payload["errors"] + payload["warnings"]:
            print(f"- {entry['severity']}: {entry['code']}: {entry['message']}")
    return 0 if payload["runtime_test_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
