#!/usr/bin/env python3
"""Regression tests for the append-only remediation learning ledger."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "remediation-learning.py"


def run(history: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args, "--history", str(history), "--json"], capture_output=True, text=True)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        history = Path(temporary) / "remediation-history.jsonl"
        first = run(history, "record-outcome", "--event-id", "outcome-001", "--issue-id", "timing-ease", "--summary", "User accepted a timing correction", "--result", "pass", "--correction-count", "0", "--source-task-id", "task-001", "--user-confirmed")
        second = run(history, "record-outcome", "--event-id", "outcome-002", "--issue-id", "timing-ease", "--summary", "Second pass required a rerender", "--result", "pass", "--correction-count", "4", "--source-task-id", "task-002", "--user-confirmed")
        benchmark = run(history, "record-benchmark", "--event-id", "benchmark-001", "--operation", "semantic-lint", "--task-id", "task-001", "--scene", "hero", "--iterations", "25", "--p95-ms", "42", "--threshold-ms", "500")
        valid = run(history, "validate")
        summary = run(history, "summary")
        summary_data = json.loads(summary.stdout or "{}")
        assert first.returncode == 0 and second.returncode == 0 and benchmark.returncode == 0
        assert valid.returncode == 0 and json.loads(valid.stdout)["event_count"] == 3
        assert summary.returncode == 0
        assert summary_data["remediation"]["first_pass_acceptance_rate"] == 0.5
        assert summary_data["remediation"]["success_rate"] == 1.0
        assert summary_data["remediation"]["outliers"][0]["event_id"] == "outcome-002"
        lines = history.read_text(encoding="utf-8").splitlines()
        tampered = json.loads(lines[1])
        tampered["correction_count"] = 1
        lines[1] = json.dumps(tampered, sort_keys=True)
        history.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rejected = run(history, "validate")
        assert rejected.returncode != 0 and json.loads(rejected.stdout)["status"] == "fail"
    print("remediation learning tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
