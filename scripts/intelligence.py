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


def finding(
    finding_id: str,
    rule_id: str,
    category: str,
    severity: str,
    confidence: float,
    basis: str,
    message: str,
    evidence_refs: list[str],
    affected_paths: list[str],
    suggested_action: str = "",
    rationale: str = "",
    approval_blocking: bool = False,
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "rule_id": rule_id,
        "category": category,
        "severity": severity,
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "basis": basis,
        "message": message,
        "rationale": rationale,
        "evidence_refs": evidence_refs,
        "affected_paths": affected_paths,
        "suggested_action": suggested_action,
        "approval_blocking": approval_blocking,
    }


def semantic_lint_data(task_dir: Path, task: dict[str, Any], ir: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    task_id = str(task.get("task_id", task_dir.name))
    scene = str(task.get("scene", ir.get("scene", "scene")))
    evidence_refs = ["task.json", "motion-ir.json", "motion-spec.json"]
    findings: list[dict[str, Any]] = []
    duration_s = float(spec.get("duration_s", 0) or 0)
    fps = float(spec.get("fps", 0) or 0)
    expected_duration_ms = round(duration_s * 1000)
    if expected_duration_ms and ir.get("duration_ms") != expected_duration_ms:
        findings.append(finding(
            "timing-duration-mismatch", "MOTION.TIMING.DURATION", "timing", "error", 0.99, "deterministic",
            "Motion IR duration does not match the source motion spec.", evidence_refs, ["motion-ir.json", "motion-spec.json"],
            "Rebuild Motion IR from the bound motion-spec.json before rendering.",
            f"Expected {expected_duration_ms} ms from duration_s={duration_s}; received {ir.get('duration_ms')}.", True,
        ))
    if fps and float(ir.get("fps", 0) or 0) != fps:
        findings.append(finding(
            "timing-fps-mismatch", "MOTION.TIMING.FPS", "timing", "error", 0.99, "deterministic",
            "Motion IR FPS does not match the source motion spec.", evidence_refs, ["motion-ir.json", "motion-spec.json"],
            "Rebuild Motion IR from the bound motion-spec.json before rendering.",
            f"Expected fps={fps}; received {ir.get('fps')}.", True,
        ))

    intent = str(ir.get("intent", "")).strip().lower()
    generic_intents = {"animation task intent", "animate scene", "animate loading", "motion"}
    if not intent:
        findings.append(finding(
            "intent-missing", "MOTION.INTENT.PRESENT", "intent", "error", 0.99, "deterministic",
            "Motion IR has no usable intent statement.", ["motion-ir.json", "task.json"], ["motion-ir.json"],
            "Populate task intent with the user-visible motion outcome and rebuild Motion IR.",
            "Semantic lint cannot compare behavior to an absent intent.", True,
        ))
    elif intent in generic_intents or len(intent.split()) < 2:
        findings.append(finding(
            "intent-low-specificity", "MOTION.INTENT.SPECIFIC", "intent", "warning", 0.86, "heuristic",
            "Motion intent is too generic to support reliable semantic review.", ["motion-ir.json", "task.json"], ["motion-ir.json", "task.json"],
            "Rewrite intent as observable behavior, trigger and user-facing outcome.",
            "A generic label can pass structural validation while still causing the Agent to select the wrong motion treatment.", False,
        ))

    known_easings = {"linear", "ease-in", "ease-out", "ease-in-out", "spring", "step-start", "step-end"}
    for track in ir.get("tracks", []):
        for index, keyframe in enumerate(track.get("keyframes", [])):
            easing = keyframe.get("easing")
            if easing and str(easing).lower() not in known_easings:
                findings.append(finding(
                    f"easing-unknown-{track.get('id', 'track')}-{index}", "MOTION.EASING.KNOWN", "easing", "warning", 0.92, "deterministic",
                    f"Track {track.get('id', 'unnamed')} uses an easing not covered by the canonical registry.", ["motion-ir.json"], ["motion-ir.json"],
                    "Map the easing to a canonical name or document the runtime-specific curve in the adapter contract.",
                    f"Unknown easing: {easing}.", False,
                ))

    accessibility = ir.get("accessibility") or {}
    reduced_motion = accessibility.get("reduced_motion")
    if reduced_motion not in {"reduce", "replace", "freeze"}:
        findings.append(finding(
            "accessibility-reduced-motion", "MOTION.A11Y.REDUCED_MOTION", "accessibility", "error", 0.98, "deterministic",
            "Motion IR does not declare a reduced-motion behavior that the runtime can enforce.", ["motion-ir.json", "motion-spec.json"], ["motion-ir.json", "motion-spec.json"],
            "Declare reduce, replace or freeze behavior and verify it in runtime evidence.",
            "A missing or none policy leaves high-motion behavior without an explicit fallback.", True,
        ))
    if accessibility.get("keyboard_safe") is False:
        findings.append(finding(
            "accessibility-keyboard-review", "MOTION.A11Y.KEYBOARD_REVIEW", "accessibility", "warning", 0.97, "human",
            "Keyboard safety is not proven by the current Motion IR and remains a human-review item.", ["motion-ir.json", "review.json"], ["motion-ir.json", "review.json"],
            "Keep the human-required acceptance assertion and record the reviewer decision in review.json.",
            "The linter does not infer keyboard safety from animation data.", False,
        ))

    budget = ir.get("performance_budget") or {}
    max_tracks = budget.get("max_tracks")
    if isinstance(max_tracks, int) and len(ir.get("tracks", [])) > max_tracks:
        findings.append(finding(
            "performance-track-budget", "MOTION.PERF.MAX_TRACKS", "performance", "error", 0.99, "deterministic",
            "Motion IR exceeds its declared track budget.", ["motion-ir.json"], ["motion-ir.json"],
            "Reduce track count or update the budget with project-context evidence and a reviewed reason.",
            f"Track count={len(ir.get('tracks', []))}; max_tracks={max_tracks}.", True,
        ))
    if not ir.get("acceptance"):
        findings.append(finding(
            "acceptance-missing", "MOTION.ACCEPTANCE.PRESENT", "intent", "error", 0.99, "deterministic",
            "Motion IR has no acceptance assertions for semantic or runtime verification.", ["motion-ir.json"], ["motion-ir.json"],
            "Add deterministic, runtime or human_required acceptance assertions.",
            "Without acceptance assertions the Agent cannot distinguish generated output from verified output.", True,
        ))

    errors = sum(item["severity"] == "error" for item in findings)
    warnings = sum(item["severity"] == "warning" for item in findings)
    infos = sum(item["severity"] == "info" for item in findings)
    blocking = sum(bool(item["approval_blocking"]) for item in findings)
    return {
        "schema_version": "0.1",
        "report_id": f"lint-{task_id}-{scene}",
        "task_id": task_id,
        "scene": scene,
        "status": "fail" if blocking else ("warn" if warnings else "pass"),
        "ruleset": {"id": "motionloom.semantic-motion", "version": "0.1"},
        "context_hash": task.get("context_hash") or ir.get("context_hash"),
        "motion_ir": {"path": "motion-ir.json", "sha256": digest_file(task_dir / "motion-ir.json")},
        "summary": {"total": len(findings), "errors": errors, "warnings": warnings, "infos": infos, "blocking": blocking},
        "findings": findings,
        "generated_at": now(),
    }


def semantic_lint_validate_data(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = {"schema_version", "report_id", "task_id", "scene", "status", "ruleset", "summary", "findings", "generated_at"}
    issues.extend(f"missing {field}" for field in sorted(required - set(report)))
    if report.get("schema_version") != "0.1":
        issues.append("schema_version must be 0.1")
    if report.get("status") not in {"pass", "warn", "fail"}:
        issues.append("status must be pass, warn or fail")
    summary = report.get("summary") or {}
    findings = report.get("findings") or []
    if summary.get("total") != len(findings):
        issues.append("summary.total does not match findings length")
    blocking = sum(bool(item.get("approval_blocking")) for item in findings if isinstance(item, dict))
    if summary.get("blocking") != blocking:
        issues.append("summary.blocking does not match findings")
    if report.get("status") == "fail" and blocking == 0:
        issues.append("fail status requires at least one blocking finding")
    return issues


def semantic_lint_build(args: argparse.Namespace) -> int:
    task_dir = task_dir_from(args.task_dir)
    task = read_json(task_dir / "task.json")
    ir = read_json(task_dir / "motion-ir.json")
    spec_path = motion_spec_path(task_dir, str(task.get("scene", "scene")), args.spec)
    spec = read_json(spec_path)
    report = semantic_lint_data(task_dir, task, ir, spec)
    issues = semantic_lint_validate_data(report)
    if issues:
        raise ValueError("semantic lint report is invalid: " + "; ".join(issues))
    output = Path(args.output).expanduser().resolve() if args.output else task_dir / "semantic-lint-report.json"
    write_json(output, report)
    print(json.dumps({"status": "built", "kind": "semantic-lint-report", "task_id": report["task_id"], "scene": report["scene"], "lint_status": report["status"], "finding_count": len(report["findings"]), "path": str(output)}, ensure_ascii=False))
    return 0


def semantic_lint_validate(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    report = read_json(path)
    issues = semantic_lint_validate_data(report if isinstance(report, dict) else {})
    if issues:
        raise ValueError("semantic lint report invalid: " + "; ".join(issues))
    print(json.dumps({"status": "valid", "kind": "semantic-lint-report", "task_id": report.get("task_id"), "scene": report.get("scene"), "lint_status": report.get("status"), "finding_count": len(report.get("findings", []))}, ensure_ascii=False))
    return 0


def continuity_report_data(task_dirs: list[Path], project_id: str | None = None) -> dict[str, Any]:
    if not task_dirs:
        raise ValueError("at least one task directory is required")
    entries = []
    seen_scenes: set[str] = set()
    for task_dir in task_dirs:
        task = read_json(task_dir / "task.json")
        ir = read_json(task_dir / "motion-ir.json")
        scene = str(task.get("scene") or ir.get("scene") or task_dir.name)
        if scene in seen_scenes:
            raise ValueError(f"duplicate scene in continuity input: {scene}")
        seen_scenes.add(scene)
        if task.get("task_id") != ir.get("task_id") or scene != ir.get("scene"):
            raise ValueError(f"task/Motion IR identity mismatch for scene: {scene}")
        order = task.get("scene_order")
        entries.append({"task_dir": task_dir, "task": task, "ir": ir, "scene": scene, "order": order if isinstance(order, int) else 0})
    entries.sort(key=lambda item: (item["order"], item["scene"]))
    scenes = []
    for index, item in enumerate(entries):
        ir_path = item["task_dir"] / "motion-ir.json"
        scenes.append({
            "scene": item["scene"],
            "order": index,
            "motion_ir_path": str(ir_path),
            "motion_ir_sha256": digest_file(ir_path),
            "context_hash": str(item["task"].get("context_hash") or item["ir"].get("context_hash")),
            "intent": str(item["ir"].get("intent", "")).strip(),
        })
    transitions = []
    errors = 0
    warnings = 0
    for previous, current in zip(entries, entries[1:]):
        previous_ir = previous["ir"]
        current_ir = current["ir"]
        checks = ["scene identity", "intent present", "context binding", "fps compatibility", "duration continuity"]
        findings: list[str] = []
        status = "pass"
        if not str(current_ir.get("intent", "")).strip() or not str(previous_ir.get("intent", "")).strip():
            findings.append("missing intent at transition boundary")
            status = "fail"
        previous_context = previous_ir.get("context_hash")
        current_context = current_ir.get("context_hash")
        if previous_context != current_context:
            findings.append("context hash changes between adjacent scenes")
            status = "warn"
        if float(previous_ir.get("fps", 0) or 0) != float(current_ir.get("fps", 0) or 0):
            findings.append("fps changes between adjacent scenes")
            status = "warn"
        if int(previous_ir.get("duration_ms", 0) or 0) <= 0 or int(current_ir.get("duration_ms", 0) or 0) <= 0:
            findings.append("non-positive duration at transition boundary")
            status = "fail"
        if status == "fail":
            errors += len(findings)
        elif status == "warn":
            warnings += len(findings)
        transitions.append({"id": f"transition-{previous['scene']}-{current['scene']}", "from_scene": previous["scene"], "to_scene": current["scene"], "status": status, "checks": checks, "findings": findings})
    status = "fail" if errors else ("warn" if warnings else "pass")
    return {
        "schema_version": "0.1",
        "report_id": f"continuity-{project_id or entries[0]['task'].get('project_name') or entries[0]['task'].get('task_id')}",
        "project_id": project_id or str(entries[0]["task"].get("project_name") or entries[0]["task"].get("task_id")),
        "status": status,
        "scenes": scenes,
        "transitions": transitions,
        "summary": {"scene_count": len(scenes), "transition_count": len(transitions), "errors": errors, "warnings": warnings, "blocking": errors},
        "generated_at": now(),
    }


def continuity_validate_data(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report.get("schema_version") != "0.1":
        issues.append("schema_version must be 0.1")
    scenes = report.get("scenes") or []
    transitions = report.get("transitions") or []
    if not scenes:
        issues.append("continuity report requires at least one scene")
    if len(transitions) != max(0, len(scenes) - 1):
        issues.append("transition count must equal scene count minus one")
    if report.get("summary", {}).get("scene_count") != len(scenes):
        issues.append("summary.scene_count does not match scenes")
    return issues


def continuity_build(args: argparse.Namespace) -> int:
    task_dirs = [task_dir_from(value) for value in args.task_dirs]
    report = continuity_report_data(task_dirs, args.project_id)
    issues = continuity_validate_data(report)
    if issues:
        raise ValueError("continuity report is invalid: " + "; ".join(issues))
    output = Path(args.output).expanduser().resolve() if args.output else task_dirs[0] / "continuity-report.json"
    write_json(output, report)
    print(json.dumps({"status": "built", "kind": "continuity-report", "project_id": report["project_id"], "scene_count": len(report["scenes"]), "transition_count": len(report["transitions"]), "continuity_status": report["status"], "path": str(output)}, ensure_ascii=False))
    return 0


def continuity_validate(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    report = read_json(path)
    issues = continuity_validate_data(report if isinstance(report, dict) else {})
    if issues:
        raise ValueError("continuity report invalid: " + "; ".join(issues))
    print(json.dumps({"status": "valid", "kind": "continuity-report", "project_id": report.get("project_id"), "continuity_status": report.get("status"), "transition_count": len(report.get("transitions", []))}, ensure_ascii=False))
    return 0


def fix_plan_build(args: argparse.Namespace) -> int:
    task_dir = task_dir_from(args.task_dir)
    reports = []
    issues = []
    for raw_path in args.reports:
        path = Path(raw_path).expanduser()
        path = (task_dir / path if not path.is_absolute() else path).resolve()
        if not within(task_dir, path) or not path.is_file():
            raise ValueError(f"fix-plan report must be a file inside task bundle: {raw_path}")
        data = read_json(path)
        kind = "semantic-lint" if "findings" in data else "continuity" if "transitions" in data else "quality"
        reports.append({"path": path.relative_to(task_dir).as_posix(), "sha256": digest_file(path), "kind": kind})
        for item in data.get("findings", []):
            if item.get("severity") == "info":
                continue
            issue_id = f"fix-{item.get('id', len(issues) + 1)}"
            category = item.get("category", "continuity")
            rerun = ["lint"]
            if category == "continuity":
                rerun = ["continuity", "quality_gate"]
            elif category in {"timing", "easing", "performance"}:
                rerun = ["lint", "render", "runtime", "replay", "quality_gate"]
            elif category == "accessibility":
                rerun = ["lint", "runtime", "browser_review", "quality_gate"]
            issues.append({
                "id": issue_id,
                "finding_ref": f"{path.relative_to(task_dir).as_posix()}#{item.get('id', issue_id)}",
                "severity": item.get("severity", "warning"),
                "confidence": item.get("confidence", 0.5),
                "root_cause": item.get("rationale") or item.get("message", "Unspecified semantic finding"),
                "affected_artifacts": item.get("affected_paths", []),
                "patch_scope": [item.get("suggested_action") or "Inspect the finding and update the bound artifact."],
                "rerun_scope": rerun,
                "verification": [f"python3 scripts/intelligence.py semantic-lint validate --path {path.relative_to(task_dir).as_posix()}", "python3 scripts/report.py check --task-dir <task-dir>"],
                "requires_user_review": bool(item.get("approval_blocking")) or category == "accessibility",
                "status": "open",
            })
    plan = {
        "schema_version": "0.1",
        "plan_id": f"fix-plan-{task_dir.name}",
        "task_id": str(read_json(task_dir / "task.json").get("task_id", task_dir.name)),
        "status": "proposed" if issues else "verified",
        "source_reports": reports,
        "issues": issues,
        "generated_at": now(),
        "next_agent": {"action": "Resolve open findings in priority order, then rerun the declared scope.", "skill": "motionloom", "evidence_needed": ["semantic-lint-report.json", "continuity-report.json", "quality-report.json"]},
    }
    output = Path(args.output).expanduser().resolve() if args.output else task_dir / "fix-plan.json"
    if not within(task_dir, output):
        raise ValueError("fix-plan output must be inside the task bundle")
    write_json(output, plan)
    sync_fix_plan_handoff(task_dir, plan, output.relative_to(task_dir).as_posix())
    print(json.dumps({"status": "built", "kind": "fix-plan", "task_id": plan["task_id"], "issue_count": len(issues), "plan_status": plan["status"], "path": str(output)}, ensure_ascii=False))
    return 0


def sync_fix_plan_handoff(task_dir: Path, plan: dict[str, Any], plan_path: str) -> None:
    """Project P1 findings into the existing report/issue/handoff contracts."""
    issue_path = task_dir / "issue-register.json"
    issue_register = read_json(issue_path) if issue_path.is_file() else {"version": "1.0", "task_id": plan["task_id"], "issues": []}
    existing = {str(item.get("id")): item for item in issue_register.get("issues", []) if item.get("id")}
    plan_issue_ids = set()
    for issue in plan.get("issues", []):
        issue_id = f"{plan['plan_id']}:{issue['id']}"
        plan_issue_ids.add(issue_id)
        existing[issue_id] = {
            "id": issue_id,
            "summary": issue.get("root_cause", "P1 finding requires investigation."),
            "status": issue.get("status", "open"),
            "severity": issue.get("severity", "warning"),
            "confidence": issue.get("confidence", 0.5),
            "evidence": [issue.get("finding_ref", ""), plan_path],
            "next_action": "; ".join(issue.get("patch_scope", [])),
            "fix_plan": plan_path,
            "rerun_scope": issue.get("rerun_scope", []),
            "requires_user_review": bool(issue.get("requires_user_review")),
        }
    issue_register["task_id"] = plan["task_id"]
    issue_register["issues"] = list(existing.values())
    write_json(issue_path, issue_register)

    report_path = task_dir / "execution-report.json"
    report = read_json(report_path)
    report_issues = {str(item.get("id")): item for item in report.get("problems", []) if item.get("id")}
    for issue_id in plan_issue_ids:
        report_issues[issue_id] = existing[issue_id]
    report["problems"] = list(report_issues.values())
    next_agent = [item for item in report.get("next_agent", []) if item.get("id") != plan["plan_id"]]
    next_agent.append({
        "id": plan["plan_id"],
        "agent": "motionloom",
        "skill": "motionloom",
        "action": plan["next_agent"]["action"],
        "status": "pending" if plan.get("issues") else "complete",
        "evidence_needed": [plan_path] + plan["next_agent"].get("evidence_needed", []),
    })
    report["next_agent"] = next_agent
    report["p1_feedback"] = {"fix_plan": plan_path, "issue_count": len(plan.get("issues", [])), "status": plan.get("status"), "generated_at": plan.get("generated_at")}
    report["generated_at"] = now()
    write_json(report_path, report)

    handoff_path = task_dir / "handoff.json"
    handoff = read_json(handoff_path)
    required = list(handoff.get("required_artifacts", []))
    for artifact in (plan_path, "semantic-lint-report.json", "continuity-report.json", "issue-register.json"):
        if artifact not in required:
            required.append(artifact)
    handoff["required_artifacts"] = required
    handoff["fix_plan"] = {"path": plan_path, "status": plan.get("status"), "issue_count": len(plan.get("issues", [])), "requires_user_review": any(item.get("requires_user_review") for item in plan.get("issues", []))}
    actions = [item for item in handoff.get("next_actions", []) if item.get("id") != plan["plan_id"]]
    actions.append({
        "id": plan["plan_id"],
        "action": plan["next_agent"]["action"],
        "kind": "p1_fix_plan",
        "agent": "motionloom",
        "skill": "motionloom",
        "fix_plan": plan_path,
        "requires_user_approval": any(item.get("requires_user_review") for item in plan.get("issues", [])),
        "evidence_needed": [plan_path] + plan["next_agent"].get("evidence_needed", []),
    })
    handoff["next_actions"] = actions
    blockers = [item for item in handoff.get("blockers", []) if not str(item).startswith(f"{plan['plan_id']}:")]
    blockers.extend(issue_id for issue_id in sorted(plan_issue_ids) if existing[issue_id].get("requires_user_review"))
    handoff["blockers"] = blockers
    handoff["feedback"] = {"source": "semantic-lint/continuity", "status": plan.get("status"), "issue_count": len(plan.get("issues", [])), "fix_plan": plan_path}
    write_json(handoff_path, handoff)


def fix_plan_validate(args: argparse.Namespace) -> int:
    path = Path(args.path).expanduser().resolve()
    plan = read_json(path)
    issues = []
    if plan.get("schema_version") != "0.1":
        issues.append("schema_version must be 0.1")
    if plan.get("status") not in {"proposed", "accepted", "in_progress", "verified", "blocked"}:
        issues.append("invalid fix-plan status")
    if not isinstance(plan.get("source_reports"), list) or not plan.get("source_reports"):
        issues.append("source_reports must not be empty")
    if not isinstance(plan.get("issues"), list):
        issues.append("issues must be an array")
    if issues:
        raise ValueError("fix plan invalid: " + "; ".join(issues))
    print(json.dumps({"status": "valid", "kind": "fix-plan", "task_id": plan.get("task_id"), "issue_count": len(plan.get("issues", [])), "plan_status": plan.get("status")}, ensure_ascii=False))
    return 0


def validate_task_p1(task_dir: Path, scene: str | None = None) -> list[str]:
    """Validate the P1 reports and their handoff binding without side effects."""
    issues: list[str] = []
    required = ("semantic-lint-report.json", "continuity-report.json", "fix-plan.json")
    if any((task_dir / name).is_file() for name in required):
        for name in required:
            if not (task_dir / name).is_file():
                issues.append(f"missing {name}")
        if issues:
            return issues
        try:
            task = read_json(task_dir / "task.json")
            lint = read_json(task_dir / "semantic-lint-report.json")
            continuity = read_json(task_dir / "continuity-report.json")
            plan = read_json(task_dir / "fix-plan.json")
            issues.extend(f"semantic lint: {item}" for item in semantic_lint_validate_data(lint))
            issues.extend(f"continuity: {item}" for item in continuity_validate_data(continuity))
            if plan.get("schema_version") != "0.1":
                issues.append("fix plan: schema_version must be 0.1")
            if plan.get("task_id") != task.get("task_id"):
                issues.append("fix plan task_id does not match task.json")
            if scene and lint.get("scene") != scene:
                issues.append("semantic lint scene does not match quality-gate scene")
            for source in plan.get("source_reports", []):
                raw_path = str(source.get("path", ""))
                try:
                    source_path = (task_dir / safe_relative(raw_path)).resolve()
                except ValueError as exc:
                    issues.append(f"fix plan source path invalid: {exc}")
                    continue
                if not within(task_dir, source_path) or not source_path.is_file():
                    issues.append(f"fix plan source report missing: {raw_path}")
                elif source.get("sha256") != digest_file(source_path):
                    issues.append(f"fix plan source report hash mismatch: {raw_path}")
            handoff = read_json(task_dir / "handoff.json")
            if handoff.get("fix_plan", {}).get("path") != "fix-plan.json":
                issues.append("handoff fix_plan must point to fix-plan.json")
            if "semantic-lint-report.json" not in handoff.get("required_artifacts", []):
                issues.append("handoff required_artifacts must include semantic-lint-report.json")
            if "continuity-report.json" not in handoff.get("required_artifacts", []):
                issues.append("handoff required_artifacts must include continuity-report.json")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            issues.append(f"P1 validation error: {exc}")
    return issues


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

    semantic_lint = sub.add_parser("semantic-lint", help="build or validate semantic-lint-report.json")
    semantic_lint_sub = semantic_lint.add_subparsers(dest="action", required=True)
    semantic_lint_build_parser = semantic_lint_sub.add_parser("build")
    semantic_lint_build_parser.add_argument("--task-dir", required=True)
    semantic_lint_build_parser.add_argument("--spec")
    semantic_lint_build_parser.add_argument("--output")
    semantic_lint_build_parser.set_defaults(func=semantic_lint_build)
    semantic_lint_validate_parser = semantic_lint_sub.add_parser("validate")
    semantic_lint_validate_parser.add_argument("--path", required=True)
    semantic_lint_validate_parser.set_defaults(func=semantic_lint_validate)

    continuity = sub.add_parser("continuity", help="build or validate continuity-report.json")
    continuity_sub = continuity.add_subparsers(dest="action", required=True)
    continuity_build_parser = continuity_sub.add_parser("build")
    continuity_build_parser.add_argument("--task-dirs", nargs="+", required=True)
    continuity_build_parser.add_argument("--project-id")
    continuity_build_parser.add_argument("--output")
    continuity_build_parser.set_defaults(func=continuity_build)
    continuity_validate_parser = continuity_sub.add_parser("validate")
    continuity_validate_parser.add_argument("--path", required=True)
    continuity_validate_parser.set_defaults(func=continuity_validate)

    fix_plan = sub.add_parser("fix-plan", help="build or validate fix-plan.json")
    fix_plan_sub = fix_plan.add_subparsers(dest="action", required=True)
    fix_plan_build_parser = fix_plan_sub.add_parser("build")
    fix_plan_build_parser.add_argument("--task-dir", required=True)
    fix_plan_build_parser.add_argument("--reports", nargs="+", required=True)
    fix_plan_build_parser.add_argument("--output")
    fix_plan_build_parser.set_defaults(func=fix_plan_build)
    fix_plan_validate_parser = fix_plan_sub.add_parser("validate")
    fix_plan_validate_parser.add_argument("--path", required=True)
    fix_plan_validate_parser.set_defaults(func=fix_plan_validate)


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
