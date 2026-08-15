"""Validate and classify asset-level provenance without granting approval.

The contract is intentionally fail-closed. An Agent may declare how an asset
was produced and may prove runtime readiness, but it cannot manufacture human
authority or production approval. The script uses pathlib and JSON only so
the same entrypoint works on Ubuntu, macOS and Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"
AUTHORITIES = {
    "ai_generated",
    "ai_assisted",
    "ai_assisted_human_reviewed",
    "artist_authored",
    "code_authored",
    "unknown",
}
READINESS = {
    "blocked",
    "runtime_ready",
    "review_required",
    "production_eligible",
    "production_approved",
}
SAFE_RELATIVE = re.compile(r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$)).+")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path}: provenance document must be a JSON object")
    return value


def is_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def is_relative_path(value: Any) -> bool:
    return isinstance(value, str) and bool(SAFE_RELATIVE.fullmatch(value))


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256.fullmatch(value))


def _required(data: dict[str, Any], keys: tuple[str, ...], prefix: str, errors: list[str]) -> None:
    for key in keys:
        if key not in data:
            errors.append(f"{prefix}.{key} is required")


def _check_text(data: dict[str, Any], key: str, prefix: str, errors: list[str]) -> None:
    if key in data and (not isinstance(data[key], str) or not data[key].strip()):
        errors.append(f"{prefix}.{key} must be a non-empty string")


def _check_human_review(data: dict[str, Any], errors: list[str]) -> None:
    review = data.get("human_review")
    if not isinstance(review, dict):
        errors.append("human_review is required for human-reviewed readiness")
        return
    _required(review, ("reviewer", "decision", "scope", "reviewed_at", "user_confirmed"), "human_review", errors)
    _check_text(review, "reviewer", "human_review", errors)
    if review.get("decision") not in {"approved", "rejected", "changes_requested"}:
        errors.append("human_review.decision must be approved, rejected or changes_requested")
    if not is_datetime(review.get("reviewed_at")):
        errors.append("human_review.reviewed_at must be an ISO-8601 timestamp")
    if review.get("user_confirmed") is not True:
        errors.append("human_review.user_confirmed must be true; Agent-only review is not sufficient")


def _check_human_attestation(data: dict[str, Any], errors: list[str]) -> None:
    attestation = data.get("human_attestation")
    if not isinstance(attestation, dict):
        errors.append("artist_authored requires human_attestation")
        return
    _required(attestation, ("attestor", "attestor_type", "decision", "attested_at", "user_confirmed"), "human_attestation", errors)
    _check_text(attestation, "attestor", "human_attestation", errors)
    if attestation.get("attestor_type") not in {"artist", "user"}:
        errors.append("human_attestation.attestor_type must be artist or user")
    if attestation.get("decision") != "artist_authored":
        errors.append("human_attestation.decision must be artist_authored")
    if not is_datetime(attestation.get("attested_at")):
        errors.append("human_attestation.attested_at must be an ISO-8601 timestamp")
    if attestation.get("user_confirmed") is not True:
        errors.append("human_attestation.user_confirmed must be true; Agent-only authority is rejected")


def _check_generator(data: dict[str, Any], errors: list[str]) -> None:
    generator = data.get("generator")
    if not isinstance(generator, dict):
        errors.append("AI-origin authority requires generator metadata")
        return
    _required(generator, ("model", "task_id", "source", "generated_at"), "generator", errors)
    for key in ("model", "task_id", "source"):
        _check_text(generator, key, "generator", errors)
    if not is_datetime(generator.get("generated_at")):
        errors.append("generator.generated_at must be an ISO-8601 timestamp")
    if "prompt_hash" in generator and not is_sha256(generator.get("prompt_hash")):
        errors.append("generator.prompt_hash must be a lowercase SHA-256")


def _check_files(data: dict[str, Any], errors: list[str]) -> None:
    files = data.get("files")
    if not isinstance(files, list) or not files:
        errors.append("files must contain at least one asset file")
        return
    for index, item in enumerate(files):
        prefix = f"files[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _required(item, ("path", "role", "sha256"), prefix, errors)
        if not is_relative_path(item.get("path")):
            errors.append(f"{prefix}.path must be a safe relative path")
        _check_text(item, "role", prefix, errors)
        if not is_sha256(item.get("sha256")):
            errors.append(f"{prefix}.sha256 must be a lowercase SHA-256")
        if "bytes" in item and (not isinstance(item["bytes"], int) or item["bytes"] < 0):
            errors.append(f"{prefix}.bytes must be a non-negative integer")


def _check_chain(data: dict[str, Any], errors: list[str]) -> None:
    chain = data.get("provenance_chain")
    if not isinstance(chain, list) or not chain:
        errors.append("provenance_chain must contain at least one step")
        return
    for index, item in enumerate(chain):
        prefix = f"provenance_chain[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        _required(item, ("step", "actor", "source", "timestamp"), prefix, errors)
        for key in ("step", "actor", "source"):
            _check_text(item, key, prefix, errors)
        if not is_datetime(item.get("timestamp")):
            errors.append(f"{prefix}.timestamp must be an ISO-8601 timestamp")
        if "sha256" in item and not is_sha256(item.get("sha256")):
            errors.append(f"{prefix}.sha256 must be a lowercase SHA-256")


def validate_document(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _required(data, ("schema_version", "provenance_id", "asset", "authority", "readiness", "files", "license", "provenance_chain", "created_at"), "provenance", errors)
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    _check_text(data, "provenance_id", "provenance", errors)
    if not is_datetime(data.get("created_at")):
        errors.append("created_at must be an ISO-8601 timestamp")

    asset = data.get("asset")
    if not isinstance(asset, dict):
        errors.append("asset must be an object")
    else:
        _required(asset, ("id", "path", "type", "framework"), "asset", errors)
        _check_text(asset, "id", "asset", errors)
        if not is_relative_path(asset.get("path")):
            errors.append("asset.path must be a safe relative path")
        for key in ("type", "framework"):
            _check_text(asset, key, "asset", errors)

    authority = data.get("authority")
    readiness = data.get("readiness")
    if authority not in AUTHORITIES:
        errors.append(f"authority must be one of {sorted(AUTHORITIES)}")
    if readiness not in READINESS:
        errors.append(f"readiness must be one of {sorted(READINESS)}")

    license_data = data.get("license")
    if not isinstance(license_data, dict):
        errors.append("license must be an object")
    else:
        _required(license_data, ("spdx", "source", "attribution"), "license", errors)
        for key in ("spdx", "source", "attribution"):
            _check_text(license_data, key, "license", errors)

    _check_files(data, errors)
    _check_chain(data, errors)
    if authority in {"ai_generated", "ai_assisted", "ai_assisted_human_reviewed"}:
        _check_generator(data, errors)
    if authority == "artist_authored":
        _check_human_attestation(data, errors)

    if authority == "unknown" and readiness != "blocked":
        errors.append("unknown authority is always blocked")
    if authority == "ai_generated" and readiness != "runtime_ready":
        errors.append("ai_generated assets may be runtime_ready only; they are never production eligible")
    if authority == "code_authored" and readiness not in {"runtime_ready", "review_required"}:
        errors.append("code_authored runtime scenes may be runtime_ready or review_required only; production eligibility remains a separate human-governed release lane")
    if authority == "ai_assisted_human_reviewed" and readiness not in {"review_required", "production_eligible"}:
        errors.append("ai_assisted_human_reviewed assets must remain review_required or pass a later production gate")
    if authority == "ai_assisted_human_reviewed":
        _check_human_review(data, errors)
    if authority == "ai_assisted" and readiness not in {"runtime_ready", "review_required", "production_eligible"}:
        errors.append("ai_assisted assets must be runtime_ready, review_required or production_eligible")
    if authority == "ai_assisted" and readiness == "production_eligible":
        _check_human_review(data, errors)
    if readiness in {"production_eligible", "production_approved"}:
        runtime = data.get("runtime_evidence")
        if not isinstance(runtime, dict) or runtime.get("status") != "pass":
            errors.append("production eligibility requires runtime_evidence.status=pass")
        full_gate = data.get("full_gate")
        if not isinstance(full_gate, dict):
            errors.append("production eligibility requires full_gate evidence")
        else:
            _required(full_gate, ("status", "quality_gate", "visual_truth", "license", "checked_at"), "full_gate", errors)
            if full_gate.get("status") != "pass" or full_gate.get("quality_gate") != "pass" or full_gate.get("visual_truth") != "pass" or full_gate.get("license") != "pass":
                errors.append("full_gate must have pass for status, quality_gate, visual_truth and license")
            if not is_datetime(full_gate.get("checked_at")):
                errors.append("full_gate.checked_at must be an ISO-8601 timestamp")
        if authority in {"ai_assisted", "ai_assisted_human_reviewed"}:
            _check_human_review(data, errors)
        if authority in {"unknown", "ai_generated", "code_authored"}:
            errors.append(f"{authority} cannot be production eligible")
    if readiness == "production_approved":
        approval = data.get("human_approval")
        if not isinstance(approval, dict):
            errors.append("production_approved requires human_approval")
        else:
            _required(approval, ("issued_by", "decision", "approved_at", "user_confirmed"), "human_approval", errors)
            issuer = approval.get("issued_by")
            if not isinstance(issuer, dict) or issuer.get("type") not in {"user", "artist"} or not str(issuer.get("id") or "").strip():
                errors.append("human_approval.issued_by must be a non-empty user or artist identity")
            if approval.get("decision") != "approved":
                errors.append("human_approval.decision must be approved")
            if not is_datetime(approval.get("approved_at")):
                errors.append("human_approval.approved_at must be an ISO-8601 timestamp")
            if approval.get("user_confirmed") is not True:
                errors.append("human_approval.user_confirmed must be true")
        if authority in {"unknown", "ai_generated", "code_authored"}:
            errors.append("unknown, ai_generated and code_authored assets can never be production_approved")
    if "human_approval" in data and readiness != "production_approved":
        errors.append("human_approval is only valid when readiness is production_approved")
    return errors


def _resolve_inside(base: Path, relative: str) -> Path | None:
    if not is_relative_path(relative):
        return None
    resolved = (base / relative).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError:
        return None
    return resolved


def validate_files(data: dict[str, Any], base: Path) -> list[str]:
    errors: list[str] = []
    for item in data.get("files", []):
        path = _resolve_inside(base, str(item.get("path", "")))
        if path is None or not path.is_file():
            errors.append(f"asset file is missing: {item.get('path', '<unknown>')}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item.get("sha256"):
            errors.append(f"asset file SHA-256 mismatch: {item.get('path', '<unknown>')}")
        if "bytes" in item and path.stat().st_size != item.get("bytes"):
            errors.append(f"asset file byte count mismatch: {item.get('path', '<unknown>')}")
    asset_path = _resolve_inside(base, str((data.get("asset") or {}).get("path", "")))
    if asset_path is None or not asset_path.is_file():
        errors.append(f"asset.path is missing: {(data.get('asset') or {}).get('path', '<unknown>')}")
    return errors


def classify(data: dict[str, Any], errors: list[str] | None = None) -> dict[str, Any]:
    errors = errors or []
    authority = data.get("authority", "unknown")
    readiness = data.get("readiness", "blocked")
    effective = "blocked" if errors or authority == "unknown" else "runtime_ready"
    if not errors:
        if authority == "ai_generated":
            effective = "runtime_ready"
        elif authority == "code_authored":
            effective = "review_required" if readiness == "review_required" else "runtime_ready"
        elif authority in {"ai_assisted", "ai_assisted_human_reviewed"}:
            review = data.get("human_review") or {}
            if data.get("full_gate", {}).get("status") == "pass" and review.get("decision") == "approved" and review.get("user_confirmed") is True:
                effective = "production_eligible"
            elif authority == "ai_assisted_human_reviewed" or readiness == "review_required":
                effective = "review_required"
            else:
                effective = "runtime_ready"
        elif authority == "artist_authored":
            effective = "production_eligible" if data.get("full_gate", {}).get("status") == "pass" else "runtime_ready"
        if readiness == "production_approved" and data.get("human_approval", {}).get("user_confirmed") is True:
            effective = "production_approved"
    return {
        "authority": authority,
        "declared_readiness": readiness,
        "effective_readiness": effective,
        "production_eligible": effective in {"production_eligible", "production_approved"},
        "production_approved": effective == "production_approved",
        "errors": errors,
    }


def evaluate(path: Path, *, base: Path | None = None, mode: str = "contract", manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        data = read_json(path)
    except ValueError as exc:
        return {"status": "fail", "provenance_path": str(path), "errors": [str(exc)]}
    errors = validate_document(data)
    if manifest is not None:
        manifest_file = manifest.get("file")
        asset_path = (data.get("asset") or {}).get("path")
        if manifest_file and asset_path != manifest_file:
            errors.append("asset.path must match scene manifest.file")
        provenance_ref = manifest.get("asset_provenance")
        if provenance_ref and provenance_ref != path.name and provenance_ref != path.as_posix():
            errors.append("scene manifest asset_provenance does not match the loaded provenance file")
    if mode in {"runtime", "production"}:
        if base is None:
            errors.append(f"{mode} check requires --root for asset file hash verification")
        else:
            errors.extend(validate_files(data, base))
        runtime = data.get("runtime_evidence") or {}
        if runtime.get("status") != "pass":
            errors.append("runtime check requires runtime_evidence.status=pass")
    if mode == "production":
        summary = classify(data, errors)
        if summary["effective_readiness"] != "production_eligible":
            errors.append("production check requires effective_readiness=production_eligible; production_approved remains a human-only state")
    summary = classify(data, errors)
    return {
        "status": "pass" if not errors else "fail",
        "mode": mode,
        "provenance_path": str(path),
        "summary": summary,
        "errors": errors,
    }


def print_result(result: dict[str, Any], as_json: bool = True) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    print(f"Asset provenance: {result.get('status', 'fail').upper()}")
    summary = result.get("summary") or {}
    print(f"Authority: {summary.get('authority', 'unknown')}")
    print(f"Declared readiness: {summary.get('declared_readiness', 'blocked')}")
    print(f"Effective readiness: {summary.get('effective_readiness', 'blocked')}")
    for error in result.get("errors", []):
        print(f"- {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate, classify and report MotionLoom asset provenance")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "classify", "check", "report"):
        command = sub.add_parser(name)
        command.add_argument("--input", required=True, help="Asset provenance JSON path")
        command.add_argument("--root", help="Directory used to resolve and hash asset files")
        command.add_argument("--mode", choices=("contract", "runtime", "production"), default="contract")
        command.add_argument("--manifest", help="Optional scene manifest used for binding checks")
        command.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()
    path = Path(args.input).expanduser().resolve()
    base = Path(args.root).expanduser().resolve() if args.root else None
    manifest = read_json(Path(args.manifest).expanduser().resolve()) if args.manifest else None
    result = evaluate(path, base=base, mode=args.mode, manifest=manifest)
    if args.command == "classify" and result.get("summary"):
        result = {"status": result.get("status"), "provenance_path": str(path), "summary": result["summary"], "errors": result.get("errors", [])}
    if args.command == "validate":
        result["mode"] = "contract"
    print_result(result, as_json=args.json or args.command != "report")
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
