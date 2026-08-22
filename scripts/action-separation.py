#!/usr/bin/env python3
"""Fail-closed validation for action-scoped isolated frame sequences.

The generator may create one PNG per frame, but this contract keeps every frame
bound to one immutable sequence/action identity and requires an independent
verifier result against explicitly forbidden competitor actions. It never moves
files, regenerates assets, grants provenance or grants human approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,95}$")
FRAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


def error(code: str, message: str, path: str = "") -> dict[str, str]:
    return {"severity": "error", "code": code, "message": message, "path": path}


def inside(root: Path, value: str) -> tuple[Path | None, dict[str, str] | None]:
    if not isinstance(value, str) or not value.strip() or Path(value).is_absolute():
        return None, error("path_escape", f"path must be a non-empty relative path: {value!r}", value if isinstance(value, str) else "")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None, error("path_escape", f"path escapes action manifest root: {value}", value)
    return candidate, None


def read_json(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [error("invalid_input", str(exc), str(path))]
    if not isinstance(value, dict):
        return None, [error("invalid_document", "document root must be an object", str(path))]
    return value, []


def sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def result_payload(verifier: dict[str, Any]) -> dict[str, Any]:
    return {key: verifier.get(key) for key in ("expected_action", "top_competitor", "margin", "threshold", "status", "method")}


def result_hash(verifier: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(result_payload(verifier))).hexdigest()


def action_ids(document: dict[str, Any]) -> tuple[str, list[str]]:
    expected = str(document.get("action_id", ""))
    forbidden = document.get("forbidden_action_ids")
    return expected, [str(item) for item in forbidden] if isinstance(forbidden, list) else []


def validate_manifest(document: dict[str, Any], root: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if document.get("schema_version") != "0.2":
        errors.append(error("schema_version", "action sequence manifest schema_version must be 0.2", "schema_version"))
    for key in ("sequence_id", "asset_identity", "action_id", "identity_lock_sha256", "generator_agent_id", "forbidden_action_ids", "actions", "frames"):
        if key not in document:
            errors.append(error("missing_field", f"required field is missing: {key}", key))
    sequence_id = str(document.get("sequence_id", ""))
    action_id = str(document.get("action_id", ""))
    if not ID_RE.fullmatch(sequence_id):
        errors.append(error("invalid_sequence_id", "sequence_id must use lowercase safe identifier characters", "sequence_id"))
    if not FRAME_RE.fullmatch(action_id):
        errors.append(error("invalid_action_id", "action_id must use lowercase safe identifier characters", "action_id"))
    generator_agent_id = str(document.get("generator_agent_id", ""))
    if not FRAME_RE.fullmatch(generator_agent_id):
        errors.append(error("invalid_generator_agent_id", "generator_agent_id must use lowercase safe identifier characters", "generator_agent_id"))
    lock_hash = str(document.get("identity_lock_sha256", ""))
    if not SHA_RE.fullmatch(lock_hash):
        errors.append(error("invalid_identity_lock_sha256", "identity_lock_sha256 must be 64 lowercase hex characters", "identity_lock_sha256"))

    forbidden_value = document.get("forbidden_action_ids")
    forbidden = [str(item) for item in forbidden_value] if isinstance(forbidden_value, list) else []
    if not forbidden_value or any(not FRAME_RE.fullmatch(item) for item in forbidden):
        errors.append(error("invalid_forbidden_actions", "forbidden_action_ids must be a non-empty safe identifier array", "forbidden_action_ids"))
    if action_id in forbidden:
        errors.append(error("expected_action_forbidden", "action_id must not also be forbidden", "forbidden_action_ids"))
    if len(set(forbidden)) != len(forbidden):
        errors.append(error("duplicate_forbidden_action", "forbidden_action_ids must be unique", "forbidden_action_ids"))

    actions_value = document.get("actions")
    actions = actions_value if isinstance(actions_value, list) else []
    declared_actions: set[str] = set()
    for index, item in enumerate(actions):
        prefix = f"actions[{index}]"
        if not isinstance(item, dict):
            errors.append(error("invalid_action", "action entry must be an object", prefix))
            continue
        declared = str(item.get("action_id", ""))
        if not FRAME_RE.fullmatch(declared):
            errors.append(error("invalid_action_id", "action_id must use lowercase safe identifier characters", f"{prefix}.action_id"))
        if declared in declared_actions:
            errors.append(error("duplicate_action", f"duplicate action declaration: {declared}", f"{prefix}.action_id"))
        declared_actions.add(declared)
        for cue_key in ("positive_cues", "negative_cues"):
            cues = item.get(cue_key)
            if not isinstance(cues, list) or not cues or any(not isinstance(cue, str) or not cue.strip() for cue in cues):
                errors.append(error("invalid_action_cues", f"{cue_key} must be a non-empty string array", f"{prefix}.{cue_key}"))
    if action_id not in declared_actions:
        errors.append(error("missing_expected_action", "actions must declare the expected action_id", "actions"))
    for competitor in forbidden:
        if competitor not in declared_actions:
            errors.append(error("missing_competitor_action", f"forbidden competitor is not declared: {competitor}", "actions"))

    frames_value = document.get("frames")
    frames = frames_value if isinstance(frames_value, list) else []
    if len(frames) < 2:
        errors.append(error("insufficient_frames", "an action sequence requires at least two frames", "frames"))
    seen_indexes: set[int] = set()
    seen_frame_ids: set[str] = set()
    seen_images: set[str] = set()
    expected_envelopes: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        prefix = f"frames[{index}]"
        if not isinstance(frame, dict):
            errors.append(error("invalid_frame", "frame entry must be an object", prefix))
            continue
        try:
            frame_index = int(frame.get("frame_index"))
        except (TypeError, ValueError):
            frame_index = -1
        if frame_index < 0 or frame_index in seen_indexes:
            errors.append(error("invalid_frame_index", "frame_index must be unique and non-negative", f"{prefix}.frame_index"))
        seen_indexes.add(frame_index)
        frame_id = str(frame.get("frame_id", ""))
        if not FRAME_RE.fullmatch(frame_id):
            errors.append(error("invalid_frame_id", "frame_id must use lowercase safe identifier characters", f"{prefix}.frame_id"))
        if frame_id in seen_frame_ids:
            errors.append(error("duplicate_frame_id", f"duplicate frame_id: {frame_id}", f"{prefix}.frame_id"))
        seen_frame_ids.add(frame_id)
        image = str(frame.get("image", ""))
        envelope = str(frame.get("envelope", ""))
        for field, value in (("image", image), ("envelope", envelope)):
            _, path_error = inside(root, value)
            if path_error:
                path_error["path"] = f"{prefix}.{field}"
                errors.append(path_error)
        if image in seen_images:
            errors.append(error("duplicate_frame_image", f"multiple frames reference the same image: {image}", f"{prefix}.image"))
        seen_images.add(image)
        expected_envelopes.append({"frame_index": frame_index, "frame_id": frame_id, "image": image, "envelope": envelope, "path": prefix})

    if seen_indexes and seen_indexes != set(range(len(frames))):
        errors.append(error("frame_order_gap", "frame_index values must be contiguous from zero", "frames"))

    envelope_count = 0
    passing_count = 0
    for item in expected_envelopes:
        envelope_path, path_error = inside(root, str(item["envelope"]))
        if path_error or envelope_path is None:
            continue
        envelope, envelope_errors = read_json(envelope_path)
        errors.extend({**entry, "path": f"{item['path']}.envelope"} for entry in envelope_errors)
        if envelope is None:
            continue
        envelope_count += 1
        checks = {
            "sequence_id": (envelope.get("sequence_id"), sequence_id),
            "action_id": (envelope.get("action_id"), action_id),
            "frame_id": (envelope.get("frame_id"), item["frame_id"]),
            "frame_index": (envelope.get("frame_index"), item["frame_index"]),
            "identity_lock_sha256": (envelope.get("identity_lock_sha256"), lock_hash),
            "image": (envelope.get("image"), item["image"]),
        }
        for field, (actual, expected) in checks.items():
            if actual != expected:
                errors.append(error("envelope_binding_mismatch", f"envelope {field} does not match manifest", f"{item['path']}.envelope.{field}"))
        image_path, image_error = inside(root, str(item["image"]))
        if image_error or image_path is None:
            continue
        actual_hash = sha256(image_path)
        if actual_hash is None:
            errors.append(error("image_unreadable", f"cannot read image: {item['image']}", f"{item['path']}.image"))
        elif envelope.get("image_sha256") != actual_hash:
            errors.append(error("image_sha256_mismatch", "frame envelope image hash does not match file bytes", f"{item['path']}.envelope.image_sha256"))
        if envelope.get("generator_agent_id") != generator_agent_id:
            errors.append(error("generator_binding_mismatch", "envelope generator_agent_id does not match manifest", f"{item['path']}.envelope.generator_agent_id"))
        if envelope.get("approval") is not False:
            errors.append(error("approval_boundary", "frame envelope validation must preserve approval=false", f"{item['path']}.envelope.approval"))
        verifier = envelope.get("verifier") if isinstance(envelope.get("verifier"), dict) else {}
        verifier_id = verifier.get("verifier_id")
        if not isinstance(verifier_id, str) or not FRAME_RE.fullmatch(verifier_id):
            errors.append(error("invalid_verifier_id", "verifier_id must use lowercase safe identifier characters", f"{item['path']}.envelope.verifier.verifier_id"))
        elif verifier_id == generator_agent_id:
            errors.append(error("non_independent_verifier", "verifier_id must differ from generator_agent_id", f"{item['path']}.envelope.verifier.verifier_id"))
        verification_mode = verifier.get("verification_mode")
        verifier_path = f"{item['path']}.envelope.verifier"
        if verification_mode not in {"declared", "independently_bound"}:
            errors.append(error("invalid_verification_mode", "verification_mode must be declared or independently_bound", f"{verifier_path}.verification_mode"))
        elif verification_mode == "declared":
            errors.append(error("verifier_evidence_declared", "declared verifier evidence cannot be treated as independently verified", f"{verifier_path}.verification_mode"))
        else:
            evidence = verifier.get("evidence") if isinstance(verifier.get("evidence"), dict) else {}
            evidence_value = evidence.get("artifact")
            if not isinstance(evidence_value, str) or not evidence_value.strip():
                errors.append(error("missing_verifier_provenance", "independently_bound evidence must include an artifact path", f"{verifier_path}.evidence.artifact"))
                evidence_path, evidence_path_error = None, None
            else:
                evidence_path, evidence_path_error = inside(root, evidence_value)
            if evidence_path_error or evidence_path is None:
                if not (not isinstance(evidence_value, str) or not evidence_value.strip()):
                    errors.append(error("missing_verifier_provenance", "independently_bound evidence must reference a safe artifact path", f"{verifier_path}.evidence.artifact"))
            else:
                evidence_doc, evidence_errors = read_json(evidence_path)
                errors.extend({**entry, "path": f"{verifier_path}.evidence.artifact"} for entry in evidence_errors)
                actual_evidence_hash = sha256(evidence_path)
                if actual_evidence_hash is None or evidence.get("artifact_sha256") != actual_evidence_hash:
                    errors.append(error("verifier_evidence_hash_mismatch", "verifier evidence artifact hash does not match file bytes", f"{verifier_path}.evidence.artifact_sha256"))
                if evidence_doc is not None:
                    provenance = evidence_doc.get("provenance") if isinstance(evidence_doc.get("provenance"), dict) else {}
                    if provenance.get("kind") != "separate_verifier_artifact":
                        errors.append(error("missing_verifier_provenance", "verifier evidence must declare separate_verifier_artifact provenance", f"{verifier_path}.evidence.artifact.provenance.kind"))
                    producer_id = provenance.get("producer_id")
                    if not isinstance(producer_id, str) or not FRAME_RE.fullmatch(producer_id) or producer_id == generator_agent_id:
                        errors.append(error("non_independent_verifier", "verifier evidence producer_id must be valid and differ from generator_agent_id", f"{verifier_path}.evidence.artifact.provenance.producer_id"))
                    expected_evidence_binding = {
                        "sequence_id": sequence_id,
                        "action_id": action_id,
                        "frame_id": item["frame_id"],
                        "frame_index": item["frame_index"],
                        "image_sha256": envelope.get("image_sha256"),
                        "identity_lock_sha256": lock_hash,
                        "generator_agent_id": generator_agent_id,
                        "verifier_id": verifier_id,
                    }
                    for field, expected in expected_evidence_binding.items():
                        if evidence_doc.get(field) != expected:
                            errors.append(error("verifier_evidence_binding_mismatch", f"verifier evidence {field} does not match envelope", f"{verifier_path}.evidence.artifact.{field}"))
                    evidence_result = evidence_doc.get("result") if isinstance(evidence_doc.get("result"), dict) else None
                    current_result = result_payload(verifier)
                    if evidence_result != current_result:
                        errors.append(error("verifier_result_mismatch", "verifier result does not match independently bound evidence", f"{verifier_path}.evidence.result_sha256"))
                    expected_result_hash = result_hash(verifier)
                    if evidence.get("result_sha256") != expected_result_hash or evidence_doc.get("result_sha256") != expected_result_hash:
                        errors.append(error("verifier_result_hash_mismatch", "verifier result hash does not match canonical result", f"{verifier_path}.evidence.result_sha256"))
        expected_action = verifier.get("expected_action")
        competitor = verifier.get("top_competitor")
        try:
            margin = float(verifier.get("margin"))
            threshold = float(verifier.get("threshold"))
        except (TypeError, ValueError):
            margin, threshold = -1.0, 0.0
        if expected_action != action_id:
            errors.append(error("action_verifier_mismatch", "verifier expected_action does not match manifest action", f"{item['path']}.envelope.verifier.expected_action"))
        if competitor not in forbidden:
            errors.append(error("undeclared_competitor", "verifier top_competitor must be one of forbidden_action_ids", f"{item['path']}.envelope.verifier.top_competitor"))
        if not (margin >= threshold >= 0):
            errors.append(error("action_confidence_margin", "action separation margin is below its declared threshold", f"{item['path']}.envelope.verifier.margin"))
        if verifier.get("status") != "pass":
            errors.append(error("action_verification_required", "ambiguous or failed action verification must remain quarantined", f"{item['path']}.envelope.verifier.status"))
        if verification_mode == "independently_bound" and expected_action == action_id and competitor in forbidden and margin >= threshold >= 0 and verifier.get("status") == "pass":
            passing_count += 1

    if document.get("approval") is not False:
        errors.append(error("approval_boundary", "action sequence validation must preserve approval=false", "approval"))
    if document.get("status") not in {"review_required", "quarantined"}:
        errors.append(error("invalid_status", "action sequence status must remain review_required or quarantined", "status"))

    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "contract": "action_sequence_manifest",
        "ready": not errors,
        "errors": errors,
        "warnings": [],
        "metrics": {
            "sequence_id": sequence_id,
            "action_id": action_id,
            "frame_count": len(frames),
            "envelope_count": envelope_count,
            "passing_action_verifications": passing_count,
            "independently_bound_verifications": passing_count,
            "manifest_sha256": hashlib.sha256(canonical).hexdigest(),
            "approval": False,
        },
        "approval": False,
    }


def build_envelope(
    document: dict[str, Any],
    root: Path,
    frame_id: str,
    expected_action: str,
    top_competitor: str,
    margin: float,
    threshold: float,
    method: str,
) -> dict[str, Any]:
    frame = next((item for item in document.get("frames", []) if isinstance(item, dict) and item.get("frame_id") == frame_id), None)
    if frame is None:
        return {"contract": "frame_envelope", "ready": False, "errors": [error("unknown_frame", f"frame_id not found in manifest: {frame_id}", "frame_id")], "warnings": [], "approval": False}
    image_value = str(frame.get("image", ""))
    image_path, path_error = inside(root, image_value)
    if path_error or image_path is None:
        return {"contract": "frame_envelope", "ready": False, "errors": [path_error or error("invalid_image", "image path is invalid", "image")], "warnings": [], "approval": False}
    image_hash = sha256(image_path)
    if image_hash is None:
        return {"contract": "frame_envelope", "ready": False, "errors": [error("image_unreadable", f"cannot read image: {image_value}", "image")], "warnings": [], "approval": False}
    expected = str(document.get("action_id", ""))
    forbidden = document.get("forbidden_action_ids", [])
    criteria_pass = expected_action == expected and top_competitor in forbidden and margin >= threshold >= 0
    status = "quarantined"
    payload = {
        "schema_version": "0.2",
        "sequence_id": document.get("sequence_id"),
        "action_id": expected,
        "frame_id": frame_id,
        "frame_index": frame.get("frame_index"),
        "image": image_value,
        "image_sha256": image_hash,
        "identity_lock_sha256": document.get("identity_lock_sha256"),
        "generator_agent_id": document.get("generator_agent_id"),
        "verifier": {
            "verifier_id": "motionloom-separation-verifier-v1",
            "verification_mode": "declared",
            "expected_action": expected_action,
            "top_competitor": top_competitor,
            "margin": margin,
            "threshold": threshold,
            "status": status,
            "method": method,
        },
        "approval": False,
    }
    reason = "generated envelope contains declared verifier fields only; an independently bound evidence artifact is required"
    if not criteria_pass:
        reason = "generated verifier criteria do not pass; envelope remains quarantined"
    return {"contract": "frame_envelope", "ready": False, "errors": [error("verifier_evidence_declared", reason, "verifier")], "warnings": [], "envelope": payload, "approval": False}


def emit(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    print(f"action separation: {'PASS' if result.get('ready') else 'QUARANTINED'}")
    for item in result.get("errors", []):
        print(f"ERROR {item.get('code')}: {item.get('message')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("validate")
    command.add_argument("--input", required=True, help="action-sequence manifest JSON")
    command.add_argument("--root", default=".", help="root used to resolve manifest paths")
    command.add_argument("--json", action="store_true", dest="as_json")
    envelope_command = sub.add_parser("envelope")
    envelope_command.add_argument("--manifest", required=True, help="action-sequence manifest JSON")
    envelope_command.add_argument("--root", default=".", help="root used to resolve manifest paths")
    envelope_command.add_argument("--frame-id", required=True)
    envelope_command.add_argument("--expected-action", required=True)
    envelope_command.add_argument("--top-competitor", required=True)
    envelope_command.add_argument("--margin", type=float, required=True)
    envelope_command.add_argument("--threshold", type=float, default=0.2)
    envelope_command.add_argument("--method", default="independent-action-rubric-v1")
    envelope_command.add_argument("--output")
    envelope_command.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    input_path = Path(args.input if args.command == "validate" else args.manifest)
    document, load_errors = read_json(input_path)
    result = {"contract": "action_sequence_manifest", "ready": False, "errors": load_errors, "warnings": [], "metrics": {}, "approval": False}
    if document is not None:
        if args.command == "validate":
            result = validate_manifest(document, Path(args.root).resolve())
        else:
            result = build_envelope(
                document,
                Path(args.root).resolve(),
                args.frame_id,
                args.expected_action,
                args.top_competitor,
                args.margin,
                args.threshold,
                args.method,
            )
            if args.output and result.get("envelope"):
                output_path = Path(args.output).resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(result["envelope"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                result["output"] = str(output_path)
    emit(result, args.as_json)
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
