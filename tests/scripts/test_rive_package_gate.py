"""Regression tests for the fail-closed Rive package gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_gate():
    spec = importlib.util.spec_from_file_location("test_rive_package_gate", ROOT / "scripts" / "rive-package-gate.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GATE = load_gate()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RivePackageGateTests(unittest.TestCase):
    def build_bundle(self, directory: Path) -> tuple[Path, Path]:
        source = directory / "hero.riv"
        source.write_bytes(b"RIVE\x07\x00demo-real-test-bytes")
        runtime = directory / "runtime.json"
        runtime.write_text(json.dumps({"schema_version": "1.0", "run_id": "rive-test", "generated_at": "2026-08-15T00:00:00Z", "mode": "runtime", "harness": "test", "source_sha256": sha(source), "status": "pass", "frameworks": [{"run_id": "rive-test", "framework": "rive", "runtime": "rive-web", "status": "pass", "ready": True, "frames": [0, 50, 100]}]}), encoding="utf-8")
        provenance = directory / "provenance.json"
        provenance.write_text(json.dumps({"schema_version": "1.0", "provenance_id": "test-rive", "asset": {"id": "hero-rive", "path": "hero.riv", "type": "character", "framework": "rive"}, "authority": "ai_generated", "readiness": "runtime_ready", "generator": {"model": "internal-imagegen", "task_id": "test", "source": "internal", "generated_at": "2026-08-15T00:00:00Z"}, "files": [{"path": "hero.riv", "role": "runtime-package", "sha256": sha(source), "bytes": source.stat().st_size}], "license": {"spdx": "LicenseRef-AI-Pilot", "source": "internal-imagegen", "attribution": "AI-generated pilot; human review required"}, "provenance_chain": [{"step": "generated", "actor": "agent", "source": "internal-imagegen", "timestamp": "2026-08-15T00:00:00Z"}], "created_at": "2026-08-15T00:00:00Z"}), encoding="utf-8")
        manifest = directory / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": "0.1", "package_id": "hero-rive-package", "package_class": "ai_generated_pilot", "asset": {"id": "hero-rive", "path": "hero.riv", "sha256": sha(source), "bytes": source.stat().st_size}, "provenance_ref": "provenance.json", "runtime": {"adapter_id": "motionloom.rive-runtime", "target": "rive", "required_state_machines": ["Locomotion"], "required_inputs": ["speed"], "required_events": ["footstep"], "runtime_evidence_ref": "runtime.json", "runtime_evidence_sha256": sha(runtime), "review_required": True}, "actions": ["idle", "walk"], "review_required": True}), encoding="utf-8")
        registry = directory / "registry.json"
        adapter_source = directory / "adapter.mjs"
        adapter_source.write_text("export const rive = true;\n", encoding="utf-8")
        registry.write_text(json.dumps({"schema_version": "0.1", "adapters": [{"adapter_id": "motionloom.rive-runtime", "target": "rive", "framework": "rive", "status": "project_integrated", "evidence": [{"path": "adapter.mjs", "sha256": sha(adapter_source)}]}]}), encoding="utf-8")
        return manifest, registry

    def validate(self, manifest: Path, registry: Path, strict: bool = True):
        return GATE.validate(argparse.Namespace(input=manifest, root=manifest.parent, registry=registry, strict=strict))

    def test_valid_ai_pilot_is_runtime_test_ready_but_not_approved(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest, registry = self.build_bundle(Path(raw))
            result = self.validate(manifest, registry)
            self.assertEqual(result["status"], "pass")
            self.assertTrue(result["runtime_test_ready"])
            self.assertTrue(result["review_required"])
            self.assertFalse(result["production_approved"])

    def test_rejects_tampered_riv_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest, registry = self.build_bundle(Path(raw))
            (Path(raw) / "hero.riv").write_bytes(b"RIVETwitter")
            result = self.validate(manifest, registry)
            self.assertEqual(result["status"], "blocked")
            self.assertTrue(any(item["code"] == "asset_sha256_mismatch" for item in result["issues"]))

    def test_strict_rejects_missing_runtime_proof(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest, registry = self.build_bundle(Path(raw))
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["runtime"].pop("runtime_evidence_ref")
            data["runtime"].pop("runtime_evidence_sha256")
            manifest.write_text(json.dumps(data), encoding="utf-8")
            result = self.validate(manifest, registry)
            self.assertEqual(result["status"], "blocked")
            self.assertTrue(any(item["code"] == "runtime_evidence_required" for item in result["issues"]))

    def test_rejects_suppressed_review_and_unknown_adapter(self):
        with tempfile.TemporaryDirectory() as raw:
            manifest, registry = self.build_bundle(Path(raw))
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["review_required"] = False
            data["runtime"]["adapter_id"] = "untrusted-rive"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            result = self.validate(manifest, registry)
            self.assertEqual(result["status"], "blocked")
            codes = {item["code"] for item in result["issues"]}
            self.assertIn("review_required", codes)
            self.assertIn("unknown_adapter", codes)


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(RivePackageGateTests))
    if result.wasSuccessful():
        print("rive package gate contract tests: PASS")
        raise SystemExit(0)
    raise SystemExit(1)
