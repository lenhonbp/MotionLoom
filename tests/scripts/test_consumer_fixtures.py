#!/usr/bin/env python3
"""Validate the example consumer fixture map and its evidence boundaries."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "examples/agent-consumer/fixture-manifest.json"


def main() -> int:
    errors: list[str] = []
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if len(cases) != 7:
        errors.append(f"expected seven consumer cases, found {len(cases)}")
    ids: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not case_id or case_id in ids:
            errors.append(f"duplicate or missing fixture id: {case_id!r}")
        ids.add(case_id)
        source = case.get("source")
        if not isinstance(source, str) or source.startswith("/") or ".." in Path(source).parts:
            errors.append(f"unsafe fixture source for {case_id}: {source!r}")
        elif not (ROOT / source).exists():
            errors.append(f"missing fixture source for {case_id}: {source}")
        if not case.get("verification"):
            errors.append(f"missing verification command for {case_id}")
        if case.get("evidence_level") == "runtime-verified-fixture" and not case.get("evidence"):
            errors.append(f"runtime fixture lacks evidence path: {case_id}")
    boundary = payload.get("review_boundary", {})
    if boundary.get("approval") is not False or boundary.get("user_review_required") is not True:
        errors.append("consumer fixture manifest weakens review boundary")
    for text_path in [ROOT / "examples/agent-consumer/README.md"]:
        text = text_path.read_text(encoding="utf-8")
        if "runtime-verified" not in text or "user approval" not in text:
            errors.append(f"consumer README does not explain evidence boundary: {text_path}")
    # Guard against accidental shell-only recipes in the machine-readable matrix.
    raw = MANIFEST.read_text(encoding="utf-8")
    if re.search(r"\bbash\s+scripts/", raw):
        errors.append("consumer fixture manifest contains a Bash-only command")
    if errors:
        print("consumer fixture tests: FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("consumer fixture tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
