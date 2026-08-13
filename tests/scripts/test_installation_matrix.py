#!/usr/bin/env python3
"""Validate the declared Ubuntu/macOS/Windows installation matrix."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "tests/fixtures/installation-matrix.json"


def main() -> int:
    data = json.loads(MATRIX.read_text(encoding="utf-8"))
    errors: list[str] = []
    if data.get("supported_platforms") != ["ubuntu", "macos", "windows"]:
        errors.append("supported platform order or values changed")
    ids = {item.get("id") for item in data.get("commands", [])}
    required_ids = {"npm-cli-help", "discovery-check-python", "discovery-check-npm", "memory-contract", "discovery-regression"}
    if ids != required_ids:
        errors.append(f"installation command set mismatch: {sorted(ids)}")
    for item in data.get("commands", []):
        command = item.get("command")
        if not isinstance(command, list) or not command or any(not isinstance(part, str) or not part for part in command):
            errors.append(f"invalid command vector: {item.get('id')}")
        if "shell" in item:
            errors.append(f"command must be an argument vector, not shell text: {item.get('id')}")
    rules = set(data.get("portability_rules", []))
    required_rules = {"no-required-bash", "no-hardcoded-posix-tmp", "no-shell-true", "pathlib-or-node-path", "utf8-json-output", "no-system-zip-or-unzip"}
    if rules != required_rules:
        errors.append("portability rules drifted")
    if errors:
        print("installation matrix tests: FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("installation matrix tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
