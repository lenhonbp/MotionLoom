#!/usr/bin/env python3
"""Run the deterministic Intelligence Core eval corpus.

The runner intentionally uses clean temporary roots and subprocesses the same
CLI entrypoints used by Agents and CI. It reports each case as pass/fail and
never turns a negative case into a successful acceptance.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
INTELLIGENCE = ROOT / "scripts/intelligence.py"
PROJECT_EVAL = ROOT / "scripts/eval-projects.py"
REPORT = ROOT / "scripts/report.py"
VERIFIER = ROOT / "scripts/evidence-verifier.py"
ATTESTATION = ROOT / "scripts/attestation.py"
ATTESTATION_VERIFIER = ROOT / "scripts/attestation-verifier.py"
CASES = ROOT / "tests/evals/intelligence-cases.json"


def invoke(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=cwd or ROOT, capture_output=True, text=True)


def record(results: list[dict[str, object]], case_id: str, passed: bool, detail: str = "") -> None:
    results.append({"id": case_id, "status": "pass" if passed else "fail", "detail": detail.strip()[-500:]})


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def attestation_policy(key_id: str, public_key: bytes, status: str = "active") -> dict[str, object]:
    now = datetime.now(timezone.utc)
    key: dict[str, object] = {
        "key_id": key_id,
        "algorithm": "ed25519",
        "public_key_base64": base64.b64encode(public_key).decode("ascii"),
        "status": status,
        "valid_from": iso(now - timedelta(days=1)),
    }
    if status == "revoked":
        key["revoked_at"] = iso(now - timedelta(hours=1))
        key["revocation_reason"] = "eval fixture revocation"
    return {
        "schema_version": "1.0",
        "policy_id": "motionloom-eval-policy",
        "trust_domain": "https://motionloom.dev/trust/eval",
        "keys": [key],
        "rotation": {"max_key_age_days": 90, "overlap_days": 7, "require_active_signer": True},
        "revocation": {"mode": "local-policy", "fail_closed": True, "sources": ["eval-fixture"]},
    }


def run_attestation_cases(root: Path, results: list[dict[str, object]]) -> None:
    """Exercise the signed-attestation boundary with stable verifier outcomes."""
    case_root = root / "attestation-eval"
    case_root.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()
    key_id = "eval-signer-v1"
    private_key_path = case_root / "private.key"
    private_key_path.write_text(base64.b64encode(private_key.private_bytes_raw()).decode("ascii") + "\n", encoding="utf-8")
    policy_path = case_root / "trust-policy.json"
    policy_path.write_text(json.dumps(attestation_policy(key_id, private_key.public_key().public_bytes_raw()), indent=2) + "\n", encoding="utf-8")
    statement = {
        "type": "https://motionloom.dev/attestation/v1",
        "predicate_type": "https://motionloom.dev/predicate/animation-evidence/v1",
        "subject": [{"name": "eval-scene", "digest": {"sha256": "a" * 64}}],
        "predicate": {
            "task_id": "attestation-eval-task",
            "scene": "eval-scene",
            "context_hash": "b" * 64,
            "source_sha256": "c" * 64,
            "manifest_sha256": "d" * 64,
            "motion_ir_sha256": "e" * 64,
            "evidence": {
                "runtime_evidence_sha256": "f" * 64,
                "runtime_telemetry_sha256": "0" * 64,
                "verifier_report_sha256": "1" * 64,
            },
            "provenance_chain_hash": "2" * 64,
            "policy_version": "1.0",
            "generated_at": iso(datetime.now(timezone.utc)),
            "builder": {"name": "motionloom-eval", "version": "1.0.0"},
        },
    }
    statement_path = case_root / "statement.json"
    statement_path.write_text(json.dumps(statement, indent=2) + "\n", encoding="utf-8")
    bundle_path = case_root / "attestation.json"
    built = invoke([
        str(ATTESTATION), "build", "--statement", str(statement_path), "--private-key", str(private_key_path),
        "--key-id", key_id, "--output", str(bundle_path),
    ])
    clean = invoke([
        str(ATTESTATION_VERIFIER), "--attestation", str(bundle_path), "--trust-policy", str(policy_path),
        "--expected-task-id", "attestation-eval-task", "--expected-scene", "eval-scene",
    ])
    clean_doc = json.loads(clean.stdout) if clean.stdout.strip().startswith("{") else {}
    record(results, "p2-attestation-clean", built.returncode == 0 and clean.returncode == 0 and clean_doc.get("verified") is True and clean_doc.get("approval") is False, clean.stdout + clean.stderr)

    tampered = json.loads(bundle_path.read_text(encoding="utf-8"))
    tampered["envelope"]["payload_base64"] = base64.b64encode(b"tampered").decode("ascii")
    tampered_path = case_root / "tampered.json"
    tampered_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    tamper_result = invoke([str(ATTESTATION_VERIFIER), "--attestation", str(tampered_path), "--trust-policy", str(policy_path)])
    record(results, "p2-attestation-payload-tamper", tamper_result.returncode == 11, tamper_result.stdout + tamper_result.stderr)

    binding_result = invoke([
        str(ATTESTATION_VERIFIER), "--attestation", str(bundle_path), "--trust-policy", str(policy_path),
        "--expected-task-id", "foreign-task",
    ])
    record(results, "p2-attestation-binding-mismatch", binding_result.returncode == 14, binding_result.stdout + binding_result.stderr)

    revoked_policy = case_root / "revoked-policy.json"
    revoked_policy.write_text(json.dumps(attestation_policy(key_id, private_key.public_key().public_bytes_raw(), "revoked"), indent=2) + "\n", encoding="utf-8")
    revoked_result = invoke([str(ATTESTATION_VERIFIER), "--attestation", str(bundle_path), "--trust-policy", str(revoked_policy)])
    record(results, "p2-attestation-revoked-signer", revoked_result.returncode == 13, revoked_result.stdout + revoked_result.stderr)

    unknown_policy = case_root / "unknown-policy.json"
    unknown_policy.write_text(json.dumps(attestation_policy("other-signer-v1", private_key.public_key().public_bytes_raw()), indent=2) + "\n", encoding="utf-8")
    unknown_result = invoke([str(ATTESTATION_VERIFIER), "--attestation", str(bundle_path), "--trust-policy", str(unknown_policy)])
    record(results, "p2-attestation-unknown-signer", unknown_result.returncode == 13, unknown_result.stdout + unknown_result.stderr)


def run_project_corpus_cases(root: Path, results: list[dict[str, object]]) -> None:
    """Keep first-party analyzer evidence separate from unavailable external evidence."""
    first_party = invoke([
        str(PROJECT_EVAL), "--workspace", str(ROOT), "--require-external", "0", "--allow-insufficient"
    ])
    first_doc = json.loads(first_party.stdout) if first_party.stdout.strip().startswith("{") else {}
    first_pass = any(item.get("id") == "motionloom-first-party" and item.get("status") == "pass" for item in first_doc.get("results", []))
    record(results, "project-corpus-first-party-pass", first_party.returncode == 0 and first_doc.get("status") == "pass" and first_pass, first_party.stdout + first_party.stderr)

    insufficient = invoke([
        str(PROJECT_EVAL), "--workspace", str(ROOT), "--allow-insufficient"
    ])
    insufficient_doc = json.loads(insufficient.stdout) if insufficient.stdout.strip().startswith("{") else {}
    record(
        results,
        "project-corpus-insufficient-external-explicit",
        insufficient.returncode == 0 and insufficient_doc.get("status") == "insufficient_evidence" and insufficient_doc.get("unavailable_external_projects") == 3,
        insufficient.stdout + insufficient.stderr,
    )


def run_p1_cases(root: Path, task_dir: Path, results: list[dict[str, object]]) -> None:
    """Exercise P1 semantic, continuity and feedback contracts in isolated copies."""
    lint_task = root / "p1-human-review"
    shutil.copytree(task_dir, lint_task)
    lint_result = invoke([str(INTELLIGENCE), "semantic-lint", "build", "--task-dir", str(lint_task)])
    lint_data: dict[str, object] = {}
    if (lint_task / "semantic-lint-report.json").is_file():
        lint_data = json.loads((lint_task / "semantic-lint-report.json").read_text(encoding="utf-8"))
    human_warning = any(
        isinstance(item, dict) and item.get("basis") == "human" and not item.get("approval_blocking")
        for item in lint_data.get("findings", []) if isinstance(lint_data.get("findings"), list)
    )
    record(results, "p1-human-review-warning-preserved", lint_result.returncode == 0 and human_warning, lint_result.stdout + lint_result.stderr)

    generic_task = root / "p1-generic-intent"
    shutil.copytree(task_dir, generic_task)
    generic_ir_path = generic_task / "motion-ir.json"
    generic_ir = json.loads(generic_ir_path.read_text(encoding="utf-8"))
    generic_ir["intent"] = "motion"
    generic_ir_path.write_text(json.dumps(generic_ir, indent=2) + "\n", encoding="utf-8")
    generic_result = invoke([str(INTELLIGENCE), "semantic-lint", "build", "--task-dir", str(generic_task)])
    generic_report = json.loads((generic_task / "semantic-lint-report.json").read_text(encoding="utf-8"))
    generic_warning = any(item.get("id") == "intent-low-specificity" for item in generic_report.get("findings", []))
    record(results, "p1-generic-intent-warning", generic_result.returncode == 0 and generic_warning and generic_report.get("status") == "warn", generic_result.stdout + generic_result.stderr)

    continuity_a = root / "p1-continuity-a"
    continuity_b = root / "p1-continuity-b"
    shutil.copytree(task_dir, continuity_a)
    shutil.copytree(task_dir, continuity_b)
    task_b_path = continuity_b / "task.json"
    task_b = json.loads(task_b_path.read_text(encoding="utf-8"))
    task_b["task_id"] = "professional-review-followup"
    task_b["scene"] = "browser-review-followup"
    task_b["scene_order"] = 1
    task_b_path.write_text(json.dumps(task_b, indent=2) + "\n", encoding="utf-8")
    ir_b_path = continuity_b / "motion-ir.json"
    ir_b = json.loads(ir_b_path.read_text(encoding="utf-8"))
    ir_b["task_id"] = task_b["task_id"]
    ir_b["scene"] = task_b["scene"]
    ir_b["context_hash"] = "f" * 64
    ir_b_path.write_text(json.dumps(ir_b, indent=2) + "\n", encoding="utf-8")
    continuity_output = root / "p1-continuity-drift.json"
    continuity_result = invoke([
        str(INTELLIGENCE), "continuity", "build", "--task-dirs", str(continuity_a), str(continuity_b), "--output", str(continuity_output)
    ])
    continuity_report = json.loads(continuity_output.read_text(encoding="utf-8")) if continuity_output.is_file() else {}
    transitions = continuity_report.get("transitions", []) if isinstance(continuity_report, dict) else []
    drift_found = bool(transitions) and "context hash changes between adjacent scenes" in transitions[0].get("findings", [])
    record(results, "p1-continuity-context-drift", continuity_result.returncode == 0 and continuity_report.get("status") == "warn" and drift_found, continuity_result.stdout + continuity_result.stderr)

    fix_plan_path = task_dir / "fix-plan.json"
    fix_plan_result = invoke([str(INTELLIGENCE), "fix-plan", "validate", "--path", str(fix_plan_path)])
    fix_plan = json.loads(fix_plan_path.read_text(encoding="utf-8")) if fix_plan_path.is_file() else {}
    selective = any(
        isinstance(issue, dict) and "lint" in issue.get("rerun_scope", []) and issue.get("finding_ref")
        for issue in fix_plan.get("issues", []) if isinstance(fix_plan.get("issues"), list)
    )
    handoff = json.loads((task_dir / "handoff.json").read_text(encoding="utf-8"))
    synced = handoff.get("fix_plan", {}).get("path") == "fix-plan.json" and "semantic-lint-report.json" in handoff.get("required_artifacts", [])
    record(results, "p1-fix-plan-selective-rerun", fix_plan_result.returncode == 0 and selective and synced, fix_plan_result.stdout + fix_plan_result.stderr)


def run_performance_perceptual_cases(root: Path, task_dir: Path, results: list[dict[str, object]]) -> None:
    """Exercise non-blocking performance/perceptual findings and the benchmark contract."""
    duration_task = root / "p1-perf-duration-budget"
    shutil.copytree(task_dir, duration_task)
    duration_ir_path = duration_task / "motion-ir.json"
    duration_ir = json.loads(duration_ir_path.read_text(encoding="utf-8"))
    duration_ir["duration_ms"] = 600
    duration_ir_path.write_text(json.dumps(duration_ir, indent=2) + "\n", encoding="utf-8")
    duration_result = invoke([str(INTELLIGENCE), "semantic-lint", "build", "--task-dir", str(duration_task)])
    duration_report = json.loads((duration_task / "semantic-lint-report.json").read_text(encoding="utf-8")) if (duration_task / "semantic-lint-report.json").is_file() else {}
    duration_warning = any(item.get("id") == "perf-animation-budget" and item.get("severity") == "warning" and not item.get("approval_blocking") for item in duration_report.get("findings", []))
    record(results, "p1-perf-duration-budget-warning", duration_result.returncode == 0 and duration_warning, duration_result.stdout + duration_result.stderr)

    fps_task = root / "p1-perf-fps"
    shutil.copytree(task_dir, fps_task)
    fps_ir_path = fps_task / "motion-ir.json"
    fps_ir = json.loads(fps_ir_path.read_text(encoding="utf-8"))
    fps_ir["fps"] = 24
    fps_ir_path.write_text(json.dumps(fps_ir, indent=2) + "\n", encoding="utf-8")
    fps_result = invoke([str(INTELLIGENCE), "semantic-lint", "build", "--task-dir", str(fps_task)])
    fps_report = json.loads((fps_task / "semantic-lint-report.json").read_text(encoding="utf-8")) if (fps_task / "semantic-lint-report.json").is_file() else {}
    fps_warning = any(item.get("id") == "perf-frame-rate" and item.get("severity") == "warning" for item in fps_report.get("findings", []))
    record(results, "p1-perf-fps-warning", fps_result.returncode == 0 and fps_warning, fps_result.stdout + fps_result.stderr)

    easing_task = root / "p1-perceptual-easing"
    shutil.copytree(task_dir, easing_task)
    easing_ir_path = easing_task / "motion-ir.json"
    easing_ir = json.loads(easing_ir_path.read_text(encoding="utf-8"))
    for keyframe in easing_ir.get("tracks", [])[0].get("keyframes", []):
        keyframe["easing"] = "linear"
    easing_ir_path.write_text(json.dumps(easing_ir, indent=2) + "\n", encoding="utf-8")
    easing_result = invoke([str(INTELLIGENCE), "semantic-lint", "build", "--task-dir", str(easing_task)])
    easing_report = json.loads((easing_task / "semantic-lint-report.json").read_text(encoding="utf-8")) if (easing_task / "semantic-lint-report.json").is_file() else {}
    easing_warning = any(item.get("id") == "perceptual-easing-linear" and item.get("severity") == "warning" for item in easing_report.get("findings", []))
    record(results, "p1-perceptual-easing-linear-warning", easing_result.returncode == 0 and easing_warning, easing_result.stdout + easing_result.stderr)

    reduced_task = root / "p1-perceptual-reduced-motion"
    shutil.copytree(task_dir, reduced_task)
    reduced_ir_path = reduced_task / "motion-ir.json"
    reduced_ir = json.loads(reduced_ir_path.read_text(encoding="utf-8"))
    reduced_ir.setdefault("accessibility", {})["reduced_motion"] = "none"
    reduced_ir_path.write_text(json.dumps(reduced_ir, indent=2) + "\n", encoding="utf-8")
    reduced_result = invoke([str(INTELLIGENCE), "semantic-lint", "build", "--task-dir", str(reduced_task)])
    reduced_report = json.loads((reduced_task / "semantic-lint-report.json").read_text(encoding="utf-8")) if (reduced_task / "semantic-lint-report.json").is_file() else {}
    reduced_warning = any(item.get("id") == "perceptual-reduced-motion-missing" and item.get("severity") == "warning" and not item.get("approval_blocking") for item in reduced_report.get("findings", []))
    record(results, "p1-perceptual-reduced-motion-warning", reduced_result.returncode == 0 and reduced_warning, reduced_result.stdout + reduced_result.stderr)

    benchmark_task = root / "p1-benchmark"
    shutil.copytree(task_dir, benchmark_task)
    benchmark_path = benchmark_task / "semantic-lint-benchmark.json"
    benchmark_result = invoke([
        str(INTELLIGENCE), "semantic-lint", "benchmark", "--task-dir", str(benchmark_task),
        "--iterations", "10", "--threshold-ms", "500", "--output", str(benchmark_path),
    ])
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path.is_file() else {}
    benchmark_ok = benchmark.get("status") == "pass" and benchmark.get("p95_ms", 999999) < benchmark.get("threshold_ms", 0) and benchmark.get("rule_count", 0) >= 10
    record(results, "p1-benchmark-execution-time", benchmark_result.returncode == 0 and benchmark_ok, benchmark_result.stdout + benchmark_result.stderr)


def run_runtime_verifier_cases(root: Path, results: list[dict[str, object]]) -> None:
    """Exercise external verification without granting approval or trusting paths."""
    scene = root / "telemetry-scene/browser-review-smoke"
    task = root / "telemetry-task"
    shutil.copytree(ROOT / "src/output/browser-review-smoke", scene)
    shutil.copytree(ROOT / "artifacts/browser-review-smoke-task", task)
    base = [str(VERIFIER), "--scene-dir", str(scene), "--task-dir", str(task)]

    clean = invoke(base)
    clean_doc = json.loads(clean.stdout) if clean.stdout.strip().startswith("{") else {}
    record(results, "p2-runtime-verifier-clean", clean.returncode == 0 and clean_doc.get("verified") is True and clean_doc.get("approval") is False, clean.stdout + clean.stderr)

    tampered_task = root / "telemetry-tampered"
    shutil.copytree(task, tampered_task)
    tampered_path = tampered_task / "runtime-adapters/rive/runtime-telemetry.json"
    tampered = json.loads(tampered_path.read_text(encoding="utf-8"))
    tampered["samples"][0]["state"]["eval_tamper"] = True
    tampered_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
    tampered_result = invoke([str(VERIFIER), "--scene-dir", str(scene), "--task-dir", str(tampered_task)])
    record(results, "p2-runtime-verifier-tamper", tampered_result.returncode != 0 and "sha256 mismatch" in tampered_result.stdout, tampered_result.stdout + tampered_result.stderr)

    foreign_task = root / "telemetry-foreign-task"
    shutil.copytree(task, foreign_task)
    foreign_doc = json.loads((foreign_task / "task.json").read_text(encoding="utf-8"))
    foreign_doc["task_id"] = "telemetry-foreign-task"
    (foreign_task / "task.json").write_text(json.dumps(foreign_doc, indent=2) + "\n", encoding="utf-8")
    foreign_result = invoke([str(VERIFIER), "--scene-dir", str(scene), "--task-dir", str(foreign_task)])
    record(results, "p2-runtime-verifier-cross-task", foreign_result.returncode != 0 and "task_id" in foreign_result.stdout, foreign_result.stdout + foreign_result.stderr)

    symlink_task = root / "telemetry-symlink-task"
    shutil.copytree(task, symlink_task)
    outside = root / "telemetry-outside"
    outside.mkdir()
    (outside / "runtime-telemetry.json").write_text((task / "runtime-adapters/rive/runtime-telemetry.json").read_text(encoding="utf-8"), encoding="utf-8")
    (symlink_task / "runtime-adapters/linked").symlink_to(outside, target_is_directory=True)
    symlink_evidence_path = symlink_task / "runtime-adapters/runtime-evidence.json"
    symlink_evidence = json.loads(symlink_evidence_path.read_text(encoding="utf-8"))
    symlink_evidence["frameworks"][0]["telemetry"]["file"] = "linked/runtime-telemetry.json"
    symlink_evidence_path.write_text(json.dumps(symlink_evidence, indent=2) + "\n", encoding="utf-8")
    symlink_result = invoke([str(VERIFIER), "--scene-dir", str(scene), "--task-dir", str(symlink_task)])
    record(results, "p2-runtime-verifier-symlink", symlink_result.returncode != 0 and "symlink" in symlink_result.stdout, symlink_result.stdout + symlink_result.stderr)


def main() -> int:
    corpus = json.loads(CASES.read_text(encoding="utf-8"))
    expected = {case["id"] for case in corpus.get("cases", [])}
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="motionloom-eval-") as td:
        root = Path(td)
        task_dir = root / "artifacts/professional-review-e2e"
        shutil.copytree(ROOT / "artifacts/professional-review-e2e", task_dir)

        registry = root / "capability-registry.json"
        build = invoke([str(INTELLIGENCE), "capabilities", "build", "--output", str(registry)])
        if build.returncode != 0:
            record(results, "verified-runtime-selection", False, build.stdout + build.stderr)
        else:
            selected = invoke([str(INTELLIGENCE), "capabilities", "select", "--registry", str(registry), "--capability", "runtime.rive"])
            record(results, "verified-runtime-selection", selected.returncode == 0, selected.stdout + selected.stderr)

        scaffold = invoke([str(INTELLIGENCE), "capabilities", "select", "--registry", str(registry), "--capability", "runtime.spine"])
        record(results, "scaffold-runtime-blocked", scaffold.returncode != 0, scaffold.stdout + scaffold.stderr)

        stale = json.loads(registry.read_text(encoding="utf-8"))
        for entry in stale["capabilities"]:
            if entry.get("id") == "runtime.rive":
                entry["last_verified_at"] = "2000-01-01T00:00:00Z"
        stale_path = root / "stale-capability-registry.json"
        stale_path.write_text(json.dumps(stale, indent=2) + "\n", encoding="utf-8")
        stale_result = invoke([str(INTELLIGENCE), "capabilities", "select", "--registry", str(stale_path), "--capability", "runtime.rive"])
        record(results, "stale-capability-evidence", stale_result.returncode != 0, stale_result.stdout + stale_result.stderr)

        tampered = json.loads(registry.read_text(encoding="utf-8"))
        for entry in tampered["capabilities"]:
            if entry.get("id") == "runtime.rive":
                entry["evidence"][0]["sha256"] = "0" * 64
        tampered_path = root / "tampered-capability-registry.json"
        tampered_path.write_text(json.dumps(tampered, indent=2) + "\n", encoding="utf-8")
        tampered_result = invoke([str(INTELLIGENCE), "capabilities", "select", "--registry", str(tampered_path), "--capability", "runtime.rive"])
        record(results, "tampered-capability-evidence", tampered_result.returncode != 0, tampered_result.stdout + tampered_result.stderr)

        graph_build = invoke([str(INTELLIGENCE), "graph", "build", "--task-dir", str(task_dir)])
        graph = json.loads((task_dir / "project-graph.json").read_text(encoding="utf-8"))
        graph["edges"].append({"from": graph["roots"][0], "to": "artifact:missing", "relation": "uses"})
        graph_path = root / "corrupt-project-graph.json"
        graph_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
        graph_result = invoke([str(INTELLIGENCE), "graph", "validate", "--path", str(graph_path)])
        record(results, "graph-edge-corruption", graph_build.returncode == 0 and graph_result.returncode != 0, graph_result.stdout + graph_result.stderr)

        replay_build = invoke([str(INTELLIGENCE), "replay", "capture", "--root", str(root), "--task-dir", str(task_dir)])
        replay_verify = invoke([str(INTELLIGENCE), "replay", "verify", "--root", str(root), "--bundle", str(task_dir / "replay-bundle.json")])
        review_path = task_dir / "review.json"
        review_path.write_text(review_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        replay_tamper = invoke([str(INTELLIGENCE), "replay", "verify", "--root", str(root), "--bundle", str(task_dir / "replay-bundle.json")])
        record(results, "replay-artifact-tamper", replay_build.returncode == 0 and replay_verify.returncode == 0 and replay_tamper.returncode != 0, replay_tamper.stdout + replay_tamper.stderr)

        foreign_task = root / "foreign-task"
        shutil.copytree(ROOT / "artifacts/professional-review-e2e", foreign_task)
        candidate = json.loads((foreign_task / "browser-review.json").read_text(encoding="utf-8"))
        candidate["status"] = "prepared"
        candidate["task_id"] = "foreign-task"
        (foreign_task / "browser-review.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        foreign = invoke([str(REPORT), "review", "--task-dir", str(foreign_task), "--candidate-id", str(candidate.get("candidate_id")), "--decision", "approved", "--reviewer", "eval"])
        record(results, "foreign-task-candidate", foreign.returncode != 0, foreign.stdout + foreign.stderr)

        run_p1_cases(root, task_dir, results)
        run_performance_perceptual_cases(root, task_dir, results)
        run_runtime_verifier_cases(root, results)
        run_attestation_cases(root, results)
        run_project_corpus_cases(root, results)

    missing = expected - {str(item["id"]) for item in results}
    for case_id in sorted(missing):
        record(results, case_id, False, "case was declared but not executed")
    failed = [item for item in results if item["status"] != "pass"]
    print(json.dumps({"status": "fail" if failed else "pass", "suite": corpus.get("suite"), "case_count": len(results), "results": results}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
