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

    report = {"status": "fail" if errors else "pass", "version": actual, "expected_version": expected, "errors": errors}
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
