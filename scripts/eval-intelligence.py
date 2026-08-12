#!/usr/bin/env python3
"""Run the deterministic Intelligence Core eval corpus.

The runner intentionally uses clean temporary roots and subprocesses the same
CLI entrypoints used by Agents and CI. It reports each case as pass/fail and
never turns a negative case into a successful acceptance.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTELLIGENCE = ROOT / "scripts/intelligence.py"
REPORT = ROOT / "scripts/report.py"
CASES = ROOT / "tests/evals/intelligence-cases.json"


def invoke(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=cwd or ROOT, capture_output=True, text=True)


def record(results: list[dict[str, object]], case_id: str, passed: bool, detail: str = "") -> None:
    results.append({"id": case_id, "status": "pass" if passed else "fail", "detail": detail.strip()[-500:]})


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

    missing = expected - {str(item["id"]) for item in results}
    for case_id in sorted(missing):
        record(results, case_id, False, "case was declared but not executed")
    failed = [item for item in results if item["status"] != "pass"]
    print(json.dumps({"status": "fail" if failed else "pass", "suite": corpus.get("suite"), "case_count": len(results), "results": results}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
