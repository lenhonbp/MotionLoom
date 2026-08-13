#!/usr/bin/env python3
"""Build MotionLoom DSSE-compatible signed evidence attestations.

This builder authenticates an exact canonical statement. It does not verify
runtime evidence and it never creates approval. Verification is intentionally
implemented in a separate read-only command in a later phase.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


PAYLOAD_TYPE = "application/vnd.motionloom.attestation+json;version=1"
SCHEMA_VERSION = "1.0"
KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{2,127}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def dsse_pae(payload_type: str, body: bytes) -> bytes:
    payload_type_bytes = payload_type.encode("utf-8")
    return b"DSSEv1 " + str(len(payload_type_bytes)).encode("ascii") + b" " + payload_type_bytes + b" " + str(len(body)).encode("ascii") + b" " + body


def reject_symlink_components(path: Path) -> None:
    current = Path(path.anchor) if path.anchor else Path(".")
    for part in path.parts:
        if part in (path.anchor, ""):
            continue
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink path component is not allowed: {path}")


def read_regular_file(path_value: str, label: str) -> bytes:
    path = Path(path_value).expanduser().absolute()
    reject_symlink_components(path)
    if not path.is_file():
        raise ValueError(f"{label} must point to an existing regular file")
    return path.read_bytes()


def parse_json_file(path_value: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(read_regular_file(path_value, label).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def sha256_file(path: Path, label: str) -> str:
    reject_symlink_components(path)
    if not path.is_file():
        raise ValueError(f"{label} must point to an existing regular file")
    return sha256_bytes(path.read_bytes())


def telemetry_bundle_sha256(task_dir: Path) -> str:
    entries = []
    for path in sorted(task_dir.glob("runtime-adapters/**/runtime-telemetry.json")):
        if not path.is_file() or task_dir.resolve() not in path.resolve().parents:
            raise ValueError("runtime telemetry path must stay inside task directory")
        entries.append({"path": path.resolve().relative_to(task_dir.resolve()).as_posix(), "sha256": sha256_file(path, "runtime telemetry")})
    if not entries:
        raise ValueError("task directory must contain runtime telemetry files")
    return sha256_bytes(canonical_json_bytes(entries))


def load_private_key(path_value: str) -> Ed25519PrivateKey:
    raw = read_regular_file(path_value, "private key").strip()
    try:
        if raw.startswith(b"-----BEGIN"):
            key = serialization.load_pem_private_key(raw, password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise ValueError("private key must be Ed25519")
            return key
        try:
            decoded = base64.b64decode(raw, validate=True)
        except ValueError:
            decoded = raw
        if len(decoded) != 32:
            raise ValueError("raw Ed25519 private key must be exactly 32 bytes or PEM encoded")
        return Ed25519PrivateKey.from_private_bytes(decoded)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid Ed25519 private key: {exc}") from exc


def validate_statement(statement: dict[str, Any]) -> None:
    if statement.get("type") != "https://motionloom.dev/attestation/v1":
        raise ValueError("statement.type must be https://motionloom.dev/attestation/v1")
    if statement.get("predicate_type") != "https://motionloom.dev/predicate/animation-evidence/v1":
        raise ValueError("statement.predicate_type is unsupported")
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or not subjects:
        raise ValueError("statement.subject must be a non-empty array")
    for index, subject in enumerate(subjects):
        if not isinstance(subject, dict) or not isinstance(subject.get("name"), str) or not subject["name"].strip():
            raise ValueError(f"statement.subject[{index}].name is required")
        digest = subject.get("digest")
        if not isinstance(digest, dict) or not SHA256_RE.fullmatch(str(digest.get("sha256") or "")):
            raise ValueError(f"statement.subject[{index}].digest.sha256 must be lowercase sha256")
    predicate = statement.get("predicate")
    if not isinstance(predicate, dict):
        raise ValueError("statement.predicate must be an object")
    required = ("task_id", "scene", "context_hash", "source_sha256", "manifest_sha256", "motion_ir_sha256", "evidence", "provenance_chain_hash", "policy_version", "generated_at", "builder")
    missing = [field for field in required if field not in predicate]
    if missing:
        raise ValueError(f"statement.predicate missing fields: {', '.join(missing)}")
    for field in ("context_hash", "source_sha256", "manifest_sha256", "motion_ir_sha256", "provenance_chain_hash"):
        if not SHA256_RE.fullmatch(str(predicate.get(field) or "")):
            raise ValueError(f"statement.predicate.{field} must be lowercase sha256")
    evidence = predicate["evidence"]
    if not isinstance(evidence, dict) or any(not SHA256_RE.fullmatch(str(evidence.get(field) or "")) for field in ("runtime_evidence_sha256", "runtime_telemetry_sha256", "verifier_report_sha256")):
        raise ValueError("statement.predicate.evidence must bind runtime evidence, telemetry and verifier report hashes")
    try:
        datetime.fromisoformat(str(predicate["generated_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("statement.predicate.generated_at must be ISO-8601 date-time") from exc
    if not isinstance(predicate["builder"], dict) or not predicate["builder"].get("name") or not predicate["builder"].get("version"):
            raise ValueError("statement.predicate.builder.name and version are required")


def build_statement(scene_dir_path: str, task_dir_path: str, context_path: str, output_path: str) -> dict[str, Any]:
    scene_dir = Path(scene_dir_path).expanduser().absolute()
    task_dir = Path(task_dir_path).expanduser().absolute()
    context = Path(context_path).expanduser().absolute()
    reject_symlink_components(scene_dir)
    reject_symlink_components(task_dir)
    manifest_path = scene_dir / "manifest.json"
    manifest = parse_json_file(str(manifest_path), "scene manifest")
    task = parse_json_file(str(task_dir / "task.json"), "task")
    source_name = str(manifest.get("file") or "")
    source_path = (scene_dir / source_name).resolve()
    if not source_name or scene_dir.resolve() not in source_path.parents:
        raise ValueError("scene manifest.file must point inside scene directory")
    motion_ir_path = task_dir / "motion-ir.json"
    runtime_evidence_path = task_dir / "runtime-adapters" / "runtime-evidence.json"
    verifier_report_path = task_dir / "evidence-verifier-report.json"
    provenance_path = task_dir / "provenance.json"
    statement = {
        "type": "https://motionloom.dev/attestation/v1",
        "predicate_type": "https://motionloom.dev/predicate/animation-evidence/v1",
        "subject": [{"name": scene_dir.name, "digest": {"sha256": sha256_file(manifest_path, "scene manifest")}}],
        "predicate": {
            "task_id": str(task.get("task_id") or ""),
            "scene": scene_dir.name,
            "context_hash": sha256_file(context, "project context"),
            "source_sha256": sha256_file(source_path, "scene source"),
            "manifest_sha256": sha256_file(manifest_path, "scene manifest"),
            "motion_ir_sha256": sha256_file(motion_ir_path, "Motion IR"),
            "evidence": {
                "runtime_evidence_sha256": sha256_file(runtime_evidence_path, "runtime evidence"),
                "runtime_telemetry_sha256": telemetry_bundle_sha256(task_dir),
                "verifier_report_sha256": sha256_file(verifier_report_path, "evidence verifier report"),
            },
            "provenance_chain_hash": sha256_file(provenance_path, "provenance"),
            "policy_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "builder": {"name": "motionloom-attestation-builder", "version": "1.0.0"},
        },
    }
    if not statement["predicate"]["task_id"]:
        raise ValueError("task.task_id is required")
    validate_statement(statement)
    output = Path(output_path).expanduser().absolute()
    reject_symlink_components(output.parent)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(statement, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return statement


def build(statement_path: str, private_key_path: str, key_id: str, output_path: str) -> dict[str, Any]:
    if not KEY_ID_RE.fullmatch(key_id):
        raise ValueError("key-id has an unsafe format")
    statement = parse_json_file(statement_path, "statement")
    validate_statement(statement)
    body = canonical_json_bytes(statement)
    private_key = load_private_key(private_key_path)
    signature = private_key.sign(dsse_pae(PAYLOAD_TYPE, body))
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "envelope": {
            "payload_type": PAYLOAD_TYPE,
            "payload_sha256": sha256_bytes(body),
            "payload_base64": base64.b64encode(body).decode("ascii"),
            "signatures": [{"key_id": key_id, "algorithm": "ed25519", "signature_base64": base64.b64encode(signature).decode("ascii")}],
        },
        "statement": statement,
        "approval": False,
    }
    output = Path(output_path).expanduser().absolute()
    reject_symlink_components(output.parent)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return bundle


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("trust policy schema_version must be 1.0")
    if not isinstance(policy.get("policy_id"), str) or not policy["policy_id"].strip():
        raise ValueError("trust policy policy_id is required")
    keys = policy.get("keys")
    if not isinstance(keys, list) or not keys:
        raise ValueError("trust policy keys must be a non-empty array")
    seen: set[str] = set()
    for index, key in enumerate(keys):
        if not isinstance(key, dict):
            raise ValueError(f"trust policy key {index} must be an object")
        key_id = str(key.get("key_id") or "")
        if not KEY_ID_RE.fullmatch(key_id) or key_id in seen:
            raise ValueError(f"trust policy key {index} has an invalid or duplicate key_id")
        seen.add(key_id)
        if key.get("algorithm") != "ed25519":
            raise ValueError(f"trust policy key {key_id} must use ed25519")
        try:
            public_key = base64.b64decode(str(key.get("public_key_base64") or ""), validate=True)
            if len(public_key) != 32:
                raise ValueError("public key must be 32 bytes")
        except ValueError as exc:
            raise ValueError(f"trust policy key {key_id} has invalid public key: {exc}") from exc
        if key.get("status") == "revoked" and not key.get("revoked_at"):
            raise ValueError(f"revoked key {key_id} must include revoked_at")
        if key.get("status") == "revoked" and not key.get("revocation_reason"):
            raise ValueError(f"revoked key {key_id} must include revocation_reason")
    rotation = policy.get("rotation")
    if not isinstance(rotation, dict) or rotation.get("require_active_signer") is not True:
        raise ValueError("trust policy must require an active signer")
    revocation = policy.get("revocation")
    if not isinstance(revocation, dict) or revocation.get("fail_closed") is not True:
        raise ValueError("trust policy revocation must be fail-closed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build MotionLoom signed evidence attestations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="sign a canonical MotionLoom statement")
    build_parser.add_argument("--statement", required=True)
    build_parser.add_argument("--private-key", required=True)
    build_parser.add_argument("--key-id", required=True)
    build_parser.add_argument("--output", required=True)
    statement_parser = subparsers.add_parser("statement", help="derive a canonical statement from scene and task artifacts")
    statement_parser.add_argument("--scene-dir", required=True)
    statement_parser.add_argument("--task-dir", required=True)
    statement_parser.add_argument("--context", required=True)
    statement_parser.add_argument("--output", required=True)
    policy_parser = subparsers.add_parser("validate-policy", help="validate a trust policy without verifying an attestation")
    policy_parser.add_argument("--policy", required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            bundle = build(args.statement, args.private_key, args.key_id, args.output)
            print(json.dumps({"built": True, "approval": bundle["approval"], "key_id": args.key_id, "payload_sha256": bundle["envelope"]["payload_sha256"]}, indent=2))
        elif args.command == "statement":
            statement = build_statement(args.scene_dir, args.task_dir, args.context, args.output)
            print(json.dumps({"built": True, "task_id": statement["predicate"]["task_id"], "scene": statement["predicate"]["scene"]}, indent=2))
        else:
            validate_policy(parse_json_file(args.policy, "trust policy"))
            print(json.dumps({"valid": True, "policy": args.policy}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"attestation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
