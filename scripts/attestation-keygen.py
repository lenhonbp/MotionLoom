#!/usr/bin/env python3
"""Create a non-production Ed25519 trust fixture for local/CI attestation tests."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from attestation import KEY_ID_RE, reject_symlink_components, validate_policy


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an ephemeral MotionLoom Ed25519 trust fixture")
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--key-id", required=True)
    args = parser.parse_args()
    try:
        if not KEY_ID_RE.fullmatch(args.key_id):
            raise ValueError("key-id has an unsafe format")
        private_path = Path(args.private_key).expanduser().absolute()
        policy_path = Path(args.policy).expanduser().absolute()
        reject_symlink_components(private_path.parent)
        reject_symlink_components(policy_path.parent)
        private_path.parent.mkdir(parents=True, exist_ok=True)
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        private_path.write_text(base64.b64encode(private_key.private_bytes_raw()).decode("ascii") + "\n", encoding="utf-8")
        policy = {
            "schema_version": "1.0",
            "policy_id": "motionloom-ephemeral-ci-policy",
            "trust_domain": "https://motionloom.dev/trust/ci-ephemeral",
            "keys": [{
                "key_id": args.key_id,
                "algorithm": "ed25519",
                "public_key_base64": base64.b64encode(private_key.public_key().public_bytes_raw()).decode("ascii"),
                "status": "active",
                "valid_from": iso_now(),
            }],
            "rotation": {"max_key_age_days": 1, "overlap_days": 0, "require_active_signer": True},
            "revocation": {"mode": "local-policy", "fail_closed": True, "sources": ["ci-ephemeral"]},
        }
        validate_policy(policy)
        policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"generated": True, "key_id": args.key_id, "policy": str(policy_path)}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"attestation keygen error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
