#!/usr/bin/env python3
"""Fail-closed Rive package gate for MotionLoom.

The gate binds a concrete `.riv` file to provenance, a project-integrated Rive
runtime adapter and (optionally/strictly) a captured runtime proof. It does not
parse a proprietary Rive graph, invent missing state-machine data, create a
placeholder production package, or grant approval of any kind.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SAFE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$)).+")
SHA = re.compile(r"^[a-f0-9]{64}$")


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


def load_json(path: Path, issues: list[Issue], label: str) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        add(issues, "invalid_json", f"{label}: {exc}", str(path))
        return None
    if not isinstance(value, dict):
        add(issues, "invalid_document", f"{label} must be a JSON object", str(path))
        return None
    return value


def resolve(root: Path, value: Any) -> Path | None:
    if not safe(value):
        return None
    raw = root / str(value)
    try:
        result = raw.resolve()
        result.relative_to(root.resolve())
    except ValueError:
        return None
    return result if not raw.is_symlink() and result.is_file() else None


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


def validate_registry(root: Path, registry_path: Path, adapter_id: Any, issues: list[Issue]) -> bool:
    registry = load_json(registry_path, issues, "rig adapter registry")
    if registry is None:
        return False
    adapters = registry.get("adapters")
    if registry.get("schema_version") != "0.1" or not isinstance(adapters, list):
        add(issues, "invalid_registry", "rig adapter registry schema_version/adapters are invalid", "registry")
        return False
    adapter = next((item for item in adapters if isinstance(item, dict) and item.get("adapter_id") == adapter_id), None)
    if adapter is None:
        add(issues, "unknown_adapter", "runtime.adapter_id is not registered", "runtime.adapter_id")
        return False
    if adapter.get("target") != "rive" or adapter.get("framework") != "rive":
        add(issues, "adapter_target_mismatch", "registered adapter must target the Rive runtime", "runtime.adapter_id")
    if adapter.get("status") not in {"project_integrated", "verified"}:
        add(issues, "adapter_not_integrated", "Rive adapter must be project_integrated or verified", "runtime.adapter_id")
    evidence = adapter.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        add(issues, "adapter_evidence_missing", "registered Rive adapter requires hash-bound evidence", "registry.adapters.evidence")
    else:
        for index, item in enumerate(evidence):
            path = resolve(root, item.get("path") if isinstance(item, dict) else None)
            expected = item.get("sha256") if isinstance(item, dict) else None
            if path is None or not isinstance(expected, str) or not SHA.fullmatch(expected):
                add(issues, "adapter_evidence_invalid", "adapter evidence needs a safe existing path and SHA-256", f"registry.adapters.evidence[{index}]")
            elif digest(path) != expected:
                add(issues, "adapter_evidence_tampered", "adapter evidence SHA-256 mismatch", f"registry.adapters.evidence[{index}]")
    return True


def validate_runtime_evidence(root: Path, runtime: dict[str, Any], source_hash: str, strict: bool, issues: list[Issue]) -> bool:
    ref = runtime.get("runtime_evidence_ref")
    expected = runtime.get("runtime_evidence_sha256")
    if ref is None and expected is None:
        if strict:
            add(issues, "runtime_evidence_required", "strict mode requires runtime.runtime_evidence_ref and SHA-256", "runtime")
        return False
    path = resolve(root, ref)
    if path is None or not isinstance(expected, str) or not SHA.fullmatch(expected):
        add(issues, "runtime_evidence_invalid_ref", "runtime evidence needs a safe existing JSON path and SHA-256", "runtime")
        return False
    if digest(path) != expected:
        add(issues, "runtime_evidence_tampered", "runtime evidence SHA-256 mismatch", "runtime.runtime_evidence_sha256")
        return False
    evidence = load_json(path, issues, "runtime evidence")
    if evidence is None:
        return False
    valid = True
    if evidence.get("mode") != "runtime" or evidence.get("status") != "pass":
        add(issues, "runtime_evidence_not_pass", "runtime evidence must have mode=runtime and status=pass", "runtime.runtime_evidence_ref")
        valid = False
    if evidence.get("source_sha256") != source_hash:
        add(issues, "runtime_source_unbound", "runtime evidence source_sha256 must bind this exact .riv file", "runtime.runtime_evidence_ref")
        valid = False
    frameworks = evidence.get("frameworks")
    if not isinstance(frameworks, list) or not any(isinstance(item, dict) and item.get("framework") == "rive" and item.get("status") == "pass" and item.get("ready") is True for item in frameworks):
        add(issues, "runtime_framework_mismatch", "runtime evidence needs a ready passing Rive framework result", "runtime.runtime_evidence_ref")
        valid = False
    return valid


def validate(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    issues: list[Issue] = []
    manifest = load_json(args.input.resolve(), issues, "Rive package manifest")
    if manifest is None:
        return result(None, issues, False)
    for field in ("schema_version", "package_id", "package_class", "asset", "provenance_ref", "runtime", "actions", "review_required"):
        if field not in manifest:
            add(issues, "missing_field", f"{field} is required", field)
    if manifest.get("schema_version") != "0.1":
        add(issues, "schema_version", "schema_version must be 0.1", "schema_version")
    if manifest.get("package_class") not in {"ai_generated_pilot", "production_candidate"}:
        add(issues, "invalid_package_class", "package_class must be ai_generated_pilot or production_candidate", "package_class")
    if manifest.get("review_required") is not True:
        add(issues, "review_required", "Rive package gate cannot suppress human review", "review_required")

    asset = manifest.get("asset") if isinstance(manifest.get("asset"), dict) else {}
    source = resolve(root, asset.get("path"))
    source_hash = asset.get("sha256")
    if source is None or source.suffix.lower() != ".riv":
        add(issues, "missing_or_unsafe_riv", "asset.path must be a safe existing .riv file", "asset.path")
    elif source.read_bytes()[:4] != b"RIVE":
        add(issues, "rive_magic_invalid", "asset.path is not a Rive binary (missing RIVE header)", "asset.path")
    if not isinstance(source_hash, str) or not SHA.fullmatch(source_hash):
        add(issues, "invalid_asset_sha256", "asset.sha256 must be lowercase SHA-256", "asset.sha256")
    elif source is not None and digest(source) != source_hash:
        add(issues, "asset_sha256_mismatch", "asset.sha256 does not bind the .riv bytes", "asset.sha256")
    if not isinstance(asset.get("bytes"), int) or asset.get("bytes") < 5:
        add(issues, "invalid_asset_bytes", "asset.bytes must be the actual non-zero .riv byte count", "asset.bytes")
    elif source is not None and source.stat().st_size != asset.get("bytes"):
        add(issues, "asset_bytes_mismatch", "asset.bytes does not bind the .riv byte count", "asset.bytes")

    provenance_ok = False
    provenance_path = resolve(root, manifest.get("provenance_ref"))
    if provenance_path is None:
        add(issues, "missing_or_unsafe_provenance", "provenance_ref must be a safe existing JSON file", "provenance_ref")
    else:
        provenance = load_json(provenance_path, issues, "asset provenance")
        try:
            module = load_module("motionloom_asset_provenance", ROOT / "scripts" / "asset-provenance.py")
            provenance_errors = module.validate_document(provenance or {}) + module.validate_files(provenance or {}, root)
        except Exception as exc:  # defensive boundary: never accept if the checker fails
            provenance_errors = [f"provenance validator failed: {exc}"]
        for message in provenance_errors:
            add(issues, "invalid_provenance", message, "provenance_ref")
        if not provenance_errors and provenance is not None:
            files = provenance.get("files") if isinstance(provenance.get("files"), list) else []
            file_match = any(isinstance(item, dict) and item.get("path") == asset.get("path") and item.get("sha256") == source_hash for item in files)
            if not file_match:
                add(issues, "provenance_file_unbound", "provenance must list this exact .riv path and SHA-256", "provenance_ref")
            elif provenance.get("asset", {}).get("id") != asset.get("id"):
                add(issues, "provenance_asset_mismatch", "provenance asset.id must match package asset.id", "provenance_ref")
            elif provenance.get("authority") == "ai_generated" and manifest.get("package_class") != "ai_generated_pilot":
                add(issues, "ai_class_mismatch", "ai_generated provenance requires package_class=ai_generated_pilot", "package_class")
            elif provenance.get("authority") == "ai_generated" and provenance.get("readiness") != "runtime_ready":
                add(issues, "ai_readiness_invalid", "ai_generated Rive packages must remain runtime_ready", "provenance_ref")
            else:
                provenance_ok = True

    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    if runtime.get("target") != "rive" or runtime.get("review_required") is not True:
        add(issues, "runtime_contract_invalid", "runtime target must be rive and review_required must be true", "runtime")
    for name in ("required_state_machines", "required_inputs", "required_events"):
        value = runtime.get(name)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            add(issues, "runtime_controls_invalid", f"runtime.{name} must be an array of non-empty strings", f"runtime.{name}")
    actions = manifest.get("actions")
    if not isinstance(actions, list) or not actions or len(set(actions)) != len(actions) or any(not isinstance(item, str) or not item.strip() for item in actions):
        add(issues, "actions_invalid", "actions must be a non-empty list of unique non-empty strings", "actions")
    validate_registry(root, args.registry.resolve(), runtime.get("adapter_id"), issues)
    runtime_ok = validate_runtime_evidence(root, runtime, source_hash if isinstance(source_hash, str) else "", args.strict, issues)
    return result(manifest, issues, provenance_ok and runtime_ok)


def result(manifest: dict[str, Any] | None, issues: list[Issue], runtime_evidence_valid: bool) -> dict[str, Any]:
    errors = [issue for issue in issues if issue.severity == "error"]
    return {
        "contract": "rive-package-gate",
        "package_id": manifest.get("package_id") if isinstance(manifest, dict) else None,
        "status": "blocked" if errors else "pass",
        "runtime_test_ready": not errors and runtime_evidence_valid,
        "review_required": True,
        "production_approved": False,
        "issues": [asdict(issue) for issue in issues],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a real Rive package without granting approval")
    parser.add_argument("validate", nargs="?", default="validate")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=ROOT / "rig-adapter-registry.json")
    parser.add_argument("--strict", action="store_true", help="Require source-bound runtime evidence")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = validate(args)
    print(json.dumps(payload, indent=2))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
