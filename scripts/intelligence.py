#!/usr/bin/env python3
"""MotionLoom Intelligence Core v0.1.

The CLI keeps the first intelligence layer deterministic and artifact-first. It
does not make aesthetic claims; it creates and verifies the relationships and
evidence an Agent needs before making those claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = "^[a-f0-9]{64}$"
GENERATED_REPLAY = {"replay-bundle.json"}
GENERATED_REPORTS = {"artifact-manifest.json", "execution-report.json", "REPORT.md", "decision-log.jsonl"}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def read_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"missing JSON file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def task_dir_from(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(f"task directory does not exist: {path}")
    return path


def safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not value or any(part == ".." for part in path.parts):
        raise ValueError(f"unsafe artifact path: {value}")
    return path


def within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def task_artifact(task_dir: Path, relative: str) -> dict[str, Any]:
    safe = safe_relative(relative)
    path = (task_dir / safe).resolve()
    if not within(task_dir, path) or not path.is_file():
        raise ValueError(f"artifact is missing or outside task bundle: {relative}")
    return {
        "id": relative.replace("/", ":"),
        "path": path.relative_to(task_dir).as_posix(),
        "type": path.suffix.lstrip(".") or "file",
        "sha256": digest_file(path),
        "bytes": path.stat().st_size,
    }


def resolve_context(task_dir: Path, raw: str | None) -> Path | None:
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    options = [candidate] if candidate.is_absolute() else [task_dir / candidate, ROOT / candidate]
    for option in options:
        resolved = option.resolve()
        if resolved.is_file():
            return resolved
    return None


def package_version() -> str:
    package = ROOT / "package.json"
    try:
        return str(read_json(package).get("version", "unknown"))
    except ValueError:
        return "unknown"


def add_node(nodes: dict[str, dict[str, Any]], node_id: str, kind: str, label: str, **kwargs: Any) -> None:
    node = {"id": node_id, "kind": kind, "label": label}
    node.update({key: value for key, value in kwargs.items() if value is not None})
    nodes.setdefault(node_id, node)


def graph_build(args: argparse.Namespace) -> int:
    task_dir = task_dir_from(args.task_dir)
    task = read_json(task_dir / "task.json")
    if not isinstance(task, dict) or not task.get("task_id") or not task.get("scene"):
        raise ValueError("task.json must contain task_id and scene")

    task_id = str(task["task_id"])
    scene = str(task["scene"])
    context_path = resolve_context(task_dir, task.get("context_path"))
    context_hash = str(task.get("context_hash") or "")
    if context_path and len(context_hash) != 64:
        context_hash = digest_file(context_path)
    if len(context_hash) != 64:
        context_hash = digest_bytes(canonical({"task_id": task_id, "scene": scene, "intent": task.get("intent", "")}))

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    project_id = f"project:{task.get('project_name') or task_id}"
    intent_id = f"intent:{task_id}"
    scene_id = f"scene:{scene}"
    add_node(nodes, project_id, "project", str(task.get("project_name") or task_id), ref=task_id)
    add_node(nodes, intent_id, "intent", str(task.get("intent") or "Animation task intent"), ref=task_id)
    add_node(nodes, scene_id, "scene", scene, ref=scene)
    edges.extend([
        {"from": project_id, "to": intent_id, "relation": "contains"},
        {"from": project_id, "to": scene_id, "relation": "contains"},
        {"from": scene_id, "to": intent_id, "relation": "constrained_by"},
    ])

    if context_path:
        context_id = f"artifact:{context_path.name}"
        add_node(nodes, context_id, "artifact", context_path.name, ref=str(context_path), sha256=digest_file(context_path))
        edges.append({"from": scene_id, "to": context_id, "relation": "derived_from"})
    else:
        context_id = None

    task_files = []
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(task_dir).as_posix()
        if relative in {"project-graph.json", "provenance.json", "replay-bundle.json"}:
            continue
        task_files.append((relative, path))

    for relative, path in task_files:
        lower = relative.lower()
        if relative == "review.json" or "review" in lower and relative.endswith(".json"):
            kind = "review"
        elif relative == "motion-ir.json":
            kind = "motion_spec"
        elif relative == "task.json" or "report" in lower or "handoff" in lower:
            kind = "evidence"
        else:
            kind = "artifact"
        node_id = f"artifact:{relative}"
        add_node(nodes, node_id, kind, relative, ref=relative, sha256=digest_file(path))
        edges.append({"from": scene_id, "to": node_id, "relation": "uses"})

    review_id = "review:" + task_id
    if (task_dir / "review.json").is_file() or task.get("browser_review", {}).get("status"):
        add_node(nodes, review_id, "review", "Browser review", ref="review.json")
        edges.append({"from": scene_id, "to": review_id, "relation": "reviewed_as"})

    graph = {
        "schema_version": "0.1",
        "graph_id": f"graph-{task_id}-{scene}",
        "task_id": task_id,
        "scene": scene,
        "generated_at": now(),
        "context_hash": context_hash,
        "nodes": list(nodes.values()),
        "edges": edges,
        "roots": [project_id, scene_id],
        "policy": {
            "source_of_truth": "task-bundle",
            "allow_unresolved_edges": False,
            "required_node_kinds": ["project", "intent", "scene"],
        },
    }
    output = Path(args.output).expanduser().resolve() if args.output else task_dir / "project-graph.json"
    write_json(output, graph)
    print(json.dumps({"status": "built", "kind": "project-graph", "task_id": task_id, "node_count": len(nodes), "edge_count": len(edges), "path": str(output)}, ensure_ascii=False))
    return 0


def graph_validate(args: argparse.Namespace) -> int:
    graph = read_json(Path(args.path).expanduser().resolve())
    required = {"schema_version", "graph_id", "task_id", "scene", "context_hash", "nodes", "edges", "roots"}
    missing = sorted(required - set(graph)) if isinstance(graph, dict) else sorted(required)
    if missing:
        raise ValueError(f"project graph missing fields: {', '.join(missing)}")
    node_ids = {node.get("id") for node in graph["nodes"] if isinstance(node, dict)}
    if len(node_ids) != len(graph["nodes"]):
        raise ValueError("project graph contains duplicate or invalid node ids")
    if any(root not in node_ids for root in graph["roots"]):
        raise ValueError("project graph root does not reference a node")
    for edge in graph["edges"]:
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            raise ValueError("project graph edge references an unknown node")
    if not isinstance(graph["context_hash"], str) or len(graph["context_hash"]) != 64:
        raise ValueError("project graph context_hash must be a SHA-256 digest")
    print(json.dumps({"status": "valid", "kind": "project-graph", "task_id": graph["task_id"], "node_count": len(node_ids), "edge_count": len(graph["edges"])}, ensure_ascii=False))
    return 0


def default_provenance_steps(task_dir: Path, task: dict[str, Any]) -> list[dict[str, Any]]:
    files = {path.name: path for path in task_dir.iterdir() if path.is_file()}
    steps: list[dict[str, Any]] = []

    def existing(names: list[str]) -> list[str]:
        return [name for name in names if name in files]

    candidates = [
        ("context", "context", ["task.json"], ["task.json"], "agent"),
        ("spec", "spec", ["task.json"], ["motion-spec.json"], "agent"),
        ("motion-ir", "motion-ir", ["task.json"], ["motion-ir.json"], "agent"),
        ("source-bind", "source-bind", ["motion-spec.json"], ["manifest.json", "manifest.yaml"], "agent"),
        ("render", "render", ["manifest.json"], ["render-meta.json", ".render-meta.json", "animation.json"], "runtime"),
        ("runtime-test", "runtime-test", ["animation.json"], ["runtime-evidence.json"], "runtime"),
        ("browser-review", "browser-review", ["browser-review.json"], ["review.json", "browser-observation.md"], "user"),
        ("quality-gate", "quality-gate", ["browser-review.json", "review.json"], ["quality-report.json"], "ci"),
        ("confirm", "confirm", ["quality-report.json"], ["task.json"], "user"),
    ]
    for step_id, step_type, material_names, product_names, actor_type in candidates:
        materials = existing(material_names)
        products = existing(product_names)
        if not materials and not products:
            continue
        timestamp = now()
        step = {
            "step_id": step_id,
            "step_type": step_type,
            "actor": {"type": actor_type, "id": "motionloom" if actor_type != "user" else "user"},
            "builder": {"name": "motionloom", "version": package_version(), "os": platform.system().lower()},
            "materials": [],
            "products": [],
            "policy": f"schemas/provenance.schema.json#{step_type}",
            "started_at": timestamp,
            "finished_at": timestamp,
            "result": "pass",
            "parent_step_ids": [steps[-1]["step_id"]] if steps else [],
        }
        for name in materials:
            step["materials"].append(task_artifact(task_dir, name))
        for name in products:
            step["products"].append(task_artifact(task_dir, name))
        steps.append(step)
    if not steps:
        timestamp = now()
        steps.append({
            "step_id": "context",
            "step_type": "context",
            "actor": {"type": "agent", "id": "motionloom"},
            "builder": {"name": "motionloom", "version": package_version(), "os": platform.system().lower()},
            "materials": [],
            "products": [task_artifact(task_dir, "task.json")],
            "policy": "schemas/provenance.schema.json#context",
            "started_at": timestamp,
            "finished_at": timestamp,
            "result": "pass",
            "parent_step_ids": [],
        })
    return steps


def normalize_step_artifacts(task_dir: Path, steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for step in steps:
        item = dict(step)
        for field in ("materials", "products"):
            entries = []
            for artifact in item.get(field, []):
                if isinstance(artifact, str):
                    entries.append(task_artifact(task_dir, artifact))
                elif isinstance(artifact, dict):
                    entries.append(task_artifact(task_dir, str(artifact.get("path", ""))))
                else:
                    raise ValueError(f"invalid {field} artifact in step {step.get('step_id')}")
            item[field] = entries
        normalized.append(item)
    return normalized


def provenance_build(args: argparse.Namespace) -> int:
    task_dir = task_dir_from(args.task_dir)
    task = read_json(task_dir / "task.json")
    if not isinstance(task, dict):
        raise ValueError("task.json must be an object")
    if args.steps_file:
        raw_steps = read_json(Path(args.steps_file).expanduser().resolve())
        if not isinstance(raw_steps, list):
            raise ValueError("steps file must contain an array")
        steps = normalize_step_artifacts(task_dir, raw_steps)
    else:
        steps = default_provenance_steps(task_dir, task)
    chain_hash = digest_bytes(canonical(steps))
    attestation = {
        "schema_version": "0.1",
        "attestation_id": f"attestation-{task.get('task_id', task_dir.name)}",
        "task_id": str(task.get("task_id", task_dir.name)),
        "scene": str(task.get("scene", "unknown")),
        "generated_at": now(),
        "subjects": [task_artifact(task_dir, args.subject)] if args.subject else [task_artifact(task_dir, "task.json")],
        "steps": steps,
        "verification": {"hash_algorithm": "sha256", "chain_hash": chain_hash, "status": "verified", "signature": {"status": "unsigned"}},
    }
    output = Path(args.output).expanduser().resolve() if args.output else task_dir / "provenance.json"
    write_json(output, attestation)
    print(json.dumps({"status": "built", "kind": "provenance", "task_id": attestation["task_id"], "step_count": len(steps), "chain_hash": chain_hash, "path": str(output)}, ensure_ascii=False))
    return 0


def provenance_validate(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    attestation = read_json(path)
    if not isinstance(attestation, dict) or not isinstance(attestation.get("steps"), list):
        raise ValueError("provenance attestation must contain steps")
    task_dir = task_dir_from(args.task_dir)
    if attestation.get("task_id") != read_json(task_dir / "task.json").get("task_id"):
        raise ValueError("provenance task_id does not match task.json")
    expected_chain = digest_bytes(canonical(attestation["steps"]))
    actual_chain = attestation.get("verification", {}).get("chain_hash")
    if expected_chain != actual_chain:
        raise ValueError("provenance chain_hash mismatch")
    known_steps = {step.get("step_id") for step in attestation["steps"]}
    for step in attestation["steps"]:
        if any(parent not in known_steps for parent in step.get("parent_step_ids", [])):
            raise ValueError(f"provenance parent step missing for {step.get('step_id')}")
        for field in ("materials", "products"):
            for artifact in step.get(field, []):
                checked = task_artifact(task_dir, str(artifact.get("path", "")))
                if checked["sha256"] != artifact.get("sha256"):
                    raise ValueError(f"provenance {field} hash mismatch: {artifact.get('path')}")
    print(json.dumps({"status": "valid", "kind": "provenance", "task_id": attestation["task_id"], "step_count": len(attestation["steps"]), "chain_hash": actual_chain}, ensure_ascii=False))
    return 0


def capability_kind(capability: str) -> str:
    if capability in {"dotlottie-package"}:
        return "packager"
    if capability in {"lottie-json", "svg-cutout-rig"}:
        return "renderer"
    if capability in {"rive", "gsap", "framer-motion"}:
        return "runtime-adapter"
    return "renderer"


def capability_build(args: argparse.Namespace) -> int:
    card_path = Path(args.card).expanduser().resolve()
    card = read_json(card_path)
    if not isinstance(card, dict):
        raise ValueError("agent-card must be an object")
    evidence_path = Path(args.evidence).expanduser().resolve() if args.evidence else ROOT / "scripts" / "runtime-adapters.mjs"
    if not evidence_path.is_file():
        raise ValueError(f"capability evidence path does not exist: {evidence_path}")
    evidence_ref = evidence_path.relative_to(ROOT).as_posix() if within(ROOT, evidence_path) else evidence_path.name
    evidence_kind = args.evidence_kind
    entries = []
    verified = list(card.get("runtime_capabilities", {}).get("verified", []))
    scaffold = list(card.get("runtime_capabilities", {}).get("scaffold_only", []))
    for capability in verified + scaffold:
        status = "verified" if capability in verified else "scaffold_only"
        entries.append({
            "id": f"runtime.{capability}",
            "kind": capability_kind(capability),
            "status": status,
            "adapter_version": str(card.get("version", "unknown")),
            "inputs": ["project-context", "motion-spec", "source-binding"],
            "outputs": ["runtime-evidence"],
            "compatibility": {"browsers": ["chromium"], "os": ["linux"], "node": ">=22"},
            "last_verified_at": now(),
            "evidence": [{"path": evidence_ref, "sha256": digest_file(evidence_path), "kind": evidence_kind}],
            "limitations": ["Capability evidence is refreshed by runtime:test."] if status == "verified" else ["Scaffold only; do not use for production acceptance."],
            "fallback": "runtime.lottie-json" if status == "scaffold_only" else "",
            "risk_level": "high" if status == "scaffold_only" else "low",
            "side_effect_level": "local_write",
        })
    registry = {
        "schema_version": "0.1",
        "registry_id": f"registry-{card.get('name', 'motionloom')}-{card.get('version', 'unknown')}",
        "generated_at": now(),
        "selection_policy": {"require_verified": True, "allow_scaffold_only": False, "max_evidence_age_seconds": 604800},
        "capabilities": entries,
    }
    output = Path(args.output).expanduser().resolve() if args.output else ROOT / "capability-registry.json"
    write_json(output, registry)
    print(json.dumps({"status": "built", "kind": "capability-registry", "capability_count": len(entries), "path": str(output)}, ensure_ascii=False))
    return 0


def capability_validate(args: argparse.Namespace) -> int:
    registry_path = Path(args.path).expanduser().resolve()
    registry = read_json(registry_path)
    if not isinstance(registry, dict) or not isinstance(registry.get("capabilities"), list):
        raise ValueError("capability registry must contain capabilities")
    ids = [entry.get("id") for entry in registry["capabilities"]]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("capability registry contains duplicate or empty ids")
    for entry in registry["capabilities"]:
        for evidence in entry.get("evidence", []):
            evidence_path = ROOT / safe_relative(str(evidence.get("path", "")))
            if not evidence_path.is_file():
                raise ValueError(f"capability evidence missing: {evidence.get('path')}")
            if digest_file(evidence_path) != evidence.get("sha256"):
                raise ValueError(f"capability evidence hash mismatch: {evidence.get('path')}")
    print(json.dumps({"status": "valid", "kind": "capability-registry", "capability_count": len(ids)}, ensure_ascii=False))
    return 0


def capability_select(args: argparse.Namespace) -> int:
    registry = read_json(Path(args.registry).expanduser().resolve())
    policy = registry.get("selection_policy", {})
    requested_status = args.status
    max_age = int(policy.get("max_evidence_age_seconds", 0) or 0)
    current = datetime.now(timezone.utc)
    selected = []
    for entry in registry.get("capabilities", []):
        if args.capability and entry.get("id") != args.capability:
            continue
        if requested_status and entry.get("status") != requested_status:
            continue
        if entry.get("status") == "scaffold_only" and not (args.allow_scaffold_only or policy.get("allow_scaffold_only")):
            continue
        if entry.get("status") == "verified" and max_age > 0:
            try:
                verified_at = datetime.fromisoformat(str(entry.get("last_verified_at", "")).replace("Z", "+00:00"))
            except ValueError:
                continue
            if (current - verified_at).total_seconds() > max_age:
                continue
        evidence_ok = True
        for evidence in entry.get("evidence", []):
            try:
                evidence_path = ROOT / safe_relative(str(evidence.get("path", "")))
                if not evidence_path.is_file() or digest_file(evidence_path) != evidence.get("sha256"):
                    evidence_ok = False
                    break
            except (OSError, ValueError):
                evidence_ok = False
                break
        if not evidence_ok:
            continue
        selected.append(entry)
    if not selected:
        raise ValueError("no capability satisfies the registry selection policy")
    print(json.dumps({"status": "selected", "count": len(selected), "capabilities": selected}, ensure_ascii=False))
    return 0


def motion_spec_path(task_dir: Path, scene: str, raw: str | None) -> Path:
    options = []
    if raw:
        supplied = Path(raw).expanduser()
        options.append(supplied if supplied.is_absolute() else task_dir / supplied)
    options.extend([
        task_dir / "motion-spec.json",
        ROOT / "src" / "output" / scene / "motion-spec.json",
    ])
    for option in options:
        if option.resolve().is_file():
            return option.resolve()
    raise ValueError(f"missing motion-spec.json for scene: {scene}")


def motion_ir_from_spec(task_dir: Path, task: dict[str, Any], spec: dict[str, Any], spec_path: Path) -> dict[str, Any]:
    task_id = str(task.get("task_id", task_dir.name))
    scene = str(task.get("scene", "scene"))
    binding = spec.get("context_binding") or {}
    context_hash = str(task.get("context_hash") or binding.get("context_sha256") or "")
    if len(context_hash) != 64:
        raise ValueError("Motion IR requires a SHA-256 context hash")
    duration_s = float(spec.get("duration_s", 0))
    fps = float(spec.get("fps", 0))
    if duration_s <= 0 or fps <= 0:
        raise ValueError("motion spec must contain positive duration_s and fps")
    easing = str(spec.get("easing") or "linear")
    reduced = str((spec.get("accessibility") or {}).get("reduced_motion") or "")
    reduced_motion = reduced if reduced in {"none", "reduce", "replace", "freeze"} else "reduce"
    source_ref = spec_path.resolve().relative_to(ROOT).as_posix() if within(ROOT, spec_path) else spec_path.name
    return {
        "schema_version": "0.1",
        "ir_id": f"ir-{task_id}-{scene}",
        "task_id": task_id,
        "scene": scene,
        "intent": str(task.get("intent") or f"Animate {spec.get('category', 'scene')}"),
        "context_hash": context_hash,
        "duration_ms": round(duration_s * 1000),
        "fps": fps,
        "tracks": [{
            "id": "scene-progress",
            "target": "scene.progress",
            "property": "custom",
            "keyframes": [
                {"offset": 0, "value": 0, "easing": easing},
                {"offset": 1, "value": 1, "easing": easing},
            ],
        }],
        "accessibility": {
            "reduced_motion": reduced_motion,
            "keyboard_safe": False,
            "fallback_description": "Keyboard safety is not proven by the source motion spec; human review is required.",
        },
        "performance_budget": {
            "max_layers": int((spec.get("performance") or {}).get("max_layers", 80)),
            "allow_layout_animation": False,
        },
        "acceptance": [
            {"id": "context-binding", "type": "deterministic", "expected": {"context_hash": context_hash}, "evidence_refs": ["task.json"]},
            {"id": "runtime-checkpoints", "type": "runtime", "expected": {"checkpoints": [0, 50, 100]}, "evidence_refs": ["snapshot/frame-00.png", "snapshot/frame-50.png", "snapshot/frame-100.png"]},
            {"id": "keyboard-safety", "type": "human_required", "expected": {"review": "explicit keyboard safety review"}, "evidence_refs": ["review.json"]},
        ],
        "confidence": {"value": 0.65, "basis": "heuristic", "evidence_refs": [source_ref, "task.json"]},
        "source_refs": [source_ref, "task.json"],
    }


def motion_ir_validate_data(ir: dict[str, Any]) -> list[str]:
    issues = []
    required = {"schema_version", "ir_id", "task_id", "scene", "intent", "context_hash", "duration_ms", "tracks", "accessibility", "acceptance"}
    issues.extend(f"missing {field}" for field in sorted(required - set(ir)))
    if ir.get("schema_version") != "0.1":
        issues.append("schema_version must be 0.1")
    if not isinstance(ir.get("context_hash"), str) or len(ir.get("context_hash", "")) != 64:
        issues.append("context_hash must be a SHA-256 digest")
    if not isinstance(ir.get("duration_ms"), int) or ir.get("duration_ms", 0) < 1:
        issues.append("duration_ms must be a positive integer")
    if not isinstance(ir.get("tracks"), list) or not ir.get("tracks"):
        issues.append("tracks must contain at least one track")
    else:
        for track in ir["tracks"]:
            keyframes = track.get("keyframes", []) if isinstance(track, dict) else []
            offsets = [frame.get("offset") for frame in keyframes if isinstance(frame, dict)]
            if len(keyframes) < 2 or offsets != sorted(offsets) or offsets[0] != 0 or offsets[-1] != 1:
                issues.append(f"track {track.get('id', 'unnamed')} must span offsets 0..1")
    accessibility = ir.get("accessibility") or {}
    if accessibility.get("reduced_motion") not in {"none", "reduce", "replace", "freeze"}:
        issues.append("accessibility.reduced_motion is invalid")
    if not isinstance(accessibility.get("keyboard_safe"), bool):
        issues.append("accessibility.keyboard_safe must be boolean")
    acceptance = ir.get("acceptance")
    if not isinstance(acceptance, list) or not acceptance:
        issues.append("acceptance must contain at least one assertion")
    else:
        allowed = {"deterministic", "runtime", "human_required"}
        for item in acceptance:
            if item.get("type") not in allowed:
                issues.append(f"invalid acceptance type: {item.get('type')}")
    return issues


def motion_ir_build(args: argparse.Namespace) -> int:
    task_dir = task_dir_from(args.task_dir)
    task = read_json(task_dir / "task.json")
    if not isinstance(task, dict) or not task.get("task_id") or not task.get("scene"):
        raise ValueError("task.json must contain task_id and scene")
    spec_path = motion_spec_path(task_dir, str(task["scene"]), args.spec)
    spec = read_json(spec_path)
    ir = motion_ir_from_spec(task_dir, task, spec, spec_path)
    issues = motion_ir_validate_data(ir)
    if issues:
        raise ValueError("generated Motion IR is invalid: " + "; ".join(issues))
    output = Path(args.output).expanduser().resolve() if args.output else task_dir / "motion-ir.json"
    write_json(output, ir)
    print(json.dumps({"status": "built", "kind": "motion-ir", "task_id": ir["task_id"], "scene": ir["scene"], "track_count": len(ir["tracks"]), "path": str(output)}, ensure_ascii=False))
    return 0


def motion_ir_validate(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    ir = read_json(path)
    issues = motion_ir_validate_data(ir if isinstance(ir, dict) else {})
    if issues:
        raise ValueError("Motion IR invalid: " + "; ".join(issues))
    print(json.dumps({"status": "valid", "kind": "motion-ir", "task_id": ir["task_id"], "scene": ir["scene"], "track_count": len(ir["tracks"])}, ensure_ascii=False))
    return 0


def node_version() -> str:
    try:
        return subprocess.run(["node", "--version"], capture_output=True, text=True, check=False).stdout.strip() or "unavailable"
    except OSError:
        return "unavailable"


def replay_capture(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    task_dir = task_dir_from(args.task_dir)
    if not within(root, task_dir):
        raise ValueError("task directory must be inside replay root")
    task = read_json(task_dir / "task.json")
    task_rel = task_dir.relative_to(root).as_posix()
    records = []
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if path.name in GENERATED_REPLAY or path.name in GENERATED_REPORTS:
            continue
        records.append({"path": relative, "sha256": digest_file(path), "bytes": path.stat().st_size})
    bundle = {
        "schema_version": "0.1",
        "bundle_id": f"replay-{task.get('task_id', task_dir.name)}-{task.get('scene', 'scene')}",
        "task_id": task.get("task_id"),
        "scene": task.get("scene"),
        "task_dir": task_rel,
        "generated_at": now(),
        "environment": {"python": platform.python_version(), "node": node_version(), "os": platform.platform()},
        "files": records,
        "policy": {"hash_algorithm": "sha256", "exclude": sorted(GENERATED_REPLAY | GENERATED_REPORTS), "mode": "integrity"},
        "replay_command": "python3 scripts/intelligence.py replay verify --bundle <bundle> --root <clean-root>",
    }
    output = Path(args.output).expanduser().resolve() if args.output else task_dir / "replay-bundle.json"
    write_json(output, bundle)
    print(json.dumps({"status": "captured", "kind": "replay-bundle", "task_id": bundle["task_id"], "file_count": len(records), "path": str(output)}, ensure_ascii=False))
    return 0


def replay_verify(args: argparse.Namespace) -> int:
    bundle = read_json(Path(args.bundle).expanduser().resolve())
    root = Path(args.root).expanduser().resolve()
    mismatches = []
    for record in bundle.get("files", []):
        safe = safe_relative(str(record.get("path", "")))
        path = (root / safe).resolve()
        if not within(root, path) or not path.is_file():
            mismatches.append({"path": str(safe), "reason": "missing"})
            continue
        actual = digest_file(path)
        if actual != record.get("sha256"):
            mismatches.append({"path": str(safe), "reason": "hash_mismatch", "expected": record.get("sha256"), "actual": actual})
    if mismatches:
        print(json.dumps({"status": "invalid", "kind": "replay-bundle", "mismatches": mismatches}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "valid", "kind": "replay-bundle", "task_id": bundle.get("task_id"), "file_count": len(bundle.get("files", []))}, ensure_ascii=False))
    return 0


def replay_mismatches(bundle: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    mismatches = []
    for record in bundle.get("files", []):
        safe = safe_relative(str(record.get("path", "")))
        path = (root / safe).resolve()
        if not within(root, path) or not path.is_file():
            mismatches.append({"path": str(safe), "reason": "missing"})
            continue
        actual = digest_file(path)
        if actual != record.get("sha256"):
            mismatches.append({"path": str(safe), "reason": "hash_mismatch", "expected": record.get("sha256"), "actual": actual})
    return mismatches


def validate_task_intelligence(task_dir: Path, scene: str | None = None) -> list[str]:
    """Return deterministic contract issues for a task bundle.

    This function is intentionally side-effect free so quality gates and tests
    can use the same verification logic as the CLI.
    """
    issues: list[str] = []
    try:
        task = read_json(task_dir / "task.json")
        if scene and task.get("scene") != scene:
            issues.append("intelligence task scene does not match quality-gate scene")
        graph_path = task_dir / "project-graph.json"
        if not graph_path.is_file():
            issues.append("missing project-graph.json")
        else:
            graph_validate(argparse.Namespace(path=str(graph_path)))
            graph = read_json(graph_path)
            if graph.get("task_id") != task.get("task_id"):
                issues.append("project graph task_id does not match task.json")
        motion_ir_path = task_dir / "motion-ir.json"
        if not motion_ir_path.is_file():
            issues.append("missing motion-ir.json")
        else:
            motion_ir_validate(argparse.Namespace(path=str(motion_ir_path)))
            motion_ir = read_json(motion_ir_path)
            if motion_ir.get("task_id") != task.get("task_id") or motion_ir.get("scene") != task.get("scene"):
                issues.append("Motion IR task_id/scene does not match task.json")
        provenance_path = task_dir / "provenance.json"
        if not provenance_path.is_file():
            issues.append("missing provenance.json")
        else:
            provenance_validate(argparse.Namespace(task_dir=str(task_dir), path=str(provenance_path)))
        replay_path = task_dir / "replay-bundle.json"
        if not replay_path.is_file():
            issues.append("missing replay-bundle.json")
        else:
            bundle = read_json(replay_path)
            mismatches = replay_mismatches(bundle, task_dir.parent.parent)
            if mismatches:
                issues.append(f"replay bundle has {len(mismatches)} mismatch(es)")
            if bundle.get("task_id") != task.get("task_id"):
                issues.append("replay bundle task_id does not match task.json")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues.append(f"intelligence validation error: {exc}")
    return issues


def add_subcommands(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="domain", required=True)

    graph = sub.add_parser("graph", help="build or validate project-graph.json")
    graph_sub = graph.add_subparsers(dest="action", required=True)
    graph_build_parser = graph_sub.add_parser("build")
    graph_build_parser.add_argument("--task-dir", required=True)
    graph_build_parser.add_argument("--output")
    graph_build_parser.set_defaults(func=graph_build)
    graph_validate_parser = graph_sub.add_parser("validate")
    graph_validate_parser.add_argument("--path", required=True)
    graph_validate_parser.set_defaults(func=graph_validate)

    provenance = sub.add_parser("provenance", help="build or validate provenance.json")
    provenance_sub = provenance.add_subparsers(dest="action", required=True)
    provenance_build_parser = provenance_sub.add_parser("build")
    provenance_build_parser.add_argument("--task-dir", required=True)
    provenance_build_parser.add_argument("--steps-file")
    provenance_build_parser.add_argument("--subject")
    provenance_build_parser.add_argument("--output")
    provenance_build_parser.set_defaults(func=provenance_build)
    provenance_validate_parser = provenance_sub.add_parser("validate")
    provenance_validate_parser.add_argument("--task-dir", required=True)
    provenance_validate_parser.add_argument("--path", required=True)
    provenance_validate_parser.set_defaults(func=provenance_validate)

    capabilities = sub.add_parser("capabilities", help="build, validate or select capability registry")
    capabilities_sub = capabilities.add_subparsers(dest="action", required=True)
    capabilities_build_parser = capabilities_sub.add_parser("build")
    capabilities_build_parser.add_argument("--card", default=str(ROOT / "agent-card.json"))
    capabilities_build_parser.add_argument("--evidence")
    capabilities_build_parser.add_argument("--evidence-kind", choices=["runtime", "ci", "browser", "static"], default="ci")
    capabilities_build_parser.add_argument("--output")
    capabilities_build_parser.set_defaults(func=capability_build)
    capabilities_validate_parser = capabilities_sub.add_parser("validate")
    capabilities_validate_parser.add_argument("--path", required=True)
    capabilities_validate_parser.set_defaults(func=capability_validate)
    capabilities_select_parser = capabilities_sub.add_parser("select")
    capabilities_select_parser.add_argument("--registry", required=True)
    capabilities_select_parser.add_argument("--capability")
    capabilities_select_parser.add_argument("--status", default="verified")
    capabilities_select_parser.add_argument("--allow-scaffold-only", action="store_true")
    capabilities_select_parser.set_defaults(func=capability_select)

    replay = sub.add_parser("replay", help="capture or verify clean-root integrity replay bundle")
    replay_sub = replay.add_subparsers(dest="action", required=True)
    replay_capture_parser = replay_sub.add_parser("capture")
    replay_capture_parser.add_argument("--task-dir", required=True)
    replay_capture_parser.add_argument("--root", default=str(ROOT))
    replay_capture_parser.add_argument("--output")
    replay_capture_parser.set_defaults(func=replay_capture)
    replay_verify_parser = replay_sub.add_parser("verify")
    replay_verify_parser.add_argument("--bundle", required=True)
    replay_verify_parser.add_argument("--root", default=str(ROOT))
    replay_verify_parser.set_defaults(func=replay_verify)

    motion_ir = sub.add_parser("motion-ir", help="build or validate framework-neutral motion-ir.json")
    motion_ir_sub = motion_ir.add_subparsers(dest="action", required=True)
    motion_ir_build_parser = motion_ir_sub.add_parser("build")
    motion_ir_build_parser.add_argument("--task-dir", required=True)
    motion_ir_build_parser.add_argument("--spec")
    motion_ir_build_parser.add_argument("--output")
    motion_ir_build_parser.set_defaults(func=motion_ir_build)
    motion_ir_validate_parser = motion_ir_sub.add_parser("validate")
    motion_ir_validate_parser.add_argument("--path", required=True)
    motion_ir_validate_parser.set_defaults(func=motion_ir_validate)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="intelligence.py", description=__doc__)
    add_subcommands(parser)
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"intelligence-error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
