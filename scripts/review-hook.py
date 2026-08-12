#!/usr/bin/env python3
"""Prepare and validate the mandatory internal-browser Dev Lab review handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SAFE_SCENE = re.compile(r"^[A-Za-z0-9._-]+$")
CANDIDATE_TTL = timedelta(hours=24)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: dict | None = None) -> dict:
    if not path.is_file():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def candidate_id(task_id: str, scene: str, context_hash: str, source_hash: str, render_hash: str) -> str:
    raw = f"{task_id}:{scene}:{context_hash}:{source_hash}:{render_hash}".encode()
    return hashlib.sha256(raw).hexdigest()[:20]


def paths(task_dir: Path, task: dict) -> tuple[Path, Path, Path, Path]:
    scene = task.get("scene", "")
    if not scene or scene in {".", ".."} or not SAFE_SCENE.fullmatch(scene):
        raise ValueError("task.scene contains unsafe path characters")
    scene_dir = ROOT / "src" / "output" / scene
    manifest_path = scene_dir / "manifest.json"
    manifest = read_json(manifest_path)
    source_path = (scene_dir / manifest["file"]).resolve()
    render_meta = scene_dir / "snapshot" / ".render-meta.json"
    context_path = Path(task.get("context_path") or ROOT / "project-context.json")
    if not context_path.is_absolute():
        context_path = ROOT / context_path
    if not source_path.is_file() or scene_dir.resolve() not in source_path.parents:
        raise ValueError("manifest.file must point to a source inside the selected scene directory")
    if not render_meta.is_file():
        raise ValueError("runtime snapshot metadata is required before browser review")
    return scene_dir, source_path, render_meta, context_path


def prepare(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task_path = task_dir / "task.json"
    task = read_json(task_path)
    scene = task.get("scene")
    if not scene:
        raise ValueError("task.json requires scene")
    scene_dir, source_path, render_meta, context_path = paths(task_dir, task)
    spec = read_json(scene_dir / "motion-spec.json")
    context_hash = (spec.get("context_binding") or {}).get("context_sha256") or sha256(context_path)
    source_hash = sha256(source_path)
    render_hash = sha256(render_meta)
    cid = candidate_id(task["task_id"], scene, context_hash, source_hash, render_hash)
    base = args.lab_url.rstrip("/")
    task_id = task["task_id"]
    url = f"{base}/?{urlencode({'scene': scene, 'task_id': task_id, 'candidate_id': cid, 'artifact_base': f'{base}/scenes/{scene}', 'task_base': f'{base}/tasks/{task_id}'})}"
    candidate = {
        "schema_version": "1.0",
        "candidate_id": cid,
        "task_id": task["task_id"],
        "scene": scene,
        "url": url,
        "status": "prepared",
        "context_sha256": context_hash,
        "source_sha256": source_hash,
        "runtime": spec.get("framework", "unknown"),
        "checkpoints": [0, 50, 100],
        "review_artifact": "review.json",
        "requires_user_approval": True,
        "prepared_at": now(),
        "expires_at": (datetime.now(timezone.utc) + CANDIDATE_TTL).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    (scene_dir / "browser-review.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    task["state"] = "review_required"
    task["updated_at"] = now()
    task["browser_review"] = {"required": True, "status": "prepared", "candidate_id": cid, "candidate_path": "browser-review.json", "review_artifact": "review.json"}
    (task_dir / "browser-review.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    (task_dir / "task.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    report_path = task_dir / "execution-report.json"
    report = read_json(report_path)
    report["status"] = "review_required"
    report["browser_review"] = [item for item in report.get("browser_review", []) if item.get("candidate_id") != cid]
    report["browser_review"].append({"candidate_id": cid, "decision": "pending", "evidence": ["browser-review.json"], "next_action": "Open the internal Dev Lab URL and ask the user to review."})
    report["next_agent"] = [item for item in report.get("next_agent", []) if item.get("id") != "browser-review"]
    report["next_agent"].append({"id": "browser-review", "summary": "Open the exact candidate in the internal Dev Lab browser.", "status": "pending", "agent": "browser-review-agent", "skill": "browser-review", "evidence_needed": ["review.json"], "next_action": "Ask user to approve or request changes."})
    report["generated_at"] = now()
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    handoff_path = task_dir / "handoff.json"
    handoff = read_json(handoff_path)
    handoff.update({"state": "review_required", "to_agent": "browser-review-agent", "summary": "Open the exact rendered candidate in the internal Dev Lab and obtain user approval before PR.", "next_actions": [{"action": "Open internal Dev Lab candidate", "kind": "browser_review", "agent": "browser-review-agent", "skill": "browser-review", "url": url, "candidate_id": cid, "requires_user_approval": True, "evidence_needed": ["review.json"], "output_artifacts": ["review.json"]}], "required_artifacts": sorted(set(handoff.get("required_artifacts", []) + ["browser-review.json", "review.json"]))})
    handoff_path.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(["bash", str(ROOT / "scripts/devlab.sh"), scene, "--prepare-only", str(task_dir)], check=True, capture_output=True, text=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/report.py"), "collect", "--task-dir", str(task_dir)], check=True, capture_output=True, text=True)
    print(json.dumps({"status": "review_required", "task_id": task["task_id"], "candidate_id": cid, "url": url, "agent": "browser-review-agent", "action": "Open this exact URL in the internal browser; ask the user to inspect frames 0/50/100 and approve or request changes.", "requires_user_approval": True, "output_artifacts": ["review.json"]}, ensure_ascii=False))
    return 0


def validate(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task = read_json(task_dir / "task.json")
    candidate = read_json(task_dir / "browser-review.json")
    scene_dir, source_path, render_meta, context_path = paths(task_dir, task)
    spec = read_json(scene_dir / "motion-spec.json")
    context_hash = (spec.get("context_binding") or {}).get("context_sha256") or sha256(context_path)
    expected = candidate_id(task["task_id"], task["scene"], context_hash, sha256(source_path), sha256(render_meta))
    errors = []
    if not candidate.get("expires_at"):
        errors.append("browser-review candidate has no expiry")
    else:
        try:
            if datetime.now(timezone.utc) > parse_time(candidate["expires_at"]):
                errors.append("browser-review candidate has expired")
        except (TypeError, ValueError):
            errors.append("browser-review candidate expiry is invalid")
    if candidate.get("candidate_id") != expected:
        errors.append("candidate_id does not match task, context, source and runtime metadata")
    if candidate.get("task_id") != task.get("task_id"):
        errors.append("candidate task_id does not match task.json")
    task_review = task.get("browser_review") or {}
    if task_review.get("candidate_id") != candidate.get("candidate_id"):
        errors.append("task browser_review candidate_id does not match browser-review.json")
    if task_review.get("status") == "approved" and candidate.get("status") != "approved":
        errors.append("task browser_review status claims approved but candidate is not approved")
    if candidate.get("scene") != task.get("scene"):
        errors.append("candidate scene does not match task scene")
    if candidate.get("source_sha256") != sha256(source_path):
        errors.append("candidate source_sha256 is stale")
    if candidate.get("context_sha256") != context_hash:
        errors.append("candidate context_sha256 is stale")
    if candidate.get("status") not in {"prepared", "opened", "reviewed", "approved", "changes_requested", "expired"}:
        errors.append(f"browser-review candidate status is invalid: {candidate.get('status')}")
    review = read_json(task_dir / "review.json", {})
    if review and review.get("candidate_id") != candidate.get("candidate_id"):
        errors.append("review.json approves a different candidate")
    if review:
        if review.get("task_id") != task.get("task_id"):
            errors.append("review.json task_id does not match task.json")
        if not str(review.get("reviewer") or "").strip():
            errors.append("review.json reviewer is required")
        reviewed_at = review.get("reviewed_at")
        if reviewed_at:
            try:
                if parse_time(reviewed_at) > parse_time(candidate["expires_at"]):
                    errors.append("review.json was recorded after candidate expiry")
            except (TypeError, ValueError, KeyError):
                errors.append("review.json reviewed_at or candidate expiry is invalid")
    if args.require_approved:
        if candidate.get("status") != "approved":
            errors.append("browser-review candidate is not approved")
        if not review or review.get("decision") != "approved":
            errors.append("review.json decision must be approved")
    status = "pass" if not errors else "fail"
    print(json.dumps({"status": status, "task_id": task.get("task_id"), "candidate_id": candidate.get("candidate_id"), "candidate_status": candidate.get("status"), "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--task-dir", required=True)
    p.add_argument("--lab-url", default="http://127.0.0.1:3300")
    p.set_defaults(func=prepare)
    v = sub.add_parser("validate")
    v.add_argument("--task-dir", required=True)
    v.add_argument("--require-approved", action="store_true")
    v.set_defaults(func=validate)
    args = parser.parse_args()
    try:
        return args.func(args)
    except (KeyError, FileNotFoundError, json.JSONDecodeError, ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
