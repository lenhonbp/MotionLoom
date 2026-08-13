#!/usr/bin/env python3
"""Focused DSSE/trust-policy contract tests for MotionLoom."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "scripts/attestation.py"
VERIFIER = ROOT / "scripts/attestation-verifier.py"


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def make_statement(**overrides: object) -> dict:
    digest = "a" * 64
    statement = {
        "type": "https://motionloom.dev/attestation/v1",
        "predicate_type": "https://motionloom.dev/predicate/animation-evidence/v1",
        "subject": [{"name": "browser-review-smoke", "digest": {"sha256": digest}}],
        "predicate": {
            "task_id": "browser-review-smoke-task",
            "scene": "browser-review-smoke",
            "context_hash": digest,
            "source_sha256": digest,
            "manifest_sha256": digest,
            "motion_ir_sha256": digest,
            "evidence": {
                "runtime_evidence_sha256": digest,
                "runtime_telemetry_sha256": digest,
                "verifier_report_sha256": digest,
            },
            "provenance_chain_hash": digest,
            "policy_version": "1.0",
            "generated_at": iso(datetime.now(timezone.utc)),
            "builder": {"name": "motionloom-test-builder", "version": "1.0.0"},
        },
    }
    predicate = statement["predicate"]
    assert isinstance(predicate, dict)
    predicate.update(overrides)
    return statement


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def telemetry_bundle_sha256(task_dir: Path) -> str:
    entries = []
    for path in sorted(task_dir.glob("runtime-adapters/**/runtime-telemetry.json")):
        entries.append({"path": path.resolve().relative_to(task_dir.resolve()).as_posix(), "sha256": sha256_file(path)})
    body = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def make_policy(key_id: str, public_key: bytes, status: str = "active") -> dict:
    now = datetime.now(timezone.utc)
    key = {
        "key_id": key_id,
        "algorithm": "ed25519",
        "public_key_base64": base64.b64encode(public_key).decode("ascii"),
        "status": status,
        "valid_from": iso(now - timedelta(days=1)),
    }
    if status == "revoked":
        key["revoked_at"] = iso(now - timedelta(hours=1))
        key["revocation_reason"] = "fixture compromise"
    return {
        "schema_version": "1.0",
        "policy_id": "motionloom-test-policy",
        "trust_domain": "https://motionloom.dev/trust/test",
        "keys": [key],
        "rotation": {"max_key_age_days": 90, "overlap_days": 7, "require_active_signer": True},
        "revocation": {"mode": "local-policy", "fail_closed": True, "sources": ["fixture"]},
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        private_key = Ed25519PrivateKey.generate()
        key_id = "test-signer-v1"
        key_file = temp / "private.key"
        key_file.write_text(base64.b64encode(private_key.private_bytes_raw()).decode("ascii") + "\n", encoding="utf-8")
        statement_file = temp / "statement.json"
        statement_file.write_text(json.dumps(make_statement(), indent=2) + "\n", encoding="utf-8")
        policy_file = temp / "trust-policy.json"
        policy_file.write_text(json.dumps(make_policy(key_id, private_key.public_key().public_bytes_raw()), indent=2) + "\n", encoding="utf-8")
        bundle_file = temp / "attestation.json"

        built = run([sys.executable, str(BUILDER), "build", "--statement", str(statement_file), "--private-key", str(key_file), "--key-id", key_id, "--output", str(bundle_file)])
        assert built.returncode == 0, built.stderr
        valid = run([sys.executable, str(VERIFIER), "--attestation", str(bundle_file), "--trust-policy", str(policy_file), "--expected-task-id", "browser-review-smoke-task", "--expected-scene", "browser-review-smoke"])
        valid_report = json.loads(valid.stdout)
        assert valid.returncode == 0 and valid_report["verified"] is True and valid_report["approval"] is False

        wrong_binding = run([sys.executable, str(VERIFIER), "--attestation", str(bundle_file), "--trust-policy", str(policy_file), "--expected-task-id", "different-task"])
        assert wrong_binding.returncode == 14

        tampered = json.loads(bundle_file.read_text(encoding="utf-8"))
        tampered["envelope"]["payload_base64"] = base64.b64encode(b"tampered").decode("ascii")
        tampered_file = temp / "tampered.json"
        tampered_file.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
        tamper_result = run([sys.executable, str(VERIFIER), "--attestation", str(tampered_file), "--trust-policy", str(policy_file)])
        assert tamper_result.returncode == 11

        revoked_file = temp / "revoked-policy.json"
        revoked_file.write_text(json.dumps(make_policy(key_id, private_key.public_key().public_bytes_raw(), "revoked"), indent=2) + "\n", encoding="utf-8")
        revoked = run([sys.executable, str(VERIFIER), "--attestation", str(bundle_file), "--trust-policy", str(revoked_file)])
        assert revoked.returncode == 13

        unknown_policy = make_policy("other-signer-v1", private_key.public_key().public_bytes_raw())
        unknown_file = temp / "unknown-policy.json"
        unknown_file.write_text(json.dumps(unknown_policy, indent=2) + "\n", encoding="utf-8")
        unknown = run([sys.executable, str(VERIFIER), "--attestation", str(bundle_file), "--trust-policy", str(unknown_file)])
        assert unknown.returncode == 13

        scene_dir = ROOT / "src" / "output" / "browser-review-smoke"
        task_dir = ROOT / "artifacts" / "browser-review-smoke-task"
        task_statement = make_statement(
            task_id="browser-review-smoke-task",
            scene="browser-review-smoke",
            context_hash=sha256_file(task_dir / "project-context.json"),
            source_sha256=sha256_file(scene_dir / "animation.json"),
            manifest_sha256=sha256_file(scene_dir / "manifest.json"),
            motion_ir_sha256=sha256_file(task_dir / "motion-ir.json"),
            evidence={
                "runtime_evidence_sha256": sha256_file(task_dir / "runtime-adapters" / "runtime-evidence.json"),
                "runtime_telemetry_sha256": telemetry_bundle_sha256(task_dir),
                "verifier_report_sha256": sha256_file(task_dir / "evidence-verifier-report.json"),
            },
            provenance_chain_hash=sha256_file(task_dir / "provenance.json"),
        )
        smoke_statement_file = temp / "smoke-statement.json"
        smoke_statement_file.write_text(json.dumps(task_statement, indent=2) + "\n", encoding="utf-8")
        smoke_bundle_file = temp / "smoke-attestation.json"
        smoke_built = run([sys.executable, str(BUILDER), "build", "--statement", str(smoke_statement_file), "--private-key", str(key_file), "--key-id", key_id, "--output", str(smoke_bundle_file)])
        assert smoke_built.returncode == 0, smoke_built.stderr
        quality_gate = run([
            sys.executable,
            str(ROOT / "scripts" / "quality-gate.py"),
            "--scene", "browser-review-smoke",
            "--context", str(task_dir / "project-context.json"),
            "--task-dir", str(task_dir),
            "--require-attestation",
            "--attestation", str(smoke_bundle_file),
            "--trust-policy", str(policy_file),
        ])
        assert quality_gate.returncode == 0, quality_gate.stdout + quality_gate.stderr
    print("attestation contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
