#!/usr/bin/env python3
"""Project Memory recovery and cross-platform path contract tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "project-memory.py"
NODE_CLI = ROOT / "bin" / "motionloom.mjs"


def run_memory(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args, "--project-root", str(root)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_memory_recovery_and_relocation() -> None:
    with tempfile.TemporaryDirectory(prefix="motionloom memory ") as td:
        root = Path(td) / "Dự án MotionLoom"
        root.mkdir(parents=True)
        (root / "package.json").write_text(json.dumps({"name": "memory-fixture"}), encoding="utf-8")
        (root / "project-context.json").write_text(json.dumps({
            "schema_version": "2.0",
            "name": "memory-fixture",
            "generated_at": "2026-08-13T00:00:00Z",
        }), encoding="utf-8")

        created = run_memory(root, "init", "--context-path", "project-context.json", "--json")
        assert created.returncode == 0, created.stderr
        memory_path = root / ".motionloom" / "project-memory.json"
        assert memory_path.is_file()

        decision = run_memory(root, "record-decision", "--id", "ease-ui", "--status", "accepted", "--summary", "Use ease-out for UI entry", "--user-confirmed", "--json")
        assert decision.returncode == 0, decision.stderr

        rejected = run_memory(root, "record-decision", "--id", "linear-ui", "--status", "rejected", "--summary", "Do not use linear easing for UI", "--rationale", "Perceptually mechanical", "--json")
        assert rejected.returncode == 0, rejected.stderr

        blocked_outcome = run_memory(root, "record-outcome", "--id", "fix-1", "--issue-id", "issue-1", "--summary", "Unreviewed fix", "--result", "pass")
        assert blocked_outcome.returncode == 2
        assert "user-confirmed" in blocked_outcome.stderr

        outcome = run_memory(root, "record-outcome", "--id", "fix-1", "--issue-id", "issue-1", "--summary", "Reduce hand-track duration", "--root-cause", "timing", "--resolution", "duration 420ms", "--result", "pass", "--correction-count", "1", "--rerun-scope", "scene:onboarding-wave", "--user-confirmed", "--json")
        assert outcome.returncode == 0, outcome.stderr

        recovered = run_memory(root, "recover", "--limit", "10")
        assert recovered.returncode == 0, recovered.stderr
        payload = json.loads(recovered.stdout)
        assert payload["project"]["project_id"].startswith("local:")
        assert payload["decisions"][-1]["id"] == "linear-ui"
        assert payload["rejected_patterns"][-1]["id"] == "linear-ui"
        assert payload["remediation"][-1]["user_confirmed"] is True
        assert payload["instructions"][0].endswith("user approval.")
        assert payload["instructions"][-1].endswith("artifacts.")

        moved = Path(td) / "relocated" / "MotionLoom copy"
        moved.parent.mkdir()
        shutil.copytree(root, moved)
        relocated = run_memory(moved, "recover", "--limit", "10")
        assert relocated.returncode == 0, relocated.stderr
        relocated_payload = json.loads(relocated.stdout)
        assert relocated_payload["project"]["root_path"] == str(moved.resolve())
        relocated_validation = run_memory(moved, "validate", "--json")
        assert relocated_validation.returncode == 0, relocated_validation.stderr

        # Only the volatile checkout path may be rebound without changing the
        # durable project payload; meaningful direct edits remain integrity failures.
        rebound = json.loads((moved / ".motionloom" / "project-memory.json").read_text(encoding="utf-8"))
        rebound["project"]["root_path"] = str(moved.parent / "another-location")
        (moved / ".motionloom" / "project-memory.json").write_text(json.dumps(rebound), encoding="utf-8")
        path_only = run_memory(moved, "validate", "--json")
        assert path_only.returncode == 0, path_only.stdout + path_only.stderr

        context = json.loads((moved / "project-context.json").read_text(encoding="utf-8"))
        context["changed_by_other_task"] = True
        (moved / "project-context.json").write_text(json.dumps(context), encoding="utf-8")
        stale = run_memory(moved, "refresh", "--json")
        assert stale.returncode == 10, stale.stdout + stale.stderr
        stale_payload = json.loads(stale.stdout)
        assert stale_payload["freshness"]["status"] == "stale"


def test_cross_project_recovery_is_fail_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="motionloom-project-a ") as td:
        source = Path(td) / "source"
        foreign = Path(td) / "foreign"
        source.mkdir(); foreign.mkdir()
        for root, name in ((source, "project-a"), (foreign, "project-b")):
            (root / "package.json").write_text(json.dumps({"name": name}), encoding="utf-8")
            (root / "project-context.json").write_text(json.dumps({"schema_version": "2.0", "name": name}), encoding="utf-8")
        assert run_memory(source, "init").returncode == 0
        foreign_memory = foreign / ".motionloom"
        foreign_memory.mkdir()
        shutil.copy2(source / ".motionloom" / "project-memory.json", foreign_memory / "project-memory.json")
        result = run_memory(foreign, "recover")
        assert result.returncode == 11
        assert "identity mismatch" in result.stderr


def test_node_cli_routes_memory_without_shell() -> None:
    with tempfile.TemporaryDirectory(prefix="motionloom node cli ") as td:
        root = Path(td)
        (root / "package.json").write_text(json.dumps({"name": "node-cli-fixture"}), encoding="utf-8")
        (root / "project-context.json").write_text(json.dumps({"schema_version": "2.0", "name": "node-cli-fixture"}), encoding="utf-8")
        result = subprocess.run(["node", str(NODE_CLI), "memory", "init", "--project-root", str(root), "--json"], cwd=ROOT, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr
        recover = subprocess.run(["node", str(NODE_CLI), "memory", "recover", "--project-root", str(root)], cwd=ROOT, capture_output=True, text=True, check=False)
        assert recover.returncode == 0, recover.stderr
        assert json.loads(recover.stdout)["project"]["name"] == "node-cli-fixture"


if __name__ == "__main__":
    test_memory_recovery_and_relocation()
    test_cross_project_recovery_is_fail_closed()
    test_node_cli_routes_memory_without_shell()
    print("project memory contract tests: PASS")
