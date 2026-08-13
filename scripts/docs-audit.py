#!/usr/bin/env python3
"""Validate public documentation, links and workflow safety without network access."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
errors: list[str] = []

for markdown in sorted(ROOT.rglob("*.md")):
    if any(part in {".git", "node_modules"} for part in markdown.parts):
        continue
    text = markdown.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = target.strip().split("#", 1)[0].split("?", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if not (markdown.parent / target).resolve().exists():
            errors.append(f"{markdown.relative_to(ROOT)} -> missing {target}")

for relative in ["package.json", "agent-card.json", "project-context.example.json", "tests/evals/project-corpus.json"]:
    path = ROOT / relative
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{relative}: invalid JSON: {exc}")

package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
for required in ["author", "repository", "homepage", "bugs", "license", "engines", "files"]:
    if not package.get(required):
        errors.append(f"package.json: missing public metadata {required}")
if package.get("packageManager") != "pnpm@11.20.0":
    errors.append("package.json: packageManager must pin pnpm@11.20.0")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
for heading in ["Why MotionLoom", "Quick start", "Durable Project Memory", "Evidence, trust and review", "Documentation map"]:
    if f"## {heading}" not in readme:
        errors.append(f"README.md: missing heading {heading}")

workflow_dir = ROOT / ".github" / "workflows"
for workflow in sorted(workflow_dir.glob("*.yml")):
    text = workflow.read_text(encoding="utf-8")
    top_level_keys: dict[str, int] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)", line)
        if not match:
            continue
        key = match.group(1)
        if key in top_level_keys:
            errors.append(
                f"{workflow.relative_to(ROOT)}: duplicate top-level key {key!r} "
                f"at lines {top_level_keys[key]} and {line_number}"
            )
        else:
            top_level_keys[key] = line_number
    for required in ["name:", "on:", "jobs:", "permissions:"]:
        if required not in text:
            errors.append(f"{workflow.relative_to(ROOT)}: missing {required}")
    if "pull_request:" in text and "secrets." in text:
        errors.append(f"{workflow.relative_to(ROOT)}: secrets referenced in pull_request workflow")

release = (workflow_dir / "release.yml").read_text(encoding="utf-8")
for required in ["workflow_dispatch:", "environment: npm-release", "id-token: write", "release_version:", "scripts/release-verify.py"]:
    if required not in release:
        errors.append(f"release.yml: missing release safety control {required}")

if errors:
    print("Documentation/workflow audit: FAIL")
    print("\n".join(f"- {error}" for error in errors))
    raise SystemExit(1)

print("Documentation/workflow audit: PASS")
print(f"markdown_files={len(list(ROOT.rglob('*.md')))}")
print(f"workflow_files={len(list(workflow_dir.glob('*.yml')))}")
print("internal_links=PASS")
print("json_metadata=PASS")
print("workflow_safety=PASS")
