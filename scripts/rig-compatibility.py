#!/usr/bin/env python3
"""MotionLoom rig compatibility validator.

This checks an explicit supplied rig contract and its runtime bridge. It does
not generate a rig, invent missing bones, or upgrade AI-generated material to
artist authority, production eligibility, production approval or a PR.
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
SHA = re.compile(r"^[a-f0-9]{64}$")
STATUSES = {"verified", "project_integrated", "static_validated", "scaffold_only", "disabled"}


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    path: str = ""


def add(issues: list[Issue], code: str, message: str, path: str = "", severity: str = "error") -> None:
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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, issues: list[Issue], label: str) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add(issues, "invalid_json", f"{label}: {exc}", str(path))
        return None
    if not isinstance(data, dict):
        add(issues, "invalid_document", f"{label} must be an object", str(path))
        return None
    return data


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def hash_ref(root: Path, section: dict[str, Any], label: str, issues: list[Issue]) -> Path | None:
    path = resolve(root, section.get("path"))
    if path is None:
        add(issues, "missing_or_unsafe_ref", f"{label}.path must be a safe existing relative file", f"{label}.path")
        return None
    expected = section.get("sha256")
    if not isinstance(expected, str) or not SHA.fullmatch(expected):
        add(issues, "invalid_sha256", f"{label}.sha256 must be lowercase SHA-256", f"{label}.sha256")
    elif digest(path) != expected:
        add(issues, "sha256_mismatch", f"{label} SHA-256 mismatch", f"{label}.sha256")
    return path


def valid_evidence(path: Path, framework: str, issues: list[Issue]) -> bool:
    evidence = load_json(path, issues, "runtime evidence")
    if evidence is None:
        return False
    if evidence.get("mode") != "runtime" or evidence.get("status") != "pass":
        add(issues, "runtime_evidence_not_pass", "runtime evidence must have mode=runtime and status=pass", "runtime.runtime_evidence_ref")
        return False
    frameworks = evidence.get("frameworks")
    if not isinstance(frameworks, list) or not any(isinstance(item, dict) and item.get("framework") == framework and item.get("status") == "pass" and item.get("ready") is True for item in frameworks):
        add(issues, "runtime_framework_mismatch", f"runtime evidence must have a ready passing {framework} framework", "runtime.runtime_evidence_ref")
        return False
    return True


def validate(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    issues: list[Issue] = []
    rig = load_json(args.input.resolve(), issues, "rig compatibility")
    registry = load_json(args.registry.resolve(), issues, "rig adapter registry")
    if rig is None or registry is None:
        return result(rig, issues, None, False)
    for field in ("schema_version", "rig_id", "asset_id", "authority", "source", "candidate", "bones", "sockets", "actions", "runtime"):
        if field not in rig:
            add(issues, "missing_field", f"rig.{field} is required", f"rig.{field}")
    if rig.get("schema_version") != "0.1":
        add(issues, "schema_version", "rig.schema_version must be 0.1", "rig.schema_version")
    if rig.get("authority") not in {"ai_generated", "ai_assisted", "ai_assisted_human_reviewed", "artist_authored", "unknown"}:
        add(issues, "invalid_authority", "rig.authority is unsupported", "rig.authority")
    source = rig.get("source") if isinstance(rig.get("source"), dict) else {}
    candidate_ref = rig.get("candidate") if isinstance(rig.get("candidate"), dict) else {}
    source_path = hash_ref(root, source, "source", issues)
    candidate_path = hash_ref(root, candidate_ref, "candidate", issues)

    adapters: dict[str, dict[str, Any]] = {}
    if registry.get("schema_version") != "0.1":
        add(issues, "registry_schema_version", "registry.schema_version must be 0.1", "registry.schema_version")
    for index, adapter in enumerate(registry.get("adapters", []) if isinstance(registry.get("adapters"), list) else []):
        if not isinstance(adapter, dict) or not isinstance(adapter.get("adapter_id"), str):
            add(issues, "invalid_adapter", "registry adapter requires adapter_id", f"registry.adapters[{index}]")
            continue
        adapters[adapter["adapter_id"]] = adapter
        if adapter.get("status") not in STATUSES:
            add(issues, "invalid_adapter_status", "adapter status is unsupported", f"registry.adapters[{index}].status")
        for evidence in adapter.get("evidence", []) if isinstance(adapter.get("evidence"), list) else []:
            if isinstance(evidence, dict):
                hash_ref(root, evidence, f"registry.adapters[{index}].evidence", issues)

    runtime = rig.get("runtime") if isinstance(rig.get("runtime"), dict) else {}
    adapter = adapters.get(str(runtime.get("adapter_id")))
    if adapter is None:
        add(issues, "unknown_adapter", "runtime.adapter_id is not in rig adapter registry", "runtime.adapter_id")
    else:
        if adapter.get("status") == "disabled":
            add(issues, "adapter_disabled", "runtime adapter is disabled", "runtime.adapter_id")
        if adapter.get("target") != runtime.get("target"):
            add(issues, "runtime_target_mismatch", "rig runtime.target must match adapter target", "runtime.target")
    if runtime.get("review_required") is not True:
        add(issues, "review_required", "rig compatibility cannot suppress human review", "runtime.review_required")

    bones = rig.get("bones") if isinstance(rig.get("bones"), list) else []
    bone_ids: set[str] = set()
    for index, bone in enumerate(bones):
        if not isinstance(bone, dict) or not isinstance(bone.get("id"), str) or not bone["id"].strip() or bone["id"] in bone_ids:
            add(issues, "invalid_bone", "bone IDs must be unique and non-empty", f"bones[{index}]")
            continue
        bone_ids.add(bone["id"])
    for index, bone in enumerate(bones):
        if isinstance(bone, dict) and bone.get("parent") and bone.get("parent") not in bone_ids:
            add(issues, "missing_parent_bone", f"bone parent is missing: {bone.get('parent')}", f"bones[{index}].parent")
    sockets = rig.get("sockets") if isinstance(rig.get("sockets"), list) else []
    socket_ids: set[str] = set()
    for index, socket in enumerate(sockets):
        if not isinstance(socket, dict) or not isinstance(socket.get("id"), str) or not socket["id"].strip() or socket["id"] in socket_ids:
            add(issues, "invalid_socket", "socket IDs must be unique and non-empty", f"sockets[{index}]")
            continue
        socket_ids.add(socket["id"])
        if socket.get("bone") not in bone_ids:
            add(issues, "socket_bone_missing", f"socket bone is missing: {socket.get('bone')}", f"sockets[{index}].bone")
    actions = rig.get("actions") if isinstance(rig.get("actions"), list) else []
    action_ids: set[str] = set()
    action_events: set[str] = set()
    for index, action in enumerate(actions):
        if not isinstance(action, dict) or not isinstance(action.get("id"), str) or not action["id"].strip() or action["id"] in action_ids:
            add(issues, "invalid_action", "action IDs must be unique and non-empty", f"actions[{index}]")
            continue
        action_ids.add(action["id"])
        action_events.update(event for event in action.get("events", []) if isinstance(event, str))
    requirements = rig.get("requirements") if isinstance(rig.get("requirements"), dict) else {}
    for socket in requirements.get("sockets", []) if isinstance(requirements.get("sockets"), list) else []:
        if socket not in socket_ids:
            add(issues, "required_socket_missing", f"required socket is absent: {socket}", "requirements.sockets")
    for action in requirements.get("actions", []) if isinstance(requirements.get("actions"), list) else []:
        if action not in action_ids:
            add(issues, "required_action_missing", f"required action is absent: {action}", "requirements.actions")
    for event in requirements.get("events", []) if isinstance(requirements.get("events"), list) else []:
        if event not in action_events:
            add(issues, "required_event_missing", f"required event is absent: {event}", "requirements.events")

    candidate_result: dict[str, Any] | None = None
    if candidate_path is not None:
        try:
            bridge = load_module("motionloom_runtime_candidate_rig", ROOT / "scripts" / "runtime-candidate.py")
            candidate_result = bridge.validate_candidate(argparse.Namespace(root=root, input=candidate_path, strict=False))
            if not candidate_result.get("runtime_test_ready"):
                add(issues, "candidate_not_ready", "referenced runtime candidate is blocked", "candidate.path")
            if candidate_result.get("asset_id") != rig.get("asset_id"):
                add(issues, "candidate_asset_mismatch", "rig.asset_id must match runtime candidate", "asset_id")
            candidate_doc = load_json(candidate_path, issues, "runtime candidate")
            if candidate_doc is not None and candidate_doc.get("runtime", {}).get("target") != runtime.get("target"):
                add(issues, "candidate_target_mismatch", "rig runtime target must match candidate runtime target", "runtime.target")
        except (OSError, RuntimeError, ValueError, AttributeError, KeyError, TypeError) as exc:
            add(issues, "candidate_unavailable", str(exc), "candidate.path")
    runtime_verified = False
    if "runtime_evidence_ref" in runtime:
        evidence_path = resolve(root, runtime.get("runtime_evidence_ref"))
        if evidence_path is None:
            add(issues, "missing_or_unsafe_runtime_evidence", "runtime evidence reference must be a safe existing file", "runtime.runtime_evidence_ref")
        elif adapter is not None:
            runtime_verified = valid_evidence(evidence_path, str(adapter.get("framework")), issues)
    if args.strict and not runtime_verified:
        add(issues, "runtime_evidence_required", "strict rig validation requires passing matching runtime evidence", "runtime.runtime_evidence_ref")
    return result(rig, issues, adapter, runtime_verified, candidate_result)


def result(rig: dict[str, Any] | None, issues: list[Issue], adapter: dict[str, Any] | None, runtime_verified: bool, candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    errors = [asdict(item) for item in issues if item.severity == "error"]
    warnings = [asdict(item) for item in issues if item.severity == "warning"]
    ready = not errors
    return {"contract": "rig-compatibility", "status": "blocked" if errors else "review_required", "ready": ready, "runtime_verified": runtime_verified, "review_required": True, "production_eligible": False, "production_approved": False, "rig_id": (rig or {}).get("rig_id"), "asset_id": (rig or {}).get("asset_id"), "adapter": {"adapter_id": (adapter or {}).get("adapter_id"), "status": (adapter or {}).get("status")}, "candidate": {"status": (candidate or {}).get("status"), "runtime_test_ready": (candidate or {}).get("runtime_test_ready")}, "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate MotionLoom rig compatibility and runtime adapter evidence")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "report"):
        item = sub.add_parser(command)
        item.add_argument("--input", required=True, type=Path)
        item.add_argument("--registry", type=Path, default=Path("rig-adapter-registry.json"))
        item.add_argument("--root", type=Path, default=Path("."))
        item.add_argument("--strict", action="store_true")
        item.add_argument("--output", type=Path)
        item.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = validate(args)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.command == "validate" or args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"rig-compatibility: {payload['status']} ({len(payload['errors'])} errors, {len(payload['warnings'])} warnings)")
    return 0 if payload["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
