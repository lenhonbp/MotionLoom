from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "artifact-intake.py"


def load_module():
    spec = importlib.util.spec_from_file_location("artifact_intake", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load artifact intake")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, document: dict) -> Path:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def bundle(root: Path) -> tuple[Path, Path, Path, Path]:
    evidence = root / "evidence.md"
    evidence.write_text("internal capability evidence\n", encoding="utf-8")
    frame_a = root / "frame-00.png"
    frame_b = root / "frame-01.png"
    frame_a.write_bytes(b"frame-zero")
    frame_b.write_bytes(b"frame-one")
    registry = {
        "schema_version": "0.1", "registry_id": "test-registry", "generated_at": "2026-08-15T00:00:00Z",
        "selection_policy": {"require_verified": True, "allow_scaffold_only": False},
        "adapters": [{
            "adapter_id": "fixture.local", "kind": "fixture", "status": "static_validated", "adapter_version": "0.1",
            "invocation_mode": "none", "cost_class": "included", "inputs": ["reference"], "outputs": ["frame_sequence"],
            "compatibility": {"os": ["linux", "macos", "windows"]},
            "evidence": [{"path": "evidence.md", "sha256": sha(evidence), "kind": "static"}],
            "limitations": ["fixture only"], "risk_level": "low", "side_effect_level": "read"
        }]
    }
    controls = {
        "schema_version": "0.1", "control_id": "test-controls", "asset_id": "test-asset", "created_at": "2026-08-15T00:00:00Z",
        "references": [{"id": "identity", "path": "frame-00.png", "sha256": sha(frame_a), "role": "identity"}],
        "tracks": [
            {"id": "identity", "kind": "identity", "binding": "required", "value_hash": "1" * 64},
            {"id": "pose", "kind": "pose", "binding": "required", "value_hash": "2" * 64, "samples": 2}
        ],
        "output_profile": {"kind": "frame_sequence", "fps": 12, "expected_frame_count": 2, "loop": True}
    }
    provenance = {
        "authority": "ai_generated",
        "files": [{"path": "frame-00.png", "sha256": sha(frame_a)}, {"path": "frame-01.png", "sha256": sha(frame_b)}]
    }
    receipt = {
        "schema_version": "0.1", "receipt_id": "test-receipt", "created_at": "2026-08-15T00:00:00Z",
        "asset": {"id": "test-asset", "kind": "frame_sequence", "intended_use": "pilot"}, "authority": "ai_generated",
        "provider": {"adapter_id": "fixture.local", "kind": "fixture", "invocation_mode": "none", "task_id": "task-1", "model": "fixture", "generated_at": "2026-08-15T00:00:00Z", "cost_class": "included"},
        "control_track_ref": "controls.json", "provenance_ref": "provenance.json",
        "outputs": [
            {"path": "frame-00.png", "role": "frame-00", "sha256": sha(frame_a), "bytes": frame_a.stat().st_size},
            {"path": "frame-01.png", "role": "frame-01", "sha256": sha(frame_b), "bytes": frame_b.stat().st_size}
        ]
    }
    export = {
        "schema_version": "0.1", "manifest_id": "test-export", "asset_id": "test-asset", "created_at": "2026-08-15T00:00:00Z",
        "receipt_ref": "receipt.json", "control_track_ref": "controls.json",
        "outputs": [dict(entry, target="preview") for entry in receipt["outputs"]]
    }
    return write(root / "registry.json", registry), write(root / "receipt.json", receipt), write(root / "controls.json", controls), write(root / "export.json", export), write(root / "provenance.json", provenance)


def result(root: Path, registry: Path, receipt: Path, controls: Path, export: Path, strict: bool = False) -> dict:
    return MODULE.evaluate_bundle(SimpleNamespace(root=root, registry=registry, receipt=receipt, controls=controls, export_manifest=export, strict=strict))


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        registry, receipt, controls, export, provenance = bundle(root)
        valid = result(root, registry, receipt, controls, export)
        check(valid["ready"] and valid["status"] == "review_required", "static adapter must produce review_required evidence, not approval")
        check(not valid["production_eligible"] and not valid["production_approved"], "intake must never grant production authority")
        strict = result(root, registry, receipt, controls, export, strict=True)
        check(not strict["ready"] and any(item["code"] == "adapter_not_runtime_verified" for item in strict["errors"]), "strict intake must fail a non-verified adapter")

        receipt_doc = json.loads(receipt.read_text())
        receipt_doc["outputs"][0]["sha256"] = "0" * 64
        tampered = write(root / "tampered-receipt.json", receipt_doc)
        bad_hash = result(root, registry, tampered, controls, export)
        check(not bad_hash["ready"] and any(item["code"] == "sha256_mismatch" for item in bad_hash["errors"]), "output hash tampering must fail closed")

        unknown_doc = copy.deepcopy(json.loads(receipt.read_text()))
        unknown_doc["provider"]["adapter_id"] = "missing.adapter"
        unknown = write(root / "unknown-receipt.json", unknown_doc)
        unknown_result = result(root, registry, unknown, controls, export)
        check(not unknown_result["ready"] and any(item["code"] == "unknown_adapter" for item in unknown_result["errors"]), "unknown adapter must fail closed")

        approval_doc = copy.deepcopy(json.loads(receipt.read_text()))
        approval_doc["production_approved"] = True
        approval = write(root / "approval-receipt.json", approval_doc)
        approval_result = result(root, registry, approval, controls, export)
        check(not approval_result["ready"] and any(item["code"] == "approval_forbidden" for item in approval_result["errors"]), "receipt cannot self-assert approval")

        controls_doc = json.loads(controls.read_text())
        controls_doc["tracks"] = [controls_doc["tracks"][0]]
        no_motion = write(root / "no-motion-controls.json", controls_doc)
        no_motion_result = result(root, registry, receipt, no_motion, export)
        check(not no_motion_result["ready"] and any(item["code"] == "missing_motion_control" for item in no_motion_result["errors"]), "animated output requires motion or pose controls")

        export_doc = json.loads(export.read_text())
        export_doc["outputs"][1]["sha256"] = "f" * 64
        bad_export = write(root / "bad-export.json", export_doc)
        export_result = result(root, registry, receipt, controls, bad_export)
        check(not export_result["ready"] and any(item["code"] in {"sha256_mismatch", "receipt_output_missing"} for item in export_result["errors"]), "export must bind to receipt bytes")

        cli = subprocess.run([sys.executable, str(MODULE_PATH), "intake", "--root", str(root), "--registry", str(registry), "--receipt", str(receipt), "--controls", str(controls), "--export-manifest", str(export), "--json"], capture_output=True, text=True)
        cli_result = json.loads(cli.stdout)
        check(cli.returncode == 0 and cli_result["status"] == "review_required", "CLI must return evidence without provider invocation")
    print("artifact intake contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
