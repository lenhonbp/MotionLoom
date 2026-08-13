#!/usr/bin/env python3
"""Verify MotionLoom signed attestations without granting approval.

Exit codes are stable for automation:
0 verified, 10 malformed envelope, 11 payload mismatch, 12 signature
failure, 13 trust-policy failure, 14 expected binding mismatch, 2 usage/I/O.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from attestation import PAYLOAD_TYPE, SCHEMA_VERSION, canonical_json_bytes, dsse_pae, parse_json_file, reject_symlink_components, validate_policy


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_ENVELOPE = 10
EXIT_PAYLOAD = 11
EXIT_SIGNATURE = 12
EXIT_TRUST = 13
EXIT_BINDING = 14


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_time(value: object, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} is not a valid date-time") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include timezone")
    return parsed.astimezone(timezone.utc)


def read_attestation(path_value: str) -> dict:
    path = Path(path_value).expanduser().absolute()
    reject_symlink_components(path)
    value = parse_json_file(str(path), "attestation")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported attestation schema_version")
    if value.get("approval") is not False:
        raise ValueError("attestation approval must be false")
    return value


def verify_attestation(attestation_path: str, policy_path: str, expected_task_id: str | None, expected_scene: str | None) -> tuple[dict, int]:
    issues: list[str] = []
    result = {"schema_version": "1.0", "verifier": "motionloom-attestation-verifier/1.0", "verified": False, "approval": False, "issues": [], "signers": [], "bindings": {}}
    try:
        bundle = read_attestation(attestation_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["issues"] = [str(exc)]
        return result, EXIT_ENVELOPE

    envelope = bundle.get("envelope")
    statement = bundle.get("statement")
    if not isinstance(envelope, dict) or not isinstance(statement, dict):
        result["issues"] = ["attestation envelope and statement must be objects"]
        return result, EXIT_ENVELOPE
    if envelope.get("payload_type") != PAYLOAD_TYPE:
        issues.append("unsupported payload_type")
        result["issues"] = issues
        return result, EXIT_ENVELOPE
    try:
        body = base64.b64decode(str(envelope.get("payload_base64") or ""), validate=True)
    except ValueError as exc:
        result["issues"] = [f"payload_base64 is invalid: {exc}"]
        return result, EXIT_PAYLOAD
    if sha256_bytes(body) != envelope.get("payload_sha256"):
        issues.append("payload sha256 mismatch")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        issues.append(f"payload is not canonical UTF-8 JSON: {exc}")
        result["issues"] = issues
        return result, EXIT_PAYLOAD
    if not isinstance(payload, dict) or payload != statement or canonical_json_bytes(payload) != body:
        issues.append("payload does not exactly match canonical statement")
    predicate = statement.get("predicate") if isinstance(statement, dict) else None
    if not isinstance(predicate, dict):
        issues.append("statement predicate is missing")
    else:
        result["bindings"] = {"task_id": predicate.get("task_id"), "scene": predicate.get("scene"), "context_hash": predicate.get("context_hash"), "source_sha256": predicate.get("source_sha256"), "manifest_sha256": predicate.get("manifest_sha256"), "motion_ir_sha256": predicate.get("motion_ir_sha256")}
        if expected_task_id is not None and predicate.get("task_id") != expected_task_id:
            issues.append("task_id does not match expected binding")
        if expected_scene is not None and predicate.get("scene") != expected_scene:
            issues.append("scene does not match expected binding")
    if issues:
        result["issues"] = issues
        return result, EXIT_BINDING if any("expected binding" in item for item in issues) else EXIT_PAYLOAD

    try:
        policy = parse_json_file(policy_path, "trust policy")
        validate_policy(policy)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["issues"] = [str(exc)]
        return result, EXIT_TRUST
    keys = {str(item["key_id"]): item for item in policy["keys"]}
    signatures = envelope.get("signatures")
    if not isinstance(signatures, list) or not signatures:
        result["issues"] = ["attestation signatures must be a non-empty array"]
        return result, EXIT_SIGNATURE
    now = datetime.now(timezone.utc)
    trust_failures: list[str] = []
    signature_failures: list[str] = []
    for signature in signatures:
        if not isinstance(signature, dict):
            signature_failures.append("signature entry must be an object")
            continue
        key_id = str(signature.get("key_id") or "")
        key = keys.get(key_id)
        if key is None:
            trust_failures.append(f"unknown signer: {key_id}")
            continue
        if signature.get("algorithm") != "ed25519" or key.get("algorithm") != "ed25519":
            trust_failures.append(f"unsupported signature algorithm for signer: {key_id}")
            continue
        if key.get("status") != "active":
            trust_failures.append(f"signer is not active: {key_id}")
            continue
        try:
            if now < parse_time(key["valid_from"], f"{key_id}.valid_from") or (key.get("valid_until") and now > parse_time(key["valid_until"], f"{key_id}.valid_until")):
                trust_failures.append(f"signer is outside validity window: {key_id}")
                continue
            public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(str(key["public_key_base64"]), validate=True))
            raw_signature = base64.b64decode(str(signature.get("signature_base64") or ""), validate=True)
            public_key.verify(raw_signature, dsse_pae(PAYLOAD_TYPE, body))
            result["signers"].append({"key_id": key_id, "status": "verified", "algorithm": "ed25519"})
        except InvalidSignature as exc:
            signature_failures.append(f"signature verification failed for {key_id}: {exc}")
        except (ValueError, TypeError) as exc:
            signature_failures.append(f"signature encoding failed for {key_id}: {exc}")
    issues.extend(trust_failures)
    issues.extend(signature_failures)
    if issues:
        result["issues"] = issues
        return result, EXIT_SIGNATURE if signature_failures else EXIT_TRUST
    result["verified"] = True
    return result, EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MotionLoom signed attestations without granting approval")
    parser.add_argument("--attestation", required=True)
    parser.add_argument("--trust-policy", required=True)
    parser.add_argument("--expected-task-id")
    parser.add_argument("--expected-scene")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        report, code = verify_attestation(args.attestation, args.trust_policy, args.expected_task_id, args.expected_scene)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report, code = ({"schema_version": "1.0", "verifier": "motionloom-attestation-verifier/1.0", "verified": False, "approval": False, "issues": [str(exc)]}, EXIT_USAGE)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output = Path(args.output).expanduser().absolute()
        reject_symlink_components(output.parent)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
