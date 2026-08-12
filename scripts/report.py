#!/usr/bin/env python3
"""Create, collect and render machine-readable animation task reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATES = ["created", "needs_context", "planning", "sourcing", "generating", "rendering", "review_required", "blocked", "failed", "validated", "ready_for_pr", "confirmed"]
TRANSITIONS = {
    "created": {"needs_context", "planning", "blocked", "failed"},
    "needs_context": {"planning", "blocked", "failed"},
    "planning": {"sourcing", "generating", "blocked", "failed"},
    "sourcing": {"generating", "blocked", "failed"},
    "generating": {"rendering", "blocked", "failed"},
    "rendering": {"review_required", "blocked", "failed"},
    "review_required": {"validated", "blocked", "failed"},
    "validated": {"ready_for_pr", "failed"},
    "ready_for_pr": {"confirmed", "failed"},
    "blocked": {"needs_context", "planning", "sourcing", "generating", "rendering", "failed"},
    "failed": {"planning", "sourcing", "generating", "rendering", "blocked"},
    "confirmed": set(),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path, default: dict | list | None = None):
    if not path.is_file():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_expiry(candidate: dict) -> datetime | None:
    value = candidate.get("expires_at")
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def candidate_is_current(candidate: dict) -> bool:
    expiry = candidate_expiry(candidate)
    return expiry is not None and datetime.now(timezone.utc) <= expiry


def init_task(args: argparse.Namespace) -> int:
    task_dir = Path(args.output or ROOT / "artifacts" / args.task_id).resolve()
    timestamp = now()
    task = {
        "schema_version": "1.0",
        "task_id": args.task_id,
        "scene": args.scene,
        "intent": args.intent,
        "project_name": args.project_name,
        "context_path": args.context_path,
        "context_hash": args.context_hash,
        "state": "created",
        "browser_review": {"required": True, "status": "not_prepared", "review_artifact": "review.json"},
        "owner_agent": args.agent,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    report = {
        "report_version": "1.0",
        "task_id": args.task_id,
        "status": "created",
        "confidence": "low",
        "completed": [],
        "verified": [],
        "not_completed": [{"id": "initial", "summary": "Task has not run yet.", "status": "pending"}],
        "problems": [],
        "structure_review": {"missing_files": [], "broken_references": [], "untracked_artifacts": []},
        "browser_review": [],
        "next_agent": [{"agent": args.agent, "action": "Run project analysis and populate context before generation."}],
        "generated_at": timestamp,
    }
    handoff = {
        "handoff_version": "1.0",
        "task_id": args.task_id,
        "from_agent": args.agent,
        "to_agent": "motionloom",
        "state": "created",
        "summary": "New animation task initialized.",
        "next_actions": [{"action": "Analyze host project context", "skill": "motionloom", "evidence_needed": ["project-context.json"]}],
        "required_artifacts": ["task.json", "execution-report.json"],
        "blockers": [],
    }
    write_json(task_dir / "task.json", task)
    write_json(task_dir / "execution-report.json", report)
    write_json(task_dir / "issue-register.json", {"version": "1.0", "task_id": args.task_id, "issues": []})
    write_json(task_dir / "handoff.json", handoff)
    write_json(task_dir / "artifact-manifest.json", {"manifest_version": "1.0", "task_id": args.task_id, "generated_at": timestamp, "artifacts": []})
    (task_dir / "decision-log.jsonl").write_text("", encoding="utf-8")
    print(json.dumps({"status": "created", "task_id": args.task_id, "task_dir": str(task_dir)}, ensure_ascii=False))
    return 0


def collect(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task = read_json(task_dir / "task.json")
    excluded = {"artifact-manifest.json", "execution-report.json", "decision-log.jsonl"}
    artifacts = []
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file() or path.name in excluded:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        artifacts.append({"path": str(path.relative_to(task_dir)), "type": path.suffix.lstrip(".") or "file", "sha256": digest, "bytes": path.stat().st_size})
    manifest = {"manifest_version": "1.0", "task_id": task.get("task_id", task_dir.name), "generated_at": now(), "artifacts": artifacts}
    write_json(task_dir / "artifact-manifest.json", manifest)
    print(json.dumps({"status": "collected", "task_id": manifest["task_id"], "artifact_count": len(artifacts)}, ensure_ascii=False))
    return 0


def add_item(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    report_path = task_dir / "execution-report.json"
    report = read_json(report_path)
    section = args.section
    if section not in {"completed", "verified", "not_completed", "problems", "next_agent"}:
        print(f"Unsupported report section: {section}", file=sys.stderr)
        return 2
    item = {
        "id": args.id,
        "summary": args.summary,
        "status": args.status,
    }
    if args.evidence:
        item["evidence"] = args.evidence
    if args.confidence:
        item["confidence"] = args.confidence
    if args.severity:
        item["severity"] = args.severity
    if args.next_action:
        item["next_action"] = args.next_action
    if args.agent:
        item["agent"] = args.agent
    if args.skill:
        item["skill"] = args.skill
    if args.evidence_needed:
        item["evidence_needed"] = args.evidence_needed
    if section in {"completed", "verified"}:
        report["not_completed"] = [
            entry for entry in report.get("not_completed", []) if entry.get("id") != "initial"
        ]
    report.setdefault(section, []).append(item)
    report["generated_at"] = now()
    write_json(report_path, report)
    print(json.dumps({"status": "recorded", "section": section, "id": args.id, "task_dir": str(task_dir)}, ensure_ascii=False))
    return 0


def record_review(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task = read_json(task_dir / "task.json")
    candidate_path = task_dir / "browser-review.json"
    candidate = read_json(candidate_path)
    if not candidate:
        print("browser-review.json is required before recording a review", file=sys.stderr)
        return 2
    if args.candidate_id and candidate.get("candidate_id") != args.candidate_id:
        print("review candidate id does not match browser-review.json", file=sys.stderr)
        return 2
    if candidate.get("task_id") != task.get("task_id"):
        print("review candidate task_id does not match task.json", file=sys.stderr)
        return 2
    if candidate.get("scene") != task.get("scene"):
        print("review candidate scene does not match task.json", file=sys.stderr)
        return 2
    if not str(args.reviewer or "").strip():
        print("reviewer is required and cannot be empty", file=sys.stderr)
        return 2
    expires_at = candidate.get("expires_at")
    if not expires_at:
        print("browser-review candidate expiry is required", file=sys.stderr)
        return 2
    if candidate_expiry(candidate) is None:
        print("browser-review candidate expiry is invalid", file=sys.stderr)
        return 2
    if not candidate_is_current(candidate):
        print("browser-review candidate has expired", file=sys.stderr)
        return 2
    if candidate.get("status") in {"expired", "approved"}:
        print("browser-review candidate cannot be reviewed again; prepare a new candidate", file=sys.stderr)
        return 2
    scene_candidate_path = ROOT / "src" / "output" / str(task.get("scene", "")) / "browser-review.json"
    scene_candidate = read_json(scene_candidate_path)
    if scene_candidate_path.is_file() and scene_candidate.get("candidate_id") != candidate.get("candidate_id"):
        print("task candidate does not match scene-level browser-review.json", file=sys.stderr)
        return 2
    review = {
        "review_version": "1.0",
        "task_id": task.get("task_id", task_dir.name),
        "candidate_id": candidate.get("candidate_id"),
        "decision": args.decision,
        "reviewer": args.reviewer,
        "notes": args.notes,
        "feedback": args.feedback,
        "reviewed_at": now(),
    }
    write_json(task_dir / "review.json", review)
    candidate["status"] = {"pending": "reviewed", "approved": "approved", "changes_requested": "changes_requested", "rejected": "changes_requested"}[args.decision]
    candidate["review_artifact"] = "review.json"
    candidate["reviewed_at"] = review["reviewed_at"]
    write_json(candidate_path, candidate)
    if scene_candidate_path.is_file():
        scene_candidate["status"] = candidate["status"]
        scene_candidate["review_artifact"] = "review.json"
        scene_candidate["reviewed_at"] = review["reviewed_at"]
        write_json(scene_candidate_path, scene_candidate)
    task["browser_review"] = {
        "required": True,
        "status": candidate["status"],
        "candidate_id": candidate.get("candidate_id"),
        "candidate_path": "browser-review.json",
        "review_artifact": "review.json",
    }
    write_json(task_dir / "task.json", task)
    report_path = task_dir / "execution-report.json"
    report = read_json(report_path)
    report["browser_review"] = [{"candidate_id": candidate.get("candidate_id"), "decision": args.decision, "reviewer": args.reviewer, "evidence": ["browser-review.json", "review.json"]}]
    report["generated_at"] = now()
    write_json(report_path, report)
    print(json.dumps({"status": "review-recorded", "decision": args.decision, "task_dir": str(task_dir)}, ensure_ascii=False))
    return 0


def record_structure(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    report_path = task_dir / "execution-report.json"
    report = read_json(report_path)
    structure = report.setdefault("structure_review", {"missing_files": [], "broken_references": [], "untracked_artifacts": []})
    for key, values in (("missing_files", args.missing_file), ("broken_references", args.broken_reference), ("untracked_artifacts", args.untracked_artifact)):
        for value in values:
            if value not in structure.setdefault(key, []):
                structure[key].append(value)
    report["generated_at"] = now()
    write_json(report_path, report)
    print(json.dumps({"status": "structure-recorded", "task_dir": str(task_dir), "review": structure}, ensure_ascii=False))
    return 0


def check_report(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    errors = []
    required = ("task.json", "execution-report.json", "artifact-manifest.json", "handoff.json", "issue-register.json")
    for name in required:
        if not (task_dir / name).is_file():
            errors.append(f"missing {name}")
    task = read_json(task_dir / "task.json")
    report = read_json(task_dir / "execution-report.json")
    manifest = read_json(task_dir / "artifact-manifest.json", {"artifacts": []})
    state = task.get("state")
    if not task.get("task_id") or not task.get("scene"):
        errors.append("task.json requires task_id and scene")
    for section in ("completed", "verified", "not_completed", "problems", "next_agent"):
        if not isinstance(report.get(section), list):
            errors.append(f"execution-report.json requires list section: {section}")
    for artifact in manifest.get("artifacts", []):
        if len(artifact.get("sha256", "")) != 64:
            errors.append(f"artifact has invalid sha256: {artifact.get('path', '<unknown>')}")
        if not (task_dir / artifact.get("path", "")).is_file():
            errors.append(f"artifact path missing: {artifact.get('path', '<unknown>')}")
    if state in {"validated", "ready_for_pr", "confirmed"}:
        quality = read_json(task_dir / "quality-report.json")
        if quality.get("status") != "pass":
            errors.append("validated-or-later task requires quality-report.json status=pass")
    if state in {"ready_for_pr", "confirmed"}:
        review = read_json(task_dir / "review.json")
        if review.get("decision") != "approved":
            errors.append("ready_for_pr-or-later task requires review.json decision=approved")
        candidate = read_json(task_dir / "browser-review.json")
        if not candidate.get("candidate_id") or review.get("candidate_id") != candidate.get("candidate_id"):
            errors.append("review.json must approve the exact browser-review candidate")
        if candidate.get("status") != "approved":
            errors.append("ready_for_pr-or-later task requires browser-review.json status=approved")
    if task.get("browser_review", {}).get("required") and state in {"review_required", "validated", "ready_for_pr", "confirmed"}:
        if not (task_dir / "browser-review.json").is_file():
            errors.append("task requires browser-review.json candidate")
    if state == "confirmed" and not (task.get("commit_sha") or task.get("pr_url")):
        errors.append("confirmed task requires commit_sha or pr_url")
    if errors:
        print(json.dumps({"status": "fail", "task_dir": str(task_dir), "errors": errors}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "pass", "task_id": task.get("task_id"), "state": state, "task_dir": str(task_dir)}, ensure_ascii=False))
    return 0


def transition(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task_path = task_dir / "task.json"
    task = read_json(task_path)
    current = task.get("state")
    target = args.state
    if current not in STATES or target not in STATES:
        print(f"Invalid state: {current} -> {target}", file=sys.stderr)
        return 2
    if target not in TRANSITIONS.get(current, set()):
        print(f"Illegal transition: {current} -> {target}", file=sys.stderr)
        return 2
    if target == "validated":
        quality = read_json(task_dir / "quality-report.json")
        if quality.get("status") != "pass":
            print("validated requires quality-report.json status=pass", file=sys.stderr)
            return 2
    if target == "ready_for_pr" and not (task_dir / "review.json").is_file():
        print("ready_for_pr requires review.json", file=sys.stderr)
        return 2
    if target == "ready_for_pr":
        review = read_json(task_dir / "review.json")
        candidate = read_json(task_dir / "browser-review.json")
        if not candidate_is_current(candidate):
            print("ready_for_pr requires a non-expired browser-review candidate", file=sys.stderr)
            return 2
        if not str(review.get("reviewer") or "").strip():
            print("ready_for_pr requires a non-empty review reviewer", file=sys.stderr)
            return 2
        if review.get("decision") != "approved" or candidate.get("task_id") != task.get("task_id") or candidate.get("scene") != task.get("scene") or not candidate.get("candidate_id") or review.get("candidate_id") != candidate.get("candidate_id") or candidate.get("status") != "approved":
            print("ready_for_pr requires approved review.json for the exact browser-review candidate", file=sys.stderr)
            return 2
    if target == "confirmed" and not (args.commit_sha or args.pr_url):
        print("confirmed requires --commit-sha or --pr-url", file=sys.stderr)
        return 2
    task["state"] = target
    task["updated_at"] = now()
    if args.commit_sha:
        task["commit_sha"] = args.commit_sha
    if args.pr_url:
        task["pr_url"] = args.pr_url
    write_json(task_path, task)
    report_path = task_dir / "execution-report.json"
    report = read_json(report_path)
    report["status"] = target
    report["generated_at"] = now()
    write_json(report_path, report)
    print(json.dumps({"status": "transitioned", "from": current, "to": target, "task_id": task.get("task_id")}, ensure_ascii=False))
    return 0


def md_table(items: list[dict], columns: list[tuple[str, str]]) -> str:
    if not items:
        return "_None recorded._\n"
    header = "| " + " | ".join(title for title, _ in columns) + " |\n"
    divider = "| " + " | ".join("---" for _ in columns) + " |\n"
    rows = ""
    for item in items:
        rows += "| " + " | ".join(str(item.get(key, "")).replace("|", "\\|") for _, key in columns) + " |\n"
    return header + divider + rows


def render(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task = read_json(task_dir / "task.json")
    report = read_json(task_dir / "execution-report.json")
    issues = read_json(task_dir / "issue-register.json", {"issues": []}).get("issues", [])
    manifest = read_json(task_dir / "artifact-manifest.json", {"artifacts": []})
    quality = read_json(task_dir / "quality-report.json", {})
    handoff = read_json(task_dir / "handoff.json", {})
    lines = [
        f"# Animation Task Report — {task.get('task_id', task_dir.name)}",
        "",
        "## Status",
        f"- Overall: **{task.get('state', report.get('status', 'unknown'))}**",
        f"- Confidence: **{report.get('confidence', 'unknown')}**",
        f"- Scene: `{task.get('scene', '')}`",
        f"- Project: `{task.get('project_name', '')}`",
        f"- Context hash: `{task.get('context_hash', '')}`",
        "",
        "## Completed",
        md_table(report.get("completed", []), [("Item", "summary"), ("Status", "status"), ("Evidence", "evidence")]),
        "## Verified",
        md_table(report.get("verified", []), [("Item", "summary"), ("Status", "status"), ("Evidence", "evidence")]),
        "## Not completed",
        md_table(report.get("not_completed", []), [("Item", "summary"), ("Status", "status"), ("Evidence", "evidence")]),
        "## Problems to fix",
        md_table(issues or report.get("problems", []), [("ID", "id"), ("Severity", "severity"), ("Problem", "summary"), ("Status", "status"), ("Next action", "next_action")]),
        "## Structure review",
        f"- Missing files: `{', '.join(report.get('structure_review', {}).get('missing_files', [])) or 'none'}`",
        f"- Broken references: `{', '.join(report.get('structure_review', {}).get('broken_references', [])) or 'none'}`",
        f"- Artifact count: **{len(manifest.get('artifacts', []))}**",
        f"- Quality gate: **{quality.get('status', 'not-run')}**",
        "",
        "## Browser review",
        md_table(report.get("browser_review", []), [("Candidate", "candidate_id"), ("Decision", "decision"), ("Reviewer", "reviewer"), ("Evidence", "evidence")]),
        "",
        "## Recommended next Agent / Skill",
        md_table(report.get("next_agent", handoff.get("next_actions", [])), [("Agent/Skill", "agent"), ("Action", "action"), ("Evidence needed", "evidence_needed")]),
        "## Evidence files",
        md_table(manifest.get("artifacts", []), [("Path", "path"), ("Type", "type"), ("Bytes", "bytes"), ("SHA-256", "sha256")]),
        "",
        f"_Generated at {now()} by `scripts/report.py`._",
    ]
    output = Path(args.output).resolve() if args.output else task_dir / "REPORT.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "rendered", "task_id": task.get("task_id", task_dir.name), "report": str(output)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--task-id", required=True)
    init.add_argument("--scene", default="pending-scene")
    init.add_argument("--intent", default="Animation task")
    init.add_argument("--project-name", default="")
    init.add_argument("--context-path", default="")
    init.add_argument("--context-hash", default="")
    init.add_argument("--agent", default="motionloom")
    init.add_argument("--output")
    init.set_defaults(func=init_task)
    collect_parser = sub.add_parser("collect")
    collect_parser.add_argument("--task-dir", required=True)
    collect_parser.set_defaults(func=collect)
    transition_parser = sub.add_parser("transition")
    transition_parser.add_argument("--task-dir", required=True)
    transition_parser.add_argument("--state", choices=STATES, required=True)
    transition_parser.add_argument("--commit-sha")
    transition_parser.add_argument("--pr-url")
    transition_parser.set_defaults(func=transition)
    render_parser = sub.add_parser("render")
    render_parser.add_argument("--task-dir", required=True)
    render_parser.add_argument("--output")
    render_parser.set_defaults(func=render)
    add_parser = sub.add_parser("add", help="Record a report item or problem")
    add_parser.add_argument("--task-dir", required=True)
    add_parser.add_argument("--section", choices=["completed", "verified", "not_completed", "problems", "next_agent"], required=True)
    add_parser.add_argument("--id", required=True)
    add_parser.add_argument("--summary", required=True)
    add_parser.add_argument("--status", default="recorded")
    add_parser.add_argument("--evidence", action="append", default=[])
    add_parser.add_argument("--confidence", choices=["high", "medium", "low"])
    add_parser.add_argument("--severity", choices=["P0", "P1", "P2", "P3"])
    add_parser.add_argument("--next-action")
    add_parser.add_argument("--agent")
    add_parser.add_argument("--skill")
    add_parser.add_argument("--evidence-needed", action="append", default=[])
    add_parser.set_defaults(func=add_item)
    review_parser = sub.add_parser("review", help="Persist a human or Agent review decision")
    review_parser.add_argument("--task-dir", required=True)
    review_parser.add_argument("--decision", choices=["pending", "approved", "changes_requested", "rejected"], required=True)
    review_parser.add_argument("--reviewer", required=True)
    review_parser.add_argument("--notes", default="")
    review_parser.add_argument("--feedback", action="append", default=[])
    review_parser.add_argument("--candidate-id")
    review_parser.set_defaults(func=record_review)
    structure_parser = sub.add_parser("structure", help="Record missing files, broken references or untracked artifacts")
    structure_parser.add_argument("--task-dir", required=True)
    structure_parser.add_argument("--missing-file", action="append", default=[])
    structure_parser.add_argument("--broken-reference", action="append", default=[])
    structure_parser.add_argument("--untracked-artifact", action="append", default=[])
    structure_parser.set_defaults(func=record_structure)
    check_parser = sub.add_parser("check", help="Validate semantic completeness of a task bundle")
    check_parser.add_argument("--task-dir", required=True)
    check_parser.set_defaults(func=check_report)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
