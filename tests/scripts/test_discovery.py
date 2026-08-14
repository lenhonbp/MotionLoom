#!/usr/bin/env python3
"""Regression tests for the offline Agent discovery/install contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "discovery.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    errors: list[str] = []

    result = run("check", "--root", str(ROOT), "--json")
    payload = json.loads(result.stdout)
    if result.returncode != 0 or payload.get("status") != "pass":
        errors.append(f"discovery check failed: {payload}")
    if payload.get("surface_count") != 4:
        errors.append("expected four Agent discovery surfaces")
    if payload.get("installation_count") != 4:
        errors.append("expected npx, npm, git and local installation sources")

    manifest = json.loads((ROOT / "agent-surfaces.json").read_text(encoding="utf-8"))
    if manifest.get("rules", {}).get("approval_is_never_inferred") is not True:
        errors.append("approval invariant is not explicit in discovery manifest")
    if manifest.get("compatibility", {}).get("operating_systems") != ["ubuntu", "macos", "windows"]:
        errors.append("cross-platform compatibility matrix drifted")

    required = [
        ROOT / ".agents/skills/motionloom/SKILL.md",
        ROOT / ".claude/skills/motionloom.md",
        ROOT / ".codex/skills/motionloom.md",
        ROOT / "AGENTS.md",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing discovery surface: {path.relative_to(ROOT)}")
    agents_skill = (ROOT / ".agents/skills/motionloom/SKILL.md").read_text(encoding="utf-8")
    if "../../../SKILL.md" not in agents_skill or "portable discovery alias" not in agents_skill:
        errors.append("Agent Skills surface does not point to canonical root Skill")

    matrix = run("install-matrix", "--root", str(ROOT), "--json")
    matrix_payload = json.loads(matrix.stdout)
    if matrix.returncode != 0 or matrix_payload.get("status") != "pass":
        errors.append("installation matrix is not available")
    if {row.get("source_kind") for row in matrix_payload.get("matrix", [])} != {"npm", "npx", "git", "local"}:
        errors.append("installation matrix source kinds drifted")

    if errors:
        print("discovery contract tests: FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("discovery contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
