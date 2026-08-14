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

for relative in ["package.json", "agent-card.json", "agent-surfaces.json", "schemas/agent-surfaces.schema.json", "schemas/provenance.schema.json", "schemas/asset-provenance.schema.json", "schemas/scene-manifest.schema.json", "schemas/visual-truth.schema.json", "schemas/remediation-history.schema.json", "project-context.example.json", "examples/agent-consumer/ai-generated-pilot-provenance.json", "tests/evals/project-corpus.json"]:
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
for required_surface in [".agents", ".claude", ".codex", "AGENTS.md", "agent-surfaces.json"]:
    if required_surface not in package.get("files", []):
        errors.append(f"package.json: files must include Agent surface {required_surface}")
for required_path in ["scripts/asset-provenance.py", "schemas/asset-provenance.schema.json", "examples/agent-consumer/ai-generated-pilot-provenance.json"]:
    if required_path not in package.get("files", []):
        errors.append(f"package.json: files must include asset provenance contract {required_path}")
for onboarding_script in ["setup", "setup:dry", "status", "repair"]:
    if onboarding_script not in package.get("scripts", {}):
        errors.append(f"package.json: missing onboarding script {onboarding_script}")

sys.path.insert(0, str(ROOT))
try:
    from scripts.discovery import validate as validate_discovery
    discovery = validate_discovery(ROOT)
    for discovery_error in discovery.get("errors", []):
        errors.append(f"agent discovery: {discovery_error}")
except Exception as exc:
    errors.append(f"agent discovery: validator could not load: {exc}")

for required_doc in ["docs/AGENT-INTEGRATION.md", "references/agent-interoperability.md"]:
    if not (ROOT / required_doc).is_file():
        errors.append(f"missing Agent interoperability document: {required_doc}")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
for heading in ["Why MotionLoom", "Quick start", "Durable Project Memory", "Evidence, trust and review", "Asset provenance tiers", "Documentation map"]:
    if f"## {heading}" not in readme:
        errors.append(f"README.md: missing heading {heading}")
if "npx --yes motionloom setup" not in readme:
    errors.append("README.md: missing one-command onboarding recipe")
if "npx --yes motionloom setup" not in (ROOT / "docs/AGENT-INTEGRATION.md").read_text(encoding="utf-8"):
    errors.append("docs/AGENT-INTEGRATION.md: missing one-command onboarding recipe")

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
if "--require-asset-provenance" not in (workflow_dir / "quality.yml").read_text(encoding="utf-8"):
    errors.append("quality.yml: missing fail-closed asset provenance production gate")
    if "pull_request:" in text and "secrets." in text:
        errors.append(f"{workflow.relative_to(ROOT)}: secrets referenced in pull_request workflow")

release = (workflow_dir / "release.yml").read_text(encoding="utf-8")
for required in ["workflow_dispatch:", "environment: npm-release", "id-token: write", "release_version:", "scripts/release-verify.py"]:
    if required not in release:
        errors.append(f"release.yml: missing release safety control {required}")

devlab = (workflow_dir / "devlab.yml").read_text(encoding="utf-8")
for required in [
    "cp -R src/output/browser-review-smoke dev-lab/public/scenes/browser-review-smoke",
    "scenes/browser-review-smoke/manifest.json",
    "scenes/browser-review-smoke/motion-spec.json",
    "--diagnostics /tmp/motionloom-devlab-diagnostics",
    "id: fixture",
    "steps.fixture.outputs.task_id",
    "steps.fixture.outputs.candidate_id",
    'payload["expires_at"] = "2099-01-01T00:00:00Z"',
]:
    if required not in devlab:
        errors.append(f"devlab.yml: missing fixture/readiness control {required}")

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
