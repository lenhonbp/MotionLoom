#!/usr/bin/env python3
"""Check the skill package structure and emit machine-readable diagnostics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = ["SKILL.md", "agent-card.json", "package.json"]
REQUIRED_DIRS = ["scripts", "templates", "references", "schemas"]
REQUIRED_SCRIPT_FILES = [
    "scripts/report-contract.py",
    "scripts/review-hook.py",
    "scripts/quality-gate.py",
    "scripts/runtime-adapters.mjs",
    "scripts/project-memory.py",
    "scripts/project_memory_loader.py",
    "scripts/analyze.py",
    "scripts/devlab.py",
    "scripts/setup.mjs",
]
REQUIRED_SCHEMAS = [
    "task.schema.json",
    "execution-report.schema.json",
    "artifact-manifest.schema.json",
    "handoff.schema.json",
    "browser-review-candidate.schema.json",
    "scene-manifest.schema.json",
    "runtime-evidence.schema.json",
    "project-graph.schema.json",
    "provenance.schema.json",
    "capability-registry.schema.json",
    "motion-ir.schema.json",
    "project-memory.schema.json",
]


def check(condition: bool, code: str, message: str, errors: list, warnings: list) -> None:
    target = errors if not condition else warnings
    if not condition:
        errors.append({"code": code, "message": message})


def parse_frontmatter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    values: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match and not match.group(1).startswith(" "):
            values[match.group(1)] = match.group(2).strip().strip('"')
    return values


def run() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    errors: list[dict] = []
    warnings: list[dict] = []
    checks: list[dict] = []

    for relative in REQUIRED_FILES:
        exists = (ROOT / relative).is_file()
        checks.append({"id": f"file:{relative}", "status": "pass" if exists else "fail"})
        if not exists:
            errors.append({"code": "missing_file", "message": f"Missing required file: {relative}"})
    for relative in REQUIRED_DIRS:
        exists = (ROOT / relative).is_dir()
        checks.append({"id": f"directory:{relative}", "status": "pass" if exists else "fail"})
        if not exists:
            errors.append({"code": "missing_directory", "message": f"Missing required directory: {relative}"})
    for relative in REQUIRED_SCRIPT_FILES:
        exists = (ROOT / relative).is_file()
        checks.append({"id": f"file:{relative}", "status": "pass" if exists else "fail"})
        if not exists:
            errors.append({"code": "missing_file", "message": f"Missing required runtime/contract script: {relative}"})

    skill_path = ROOT / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        valid_meta = bool(frontmatter and frontmatter.get("name") and frontmatter.get("description"))
        checks.append({"id": "skill:frontmatter", "status": "pass" if valid_meta else "fail"})
        if not valid_meta:
            errors.append({"code": "invalid_frontmatter", "message": "SKILL.md needs YAML frontmatter with name and description."})
        line_count = len(text.splitlines())
        checks.append({"id": "skill:line_count", "status": "pass" if line_count <= 500 else "fail", "lines": line_count})
        if line_count > 500:
            errors.append({"code": "skill_too_long", "message": f"SKILL.md has {line_count} lines; keep the body under 500 lines."})

    for relative in REQUIRED_SCHEMAS:
        path = ROOT / "schemas" / relative
        try:
            json.loads(path.read_text(encoding="utf-8"))
            checks.append({"id": f"schema:{relative}", "status": "pass"})
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            checks.append({"id": f"schema:{relative}", "status": "fail"})
            errors.append({"code": "invalid_schema", "message": f"{relative}: {exc}"})

    card_path = ROOT / "agent-card.json"
    try:
        card = json.loads(card_path.read_text(encoding="utf-8"))
        for field in ("name", "version", "capabilities", "input_artifacts", "output_artifacts", "runtime_capabilities", "side_effects"):
            if field not in card:
                errors.append({"code": "agent_card_field", "message": f"agent-card.json missing field: {field}"})
        verified = set(card.get("runtime_capabilities", {}).get("verified", []))
        scaffold = set(card.get("runtime_capabilities", {}).get("scaffold_only", []))
        overlap = sorted(verified & scaffold)
        if overlap:
            errors.append({"code": "capability_overlap", "message": f"Runtime listed as verified and scaffold-only: {overlap}"})
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        errors.append({"code": "invalid_agent_card", "message": str(exc)})

    skill_text = skill_path.read_text(encoding="utf-8") if skill_path.is_file() else ""
    for reference in re.findall(r"`(references/[A-Za-z0-9_./-]+)`", skill_text):
        exists = (ROOT / reference).is_file()
        checks.append({"id": f"reference:{reference}", "status": "pass" if exists else "fail"})
        if not exists:
            errors.append({"code": "broken_reference", "message": f"SKILL.md references missing file: {reference}"})

    package_path = ROOT / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        for script in ("test", "validate", "doctor", "setup", "setup:dry", "status", "repair", "report", "report:check", "review", "memory:bootstrap", "memory:recover", "memory:validate", "devlab", "pack:dotlottie"):
            if script not in package.get("scripts", {}):
                warnings.append({"code": "missing_package_script", "message": f"package.json has no {script} script."})
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        errors.append({"code": "invalid_package_json", "message": str(exc)})

    result = {
        "doctor_version": "1.0",
        "skill_root": str(ROOT),
        "status": "pass" if not errors else "fail",
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }
    if args.as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"skill-doctor: {result['status'].upper()}")
        for item in errors:
            print(f"ERROR {item['code']}: {item['message']}")
        for item in warnings:
            print(f"WARN  {item['code']}: {item['message']}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(run())
