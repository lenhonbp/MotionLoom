#!/usr/bin/env python3
"""Adversarial regression tests for action-scoped verifier evidence."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GEOMETRY = ROOT / "examples/agent-consumer/asset-consistency/hero-walk-frame-geometry.json"
ACTION_SCRIPT = ROOT / "scripts/action-separation.py"
PREFLIGHT_SCRIPT = ROOT / "scripts/frame-set-preflight.py"


def run_json(script: Path, *args: str) -> tuple[int, dict]:
    result = subprocess.run([sys.executable, str(script), *args, "--json"], cwd=ROOT, capture_output=True, text=True)
    try:
        return result.returncode, json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid JSON from {script}: {result.stdout}\n{result.stderr}") from exc


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def copied_fixture(root: Path) -> tuple[Path, Path]:
    fixture_root = root / "asset-consistency"
    shutil.copytree(ROOT / "examples/agent-consumer/asset-consistency", fixture_root)
    return fixture_root / "action-sequence/hero-walk-action-manifest.json", fixture_root / "hero-walk-frame-geometry.json"


def load_first(manifest: Path, fixture_root: Path) -> tuple[dict, Path, dict]:
    document = json.loads(manifest.read_text(encoding="utf-8"))
    frame = document["frames"][0]
    envelope_path = fixture_root / frame["envelope"]
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    return document, envelope_path, envelope


def validate_variant(mutator) -> tuple[int, dict]:
    with tempfile.TemporaryDirectory(prefix="motionloom-action-separation-") as td:
        root = Path(td)
        manifest, _ = copied_fixture(root)
        fixture_root = root / "asset-consistency"
        document, envelope_path, envelope = load_first(manifest, fixture_root)
        mutator(document, envelope)
        manifest.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        envelope_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")
        return run_json(ACTION_SCRIPT, "validate", "--input", str(manifest), "--root", str(fixture_root))


def has_code(result: dict, code: str) -> bool:
    return any(item.get("code") == code for item in result.get("errors", []))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="motionloom-action-separation-") as td:
        root = Path(td)
        manifest, geometry = copied_fixture(root)
        fixture_root = root / "asset-consistency"

        code, result = run_json(ACTION_SCRIPT, "validate", "--input", str(manifest), "--root", str(fixture_root))
        check(code == 0 and result.get("ready") is True, f"canonical independently bound manifest must pass: {result}")
        check(result["metrics"]["envelope_count"] == 4, "all frame envelopes must be checked")
        check(result["metrics"]["independently_bound_verifications"] == 4, "only independent evidence may count as passing")
        check(result.get("approval") is False, "action separation must never grant approval")

        code, result = run_json(PREFLIGHT_SCRIPT, "--input", str(geometry), "--root", str(fixture_root), "--action-manifest", str(manifest))
        check(code == 0 and result.get("ready") is True, f"manifest-aware frame preflight must pass: {result}")
        check(result["metrics"]["action_manifest"]["passing_action_verifications"] == 4, "preflight must expose independent verification metrics")
        check(result.get("approval") is False, "preflight must preserve approval=false")

        envelope_output = fixture_root / "action-sequence/envelopes/generated.00.json"
        code, result = run_json(ACTION_SCRIPT, "envelope", "--manifest", str(manifest), "--root", str(fixture_root), "--frame-id", "walk.00", "--expected-action", "walk", "--top-competitor", "run", "--margin", "0.42", "--threshold", "0.20", "--output", str(envelope_output))
        generated = json.loads(envelope_output.read_text(encoding="utf-8"))
        check(code != 0 and result.get("approval") is False, "generator envelope must not claim independent verification")
        check(generated["verifier"]["verification_mode"] == "declared" and generated["verifier"]["status"] == "quarantined", "generator-created evidence must remain declared/quarantined")

    code, result = validate_variant(lambda _document, envelope: envelope["verifier"].update({"verifier_id": envelope["generator_agent_id"]}))
    check(code != 0 and has_code(result, "non_independent_verifier"), "verifier equal to generator must fail closed")

    code, result = validate_variant(lambda _document, envelope: envelope["verifier"].pop("evidence"))
    check(code != 0 and has_code(result, "missing_verifier_provenance"), "missing verifier provenance must fail closed")

    code, result = validate_variant(lambda _document, envelope: envelope["verifier"].update({"margin": 0.91}))
    check(code != 0 and (has_code(result, "verifier_result_mismatch") or has_code(result, "verifier_result_hash_mismatch")), "modified verifier result must fail closed")

    code, result = validate_variant(lambda _document, envelope: envelope["verifier"]["evidence"].update({"artifact_sha256": "0" * 64}))
    check(code != 0 and has_code(result, "verifier_evidence_hash_mismatch"), "modified verifier evidence hash must fail closed")

    code, result = validate_variant(lambda _document, envelope: envelope["verifier"].update({"margin": 0.05}))
    check(code != 0 and has_code(result, "action_confidence_margin"), "low confidence must remain blocked")

    code, result = validate_variant(lambda _document, envelope: envelope["verifier"].update({"expected_action": "attack"}))
    check(code != 0 and has_code(result, "action_verifier_mismatch"), "wrong expected action must fail closed")

    code, result = validate_variant(lambda _document, envelope: envelope["verifier"].update({"top_competitor": "slide"}))
    check(code != 0 and has_code(result, "undeclared_competitor"), "undeclared competitor must fail closed")

    code, result = validate_variant(lambda _document, envelope: envelope["verifier"].update({"status": "quarantined"}))
    check(code != 0 and has_code(result, "action_verification_required"), "quarantined evidence must remain quarantined")

    code, result = validate_variant(lambda _document, envelope: envelope.update({"approval": True}))
    check(code != 0 and has_code(result, "approval_boundary"), "approval=true must fail closed on every machine path")

    print("action separation tests: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"action separation tests: FAIL — {exc}", file=sys.stderr)
        raise
