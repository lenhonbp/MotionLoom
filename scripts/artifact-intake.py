#!/usr/bin/env python3
"""MotionLoom Artifact Intake.

Style: Timeline Desk — bind generation controls, provider receipt, provenance
and exported bytes before a runtime candidate reaches Dev Lab. This tool uses
only the standard library, does not invoke a provider or skill, and never
creates artist authority, production eligibility, production approval or a PR.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[a-f0-9]{64}$")
SAFE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$)).+")
AUTHORITY = {"ai_generated", "ai_assisted", "ai_assisted_human_reviewed", "artist_authored", "code_authored", "unknown"}
ADAPTER_STATUS = {"verified", "scaffold_only", "static_validated", "project_integrated", "disabled"}
SENSITIVE_KEYS = {"api_key", "apikey", "token", "secret", "password", "authorization", "credential"}


@dataclass
class Issue:
    severity: str
    code: str
    message: str
    path: str = ""


def _issue(issues: list[Issue], code: str, message: str, path: str = "", severity: str = "error") -> None:
    issues.append(Issue(severity, code, message, path))


def _read_json(path: Path, issues: list[Issue], label: str) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _issue(issues, "invalid_json", f"{label}: {exc}", str(path))
        return None
    if not isinstance(value, dict):
        _issue(issues, "invalid_document", f"{label} root must be an object", str(path))
        return None
    return value


def _datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _hash(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256.fullmatch(value))


def _safe(value: Any) -> bool:
    return isinstance(value, str) and "\\" not in value and bool(SAFE.fullmatch(value))


def _resolve(root: Path, value: Any) -> Path | None:
    if not _safe(value):
        return None
    raw = root / str(value)
    try:
        resolved = raw.resolve()
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    if raw.is_symlink() or not resolved.is_file():
        return None
    return resolved


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _required(doc: dict[str, Any], fields: tuple[str, ...], prefix: str, issues: list[Issue]) -> None:
    for field in fields:
        if field not in doc:
            _issue(issues, "missing_field", f"{prefix}.{field} is required", f"{prefix}.{field}")


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _forbidden_secrets(value: Any, issues: list[Issue], path: str = "") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            current = f"{path}.{key}" if path else str(key)
            if str(key).lower() in SENSITIVE_KEYS:
                _issue(issues, "secret_forbidden", "artifact intake must not store credentials or tokens", current)
            _forbidden_secrets(item, issues, current)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _forbidden_secrets(item, issues, f"{path}[{index}]")


def _validate_file_entries(entries: Any, root: Path, prefix: str, issues: list[Issue]) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or not entries:
        _issue(issues, "missing_outputs", f"{prefix} must contain at least one file", prefix)
        return []
    seen: set[str] = set()
    valid: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        path = f"{prefix}[{index}]"
        if not isinstance(entry, dict):
            _issue(issues, "invalid_file_entry", "file entry must be an object", path)
            continue
        _required(entry, ("path", "sha256"), path, issues)
        file_ref = entry.get("path")
        if not _safe(file_ref):
            _issue(issues, "unsafe_path", "path must be a safe relative path", f"{path}.path")
            continue
        if file_ref in seen:
            _issue(issues, "duplicate_output", f"duplicate artifact path: {file_ref}", f"{path}.path")
        seen.add(str(file_ref))
        if not _hash(entry.get("sha256")):
            _issue(issues, "invalid_sha256", "sha256 must be lowercase SHA-256", f"{path}.sha256")
        target = _resolve(root, file_ref)
        if target is None:
            _issue(issues, "artifact_missing", f"artifact missing or unsafe: {file_ref}", f"{path}.path")
            continue
        if _hash(entry.get("sha256")) and _digest(target) != entry["sha256"]:
            _issue(issues, "sha256_mismatch", f"artifact SHA-256 mismatch: {file_ref}", f"{path}.sha256")
        if "bytes" in entry and (not isinstance(entry["bytes"], int) or entry["bytes"] < 0 or target.stat().st_size != entry["bytes"]):
            _issue(issues, "byte_count_mismatch", f"artifact byte count mismatch: {file_ref}", f"{path}.bytes")
        valid.append(entry)
    return valid


def validate_registry(registry: dict[str, Any], root: Path) -> tuple[list[Issue], dict[str, dict[str, Any]]]:
    issues: list[Issue] = []
    _required(registry, ("schema_version", "registry_id", "generated_at", "selection_policy", "adapters"), "registry", issues)
    if registry.get("schema_version") != "0.1":
        _issue(issues, "schema_version", "registry.schema_version must be 0.1", "registry.schema_version")
    if not _datetime(registry.get("generated_at")):
        _issue(issues, "invalid_datetime", "registry.generated_at must be ISO-8601", "registry.generated_at")
    policy = registry.get("selection_policy") if isinstance(registry.get("selection_policy"), dict) else {}
    _required(policy, ("require_verified", "allow_scaffold_only"), "registry.selection_policy", issues)
    adapters = registry.get("adapters")
    if not isinstance(adapters, list) or not adapters:
        _issue(issues, "missing_adapters", "registry.adapters must contain at least one adapter", "registry.adapters")
        return issues, {}
    indexed: dict[str, dict[str, Any]] = {}
    for index, adapter in enumerate(adapters):
        prefix = f"registry.adapters[{index}]"
        if not isinstance(adapter, dict):
            _issue(issues, "invalid_adapter", "adapter must be an object", prefix)
            continue
        _required(adapter, ("adapter_id", "kind", "status", "adapter_version", "invocation_mode", "cost_class", "inputs", "outputs", "compatibility", "evidence", "limitations", "risk_level", "side_effect_level"), prefix, issues)
        adapter_id = adapter.get("adapter_id")
        if not _text(adapter_id) or adapter_id in indexed:
            _issue(issues, "duplicate_adapter", f"adapter_id must be unique and non-empty: {adapter_id}", f"{prefix}.adapter_id")
            continue
        indexed[adapter_id] = adapter
        if adapter.get("status") not in ADAPTER_STATUS:
            _issue(issues, "invalid_adapter_status", "adapter status is unsupported", f"{prefix}.status")
        if adapter.get("kind") not in {"fixture", "internal_skill", "external_provider", "manual_import"}:
            _issue(issues, "invalid_adapter_kind", "adapter kind is unsupported", f"{prefix}.kind")
        if adapter.get("invocation_mode") not in {"none", "manual", "agent-mediated", "api"}:
            _issue(issues, "invalid_invocation_mode", "invocation_mode is unsupported", f"{prefix}.invocation_mode")
        if adapter.get("cost_class") not in {"included", "metered", "external", "unknown"}:
            _issue(issues, "invalid_cost_class", "cost_class is unsupported", f"{prefix}.cost_class")
        if adapter.get("side_effect_level") in {"remote_write", "user_review_required"}:
            _issue(issues, "adapter_side_effect", "adapter registry cannot be used as authority to run a side-effecting provider", f"{prefix}.side_effect_level", "warning")
        _validate_file_entries(adapter.get("evidence"), root, f"{prefix}.evidence", issues)
    _forbidden_secrets(registry, issues)
    return issues, indexed


def validate_controls(controls: dict[str, Any], root: Path) -> list[Issue]:
    issues: list[Issue] = []
    _required(controls, ("schema_version", "control_id", "asset_id", "references", "tracks", "output_profile", "created_at"), "controls", issues)
    if controls.get("schema_version") != "0.1":
        _issue(issues, "schema_version", "controls.schema_version must be 0.1", "controls.schema_version")
    if not _datetime(controls.get("created_at")):
        _issue(issues, "invalid_datetime", "controls.created_at must be ISO-8601", "controls.created_at")
    refs = controls.get("references")
    if not isinstance(refs, list) or not refs:
        _issue(issues, "missing_references", "controls.references must contain at least one hash-bound input", "controls.references")
    else:
        seen: set[str] = set()
        for index, ref in enumerate(refs):
            prefix = f"controls.references[{index}]"
            if not isinstance(ref, dict):
                _issue(issues, "invalid_reference", "reference must be an object", prefix)
                continue
            _required(ref, ("id", "path", "sha256", "role"), prefix, issues)
            if not _text(ref.get("id")) or ref.get("id") in seen:
                _issue(issues, "duplicate_reference", "reference id must be unique and non-empty", f"{prefix}.id")
            seen.add(str(ref.get("id")))
            _validate_file_entries([ref], root, prefix, issues)
    tracks = controls.get("tracks")
    kinds: set[str] = set()
    if not isinstance(tracks, list) or not tracks:
        _issue(issues, "missing_tracks", "controls.tracks must contain at least one bound control", "controls.tracks")
    else:
        ids: set[str] = set()
        for index, track in enumerate(tracks):
            prefix = f"controls.tracks[{index}]"
            if not isinstance(track, dict):
                _issue(issues, "invalid_track", "control track must be an object", prefix)
                continue
            _required(track, ("id", "kind", "binding", "value_hash"), prefix, issues)
            if not _text(track.get("id")) or track.get("id") in ids:
                _issue(issues, "duplicate_track", "track id must be unique and non-empty", f"{prefix}.id")
            ids.add(str(track.get("id")))
            kind = track.get("kind")
            kinds.add(str(kind))
            if kind not in {"identity", "style", "camera", "motion", "pose", "seed", "negative_prompt", "lighting", "source"}:
                _issue(issues, "invalid_track_kind", "track kind is unsupported", f"{prefix}.kind")
            if track.get("binding") not in {"required", "advisory", "not_applicable"}:
                _issue(issues, "invalid_track_binding", "track binding is unsupported", f"{prefix}.binding")
            if not _hash(track.get("value_hash")):
                _issue(issues, "invalid_sha256", "track value_hash must be lowercase SHA-256", f"{prefix}.value_hash")
    profile = controls.get("output_profile") if isinstance(controls.get("output_profile"), dict) else {}
    if profile.get("kind") not in {"image", "frame_sequence", "sprite_atlas", "layered_map", "video", "rigged_2d", "rigged_3d", "runtime_scene"}:
        _issue(issues, "invalid_output_kind", "controls.output_profile.kind is unsupported", "controls.output_profile.kind")
    animated = profile.get("kind") in {"frame_sequence", "sprite_atlas", "video", "rigged_2d", "rigged_3d", "runtime_scene"}
    if animated and "motion" not in kinds and "pose" not in kinds:
        _issue(issues, "missing_motion_control", "animated output requires a motion or pose control track", "controls.tracks")
    if animated and (not isinstance(profile.get("fps"), (int, float)) or profile.get("fps", 0) <= 0 or not isinstance(profile.get("expected_frame_count"), int) or profile.get("expected_frame_count", 0) < 1):
        _issue(issues, "missing_timeline_profile", "animated output requires positive fps and expected_frame_count", "controls.output_profile")
    _forbidden_secrets(controls, issues)
    return issues


def validate_receipt(receipt: dict[str, Any], controls: dict[str, Any] | None, provenance: dict[str, Any] | None, root: Path, adapters: dict[str, dict[str, Any]]) -> list[Issue]:
    issues: list[Issue] = []
    _required(receipt, ("schema_version", "receipt_id", "asset", "authority", "provider", "control_track_ref", "provenance_ref", "outputs", "created_at"), "receipt", issues)
    if receipt.get("schema_version") != "0.1":
        _issue(issues, "schema_version", "receipt.schema_version must be 0.1", "receipt.schema_version")
    if not _datetime(receipt.get("created_at")):
        _issue(issues, "invalid_datetime", "receipt.created_at must be ISO-8601", "receipt.created_at")
    asset = receipt.get("asset") if isinstance(receipt.get("asset"), dict) else {}
    _required(asset, ("id", "kind", "intended_use"), "receipt.asset", issues)
    if asset.get("kind") not in {"image", "frame_sequence", "sprite_atlas", "layered_map", "video", "rigged_2d", "rigged_3d", "runtime_scene"}:
        _issue(issues, "invalid_asset_kind", "receipt.asset.kind is unsupported", "receipt.asset.kind")
    if asset.get("intended_use") not in {"pilot", "runtime_candidate", "reference_only"}:
        _issue(issues, "invalid_intended_use", "receipt.asset.intended_use is unsupported", "receipt.asset.intended_use")
    if receipt.get("authority") not in AUTHORITY:
        _issue(issues, "invalid_authority", "receipt.authority is unsupported", "receipt.authority")
    provider = receipt.get("provider") if isinstance(receipt.get("provider"), dict) else {}
    _required(provider, ("adapter_id", "kind", "invocation_mode", "task_id", "model", "generated_at", "cost_class"), "receipt.provider", issues)
    adapter = adapters.get(str(provider.get("adapter_id", "")))
    if adapter is None:
        _issue(issues, "unknown_adapter", f"adapter not found: {provider.get('adapter_id')}", "receipt.provider.adapter_id")
    elif adapter.get("status") == "disabled":
        _issue(issues, "adapter_disabled", f"adapter is disabled: {provider.get('adapter_id')}", "receipt.provider.adapter_id")
    else:
        for key in ("kind", "invocation_mode", "cost_class"):
            if provider.get(key) != adapter.get(key):
                _issue(issues, "adapter_mismatch", f"receipt provider {key} must match adapter registry", f"receipt.provider.{key}")
    if not _datetime(provider.get("generated_at")):
        _issue(issues, "invalid_datetime", "receipt.provider.generated_at must be ISO-8601", "receipt.provider.generated_at")
    if "prompt_hash" in provider and not _hash(provider.get("prompt_hash")):
        _issue(issues, "invalid_sha256", "receipt.provider.prompt_hash must be lowercase SHA-256", "receipt.provider.prompt_hash")
    _validate_file_entries(receipt.get("outputs"), root, "receipt.outputs", issues)
    if controls is not None and asset.get("id") != controls.get("asset_id"):
        _issue(issues, "asset_id_mismatch", "receipt asset id must match control track asset id", "receipt.asset.id")
    if provenance is not None:
        if receipt.get("authority") != provenance.get("authority"):
            _issue(issues, "authority_mismatch", "receipt authority must match provenance authority", "receipt.authority")
        provenance_paths = {(entry.get("path"), entry.get("sha256")) for entry in provenance.get("files", []) if isinstance(entry, dict)}
        for entry in receipt.get("outputs", []):
            if isinstance(entry, dict) and (entry.get("path"), entry.get("sha256")) not in provenance_paths:
                _issue(issues, "provenance_output_missing", "every receipt output must be hash-bound in provenance", "receipt.outputs")
    _forbidden_secrets(receipt, issues)
    for forbidden in ("human_approval", "production_approved", "production_eligible", "open_pr"):
        if forbidden in receipt:
            _issue(issues, "approval_forbidden", "receipt cannot contain approval or PR authority", f"receipt.{forbidden}")
    return issues


def validate_export(export: dict[str, Any], receipt: dict[str, Any] | None, controls: dict[str, Any] | None, root: Path) -> list[Issue]:
    issues: list[Issue] = []
    _required(export, ("schema_version", "manifest_id", "asset_id", "receipt_ref", "control_track_ref", "outputs", "created_at"), "export", issues)
    if export.get("schema_version") != "0.1":
        _issue(issues, "schema_version", "export.schema_version must be 0.1", "export.schema_version")
    if not _datetime(export.get("created_at")):
        _issue(issues, "invalid_datetime", "export.created_at must be ISO-8601", "export.created_at")
    outputs = _validate_file_entries(export.get("outputs"), root, "export.outputs", issues)
    for index, entry in enumerate(outputs):
        if entry.get("target") not in {"runtime_candidate", "preview", "archive"}:
            _issue(issues, "invalid_export_target", "export target is unsupported", f"export.outputs[{index}].target")
    if receipt is not None:
        if export.get("asset_id") != (receipt.get("asset") or {}).get("id"):
            _issue(issues, "asset_id_mismatch", "export asset id must match receipt asset id", "export.asset_id")
        receipt_outputs = {(item.get("path"), item.get("sha256")) for item in receipt.get("outputs", []) if isinstance(item, dict)}
        for entry in outputs:
            if (entry.get("path"), entry.get("sha256")) not in receipt_outputs:
                _issue(issues, "receipt_output_missing", "every export output must appear in receipt with same hash", "export.outputs")
    if controls is not None and export.get("asset_id") != controls.get("asset_id"):
        _issue(issues, "asset_id_mismatch", "export asset id must match control track asset id", "export.asset_id")
    _forbidden_secrets(export, issues)
    return issues


def evaluate_bundle(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    issues: list[Issue] = []
    registry_path = args.registry.resolve()
    receipt_path = args.receipt.resolve()
    controls_path = args.controls.resolve()
    export_path = args.export_manifest.resolve()
    receipt = _read_json(receipt_path, issues, "receipt")
    provenance_path = _resolve(root, receipt.get("provenance_ref", "") if receipt else "")
    registry = _read_json(registry_path, issues, "registry")
    controls = _read_json(controls_path, issues, "controls")
    export = _read_json(export_path, issues, "export")
    provenance = _read_json(provenance_path, issues, "provenance") if provenance_path else None
    adapters: dict[str, dict[str, Any]] = {}
    if registry is not None:
        more, adapters = validate_registry(registry, registry_path.parent)
        issues.extend(more)
    if controls is not None:
        issues.extend(validate_controls(controls, root))
    if receipt is not None:
        control_ref = _resolve(root, receipt.get("control_track_ref"))
        if control_ref is None or control_ref.resolve() != controls_path:
            _issue(issues, "control_ref_mismatch", "--controls must match receipt.control_track_ref and resolve inside root", "receipt.control_track_ref")
        if provenance_path is None:
            _issue(issues, "provenance_missing", "receipt.provenance_ref is missing or unsafe", "receipt.provenance_ref")
        issues.extend(validate_receipt(receipt, controls, provenance, root, adapters))
    if export is not None:
        if receipt is not None and export.get("receipt_ref") != receipt_path.relative_to(root).as_posix():
            _issue(issues, "receipt_ref_mismatch", "export.receipt_ref must match --receipt relative to root", "export.receipt_ref")
        if controls is not None and export.get("control_track_ref") != controls_path.relative_to(root).as_posix():
            _issue(issues, "control_ref_mismatch", "export.control_track_ref must match --controls relative to root", "export.control_track_ref")
        issues.extend(validate_export(export, receipt, controls, root))
    adapter = adapters.get(str(((receipt or {}).get("provider") or {}).get("adapter_id", "")))
    warnings: list[Issue] = []
    if adapter and adapter.get("status") != "verified":
        warnings.append(Issue("warning", "adapter_not_runtime_verified", f"adapter status is {adapter.get('status')}; retain human review and runtime evidence", "receipt.provider.adapter_id"))
    if args.strict and warnings:
        issues.extend(Issue("error", item.code, item.message, item.path) for item in warnings)
        warnings = []
    errors = [asdict(item) for item in issues if item.severity == "error"]
    warnings_json = [asdict(item) for item in issues if item.severity == "warning"] + [asdict(item) for item in warnings]
    return {"contract": "artifact-intake", "status": "blocked" if errors else ("review_required" if warnings_json else "pass"), "ready": not errors, "runtime_candidate": bool(not errors and ((receipt or {}).get("asset") or {}).get("intended_use") == "runtime_candidate"), "production_eligible": False, "production_approved": False, "adapter": {"adapter_id": adapter.get("adapter_id"), "status": adapter.get("status"), "invocation_mode": adapter.get("invocation_mode"), "cost_class": adapter.get("cost_class")} if adapter else None, "errors": errors, "warnings": warnings_json, "evidence": {"receipt": str(receipt_path), "controls": str(controls_path), "export_manifest": str(export_path), "registry": str(registry_path), "provenance": str(provenance_path) if provenance_path else None}}


def evaluate_single(args: argparse.Namespace) -> dict[str, Any]:
    issues: list[Issue] = []
    document = _read_json(args.input.resolve(), issues, args.kind)
    if document is not None:
        if args.kind == "registry":
            more, _ = validate_registry(document, args.input.resolve().parent)
        elif args.kind == "controls":
            more = validate_controls(document, args.root.resolve())
        else:
            more = [Issue("error", "single_kind_unsupported", "receipt/export require the complete bundle command", "kind")]
        issues.extend(more)
    errors = [asdict(item) for item in issues if item.severity == "error"]
    warnings = [asdict(item) for item in issues if item.severity == "warning"]
    return {"contract": f"artifact-intake-{args.kind}", "status": "blocked" if errors else ("review_required" if warnings else "pass"), "ready": not errors, "production_eligible": False, "production_approved": False, "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate provider-neutral MotionLoom artifact intake evidence")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("intake", "report"):
        item = sub.add_parser(command)
        item.add_argument("--root", type=Path, default=Path("."))
        item.add_argument("--registry", type=Path, required=True)
        item.add_argument("--receipt", type=Path, required=True)
        item.add_argument("--controls", type=Path, required=True)
        item.add_argument("--export-manifest", type=Path, required=True)
        item.add_argument("--strict", action="store_true")
        item.add_argument("--output", type=Path)
        item.add_argument("--json", action="store_true")
    check = sub.add_parser("validate")
    check.add_argument("--kind", choices=("registry", "controls"), required=True)
    check.add_argument("--input", type=Path, required=True)
    check.add_argument("--root", type=Path, default=Path("."))
    check.add_argument("--output", type=Path)
    check.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = evaluate_bundle(args) if args.command in {"intake", "report"} else evaluate_single(args)
    if getattr(args, "output", None):
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.command != "report" or args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"{result['contract']}: {result['status']} ({len(result['errors'])} errors, {len(result['warnings'])} warnings)")
        for issue in result["errors"] + result["warnings"]:
            print(f"- {issue['severity']}: {issue['code']}: {issue['message']}")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
