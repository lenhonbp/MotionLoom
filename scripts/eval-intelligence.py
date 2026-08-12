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

    missing = expected - {str(item["id"]) for item in results}
    for case_id in sorted(missing):
        record(results, case_id, False, "case was declared but not executed")
    failed = [item for item in results if item["status"] != "pass"]
    print(json.dumps({"status": "fail" if failed else "pass", "suite": corpus.get("suite"), "case_count": len(results), "results": results}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
