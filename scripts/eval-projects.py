#!/usr/bin/env python3
"""Evaluate MotionLoom's project-aware analyzer against a labeled project corpus.

The manifest records provenance and expected signals, but this runner never
clones, installs or executes code from external projects. A checkout is only
considered available when the caller explicitly places it under --workspace.
Missing external projects produce ``insufficient_evidence`` rather than a
false pass. This keeps product-value claims separate from owned fixtures.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tests/evals/project-corpus.json"
ANALYZER = ROOT / "scripts/analyze.py"


def invoke(project: Path, output: Path, args: argparse.Namespace) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ANALYZER),
        str(project),
        "--output",
        str(output),
        "--max-files",
        str(args.max_files),
        "--max-bytes",
        str(args.max_bytes),
        "--max-seconds",
        str(args.max_seconds),
    ]
    for value in args.ignore_dir:
        command.extend(["--ignore-dir", value])
    for value in args.ignore_glob:
        command.extend(["--ignore-glob", value])
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def evaluate_case(case: dict, workspace: Path, repository_root: Path, args: argparse.Namespace, temp: Path) -> dict:
    relative = Path(str(case["local_path"]))
    base = repository_root if case.get("scope") == "repository" else workspace
    project = (base / relative).resolve()
    try:
        project.relative_to(base.resolve())
    except ValueError:
        return {"id": case["id"], "class": case.get("class"), "status": "fail", "detail": "local_path escapes evaluation root"}
    if not project.is_dir():
        return {
            "id": case["id"],
            "class": case.get("class"),
            "status": "unavailable",
            "external": bool(case.get("external")),
            "source": case.get("source"),
            "detail": f"checkout not present at {relative.as_posix()}",
        }

    output = temp / f"{case['id']}.json"
    result = invoke(project, output, args)
    if result.returncode != 0 or not output.is_file():
        return {
            "id": case["id"],
            "class": case.get("class"),
            "status": "fail",
            "external": bool(case.get("external")),
            "source": case.get("source"),
            "detail": (result.stdout + result.stderr).strip()[-1000:],
        }

    context = json.loads(output.read_text(encoding="utf-8"))
    expected = case.get("expected", {})
    checks = []
    if expected.get("name") is not None:
        checks.append((context.get("name") == expected["name"], f"name={context.get('name')!r}"))
    if expected.get("framework") is not None:
        actual = context.get("stack", {}).get("framework")
        checks.append((actual == expected["framework"], f"framework={actual!r}"))
    if expected.get("scan_truncated") is not None:
        checks.append((context.get("scan_truncated") is expected["scan_truncated"], f"scan_truncated={context.get('scan_truncated')!r}"))
    passed = all(item[0] for item in checks)
    return {
        "id": case["id"],
        "class": case.get("class"),
        "status": "pass" if passed else "fail",
        "external": bool(case.get("external")),
        "source": case.get("source"),
        "checks": [detail for _, detail in checks],
        "scan": context.get("scan", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a provenance-labeled MotionLoom project corpus evaluation.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--workspace", default=str(ROOT), help="Explicit directory containing corpus checkouts")
    parser.add_argument("--repository-root", default=str(ROOT), help="First-party repository root")
    parser.add_argument("--output")
    parser.add_argument("--require-external", type=int, help="Override manifest external-project requirement")
    parser.add_argument("--allow-insufficient", action="store_true", help="Return success while reporting insufficient_evidence")
    parser.add_argument("--max-files", type=int, default=2500)
    parser.add_argument("--max-bytes", type=int, default=25_000_000)
    parser.add_argument("--max-seconds", type=float, default=10.0)
    parser.add_argument("--ignore-dir", action="append", default=[])
    parser.add_argument("--ignore-glob", action="append", default=[])
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    workspace = Path(args.workspace).expanduser().resolve()
    repository_root = Path(args.repository_root).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("projects", [])
    required_external = args.require_external if args.require_external is not None else int(manifest.get("required_external_projects", 0))

    with tempfile.TemporaryDirectory(prefix="motionloom-project-eval-") as td:
        results = [evaluate_case(case, workspace, repository_root, args, Path(td)) for case in cases]
    available_external = sum(1 for item in results if item.get("external") and item.get("status") == "pass")
    failed = [item for item in results if item["status"] == "fail"]
    unavailable_external = [item for item in results if item.get("external") and item["status"] == "unavailable"]
    if failed:
        status = "fail"
    elif available_external < required_external:
        status = "insufficient_evidence"
    else:
        status = "pass"

    report = {
        "schema_version": "1.0",
        "corpus_id": manifest.get("corpus_id"),
        "status": status,
        "workspace": str(workspace),
        "required_external_projects": required_external,
        "available_external_projects": available_external,
        "unavailable_external_projects": len(unavailable_external),
        "project_count": len(results),
        "results": results,
    }
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if status == "insufficient_evidence" and args.allow_insufficient:
        return 0
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
