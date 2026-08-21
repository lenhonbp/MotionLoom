#!/usr/bin/env python3
"""Prepare and validate the mandatory internal-browser Dev Lab review handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
SAFE_SCENE = re.compile(r"^[A-Za-z0-9._-]+$")
SAFE_ANIMATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
CANDIDATE_TTL = timedelta(hours=24)
RUNTIME_DESCRIPTOR = "devlab-runtime.json"
RUNTIME_MODES = {"sprite-sequence", "iframe"}


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


def candidate_id(
    task_id: str,
    scene: str,
    context_hash: str,
    source_hash: str,
    render_hash: str,
    runtime_bundle_hash: str | None = None,
) -> str:
    # Keep the legacy identity formula byte-for-byte when a scene has no live
    # runtime descriptor so already-prepared snapshot candidates remain valid.
    raw = f"{task_id}:{scene}:{context_hash}:{source_hash}:{render_hash}"
    if runtime_bundle_hash:
        raw += f":devlab-runtime:{runtime_bundle_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def review_urls(lab_url: str, scene: str, task_id: str, candidate: str) -> tuple[str, str, str]:
    """Build an exact review route while anchoring artifact paths at its origin."""
    parsed = urlsplit(lab_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("lab-url must be an absolute http(s) Dev Lab route without query or fragment")
    origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    review_path = parsed.path.rstrip("/") or "/"
    review_base = f"{origin}{review_path}" if review_path != "/" else origin
    query = urlencode({
        "scene": scene,
        "task_id": task_id,
        "candidate_id": candidate,
        "artifact_base": f"{origin}/scenes/{scene}",
        "task_base": f"{origin}/tasks/{task_id}",
    })
    return (
        f"{review_base}/?{query}" if review_path != "/" else f"{origin}/?{query}",
        f"{origin}/scenes/{scene}",
        f"{origin}/tasks/{task_id}",
    )


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


def safe_relative_file(scene_dir: Path, value: object, label: str) -> tuple[str, Path]:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")) or "\\" in value:
        raise ValueError(f"{label} must be a scene-relative path")
    parts = Path(value).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{label} contains unsafe path segments: {value!r}")
    scene_root = scene_dir.resolve()
    current = scene_root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label} must not traverse symlinks: {value}")
    resolved = (scene_root / value).resolve()
    if not resolved.is_file() or scene_root not in resolved.parents:
        raise ValueError(f"{label} must resolve to an existing file inside the scene: {value}")
    return value, resolved


def runtime_bundle(scene_dir: Path) -> dict | None:
    descriptor_path = scene_dir / RUNTIME_DESCRIPTOR
    if not descriptor_path.exists():
        return None
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        raise ValueError("devlab-runtime.json must be a regular scene-local file")
    descriptor = read_json(descriptor_path)
    if descriptor.get("schema_version") != "1.0":
        raise ValueError("devlab-runtime.json schema_version must be 1.0")
    mode = descriptor.get("mode")
    if mode not in RUNTIME_MODES:
        raise ValueError(f"devlab-runtime.json mode is unsupported: {mode!r}")
    files = descriptor.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("devlab-runtime.json requires a non-empty files array")
    resolved_files: dict[str, Path] = {}
    reserved_runtime_files = {RUNTIME_DESCRIPTOR, "browser-review.json", "review.json"}
    for raw in files:
        relative, resolved = safe_relative_file(scene_dir, raw, "runtime file")
        if relative in reserved_runtime_files:
            raise ValueError(f"devlab-runtime.json must not hash mutable review metadata as runtime bytes: {relative}")
        if relative in resolved_files:
            raise ValueError(f"devlab-runtime.json repeats runtime file: {relative}")
        resolved_files[relative] = resolved

    animations = descriptor.get("animations")
    if not isinstance(animations, list) or not animations:
        raise ValueError("devlab-runtime.json requires at least one animation")
    animation_ids: list[str] = []
    for animation in animations:
        if not isinstance(animation, dict):
            raise ValueError("devlab-runtime.json animations must be objects")
        action_id = animation.get("id")
        if not isinstance(action_id, str) or not SAFE_ANIMATION.fullmatch(action_id):
            raise ValueError(f"devlab-runtime.json animation id is invalid: {action_id!r}")
        if action_id in animation_ids:
            raise ValueError(f"devlab-runtime.json repeats animation id: {action_id}")
        animation_ids.append(action_id)
        if mode == "sprite-sequence":
            fps = animation.get("fps")
            frames = animation.get("frames")
            if not isinstance(fps, (int, float)) or isinstance(fps, bool) or fps <= 0:
                raise ValueError(f"sprite animation {action_id} requires a positive fps")
            if not isinstance(frames, list) or not frames:
                raise ValueError(f"sprite animation {action_id} requires frames")
            for frame in frames:
                relative, _ = safe_relative_file(scene_dir, frame, f"frame for {action_id}")
                if relative not in resolved_files:
                    raise ValueError(f"frame for {action_id} is not declared in runtime files: {relative}")

    default_animation = descriptor.get("default_animation")
    if default_animation not in animation_ids:
        raise ValueError("devlab-runtime.json default_animation must reference a declared animation")
    if mode == "iframe":
        entrypoint, _ = safe_relative_file(scene_dir, descriptor.get("entrypoint"), "runtime entrypoint")
        if entrypoint not in resolved_files:
            raise ValueError("runtime entrypoint must be declared in runtime files")

    controls = descriptor.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("devlab-runtime.json controls object is required")
    for control in ("play", "pause", "restart", "seek", "step", "speed", "loop"):
        if not isinstance(controls.get(control), bool):
            raise ValueError(f"devlab-runtime.json controls.{control} must be boolean")
    review_policy = descriptor.get("review_policy")
    if not isinstance(review_policy, dict) or not isinstance(review_policy.get("require_all_animations"), bool):
        raise ValueError("devlab-runtime.json review_policy.require_all_animations must be boolean")

    digest = hashlib.sha256()
    digest.update(b"motionloom-devlab-runtime-v1\0")
    digest.update(descriptor_path.read_bytes())
    for relative in sorted(resolved_files):
        digest.update(b"\0path\0")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0bytes\0")
        digest.update(resolved_files[relative].read_bytes())
    return {
        "descriptor": descriptor,
        "bundle_sha256": digest.hexdigest(),
        "animations": animation_ids,
        "mode": mode,
        "files": sorted(resolved_files),
        "review_policy": {"require_all_animations": review_policy["require_all_animations"]},
    }


def runtime_review_payload(bundle: dict | None) -> dict:
    if not bundle:
        return {
            "live": False,
            "mode": "captured-evidence",
            "checkpoints": [0, 50, 100],
        }
    return {
        "live": True,
        "mode": bundle["mode"],
        "descriptor": RUNTIME_DESCRIPTOR,
        "bundle_sha256": bundle["bundle_sha256"],
        "animations": bundle["animations"],
        "review_policy": bundle["review_policy"],
    }


def review_instruction(bundle: dict | None) -> str:
    if bundle:
        actions = ", ".join(bundle["animations"])
        return (
            "Open this exact URL in the internal browser; exercise the live runtime controls, "
            f"inspect the declared animations ({actions}), scrub/step the candidate, and ask the user to approve or request changes."
        )
    return "Open this exact URL in the internal browser; inspect frames 0/50/100 and ask the user to approve or request changes."


def prepare(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task_path = task_dir / "task.json"
    task = read_json(task_path)
    scene = task.get("scene")
    if not scene:
        raise ValueError("task.json requires scene")
    scene_dir, source_path, render_meta, context_path = paths(task_dir, task)
    bundle = runtime_bundle(scene_dir)
    memory_path = ROOT / ".motionloom" / "project-memory.json"
    memory = read_json(memory_path, {}) if memory_path.is_file() else {}
    memory_status = (memory.get("freshness") or {}).get("status")
    if memory_path.is_file() and memory_status not in {"fresh", None}:
        raise ValueError(f"project memory is {memory_status}; run motionloom memory refresh/analyze before browser review")
    spec = read_json(scene_dir / "motion-spec.json")
    context_hash = (spec.get("context_binding") or {}).get("context_sha256") or sha256(context_path)
    source_hash = sha256(source_path)
    render_hash = sha256(render_meta)
    cid = candidate_id(task["task_id"], scene, context_hash, source_hash, render_hash, bundle["bundle_sha256"] if bundle else None)
    task_id = task["task_id"]
    url, artifact_base, task_base = review_urls(args.lab_url, scene, task_id, cid)
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
        "runtime_review": runtime_review_payload(bundle),
        "review_artifact": "review.json",
        "requires_user_approval": True,
        "prepared_at": now(),
        "expires_at": (datetime.now(timezone.utc) + CANDIDATE_TTL).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    if memory_path.is_file():
        candidate["project_memory_sha256"] = sha256(memory_path)
        candidate["project_memory_id"] = memory.get("memory_id")
    (scene_dir / "browser-review.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    task["state"] = "review_required"
    task["updated_at"] = now()
    task["browser_review"] = {
        "required": True,
        "status": "prepared",
        "candidate_id": cid,
        "candidate_path": "browser-review.json",
        "review_artifact": "review.json",
        "runtime_review": candidate["runtime_review"],
    }
    (task_dir / "browser-review.json").write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    (task_dir / "task.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
    report_path = task_dir / "execution-report.json"
    report = read_json(report_path)
    report["status"] = "review_required"
    report["browser_review"] = [item for item in report.get("browser_review", []) if item.get("candidate_id") != cid]
    report["browser_review"].append({
        "candidate_id": cid,
        "decision": "pending",
        "evidence": ["browser-review.json"] + ([RUNTIME_DESCRIPTOR] if bundle else []),
        "next_action": review_instruction(bundle),
    })
    report["next_agent"] = [item for item in report.get("next_agent", []) if item.get("id") != "browser-review"]
    report["next_agent"].append({
        "id": "browser-review",
        "summary": "Open the exact candidate in the internal Dev Lab browser.",
        "status": "pending",
        "agent": "browser-review-agent",
        "skill": "browser-review",
        "evidence_needed": ["review.json"],
        "next_action": review_instruction(bundle),
    })
    report["generated_at"] = now()
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    handoff_path = task_dir / "handoff.json"
    handoff = read_json(handoff_path)
    if memory_path.is_file():
        shutil.copy2(memory_path, task_dir / "project-memory.json")
    handoff.update({
        "state": "review_required",
        "to_agent": "browser-review-agent",
        "summary": "Open the exact rendered candidate in the internal Dev Lab and obtain user approval before PR.",
        "next_actions": [{
            "action": "Open internal Dev Lab candidate",
            "kind": "browser_review",
            "agent": "browser-review-agent",
            "skill": "browser-review",
            "url": url,
            "artifact_base": artifact_base,
            "task_base": task_base,
            "candidate_id": cid,
            "runtime_review": candidate["runtime_review"],
            "requires_user_approval": True,
            "evidence_needed": ["review.json"],
            "output_artifacts": ["review.json"],
        }],
        "required_artifacts": sorted(set(
            handoff.get("required_artifacts", [])
            + ["browser-review.json", "review.json", "semantic-lint-benchmark.json", "evidence-verifier-report.json", "runtime-adapters/runtime-evidence.json"]
            + ([RUNTIME_DESCRIPTOR] if bundle else [])
            + (["project-memory.json"] if memory_path.is_file() else [])
        )),
    })
    handoff_path.write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts/devlab.py"), scene, "--prepare-only", "--task-dir", str(task_dir)], check=True, capture_output=True, text=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/report.py"), "collect", "--task-dir", str(task_dir)], check=True, capture_output=True, text=True)
    print(json.dumps({
        "status": "review_required",
        "task_id": task["task_id"],
        "candidate_id": cid,
        "url": url,
        "agent": "browser-review-agent",
        "action": review_instruction(bundle),
        "runtime_review": candidate["runtime_review"],
        "requires_user_approval": True,
        "output_artifacts": ["review.json"],
    }, ensure_ascii=False))
    return 0


def validate(args: argparse.Namespace) -> int:
    task_dir = Path(args.task_dir).resolve()
    task = read_json(task_dir / "task.json")
    candidate = read_json(task_dir / "browser-review.json")
    scene_dir, source_path, render_meta, context_path = paths(task_dir, task)
    spec = read_json(scene_dir / "motion-spec.json")
    bundle = runtime_bundle(scene_dir)
    context_hash = (spec.get("context_binding") or {}).get("context_sha256") or sha256(context_path)
    expected = candidate_id(
        task["task_id"], task["scene"], context_hash, sha256(source_path), sha256(render_meta),
        bundle["bundle_sha256"] if bundle else None,
    )
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
        errors.append("candidate_id does not match task, context, source, runtime metadata and live runtime bundle")
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

    runtime_review = candidate.get("runtime_review") or {}
    if bundle:
        if runtime_review.get("live") is not True:
            errors.append("candidate does not declare the available live runtime")
        if runtime_review.get("descriptor") != RUNTIME_DESCRIPTOR:
            errors.append("candidate live runtime descriptor binding is missing")
        if runtime_review.get("mode") != bundle["mode"]:
            errors.append("candidate live runtime mode is stale")
        if runtime_review.get("bundle_sha256") != bundle["bundle_sha256"]:
            errors.append("candidate live runtime bundle hash is stale")
        if runtime_review.get("animations") != bundle["animations"]:
            errors.append("candidate live runtime animation set is stale")
    elif runtime_review.get("live") is True:
        errors.append("candidate claims live runtime but devlab-runtime.json is missing")

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
        if review.get("decision") == "approved" and bundle and bundle["review_policy"]["require_all_animations"]:
            inspected = set(review.get("animations_inspected") or [])
            required = {
                animation["id"] for animation in bundle["descriptor"]["animations"]
                if animation.get("review_required", True)
            }
            missing = sorted(required - inspected)
            if missing:
                errors.append(f"approved review did not inspect required animations: {', '.join(missing)}")
    if args.require_approved:
        if candidate.get("status") != "approved":
            errors.append("browser-review candidate is not approved")
        if not review or review.get("decision") != "approved":
            errors.append("review.json decision must be approved")
    status = "pass" if not errors else "fail"
    print(json.dumps({
        "status": status,
        "task_id": task.get("task_id"),
        "candidate_id": candidate.get("candidate_id"),
        "candidate_status": candidate.get("status"),
        "runtime_review": runtime_review,
        "errors": errors,
    }, ensure_ascii=False))
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
