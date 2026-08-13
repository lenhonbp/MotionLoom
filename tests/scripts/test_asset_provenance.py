"""Focused regression tests for the asset provenance contract."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "asset-provenance.py"
SPEC = importlib.util.spec_from_file_location("asset_provenance", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def make_document(asset_path: str, digest: str, *, authority: str = "ai_generated", readiness: str = "runtime_ready") -> dict:
    document = {
        "schema_version": "1.0",
        "provenance_id": "test-asset-provenance",
        "task_id": "test-task",
        "scene": "test-scene",
        "created_at": "2026-08-14T00:00:00Z",
        "asset": {"id": "test-asset", "path": asset_path, "type": "runtime-pilot", "framework": "body-rig"},
        "authority": authority,
        "readiness": readiness,
        "generator": {
            "model": "test-model",
            "task_id": "test-task",
            "source": "test-fixture",
            "generated_at": "2026-08-14T00:00:00Z",
        },
        "license": {"spdx": "UNLICENSED", "source": "test", "attribution": "test"},
        "files": [{"path": asset_path, "role": "runtime-pilot", "sha256": digest}],
        "provenance_chain": [{"step": "generate", "actor": "agent:test", "source": "test", "timestamp": "2026-08-14T00:00:00Z"}],
        "runtime_evidence": {"status": "pass", "runtime": "test-runtime", "tested_at": "2026-08-14T00:00:00Z"},
    }
    if authority == "artist_authored":
        document["human_attestation"] = {
            "attestor": "agent-self-assertion",
            "attestor_type": "artist",
            "decision": "artist_authored",
            "attested_at": "2026-08-14T00:00:00Z",
            "user_confirmed": False,
        }
    return document


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        asset = root / "pilot.json"
        asset.write_text('{"fixture":"runtime-pilot"}\n', encoding="utf-8")
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()

        pilot = make_document("pilot.json", digest)
        pilot_path = root / "pilot-provenance.json"
        pilot_path.write_text(json.dumps(pilot), encoding="utf-8")

        contract = MODULE.evaluate(pilot_path)
        check(contract["status"] == "pass", "AI-generated pilot contract should validate")
        runtime = MODULE.evaluate(pilot_path, base=root, mode="runtime")
        check(runtime["status"] == "pass" and not runtime["summary"]["production_eligible"], "AI-generated pilot should be runtime-ready only")
        production = MODULE.evaluate(pilot_path, base=root, mode="production")
        check(production["status"] == "fail" and not production["summary"]["production_eligible"], "AI-generated pilot must fail production gate")

        pilot["files"][0]["sha256"] = "0" * 64
        tampered_path = root / "tampered.json"
        tampered_path.write_text(json.dumps(pilot), encoding="utf-8")
        tampered = MODULE.evaluate(tampered_path, base=root, mode="runtime")
        check(tampered["status"] == "fail" and any("SHA-256 mismatch" in item for item in tampered["errors"]), "asset hash tampering must fail closed")

        artist_claim = make_document("pilot.json", digest, authority="artist_authored", readiness="runtime_ready")
        artist_path = root / "artist-self-asserted.json"
        artist_path.write_text(json.dumps(artist_claim), encoding="utf-8")
        artist = MODULE.evaluate(artist_path)
        check(artist["status"] == "fail" and any("user_confirmed" in item or "Agent-only authority" in item for item in artist["errors"]), "Agent cannot self-assert artist authority")

    print("asset provenance contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
