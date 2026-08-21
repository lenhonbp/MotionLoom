#!/usr/bin/env python3
"""Verify the immutable metadata chain before an npm/GitHub release."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify package version, changelog and release note alignment.")
    parser.add_argument("--expected-version", default="")
    parser.add_argument("--package", default=str(ROOT / "package.json"))
    parser.add_argument("--changelog", default=str(ROOT / "CHANGELOG.md"))
    parser.add_argument("--release-note", default="")
    parser.add_argument("--tag", default="", help="Optional Git tag; accepts v<version> or <version>")
    parser.add_argument("--capability-registry", default=str(ROOT / "capability-registry.json"))
    args = parser.parse_args()

    errors: list[str] = []
    package_path = Path(args.package).resolve()
    package = json.loads(package_path.read_text(encoding="utf-8"))
    actual = str(package.get("version", ""))
    expected = str(args.expected_version or actual).removeprefix("v")
    if actual != expected:
        errors.append(f"package version {actual!r} does not match expected {expected!r}")

    changelog = Path(args.changelog).resolve()
    if not re.search(rf"^## \[{re.escape(expected)}\](?:\s|$)", changelog.read_text(encoding="utf-8"), re.MULTILINE):
        errors.append(f"CHANGELOG.md has no heading for [{expected}]")

    note = Path(args.release_note) if args.release_note else ROOT / "docs/releases" / f"{expected}.md"
    if not note.is_absolute():
        note = ROOT / note
    if not note.is_file():
        errors.append(f"release note is missing: {note.relative_to(ROOT) if note.is_relative_to(ROOT) else note}")

    if args.tag and args.tag.removeprefix("v") != expected:
        errors.append(f"tag {args.tag!r} does not match version {expected!r}")

    registry_path = Path(args.capability_registry).resolve()
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        expected_registry_id = f"registry-{package.get('name', 'motionloom')}-{expected}"
        if registry.get("registry_id") != expected_registry_id:
            errors.append(
                f"capability registry id {registry.get('registry_id')!r} does not match {expected_registry_id!r}"
            )
        capabilities = registry.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            errors.append("capability registry must contain a non-empty capabilities array")
        else:
            mismatched = [
                str(item.get("id", "<unknown>"))
                for item in capabilities
                if item.get("adapter_version") != expected
            ]
            if mismatched:
                errors.append(
                    "capability registry adapter_version mismatch: " + ", ".join(mismatched)
                )
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        errors.append(f"capability registry is invalid: {exc}")

    report = {"status": "fail" if errors else "pass", "version": actual, "expected_version": expected, "errors": errors}
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
