#!/usr/bin/env python3
"""Build a hash-bound, review-only MotionLoom AI scout pilot from four PNG frames.

The builder is intentionally pilot-specific. It copies source bytes into a local
``.motionloom`` workspace, measures their actual alpha geometry using the same
deterministic reader as Asset Consistency, and writes the contracts that feed
Artifact Intake and Runtime Candidate. It never manufactures a human approval,
artist authority, or runtime-pass claim.

It uses Python's standard library only and runs on Ubuntu, macOS, and Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ID = "character.scout-robot.ai-pilot"
PILOT_ID = "ai-pilot-scout-walk"
FRAME_ORDER = (
    ("idle", "idle", "preview"),
    ("contact-right", "contact_right", "runtime_candidate"),
    ("passing", "passing", "runtime_candidate"),
    ("contact-left", "contact_left", "runtime_candidate"),
)
PROVIDER_PROFILES = {
    "internal-imagegen": {
        "adapter_id": "internal.imagegen",
        "kind": "internal_skill",
        "invocation_mode": "agent-mediated",
        "cost_class": "included",
        "generator_source": "internal-imagegen",
        "default_model": "default",
        "default_task_id": "motionloom-scout-ai-pilot-ingest-2026",
        "license_source": "Internal ImageGen generation; provider-native receipt was not exported",
        "reconstruction_source": "agent-mediated ImageGen source",
        "lab_limit": "Internal ImageGen adapter is scaffold-only",
    },
    "chatgpt": {
        "adapter_id": "openai.chatgpt",
        "kind": "external_provider",
        "invocation_mode": "manual",
        "cost_class": "external",
        "generator_source": "openai-chatgpt",
        "default_model": "chatgpt-image-generation",
        "default_task_id": "motionloom-scout-chatgpt-pilot-2026",
        "license_source": "User-provided ChatGPT generation; provider-native receipt was not exported",
        "reconstruction_source": "user-mediated ChatGPT source",
        "lab_limit": "ChatGPT import adapter is scaffold-only",
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_png_reader() -> Any:
    source = REPO_ROOT / "scripts" / "asset-consistency.py"
    spec = importlib.util.spec_from_file_location("motionloom_pilot_png", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load deterministic PNG reader: {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PNGImage


def parse_urls(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        frame_id, separator, url = value.partition("=")
        if not separator or frame_id not in {item[0] for item in FRAME_ORDER} or not url.startswith(("/", "https://", "http://")):
            raise ValueError("--frame-url must look like idle=/manus-storage/frame.png")
        result[frame_id] = url
    return result


def measured_frame(PNGImage: Any, path: Path) -> dict[str, Any]:
    image = PNGImage(path)
    supports_alpha = image.color_type in {4, 6} or (image.color_type == 3 and bool(image._transparency))
    if not supports_alpha:
        raise ValueError(
            f"{path.name} is color type {image.color_type} and has no alpha channel; "
            "do not treat a painted checkerboard as transparency"
        )
    total = image.width * image.height
    alpha_pixels = image.alpha_count(1)
    if alpha_pixels == total:
        raise ValueError(f"{path.name} has no transparent padding; an isolated alpha frame is required")
    bbox = image.alpha_bbox(1)
    if bbox is None:
        raise ValueError(f"{path.name} has no visible alpha pixels")
    return {
        "width": image.width,
        "height": image.height,
        "alpha_pixels": alpha_pixels,
        "alpha_bbox": bbox,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def require_clean_pilot_geometry(frame_id: str, data: dict[str, Any]) -> None:
    """Reject canvas-spanning residue for this isolated, single-character pilot.

    Alpha isolation can deliberately remove only edge-connected background. A
    detached band may therefore remain alpha-opaque without touching an edge.
    The pilot has a narrow, centred single-character contract, so its measured
    alpha bounds must retain padding on every side and cannot occupy most of a
    canvas width. This is a geometry guard, not a human-quality approval.
    """
    bbox = data["alpha_bbox"]
    width, height = int(data["width"]), int(data["height"])
    minimum_padding = max(1, round(min(width, height) * 0.05))
    paddings = {
        "left": int(bbox["x"]),
        "top": int(bbox["y"]),
        "right": width - (int(bbox["x"]) + int(bbox["width"])),
        "bottom": height - (int(bbox["y"]) + int(bbox["height"])),
    }
    if min(paddings.values()) < minimum_padding:
        raise ValueError(
            f"{frame_id} does not retain {minimum_padding}px clean padding on every edge; "
            f"measured {paddings}. Reject possible canvas-spanning contamination."
        )
    if int(bbox["width"]) / width > 0.6:
        raise ValueError(
            f"{frame_id} alpha subject spans {int(bbox['width'])}/{width}px of the canvas width; "
            "reject possible detached horizontal contamination."
        )


def frame_entry(frame_id: str, role: str, target: str, file_name: str, data: dict[str, Any], root_relative_output: str) -> dict[str, Any]:
    return {
        "path": f"{root_relative_output}/frames/{file_name}",
        "role": f"walk_{role}",
        "sha256": data["sha256"],
        "bytes": data["bytes"],
        "target": target,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MotionLoom's review-only scout AI pilot workspace")
    parser.add_argument("--idle", required=True, type=Path, help="Alpha-isolated idle PNG")
    parser.add_argument("--contact-right", required=True, type=Path, help="Alpha-isolated contact-right PNG")
    parser.add_argument("--passing", required=True, type=Path, help="Alpha-isolated passing PNG")
    parser.add_argument("--contact-left", required=True, type=Path, help="Alpha-isolated contact-left PNG")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="MotionLoom repository root")
    parser.add_argument(
        "--output",
        default=".motionloom/pilots/ai-pilot-scout",
        help="Safe relative output directory inside --root",
    )
    parser.add_argument("--frame-url", action="append", default=[], help="Optional frame URL: idle=/manus-storage/frame.png")
    parser.add_argument("--generated-at", default=None, help="ISO-8601 evidence timestamp; defaults to build time")
    parser.add_argument("--provider", choices=sorted(PROVIDER_PROFILES), default="internal-imagegen", help="Truthful source provider profile")
    parser.add_argument("--provider-model", default=None, help="Provider/model label for provenance; defaults to profile value")
    parser.add_argument("--provider-task-id", default=None, help="Provider or user-mediated task identifier for provenance")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing pilot workspace")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    output = (root / args.output).resolve()
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise SystemExit("--output must stay inside --root") from exc
    if output.exists():
        if not args.overwrite:
            raise SystemExit(f"pilot workspace already exists: {output}; pass --overwrite to replace it")
        shutil.rmtree(output)
    urls = parse_urls(args.frame_url)
    timestamp = args.generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    provider = PROVIDER_PROFILES[args.provider]
    provider_model = args.provider_model or provider["default_model"]
    provider_task_id = args.provider_task_id or provider["default_task_id"]

    sources = {
        "idle": args.idle,
        "contact-right": args.contact_right,
        "passing": args.passing,
        "contact-left": args.contact_left,
    }
    for frame_id, source in sources.items():
        if not source.is_file():
            raise SystemExit(f"missing {frame_id} source image: {source}")

    output.mkdir(parents=True)
    frames_dir = output / "frames"
    frames_dir.mkdir()
    PNGImage = load_png_reader()
    frames: dict[str, dict[str, Any]] = {}
    for frame_id, role, _ in FRAME_ORDER:
        destination = frames_dir / f"scout-{frame_id}.png"
        shutil.copy2(sources[frame_id], destination)
        frames[frame_id] = measured_frame(PNGImage, destination)
        require_clean_pilot_geometry(frame_id, frames[frame_id])

    canvas_sizes = {(item["width"], item["height"]) for item in frames.values()}
    if len(canvas_sizes) != 1:
        raise SystemExit(f"all frames must use one canvas; measured {sorted(canvas_sizes)}")
    width, height = next(iter(canvas_sizes))
    alpha_bboxes = [item["alpha_bbox"] for item in frames.values()]
    footlines = [bbox["y"] + bbox["height"] - 1 for bbox in alpha_bboxes]
    pivots = [(bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] - 1) for bbox in alpha_bboxes]
    reference_pivot = pivots[0]
    pivot_tolerance = max(max(abs(x - reference_pivot[0]), abs(y - reference_pivot[1])) for x, y in pivots)
    footline_tolerance = max(abs(value - footlines[0]) for value in footlines)
    bbox_tolerance = max(
        max(abs(item["width"] - alpha_bboxes[0]["width"]), abs(item["height"] - alpha_bboxes[0]["height"]))
        for item in alpha_bboxes
    )
    min_alpha = min(int(item["alpha_pixels"]) for item in frames.values())
    idle_hash = frames["idle"]["sha256"]
    prompt_capsule = (
        f"MotionLoom scout robot AI pilot imported from {provider['generator_source']}. "
        "Post-hoc ingest capsule only; provider-native prompt and task receipt were not exported. "
        "The capsule binds reviewed output bytes without asserting a human approval or artist authorship."
    )
    prompt_hash = sha256_text(prompt_capsule)
    motion_hash = sha256_text("walk_pilot_4frame:idle,contact-right,passing,contact-left")
    style_hash = sha256_text("cream-orange-black-cyan pixel-art scout robot style lock")

    relative_output = output.relative_to(root).as_posix()
    geometry_frames: list[dict[str, Any]] = []
    receipt_outputs: list[dict[str, Any]] = []
    export_outputs: list[dict[str, Any]] = []
    provenance_files: list[dict[str, Any]] = []
    for index, (frame_id, role, target) in enumerate(FRAME_ORDER):
        data = frames[frame_id]
        bbox = data["alpha_bbox"]
        pivot = pivots[index]
        filename = f"scout-{frame_id}.png"
        geometry_frames.append(
            {
                "frame_id": f"scout-{frame_id}",
                "image": f"frames/{filename}",
                "rect": {"x": 0, "y": 0, "width": width, "height": height},
                "alpha_bbox": bbox,
                "pivot": {"x": pivot[0], "y": pivot[1], "space": "pixels"},
                "footline_px": footlines[index],
                "safe_rect": bbox,
                "bleed_margin_px": 0,
                "sha256": data["sha256"],
            }
        )
        record = frame_entry(frame_id, role, target, filename, data, relative_output)
        receipt_outputs.append({key: value for key, value in record.items() if key != "target"})
        export_outputs.append(record)
        provenance_files.append(
            {
                "path": record["path"],
                "role": record["role"],
                "sha256": record["sha256"],
                "bytes": record["bytes"],
            }
        )

    controls = {
        "schema_version": "0.1",
        "control_id": "scout-ai-pilot-controls-v1",
        "asset_id": ASSET_ID,
        "created_at": timestamp,
        "references": [{"id": "scout-idle-master", "path": f"{relative_output}/frames/scout-idle.png", "sha256": idle_hash, "role": "identity"}],
        "tracks": [
            {"id": "identity-lock", "kind": "identity", "binding": "required", "value_hash": idle_hash, "samples": 1},
            {"id": "style-lock", "kind": "style", "binding": "advisory", "value_hash": style_hash, "samples": 4},
            {"id": "pose-motion", "kind": "pose", "binding": "required", "value_hash": motion_hash, "samples": 4},
        ],
        "output_profile": {"kind": "frame_sequence", "fps": 8, "expected_frame_count": 4, "loop": True},
    }
    provenance = {
        "schema_version": "1.0",
        "provenance_id": "scout-ai-pilot-provenance-v1",
        "task_id": provider_task_id,
        "scene": "scout-walk",
        "created_at": timestamp,
        "asset": {"id": ASSET_ID, "path": f"{relative_output}/frames/scout-idle.png", "type": "frame_sequence", "framework": "canvas", "version": "pilot-v1"},
        "authority": "ai_generated",
        "readiness": "runtime_ready",
        "generator": {"model": provider_model, "task_id": provider_task_id, "source": provider["generator_source"], "generated_at": timestamp, "prompt_hash": prompt_hash, "agent": "MotionLoom"},
        "license": {"spdx": "LicenseRef-Generated-Pilot", "source": provider["license_source"], "attribution": "AI-generated scout pilot; human review remains required"},
        "files": provenance_files,
        "provenance_chain": [{"step": "ingest", "actor": "MotionLoom", "source": f"post-hoc hash-bound local ingest from {provider['reconstruction_source']}; not a provider-native receipt", "timestamp": timestamp}],
        "runtime_evidence": {"status": "not_run", "runtime": "canvas", "tested_at": timestamp},
    }
    receipt = {
        "schema_version": "0.1",
        "receipt_id": "scout-ai-pilot-receipt-v1",
        "created_at": timestamp,
        "asset": {"id": ASSET_ID, "kind": "frame_sequence", "intended_use": "runtime_candidate"},
        "authority": "ai_generated",
        "provider": {"adapter_id": provider["adapter_id"], "kind": provider["kind"], "invocation_mode": provider["invocation_mode"], "task_id": provider_task_id, "model": provider_model, "generated_at": timestamp, "cost_class": provider["cost_class"], "prompt_hash": prompt_hash},
        "control_track_ref": f"{relative_output}/controls.json",
        "provenance_ref": f"{relative_output}/provenance.json",
        "outputs": receipt_outputs,
    }
    export = {
        "schema_version": "0.1",
        "manifest_id": "scout-ai-pilot-export-v1",
        "asset_id": ASSET_ID,
        "created_at": timestamp,
        "receipt_ref": f"{relative_output}/receipt.json",
        "control_track_ref": f"{relative_output}/controls.json",
        "outputs": export_outputs,
    }
    identity = {
        "schema_version": "0.1",
        "asset_id": ASSET_ID,
        "asset_kind": "character",
        "identity": {
            "subject_id": "scout-robot",
            "reference_hashes": [idle_hash],
            "camera": {"projection": "orthographic", "width": width, "height": height, "focal_length": 1},
            "coordinate_system": "screen_y_down",
            "scale": 1,
            "pivot": {"x": reference_pivot[0] / width, "y": reference_pivot[1] / height, "space": "normalized_canvas"},
            "palette_lock": {"colors": ["#f7e4c6", "#f47c15", "#121116", "#18d8f8"], "delta_e_tolerance": 28},
            "style_profile": "pixel-art scout robot pilot",
            "lighting_profile": "flat game sprite lighting",
        },
        "derivation": {"origin": "ai_generated", "generator": {"model": provider_model, "task_id": provider_task_id, "prompt_hash": prompt_hash}, "source_refs": ["provenance.json", "receipt-reconstruction.json"]},
        "provenance_ref": "provenance.json",
        "notes": "Identity controls are a post-hoc ingest representation. They bind output hashes but do not prove provider-native generation controls.",
    }
    action_set = {
        "schema_version": "0.1",
        "asset_identity": ASSET_ID,
        "actions": [{"action_id": "walk-pilot", "fps": 8, "frames": [f"frames/scout-{frame_id}.png" for frame_id, _, _ in FRAME_ORDER], "loop": True, "events": ["foot_contact_right", "passing", "foot_contact_left"]}],
        "invariants": {"canvas_width": width, "canvas_height": height, "pivot_tolerance_px": pivot_tolerance, "footline_tolerance_px": footline_tolerance, "bbox_drift_tolerance_px": bbox_tolerance, "min_alpha_pixels": min_alpha},
    }
    frame_geometry = {
        "schema_version": "0.1",
        "asset_identity": ASSET_ID,
        "canvas": {"width": width, "height": height, "color_space": "srgb", "alpha_mode": "straight"},
        "invariants": {"pivot_tolerance_px": pivot_tolerance, "footline_tolerance_px": footline_tolerance, "bbox_drift_tolerance_px": bbox_tolerance, "min_alpha_pixels": min_alpha, "allow_external_opaque_pixels": False},
        "frames": geometry_frames,
    }
    candidate = {
        "schema_version": "0.1",
        "candidate_id": "scout-ai-pilot-candidate-v1",
        "asset_id": ASSET_ID,
        "created_at": timestamp,
        "artifact_intake": {"registry": "artifact-adapter-registry.json", "receipt": f"{relative_output}/receipt.json", "controls": f"{relative_output}/controls.json", "export_manifest": f"{relative_output}/export.json"},
        "consistency": {"asset_identity": f"{relative_output}/asset-identity.json", "action_set": f"{relative_output}/action-set.json", "frame_geometry": f"{relative_output}/frame-geometry.json"},
        "runtime": {"target": "canvas", "review_required": True},
    }
    reconstruction = {
        "artifact": ASSET_ID,
        "status": "incomplete_provider_receipt",
        "created_at": timestamp,
        "known": ["output bytes", "output SHA-256", provider["reconstruction_source"], "post-hoc control capsule hash"],
        "unknown": ["provider-native request ID", "provider-native prompt record", "provider-native seed", "provider-native output receipt"],
        "governance": {"authority": "ai_generated", "human_review": "required", "production_approved": False, "attestation_approval": False},
    }
    lab_evidence = {
        "pilot_id": PILOT_ID,
        "asset_id": ASSET_ID,
        "created_at": timestamp,
        "state": "review_required",
        "authority": "ai_generated",
        "production_approved": False,
        "runtime_verified": False,
        "limits": [provider["lab_limit"], "Provider-native generation receipt was unavailable", "Runtime proof is not yet present", "No human approval exists"],
        "frames": [
            {"id": frame_id, "label": role.replace("_", " "), "path": f"frames/scout-{frame_id}.png", "url": urls.get(frame_id), "sha256": frames[frame_id]["sha256"], "alpha_bbox": frames[frame_id]["alpha_bbox"]}
            for frame_id, role, _ in FRAME_ORDER
        ],
    }
    for filename, document in (
        ("controls.json", controls),
        ("provenance.json", provenance),
        ("receipt.json", receipt),
        ("export.json", export),
        ("asset-identity.json", identity),
        ("action-set.json", action_set),
        ("frame-geometry.json", frame_geometry),
        ("candidate.json", candidate),
        ("receipt-reconstruction.json", reconstruction),
        ("devlab-pilot-evidence.json", lab_evidence),
    ):
        write_json(output / filename, document)
    print(json.dumps({"status": "built", "root": str(root), "output": relative_output, "asset_id": ASSET_ID, "frame_count": len(frames), "alpha_geometry": {"footline_range": [min(footlines), max(footlines)], "pivot_tolerance_px": pivot_tolerance, "footline_tolerance_px": footline_tolerance, "bbox_drift_tolerance_px": bbox_tolerance}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
