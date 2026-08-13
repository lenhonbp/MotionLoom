#!/usr/bin/env python3
"""Create, collect and render machine-readable animation task reports."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ARTIFACTS = (
    "semantic-lint-benchmark.json",
    "evidence-verifier-report.json",
    "runtime-adapters/runtime-evidence.json",
)
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


def project_memory_path() -> Path:
    return ROOT / ".motionloom" / "project-memory.json"


def asset_provenance_module():
    path = ROOT / "scripts" / "asset-provenance.py"
    loader = importlib.util.spec_from_file_location("motionloom_asset_provenance", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def asset_provenance_result(scene_manifest_path: Path, scene_manifest: dict, mode: str = "runtime") -> dict:
    name = scene_manifest.get("asset_provenance")
    if not name:
        return {"status": "not-run", "errors": ["scene manifest has no asset_provenance"]}
    provenance_path = (scene_manifest_path.parent / str(name)).resolve()
    if scene_manifest_path.parent.resolve() not in provenance_path.parents or not provenance_path.is_file():
        return {"status": "fail", "errors": ["scene manifest asset_provenance points to a missing or unsafe artifact"]}
    try:
        return asset_provenance_module().evaluate(
            provenance_path,
            base=scene_manifest_path.parent,
            mode=mode,
            manifest=scene_manifest,
        )
    except (OSError, ValueError, AttributeError) as exc:
        return {"status": "fail", "errors": [f"asset provenance contract: {exc}"]}


def memory_summary() -> dict | None:
    path = project_memory_path()
    if not path.is_file():
        return None
    try:
        memory = read_json(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, json.JSONDecodeError):
        return {"path": ".motionloom/project-memory.json", "status": "invalid"}
    freshness = memory.get("freshness") if isinstance(memory, dict) else {}
    return {
        "path": ".motionloom/project-memory.json",
        "snapshot_path": "project-memory.json",
        "memory_id": memory.get("memory_id"),
        "status": freshness.get("status", "invalid"),
        "sha256": digest,
        "updated_at": memory.get("updated_at"),
    }


def sync_memory_snapshot(task_dir: Path) -> dict | None:
    source = project_memory_path()
    if not source.is_file():
        return None
    destination = task_dir / "project-memory.json"
    shutil.copy2(source, destination)
    return memory_summary()


def has_symlink_component(path: Path) -> bool:
    current = path
    while True:
        if current.is_symlink():
            return True
        if current.parent == current:
            return False
        current = current.parent


def candidate_expiry(candidate: dict) -> datetime | None:
    value = candidate.get("expires_at")
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (TypeError, ValueError):
        return None


def candidate_is_current(candidate: dict) -> bool:
    expiry = candidate_expiry(candidate)
    return expiry is not None and datetime.now(timezone.utc) <= expiry


def init_task(args: argparse.Namespace) -> int:
    task_dir = Path(args.output or ROOT / "artifacts" / args.task_id).resolve()
    timestamp = now()
    memory = memory_summary()
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
    if memory:
        task["project_memory"] = memory
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
        "next_agent": [{"agent": args.agent, "action": "Recover Project Memory and run project analysis before generation.", "evidence_needed": ["project-memory.json", "project-context.json"]}],
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
        "required_artifacts": ["task.json", "execution-report.json", *EVIDENCE_ARTIFACTS, *( ["project-memory.json"] if memory else [] )],
        "blockers": [],
    }
    write_json(task_dir / "task.json", task)
    write_json(task_dir / "execution-report.json", report)
    write_json(task_dir / "issue-register.json", {"version": "1.0", "task_id": args.task_id, "issues": []})
    write_json(task_dir / "handoff.json", handoff)
    write_json(task_dir / "artifact-manifest.json", {"manifest_version": "1.0", "task_id": args.task_id, "generated_at": timestamp, "artifacts": []})
    if memory:
        sync_memory_snapshot(task_dir)
    (task_dir / "decision-log.jsonl").write_text("", encoding="utf-8")
    print(json.dumps({"status": "created", "task_id": args.task_id, "task_dir": str(task_dir)}, ensure_ascii=False))
    return 0


def collect(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task = read_json(task_dir / "task.json")
    sync_memory_snapshot(task_dir)
    excluded = {"artifact-manifest.json", "execution-report.json", "decision-log.jsonl"}
    artifacts = []
    for path in sorted(task_dir.rglob("*")):
        if has_symlink_component(path):
            raise ValueError(f"task bundle cannot contain symlinked artifact: {path.relative_to(task_dir)}")
        if not path.is_file() or path.name in excluded:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        artifacts.append({"path": str(path.relative_to(task_dir)), "type": path.suffix.lstrip(".") or "file", "sha256": digest, "bytes": path.stat().st_size})
    manifest = {"manifest_version": "1.0", "task_id": task.get("task_id", task_dir.name), "generated_at": now(), "artifacts": artifacts}
    write_json(task_dir / "artifact-manifest.json", manifest)
    handoff_path = task_dir / "handoff.json"
    if handoff_path.is_file():
        handoff = read_json(handoff_path)
        required = set(handoff.get("required_artifacts", []))
        required.update(name for name in EVIDENCE_ARTIFACTS if (task_dir / name).is_file())
        if (task_dir / "project-memory.json").is_file():
            required.add("project-memory.json")
        handoff["required_artifacts"] = sorted(required)
        write_json(handoff_path, handoff)
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


def p1_contract_errors(task_dir: Path, task: dict) -> list[str]:
    names = ("semantic-lint-report.json", "continuity-report.json", "fix-plan.json")
    present = [name for name in names if (task_dir / name).is_file()]
    if not present:
        return []
    errors = [f"P1 contract requires {name}" for name in names if not (task_dir / name).is_file()]
    if errors:
        return errors
    lint = read_json(task_dir / "semantic-lint-report.json")
    if lint.get("schema_version") != "0.1":
        errors.append("semantic-lint-report.json schema_version must be 0.1")
    if lint.get("task_id") != task.get("task_id") or lint.get("scene") != task.get("scene"):
        errors.append("semantic-lint-report.json must bind task_id and scene to task.json")
    continuity = read_json(task_dir / "continuity-report.json")
    if continuity.get("schema_version") != "0.1":
        errors.append("continuity-report.json schema_version must be 0.1")
    if not continuity.get("scenes"):
        errors.append("continuity-report.json requires scenes")
    plan = read_json(task_dir / "fix-plan.json")
    if plan.get("schema_version") != "0.1" or plan.get("task_id") != task.get("task_id"):
        errors.append("fix-plan.json must use schema 0.1 and bind task_id to task.json")
    for source in plan.get("source_reports", []):
        source_path = task_dir / str(source.get("path", ""))
        if not source_path.is_file():
            errors.append(f"fix-plan source report missing: {source.get('path', '<unknown>')}")
        elif source.get("sha256") != hashlib.sha256(source_path.read_bytes()).hexdigest():
            errors.append(f"fix-plan source report hash mismatch: {source.get('path', '<unknown>')}")
    handoff = read_json(task_dir / "handoff.json")
    if handoff.get("fix_plan", {}).get("path") != "fix-plan.json":
        errors.append("handoff.json must expose fix-plan.json")
    return errors


def approval_contract_errors(task_dir: Path, task: dict, require_current: bool) -> list[str]:
    errors: list[str] = []
    candidate_path = task_dir / "browser-review.json"
    review_path = task_dir / "review.json"
    candidate = read_json(candidate_path)
    review = read_json(review_path)
    if not candidate_path.is_file():
        return ["ready-for-PR task requires browser-review.json"]
    if not review_path.is_file():
        return ["ready-for-PR task requires review.json"]
    if candidate.get("task_id") != task.get("task_id"):
        errors.append("browser-review candidate task_id does not match task.json")
    if candidate.get("scene") != task.get("scene"):
        errors.append("browser-review candidate scene does not match task.json")
    task_review = task.get("browser_review") or {}
    if task_review.get("candidate_id") != candidate.get("candidate_id"):
        errors.append("task browser_review candidate_id does not match browser-review.json")
    if task_review.get("status") != candidate.get("status"):
        errors.append("task browser_review status does not match browser-review.json")
    if review.get("task_id") != task.get("task_id"):
        errors.append("review.json task_id does not match task.json")
    if review.get("candidate_id") != candidate.get("candidate_id"):
        errors.append("review.json must approve the exact browser-review candidate")
    if review.get("decision") != "approved":
        errors.append("ready-for-PR task requires review.json decision=approved")
    if candidate.get("status") != "approved":
        errors.append("ready-for-PR task requires browser-review.json status=approved")
    if candidate.get("requires_user_approval") is not True:
        errors.append("browser-review candidate must explicitly require user approval")
    expiry = candidate_expiry(candidate)
    if expiry is None:
        errors.append("browser-review candidate expiry must be a timezone-aware timestamp")
    elif require_current and datetime.now(timezone.utc) > expiry:
        errors.append("browser-review candidate has expired before PR readiness")
    reviewed_at_raw = review.get("reviewed_at")
    if not reviewed_at_raw:
        errors.append("review.json reviewed_at is required")
    else:
        try:
            reviewed_at = datetime.fromisoformat(str(reviewed_at_raw).replace("Z", "+00:00"))
            if reviewed_at.tzinfo is None:
                raise ValueError("reviewed_at must include timezone")
            if expiry is not None and reviewed_at.astimezone(timezone.utc) > expiry:
                errors.append("review.json was recorded after candidate expiry")
        except (TypeError, ValueError):
            errors.append("review.json reviewed_at is invalid")
    return errors


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
    scene_manifest_path = ROOT / "src" / "output" / str(task.get("scene", "")) / "manifest.json"
    scene_manifest = read_json(scene_manifest_path, {})
    state = task.get("state")
    if not task.get("task_id") or not task.get("scene"):
        errors.append("task.json requires task_id and scene")
    errors.extend(p1_contract_errors(task_dir, task))
    for section in ("completed", "verified", "not_completed", "problems", "next_agent"):
        if not isinstance(report.get(section), list):
            errors.append(f"execution-report.json requires list section: {section}")
    for artifact in manifest.get("artifacts", []):
        if len(artifact.get("sha256", "")) != 64:
            errors.append(f"artifact has invalid sha256: {artifact.get('path', '<unknown>')}")
        if not (task_dir / artifact.get("path", "")).is_file():
            errors.append(f"artifact path missing: {artifact.get('path', '<unknown>')}")
    visual_truth_name = scene_manifest.get("visual_truth")
    if visual_truth_name:
        visual_truth_path = scene_manifest_path.parent / str(visual_truth_name)
        if not visual_truth_path.is_file():
            errors.append("scene manifest visual_truth points to a missing artifact")
    provenance_mode = "production" if state in {"ready_for_pr", "confirmed"} else "runtime"
    provenance = asset_provenance_result(scene_manifest_path, scene_manifest, provenance_mode)
    if provenance.get("status") == "fail":
        errors.extend(f"asset provenance: {error}" for error in provenance.get("errors", []))
    # Legacy report-contract fixtures may exercise lifecycle/report behavior
    # without materializing a scene manifest. Do not invent provenance for
    # those synthetic tasks. Once a real scene manifest exists, readiness is
    # fail-closed and its asset_provenance reference is mandatory for PR
    # states; the production quality gate remains independently strict when
    # --require-asset-provenance is supplied.
    if state in {"ready_for_pr", "confirmed"} and scene_manifest_path.is_file():
        if provenance.get("status") != "pass":
            errors.append("ready-for-PR or confirmed task requires a passing asset provenance production check")
        elif not provenance.get("summary", {}).get("production_eligible"):
            errors.append("ready-for-PR or confirmed task requires asset provenance production_eligible")
    if state in {"validated", "ready_for_pr", "confirmed"}:
        quality = read_json(task_dir / "quality-report.json")
        if quality.get("status") != "pass":
            errors.append("validated-or-later task requires quality-report.json status=pass")
    if state in {"ready_for_pr", "confirmed"}:
        errors.extend(approval_contract_errors(task_dir, task, require_current=state == "ready_for_pr"))
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
    lint = read_json(task_dir / "semantic-lint-report.json", {})
    continuity = read_json(task_dir / "continuity-report.json", {})
    fix_plan = read_json(task_dir / "fix-plan.json", {})
    scene_manifest = read_json(ROOT / "src" / "output" / str(task.get("scene", "")) / "manifest.json", {})
    visual_truth = read_json(
        ROOT / "src" / "output" / str(task.get("scene", "")) / str(scene_manifest.get("visual_truth", "")),
        {},
    ) if scene_manifest.get("visual_truth") else {}
    provenance = asset_provenance_result(
        ROOT / "src" / "output" / str(task.get("scene", "")) / "manifest.json",
        scene_manifest,
        "production" if task.get("state") in {"ready_for_pr", "confirmed"} else "runtime",
    )
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
        "## Visual Truth",
        f"- Status: **{visual_truth.get('status', 'not-run')}**; scene: `{visual_truth.get('scene', task.get('scene', ''))}`; approval: **{visual_truth.get('review_boundary', {}).get('approval', False)}**",
        f"- Baseline: `{visual_truth.get('frames', {}).get('baseline', {}).get('path', '')}`; candidate: `{visual_truth.get('frames', {}).get('candidate', {}).get('path', '')}`",
        f"- Changed pixels: **{visual_truth.get('comparison', {}).get('changed_pixels', 'not-run')}**; changed regions: **{len(visual_truth.get('comparison', {}).get('regions', []))}**",
        "## Asset provenance",
        f"- Status: **{provenance.get('status', 'not-run')}**; authority: **{provenance.get('summary', {}).get('authority', 'unknown')}**; declared readiness: **{provenance.get('summary', {}).get('declared_readiness', 'blocked')}**; effective readiness: **{provenance.get('summary', {}).get('effective_readiness', 'blocked')}**",
        f"- Production eligible: **{provenance.get('summary', {}).get('production_eligible', False)}**; production approved: **{provenance.get('summary', {}).get('production_approved', False)}**; errors: **{len(provenance.get('errors', []))}**",
        "## Semantic motion lint",
        f"- Status: **{lint.get('status', 'not-run')}**; errors: **{lint.get('summary', {}).get('errors', 0)}**; warnings: **{lint.get('summary', {}).get('warnings', 0)}**; blocking: **{lint.get('summary', {}).get('blocking', 0)}**",
        md_table(lint.get("findings", []), [("Rule", "rule_id"), ("Severity", "severity"), ("Confidence", "confidence"), ("Message", "message"), ("Basis", "basis")]),
        "## Multi-scene continuity",
        f"- Status: **{continuity.get('status', 'not-run')}**; scenes: **{continuity.get('summary', {}).get('scene_count', 0)}**; transitions: **{continuity.get('summary', {}).get('transition_count', 0)}**; warnings: **{continuity.get('summary', {}).get('warnings', 0)}**",
        "## Fix plan",
        f"- Status: **{fix_plan.get('status', 'not-run')}**; issues: **{len(fix_plan.get('issues', []))}**; next action: **{fix_plan.get('next_agent', {}).get('action', '')}**",
        md_table(fix_plan.get("issues", []), [("ID", "id"), ("Severity", "severity"), ("Confidence", "confidence"), ("Root cause", "root_cause"), ("Rerun", "rerun_scope"), ("Status", "status")]),
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
