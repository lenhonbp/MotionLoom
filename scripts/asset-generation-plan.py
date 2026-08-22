#!/usr/bin/env python3
"""Plan provider-aware asset generation without invoking a provider.

The planner is intentionally advisory: it turns project intent and registry
capabilities into explicit options and adaptation steps. It never transfers
credentials, calls an API, changes image bytes, or grants approval.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


CONTRACT = "motionloom-asset-generation-plan"
SCHEMA_VERSION = "0.1"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON document must be an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_relative(path: str, root: Path) -> bool:
    candidate = Path(path)
    if candidate.is_absolute():
        return False
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def detect_project_contracts(root: Path) -> dict[str, Any]:
    checks = {
        "action_separation": root / "scripts" / "action-separation.py",
        "frame_generation_lock": root / "schemas" / "frame-generation-lock.schema.json",
        "asset_identity": root / "schemas" / "asset-identity.schema.json",
        "frame_geometry": root / "schemas" / "frame-geometry.schema.json",
        "asset_provenance": root / "schemas" / "asset-provenance.schema.json",
        "artifact_intake": root / "schemas" / "generation-receipt.schema.json",
        "devlab": root / "dev-lab" / "public" / "devlab.js",
    }
    present = [name for name, path in checks.items() if path.exists()]
    missing = [name for name, path in checks.items() if not path.exists()]
    return {
        "root": str(root),
        "detected_contracts": present,
        "missing_contracts": missing,
        "recommendations": [
            "bind generation receipt, control track and export manifest before ingest" if "artifact_intake" in present else "add artifact-intake contracts before provider integration",
            "require action manifest and independent frame envelopes" if "action_separation" in present else "add action-scoped envelopes for multi-action frame sequences",
            "measure real PNG geometry before runtime" if "frame_geometry" in present else "add deterministic frame-geometry measurement",
            "keep generated output review_required and approval=false" if "asset_provenance" in present else "add provenance and human-review boundary",
        ],
    }


def target_summary(request: dict[str, Any]) -> dict[str, Any]:
    target = request.get("target") or {}
    canvas = target.get("canvas") or {}
    width = int(canvas.get("width", 0))
    height = int(canvas.get("height", 0))
    return {
        "width": width,
        "height": height,
        "shape": "square" if width == height else "portrait" if height > width else "landscape",
        "area": width * height,
        "frame_count": int(target.get("frame_count", 1)),
        "fps": target.get("fps"),
        "alpha_mode": target.get("alpha_mode"),
        "pixel_art": bool(target.get("pixel_art", False)),
        "anchor": target.get("anchor", "footline"),
    }


def allowed_size_match(canvas: dict[str, Any], width: int, height: int) -> bool | None:
    allowed = canvas.get("allowed_sizes")
    if allowed is None:
        return None
    pairs = {(int(item[0]), int(item[1])) for item in allowed if isinstance(item, list) and len(item) == 2}
    return (width, height) in pairs


def source_fits(source_width: int, source_height: int, target: dict[str, Any], scale: int = 1) -> bool:
    return source_width * scale <= target["width"] and source_height * scale <= target["height"]


def selection_class(adapter: dict[str, Any], selection_policy: dict[str, Any]) -> str:
    status = adapter.get("status")
    if status == "disabled":
        return "blocked"
    if status == "verified":
        return "eligible"
    if selection_policy.get("require_verified", True):
        return "provisional"
    if status == "scaffold_only" and not selection_policy.get("allow_scaffold_only", False):
        return "provisional"
    return "eligible" if status in {"verified", "project_integrated", "static_validated"} or (status == "scaffold_only" and selection_policy.get("allow_scaffold_only", False)) else "provisional"


def canvas_assessment(adapter: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    capability = adapter.get("capabilities") or {}
    canvas = capability.get("canvas") or {}
    width, height = target["width"], target["height"]
    if not canvas:
        return {
            "status": "unknown",
            "native": False,
            "reason": "adapter does not declare canvas capability",
            "adaptation_required": True,
        }
    shape_ok = not canvas.get("shapes") or target["shape"] in canvas.get("shapes", [])
    max_ok = width <= int(canvas.get("max_width", width)) and height <= int(canvas.get("max_height", height))
    exact = allowed_size_match(canvas, width, height)
    if exact is False:
        native = False
    else:
        native = shape_ok and max_ok
    if exact is True:
        reason = "target canvas is explicitly supported"
    elif not shape_ok:
        reason = f"target shape {target['shape']} is not in provider-supported shapes {canvas.get('shapes', [])}"
    elif not max_ok:
        reason = "target exceeds provider-declared maximum canvas"
    elif exact is False:
        reason = "target canvas is not in provider's explicit allowed sizes"
    else:
        reason = "provider declares a compatible canvas range but not an exact size list"
    return {
        "status": "native" if native else "adaptation_required",
        "native": native,
        "reason": reason,
        "provider_canvas": canvas,
        "adaptation_required": not native,
    }


def frame_assessment(adapter: dict[str, Any], target: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    behavior = (adapter.get("capabilities") or {}).get("frame_behavior") or {}
    count = target["frame_count"]
    if not behavior:
        return {
            "status": "unknown",
            "single_frame": False,
            "max_frames_per_request": None,
            "frame_count_policy": "unknown",
            "reason": "adapter does not declare frame isolation behavior",
        }
    max_frames = behavior.get("max_frames_per_request")
    single = bool(behavior.get("single_frame", False))
    enough = single or (isinstance(max_frames, int) and max_frames >= count)
    if policy.get("frame_isolation") == "required" and not single:
        status = "provisional_batch_only" if policy.get("allow_provider_batch_as_provisional") else "blocked_for_isolation"
    elif enough:
        status = "native"
    else:
        status = "batch_split_required"
    return {
        "status": status,
        "single_frame": single,
        "max_frames_per_request": max_frames,
        "frame_count_policy": behavior.get("frame_count_policy", "fixed" if max_frames is not None else "unknown"),
        "declared_mode": behavior.get("mode"),
        "reason": "provider can emit one source frame per request" if single else "provider emits multiple frames; per-frame envelopes must be created after export",
    }


def adaptation_options(adapter: dict[str, Any], target: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    declared = ((adapter.get("capabilities") or {}).get("adaptation") or [])
    canvas = ((adapter.get("capabilities") or {}).get("canvas") or {})
    allowed = canvas.get("allowed_sizes") or []
    square_sizes = sorted({int(pair[0]) for pair in allowed if isinstance(pair, list) and len(pair) == 2 and pair[0] == pair[1]})
    fitting_sizes = [size for size in square_sizes if source_fits(size, size, target, 1)]
    source_size = max(fitting_sizes, default=0)
    if target["width"] != target["height"] and source_size and ("pad_to_target" in declared or canvas):
        options.append({
            "id": "deterministic-pad-to-target",
            "kind": "deterministic_adaptation",
            "source_canvas": [source_size, source_size],
            "target_canvas": [target["width"], target["height"]],
            "operation": "generate on a compatible source canvas, preserve aspect ratio, then place on transparent target canvas",
            "anchor": target["anchor"],
            "stretch": False,
            "crop": False,
            "approval": False,
            "requires_validation": ["alpha-bounds", "pivot-footline", "frame-geometry", "action-separation"],
        })
    if policy.get("integer_scale_only") and source_size:
        max_scale = min(target["width"] // source_size, target["height"] // source_size)
        if max_scale >= 2:
            options.append({
                "id": "integer-upscale-and-pad",
                "kind": "deterministic_adaptation",
                "operation": "integer nearest-neighbour upscale only, followed by transparent padding",
                "source_canvas": [source_size, source_size],
                "target_canvas": [target["width"], target["height"]],
                "scale": max_scale,
                "stretch": False,
                "crop": False,
                "approval": False,
                "requires_validation": ["pixel-grid", "alpha-bounds", "frame-geometry"],
            })
    if "provider_native_resize" in declared:
        options.append({
            "id": "provider-native-resize",
            "kind": "provider_operation",
            "operation": "use provider-native resize only when the selected adapter declares API evidence for it",
            "stretch": False,
            "crop": False,
            "requires_provider_evidence": True,
            "approval": False,
        })
    if "tile_stitch" in declared:
        options.append({
            "id": "tile-and-stitch",
            "kind": "multi_request_adaptation",
            "operation": "generate bounded tiles and stitch only with explicit overlap, seam and identity contracts",
            "stretch": False,
            "crop": False,
            "requires_validation": ["tile-seam", "identity", "action-separation"],
            "risk": "high",
            "approval": False,
        })
    return options


def assess_adapter(adapter: dict[str, Any], target: dict[str, Any], policy: dict[str, Any], requested_kind: str, selection_policy: dict[str, Any]) -> dict[str, Any]:
    capabilities = adapter.get("capabilities") or {}
    outputs = set(adapter.get("outputs") or [])
    selection_status = selection_class(adapter, selection_policy)
    kind_ok = requested_kind in outputs or requested_kind.replace("_", "-") in outputs or requested_kind in {"image", "frame_sequence"} and "image" in outputs
    canvas = canvas_assessment(adapter, target)
    frames = frame_assessment(adapter, target, policy)
    hard_failures: list[str] = []
    warnings: list[str] = []
    if not kind_ok:
        hard_failures.append(f"adapter does not declare output kind {requested_kind}")
    if policy.get("frame_isolation") == "required" and frames["status"] == "blocked_for_isolation":
        hard_failures.append("required per-frame isolation is not supported by the declared provider behavior")
    if canvas["adaptation_required"]:
        warnings.append(canvas["reason"])
    if adapter.get("status") not in {"verified", "project_integrated"}:
        warnings.append(f"adapter status is {adapter.get('status')}; real provider/runtime evidence is still required")
    options = adaptation_options(adapter, target, policy)
    if canvas["adaptation_required"] and not options:
        hard_failures.append("no declared safe canvas adaptation strategy")
    if hard_failures:
        selection_status = "blocked"
    return {
        "adapter_id": adapter.get("adapter_id"),
        "status": adapter.get("status"),
        "selection_status": selection_status,
        "eligible": selection_status == "eligible" and not hard_failures,
        "kind": adapter.get("kind"),
        "invocation_mode": adapter.get("invocation_mode"),
        "cost_class": adapter.get("cost_class"),
        "kind_compatible": kind_ok,
        "canvas": canvas,
        "frames": frames,
        "hard_failures": hard_failures,
        "warnings": warnings,
        "adaptation_options": options,
        "limitations": adapter.get("limitations", []),
        "evidence": adapter.get("evidence", []),
        "docs": capabilities.get("official_docs", []),
        "approval": False,
    }


def build_plan(request: dict[str, Any], registry: dict[str, Any], root: Path) -> dict[str, Any]:
    target = target_summary(request)
    policy = request.get("generation_policy") or {}
    adapters = registry.get("adapters") if isinstance(registry.get("adapters"), list) else []
    selection_policy = registry.get("selection_policy") if isinstance(registry.get("selection_policy"), dict) else {}
    assessments = [assess_adapter(adapter, target, policy, request.get("asset_kind", "image"), selection_policy) for adapter in adapters if isinstance(adapter, dict)]
    eligible = [item for item in assessments if item["eligible"]]
    provisional = [item for item in assessments if item["selection_status"] == "provisional"]
    blocked = [item for item in assessments if item["selection_status"] == "blocked"]
    if eligible and any(item["canvas"]["native"] and item["frames"]["status"] == "native" for item in eligible):
        decision = "compatible_provider_available"
    elif eligible:
        decision = "adaptation_required_or_review_required"
    else:
        decision = "no_eligible_provider_meets_hard_constraints"
    recommendations: list[dict[str, Any]] = []
    for item in sorted(eligible, key=lambda value: value["adapter_id"])[:5]:
        if item in recommendations:
            continue
        rank = 0
        if item["selection_status"] == "eligible":
            rank += 4
        if item["canvas"]["native"]:
            rank += 3
        if item["frames"]["status"] == "native":
            rank += 3
        if item["hard_failures"]:
            rank -= 10
        recommendations.append({
            "adapter_id": item["adapter_id"],
            "rank": rank,
            "route": "use_native" if item["canvas"]["native"] and item["frames"]["status"] == "native" else "use_with_explicit_adaptation",
            "why": item["warnings"] or ["declared capability matches request"],
            "adaptation_options": item["adaptation_options"],
            "hard_failures": item["hard_failures"],
            "approval": False,
        })
    recommendations.sort(key=lambda item: item["rank"], reverse=True)
    next_steps = [
        "Keep this output as a plan only; do not send credentials or invoke a provider from the planner.",
        "If adaptation is selected, record source_canvas, target_canvas, anchor and transform in the export manifest.",
        "Generate or import each frame with its own hash-bound envelope when frame_isolation is required.",
        "Run frame geometry, asset consistency and action-separation validation before Dev Lab review.",
        "Keep production_approved and approval false until a human reviews the runtime candidate.",
    ]
    if decision == "no_eligible_provider_meets_hard_constraints":
        next_steps.insert(0, "No provider satisfies the active registry selection policy. Choose a verified adapter, explicitly allow scaffold-only research routing, or relax the isolation/geometry requirement; do not silently crop or stretch.")
    return {
        "contract": CONTRACT,
        "schema_version": SCHEMA_VERSION,
        "status": "plan_only",
        "decision": decision,
        "approval": False,
        "production_approved": False,
        "request": {
            "request_id": request.get("request_id"),
            "asset_id": request.get("asset_id"),
            "asset_kind": request.get("asset_kind"),
            "target": target,
            "generation_policy": policy,
            "actions": request.get("actions", []),
        },
        "project": detect_project_contracts(root),
        "registry": {
            "path": str((root / "artifact-adapter-registry.json").resolve()),
            "selection_policy": registry.get("selection_policy", {}),
        },
        "providers": assessments,
        "selection": {
            "policy": selection_policy,
            "eligible_count": len(eligible),
            "provisional_count": len(provisional),
            "eligible_adapter_ids": [item["adapter_id"] for item in eligible],
            "provisional_adapter_ids": [item["adapter_id"] for item in provisional],
            "blocked_count": len(blocked),
            "blocked_adapter_ids": [item["adapter_id"] for item in blocked],
        },
        "recommendations": recommendations,
        "next_steps": next_steps,
        "warnings": [
            "Provider capability metadata is advisory until backed by real export and target-runtime evidence.",
            "A provider-native batch animation is not equivalent to isolated per-frame generation.",
            "Padding preserves content; crop and non-uniform stretch are forbidden by this request.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan provider-aware MotionLoom asset generation without invoking providers")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="build a provider/canvas adaptation plan")
    plan.add_argument("--request", required=True, type=Path)
    plan.add_argument("--registry", type=Path, default=None)
    plan.add_argument("--project-root", type=Path, default=Path.cwd())
    plan.add_argument("--output", type=Path, default=None)
    plan.add_argument("--strict", action="store_true", help="return non-zero when no route meets hard constraints")
    plan.add_argument("--json", action="store_true", help="emit machine-readable JSON (default output)")
    args = parser.parse_args(argv)
    if args.command != "plan":
        parser.error("unsupported command")
    root = args.project_root.resolve()
    registry_path = (args.registry or (root / "artifact-adapter-registry.json")).resolve()
    try:
        request_path = args.request.resolve()
        try:
            request_path.relative_to(root)
        except ValueError as exc:
            raise ValueError("--request must resolve inside --project-root") from exc
        request = read_json(request_path)
        registry = read_json(registry_path)
        result = build_plan(request, registry, root)
    except ValueError as exc:
        print(json.dumps({"contract": CONTRACT, "status": "invalid", "approval": False, "errors": [str(exc)]}, indent=2))
        return 2
    if args.output:
        write_json(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.strict and result["decision"] == "no_eligible_provider_meets_hard_constraints":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
