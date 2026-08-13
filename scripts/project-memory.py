#!/usr/bin/env python3
"""MotionLoom durable Project Memory CLI.

The memory is intentionally relocatable: project identity is derived from a
normalized Git remote when available, not from an absolute checkout path.
Writes are atomic and use pathlib/standard Python only so the same contract
runs on Ubuntu, macOS and Windows. Memory is context, not approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def configure_utf8_stdio() -> None:
    """Keep JSON/errors printable for Unicode project paths on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="strict")
        except (OSError, ValueError):
            # Embedded callers may expose a non-reconfigurable stream.
            pass


configure_utf8_stdio()


SCHEMA_VERSION = "1.0"
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_STALE = 10
EXIT_INVALID = 11
EXIT_MISSING = 12


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def write_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass


def project_root(args: argparse.Namespace) -> Path:
    return Path(args.project_root or ".").expanduser().resolve()


def memory_path(args: argparse.Namespace, root: Path) -> Path:
    raw = args.memory_path or ".motionloom/project-memory.json"
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def git_remote(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    remote = result.stdout.strip()
    return remote or None


def normalize_remote(remote: str | None) -> str | None:
    if not remote:
        return None
    value = remote.strip().lower()
    value = re.sub(r"^git\+", "", value)
    value = re.sub(r"^https?://", "", value)
    value = re.sub(r"^ssh://git@", "", value)
    value = re.sub(r"^git@", "", value)
    value = value.replace(":", "/", 1) if value.startswith("github.com:") else value
    value = value.removesuffix(".git").rstrip("/")
    return value


def project_identity(root: Path) -> tuple[str, str | None, str | None]:
    package = read_json(root / "package.json") or {}
    remote = git_remote(root)
    normalized = normalize_remote(remote)
    if normalized:
        return f"git:{normalized}", remote, package.get("name")
    name = str(package.get("name") or root.name).strip().lower()
    return f"local:{name}", remote, package.get("name")


def fingerprint_inputs(root: Path) -> list[tuple[str, str]]:
    candidates = [
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lockb",
        "project-manifest.json",
        "requirements.txt",
        "pyproject.toml",
    ]
    found: list[tuple[str, str]] = []
    for relative in candidates:
        path = root / relative
        digest = sha256_file(path)
        if digest:
            found.append((relative.replace("\\", "/"), digest))
    return found


def project_fingerprint(root: Path) -> str:
    inventory = fingerprint_inputs(root)
    return sha256_bytes(canonical(inventory))


def context_info(root: Path, context_arg: str | None) -> dict[str, Any]:
    raw = context_arg or "project-context.json"
    path = Path(raw).expanduser()
    context_path = path.resolve() if path.is_absolute() else (root / path).resolve()
    relative = os.path.relpath(context_path, root).replace("\\", "/")
    context = read_json(context_path)
    return {
        "path": relative,
        "sha256": sha256_file(context_path),
        "schema_version": str(context.get("schema_version")) if context else None,
        "generated_at": context.get("generated_at") if context else None,
        "exists": context is not None,
    }


def base_memory(root: Path, context_arg: str | None) -> dict[str, Any]:
    project_id, remote, package_name = project_identity(root)
    package = read_json(root / "package.json") or {}
    context = context_info(root, context_arg)
    checked = now()
    status = "fresh" if context["exists"] else "needs_context"
    reason = "project-context.json is available" if context["exists"] else "run motionloom analyze before animation work"
    memory = {
        "schema_version": SCHEMA_VERSION,
        "memory_id": "pm-" + re.sub(r"[^a-z0-9._-]+", "-", project_id.lower()).strip("-")[:100],
        "created_at": checked,
        "updated_at": checked,
        "project": {
            "project_id": project_id,
            "name": str(package.get("name") or root.name),
            "root_path": str(root),
            "repository": remote,
            "package_name": package_name,
        },
        "context": {key: context[key] for key in ("path", "sha256", "schema_version", "generated_at")},
        "motion_principles": {
            "duration_ms": None,
            "easing": None,
            "rhythm": None,
            "reduced_motion": "respect prefers-reduced-motion; review exceptions explicitly",
            "notes": [],
        },
        "policies": {
            "asset": {"authoritative_sources": ["project-manifest.json", "assets/library/"], "license_required": True, "unknown_asset_policy": "block"},
            "runtime": {"preferred_frameworks": [], "verified_runtimes": [], "browser_matrix": []},
        },
        "decisions": [],
        "rejected_patterns": [],
        "remediation": [],
        "freshness": {
            "status": status,
            "checked_at": checked,
            "context_hash": context["sha256"],
            "project_fingerprint": project_fingerprint(root),
            "reason": reason,
        },
        "recovery": {
            "last_task_id": None,
            "next_actions": ["Read project context before starting an animation task.", "Use Dev Lab review before any PR confirmation."],
            "last_review_state": None,
        },
    }
    return with_integrity(memory)


def without_integrity(memory: dict[str, Any]) -> dict[str, Any]:
    copy = json.loads(json.dumps(memory))
    copy.pop("integrity", None)
    return copy


def integrity_payload(memory: dict[str, Any]) -> dict[str, Any]:
    """Return the durable payload used to calculate the integrity hash.

    ``project.root_path`` is a runtime checkout location. It is deliberately
    excluded so relocating a valid project does not look like tampering;
    project identity remains bound to its normalized Git remote/package name.
    """
    payload = without_integrity(memory)
    project = payload.get("project")
    if isinstance(project, dict):
        project.pop("root_path", None)
    return payload


def with_integrity(memory: dict[str, Any]) -> dict[str, Any]:
    result = without_integrity(memory)
    result["integrity"] = {"canonical_sha256": sha256_bytes(canonical(integrity_payload(result)))}
    return result


def invariant_errors(memory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["schema_version", "memory_id", "project", "context", "motion_principles", "policies", "decisions", "rejected_patterns", "remediation", "freshness", "recovery"]
    for key in required:
        if key not in memory:
            errors.append(f"missing:{key}")
    if memory.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version:unsupported")
    project = memory.get("project") or {}
    if not project.get("project_id"):
        errors.append("project.project_id:missing")
    for field in ("name", "root_path", "repository"):
        if field not in project:
            errors.append(f"project.{field}:missing")
    if not re.match(r"^pm-[a-z0-9][a-z0-9._-]*$", str(memory.get("memory_id", ""))):
        errors.append("memory_id:invalid")
    integrity = (memory.get("integrity") or {}).get("canonical_sha256")
    if integrity and integrity != sha256_bytes(canonical(integrity_payload(memory))):
        errors.append("integrity:hash-mismatch")
    freshness = memory.get("freshness") or {}
    if freshness.get("status") not in {"fresh", "stale", "needs_context", "invalid"}:
        errors.append("freshness.status:invalid")
    return errors


def load_or_fail(path: Path) -> dict[str, Any]:
    memory = read_json(path)
    if memory is None:
        print(json.dumps({"status": "missing", "memory_path": str(path), "error": "memory file is missing or invalid JSON"}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(EXIT_MISSING)
    errors = invariant_errors(memory)
    if errors:
        print(json.dumps({"status": "invalid", "memory_path": str(path), "errors": errors}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(EXIT_INVALID)
    return memory


def refresh_memory(memory: dict[str, Any], root: Path, context_arg: str | None) -> dict[str, Any]:
    project_id, remote, package_name = project_identity(root)
    if project_id != memory["project"].get("project_id"):
        raise ValueError(f"project identity mismatch: memory={memory['project'].get('project_id')} current={project_id}")
    context = context_info(root, context_arg or memory["context"].get("path"))
    previous_context = memory["context"].get("sha256")
    previous_fingerprint = memory["freshness"].get("project_fingerprint")
    current_fingerprint = project_fingerprint(root)
    if not context["exists"]:
        status, reason = "needs_context", "project context is missing"
    elif previous_context and previous_context != context["sha256"]:
        status, reason = "stale", "project context hash changed; re-review assumptions"
    elif previous_fingerprint and previous_fingerprint != current_fingerprint:
        status, reason = "stale", "project dependency or manifest fingerprint changed"
    else:
        status, reason = "fresh", "context and project fingerprint match recorded memory"
    memory["updated_at"] = now()
    memory["project"].update({"root_path": str(root), "repository": remote, "package_name": package_name})
    memory["context"] = {key: context[key] for key in ("path", "sha256", "schema_version", "generated_at")}
    memory["freshness"] = {"status": status, "checked_at": now(), "context_hash": context["sha256"], "project_fingerprint": current_fingerprint, "reason": reason}
    return with_integrity(memory)


def emit(value: Any, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return
    if isinstance(value, dict):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(value)


def cmd_init(args: argparse.Namespace) -> int:
    root, path = project_root(args), memory_path(args, project_root(args))
    if path.exists() and not args.force:
        print(f"Project Memory already exists: {path}. Use --force only to replace it.", file=sys.stderr)
        return EXIT_USAGE
    memory = base_memory(root, args.context_path)
    write_atomic(path, memory)
    emit({"status": "created", "memory_path": str(path), "freshness": memory["freshness"], "project_id": memory["project"]["project_id"]}, args.json)
    return EXIT_OK


def cmd_inspect(args: argparse.Namespace) -> int:
    root = project_root(args)
    path = memory_path(args, root)
    memory = load_or_fail(path)
    emit(memory, args.json)
    return EXIT_OK


def cmd_validate(args: argparse.Namespace) -> int:
    root = project_root(args)
    path = memory_path(args, root)
    memory = load_or_fail(path)
    current_id, _, _ = project_identity(root)
    errors = invariant_errors(memory)
    if current_id != memory["project"].get("project_id"):
        errors.append(f"project.identity-mismatch:{current_id}")
    result = {"status": "pass" if not errors else "fail", "memory_path": str(path), "project_id": memory["project"].get("project_id"), "freshness": memory["freshness"], "errors": errors}
    emit(result, args.json)
    return EXIT_OK if not errors else EXIT_INVALID


def cmd_refresh(args: argparse.Namespace) -> int:
    root = project_root(args)
    path = memory_path(args, root)
    memory = load_or_fail(path)
    try:
        refreshed = refresh_memory(memory, root, args.context_path)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return EXIT_INVALID
    write_atomic(path, refreshed)
    emit({"status": refreshed["freshness"]["status"], "memory_path": str(path), "freshness": refreshed["freshness"]}, args.json)
    return EXIT_STALE if refreshed["freshness"]["status"] == "stale" else EXIT_OK


def cmd_recover(args: argparse.Namespace) -> int:
    root = project_root(args)
    path = memory_path(args, root)
    memory = load_or_fail(path)
    current_id, _, _ = project_identity(root)
    if current_id != memory["project"].get("project_id"):
        print(json.dumps({"status": "invalid", "memory_path": str(path), "error": "project identity mismatch", "expected": current_id, "recorded": memory["project"].get("project_id")}, ensure_ascii=False), file=sys.stderr)
        return EXIT_INVALID
    project = memory["project"]
    current_remote = git_remote(root)
    current_package = (read_json(root / "package.json") or {}).get("name")
    runtime_changed = (
        project.get("root_path") != str(root)
        or project.get("repository") != current_remote
        or project.get("package_name") != current_package
    )
    if runtime_changed:
        project.update({"root_path": str(root), "repository": current_remote, "package_name": current_package})
        write_atomic(path, with_integrity(memory))
    freshness = memory["freshness"]
    recovery = {
        "status": freshness["status"],
        "memory_path": str(path),
        "project": memory["project"],
        "context": memory["context"],
        "motion_principles": memory["motion_principles"],
        "policies": memory["policies"],
        "decisions": memory["decisions"][-args.limit :],
        "rejected_patterns": memory["rejected_patterns"][-args.limit :],
        "remediation": memory["remediation"][-args.limit :],
        "freshness": freshness,
        "recovery": memory["recovery"],
        "instructions": [
            "Treat this memory as project context, not as user approval.",
            "If status is stale or needs_context, refresh/analyze before generating animation.",
            "Revalidate source, manifest, runtime and task bindings before reusing artifacts.",
        ],
    }
    emit(recovery, True)
    return EXIT_STALE if freshness["status"] == "stale" else EXIT_OK


def save_entry(args: argparse.Namespace, kind: str) -> int:
    root = project_root(args)
    path = memory_path(args, root)
    memory = load_or_fail(path)
    if kind == "outcome" and not args.user_confirmed:
        print("record-outcome requires --user-confirmed; unreviewed outcomes are not durable learning signals", file=sys.stderr)
        return EXIT_USAGE
    recorded = now()
    source_task = args.source_task_id
    if kind == "decision":
        entry = {"id": args.id, "recorded_at": recorded, "status": args.status, "summary": args.summary, "rationale": args.rationale or "", "user_confirmed": bool(args.user_confirmed), "source_task_id": source_task, "evidence": args.evidence or []}
        memory["decisions"].append(entry)
        if args.status == "rejected":
            memory["rejected_patterns"].append({"id": args.id, "recorded_at": recorded, "pattern": args.summary, "reason": args.rationale or "", "source_task_id": source_task})
    else:
        entry = {"id": args.id, "recorded_at": recorded, "issue_id": args.issue_id, "summary": args.summary, "root_cause": args.root_cause or "", "resolution": args.resolution or "", "result": args.result, "correction_count": args.correction_count, "rerun_scope": args.rerun_scope or [], "user_confirmed": bool(args.user_confirmed), "source_task_id": source_task}
        memory["remediation"].append(entry)
    memory["updated_at"] = recorded
    memory["recovery"]["next_actions"] = ["Revalidate current context before the next animation task.", "Use the recorded scope to avoid rerunning unrelated scenes."]
    write_atomic(path, with_integrity(memory))
    emit({"status": "recorded", "kind": kind, "id": args.id, "memory_path": str(path), "user_confirmed": bool(args.user_confirmed)}, args.json)
    return EXIT_OK


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", default=".", help="Host project root; defaults to current directory")
    parser.add_argument("--memory-path", help="Memory path, relative to project root by default")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MotionLoom durable Project Memory")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a relocatable project memory")
    add_common(init); init.add_argument("--context-path"); init.add_argument("--force", action="store_true"); init.add_argument("--json", action="store_true"); init.set_defaults(func=cmd_init)
    for name, func in (("inspect", cmd_inspect), ("validate", cmd_validate)):
        item = sub.add_parser(name, help=f"{name.title()} the project memory")
        add_common(item); item.add_argument("--json", action="store_true"); item.set_defaults(func=func)
    refresh = sub.add_parser("refresh", help="Refresh context and dependency freshness")
    add_common(refresh); refresh.add_argument("--context-path"); refresh.add_argument("--json", action="store_true"); refresh.set_defaults(func=cmd_refresh)
    recover = sub.add_parser("recover", help="Emit a compact Agent recovery payload")
    add_common(recover); recover.add_argument("--limit", type=int, default=10); recover.set_defaults(func=cmd_recover)
    decision = sub.add_parser("record-decision", help="Persist a project motion decision")
    add_common(decision); decision.add_argument("--id", required=True); decision.add_argument("--summary", required=True); decision.add_argument("--rationale"); decision.add_argument("--status", choices=["accepted", "rejected", "superseded"], required=True); decision.add_argument("--source-task-id"); decision.add_argument("--evidence", action="append"); decision.add_argument("--user-confirmed", action="store_true"); decision.add_argument("--json", action="store_true"); decision.set_defaults(func=lambda args: save_entry(args, "decision"))
    outcome = sub.add_parser("record-outcome", help="Persist a user-confirmed remediation outcome")
    add_common(outcome); outcome.add_argument("--id", required=True); outcome.add_argument("--issue-id", required=True); outcome.add_argument("--summary", required=True); outcome.add_argument("--root-cause"); outcome.add_argument("--resolution"); outcome.add_argument("--result", choices=["pass", "fail", "partial", "unknown"], required=True); outcome.add_argument("--correction-count", type=int, default=0); outcome.add_argument("--rerun-scope", action="append"); outcome.add_argument("--source-task-id"); outcome.add_argument("--user-confirmed", action="store_true"); outcome.add_argument("--json", action="store_true"); outcome.set_defaults(func=lambda args: save_entry(args, "outcome"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return EXIT_OK
    except ValueError as error:
        print(f"MotionLoom memory contract error: {error}", file=sys.stderr)
        return EXIT_INVALID
    except OSError as error:
        print(f"MotionLoom memory I/O error: {error}", file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    raise SystemExit(main())
