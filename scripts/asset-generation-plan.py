#!/usr/bin/env python3
"""Build a MotionLoom project-aware asset generation recommendation.

The planner is advisory: it understands a request, compares it with declared
adapter capabilities, and produces explainable routes for an Agent. It never
transfers credentials, calls a provider, changes image bytes, or grants
approval. Recommendation status and execution status are deliberately
separate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CONTRACT = "motionloom-asset-generation-plan"
SCHEMA_VERSION = "0.2"


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


def detect_project_contracts(root: Path, requested_context: dict[str, Any] | None = None) -> dict[str, Any]:
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
    requested_context = requested_context or {}
    asset_roots = []
    for relative in ("assets", "assets/library", "src/assets", "src/output"):
        if (root / relative).exists():
            asset_roots.append(relative)
    return {
        "root": str(root),
        "runtime": requested_context.get("runtime"),
        "framework": requested_context.get("framework"),
        "existing_asset_roots": asset_roots,
        "requested_existing_assets": requested_context.get("existing_assets", []),
        "rig_requirements": requested_context.get("rig_requirements", []),
        "provenance_requirements": requested_context.get("provenance_requirements", []),
        "validation_requirements": requested_context.get("validation_requirements", []),
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
    limits_by_canvas = behavior.get("limits_by_canvas") or []
    if max_frames is None:
        for limit in limits_by_canvas:
            if isinstance(limit, dict) and limit.get("canvas") == [target["width"], target["height"]]:
                max_frames = limit.get("max_frames_per_request")
                break
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
        "limits_by_canvas": limits_by_canvas,
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


def preference_context(request: dict[str, Any]) -> dict[str, set[str]]:
    raw = request.get("provider_preferences") or {}
    return {
        "preferred": {str(value) for value in raw.get("preferred_adapter_ids", []) if isinstance(value, str)},
        "excluded": {str(value) for value in raw.get("excluded_adapter_ids", []) if isinstance(value, str)},
    }


def availability_assessment(adapter: dict[str, Any]) -> dict[str, Any]:
    raw = adapter.get("availability") if isinstance(adapter.get("availability"), dict) else {}
    status = raw.get("status", "unknown")
    if status not in {"known", "available", "unavailable", "unknown"}:
        status = "unknown"
    result = {
        "status": status,
        "known_to_motionloom": True,
        "executable_in_current_environment": status == "available" if status != "unknown" else None,
    }
    for key in ("environment", "checked_at", "reason"):
        if key in raw:
            result[key] = raw[key]
    if status == "unknown" and "reason" not in result:
        result["reason"] = "registry does not declare current tool connectivity or installation"
    return result


def project_fit(canvas: dict[str, Any], frames: dict[str, Any], hard_failures: list[str], options: list[dict[str, Any]]) -> tuple[str, int]:
    if hard_failures:
        return "low", 0
    score = 0
    if canvas.get("native"):
        score += 4
    elif options:
        score += 2
    if frames.get("status") == "native":
        score += 4
    elif frames.get("status") in {"provisional_batch_only", "batch_split_required"}:
        score += 1
    if not canvas.get("native") and not options:
        score -= 4
    if score >= 7:
        return "high", score
    if score >= 3:
        return "medium", score
    return "low", score


def agent_guidance(adapter: dict[str, Any], target: dict[str, Any], frames: dict[str, Any], options: list[dict[str, Any]], availability: dict[str, Any], execution_status: str) -> dict[str, Any]:
    adapter_id = adapter.get("adapter_id", "selected route")
    steps = ["Use the MotionLoom Project Assessment and preserve this route's declared limitations."]
    if availability["status"] in {"unknown", "unavailable"}:
        steps.append("Resolve tool availability or connector access before execution; MotionLoom cannot claim it can invoke this route from registry metadata alone.")
    if options:
        primary = options[0]
        source = primary.get("source_canvas")
        target_canvas = primary.get("target_canvas")
        if source and target_canvas:
            steps.append(f"Generate or import at source canvas {source[0]}x{source[1]}, then run MotionLoom asset adaptation to {target_canvas[0]}x{target_canvas[1]} with the declared anchor; do not crop or stretch.")
        else:
            steps.append("Apply the declared adaptation only after recording source and target geometry in the MotionLoom export manifest.")
    if frames.get("status") != "native":
        steps.append("Treat batch output as provisional and bind one frame envelope plus independent verifier evidence per accepted frame when isolation is required.")
    if execution_status == "blocked":
        steps.append("Do not execute this route under the current hard constraints; use a MotionLoom-ranked alternative or revise the request explicitly.")
    steps.extend([
        "Run MotionLoom frame geometry and asset consistency validation before packing an atlas.",
        "Run MotionLoom action separation, then review the candidate in MotionLoom Dev Lab.",
        "Keep approval and production_approved false until human review is recorded.",
    ])
    return {
        "recommended_by": "MotionLoom",
        "summary": f"MotionLoom recommends evaluating {adapter_id} through its declared project route; execution status remains {execution_status}.",
        "steps": steps,
        "validation_route": ["MotionLoom frame geometry", "MotionLoom action separation", "MotionLoom Dev Lab review"],
    }


def assess_adapter(adapter: dict[str, Any], target: dict[str, Any], policy: dict[str, Any], requested_kind: str, selection_policy: dict[str, Any], preferences: dict[str, set[str]]) -> dict[str, Any]:
    capabilities = adapter.get("capabilities") or {}
    outputs = set(adapter.get("outputs") or [])
    adapter_id = adapter.get("adapter_id")
    preference = "excluded" if adapter_id in preferences["excluded"] else "preferred" if adapter_id in preferences["preferred"] else "neutral"
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
    status = adapter.get("status")
    if status not in {"verified", "project_integrated"}:
        warnings.append(f"adapter status is {status}; real provider/runtime evidence is still required")
    options = adaptation_options(adapter, target, policy)
    if canvas["adaptation_required"] and not options:
        hard_failures.append("no declared safe canvas adaptation strategy")
    availability = availability_assessment(adapter)
    if availability["status"] == "unavailable":
        warnings.append("adapter is currently marked unavailable; resolve availability before execution")
    elif availability["status"] == "unknown":
        warnings.append("adapter availability is unknown; the Agent must resolve connectivity or installation before execution")

    evidence_status = "verified" if status == "verified" else "provisional"
    if hard_failures or preference == "excluded" or status == "disabled" or availability["status"] == "unavailable":
        execution_status = "blocked"
    elif status == "verified" and availability["status"] == "available":
        execution_status = "verified"
    else:
        execution_status = "provisional"
    execution_eligible = not hard_failures and availability["status"] == "available" and status == "verified"
    if not hard_failures and availability["status"] == "available" and not selection_policy.get("require_verified", True):
        allowed_statuses = {"verified", "project_integrated", "static_validated"}
        if status in allowed_statuses or (status == "scaffold_only" and selection_policy.get("allow_scaffold_only", False)):
            execution_eligible = True
    non_generation_fixture = adapter.get("kind") == "fixture"
    if non_generation_fixture:
        warnings.append("fixture adapter is regression evidence only and is not a user-facing generation route")
    recommendation_status = "not_recommended" if hard_failures or preference == "excluded" or non_generation_fixture else "recommended" if preference == "preferred" or canvas.get("native") or options else "acceptable"
    fit_label, fit_score = project_fit(canvas, frames, hard_failures, options)
    ranking_factors = {
        "project_fit": fit_score,
        "native_canvas": 4 if canvas.get("native") else 0,
        "frame_isolation": 4 if frames.get("status") == "native" else 1 if frames.get("status") in {"provisional_batch_only", "batch_split_required"} else 0,
        "execution_evidence": 3 if status == "verified" else 1,
        "user_preference": 5 if preference == "preferred" else -100 if preference == "excluded" else 0,
        "availability": 1 if availability["status"] == "available" else 0,
        "risk": {"low": 1, "medium": 0, "high": -2}.get(adapter.get("risk_level"), 0),
        "adaptation_cost": -1 if options and not canvas.get("native") else 0,
    }
    ranking_score = sum(ranking_factors.values()) if recommendation_status != "not_recommended" else -1000
    rationale = []
    rationale.append("matches the requested asset kind" if kind_ok else f"does not declare the requested asset kind {requested_kind}")
    rationale.append("matches the target canvas natively" if canvas.get("native") else ("has a declared safe adaptation route" if options else "has no declared safe canvas route"))
    rationale.append("supports isolated frames natively" if frames.get("status") == "native" else "requires provisional batch handling and per-frame evidence")
    rationale.append(f"execution evidence is {execution_status}")
    if preference == "preferred":
        rationale.append("explicitly preferred by the user; preference does not override hard constraints")
    elif preference == "excluded":
        rationale.append("explicitly excluded by the user")
    rationale.append(f"availability is {availability['status']}")
    rationale.extend(warnings)
    legacy_selection = execution_status if execution_status != "verified" else "eligible"
    return {
        "adapter_id": adapter_id,
        "status": status,
        "recommendation_status": recommendation_status,
        "execution_status": execution_status,
        "execution_evidence_status": evidence_status,
        "execution_eligible": execution_eligible,
        "selection_status": legacy_selection,
        "eligible": execution_eligible,
        "user_preference": {"state": preference, "requested": preference != "neutral"},
        "availability": availability,
        "project_fit": fit_label,
        "ranking_score": ranking_score,
        "ranking_factors": ranking_factors,
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
        "rationale": rationale,
        "agent_guidance": agent_guidance(adapter, target, frames, options, availability, execution_status),
        "approval": False,
    }


def recommendation_view(item: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    native = item["canvas"].get("native")
    frame_native = item["frames"].get("status") == "native"
    if item["availability"].get("status") == "unavailable" and item["recommendation_status"] != "not_recommended":
        route = "resolve_availability_first"
    elif item["execution_status"] == "blocked":
        route = "blocked_use_alternative"
    elif native and frame_native and item["execution_status"] == "verified":
        route = "use_native"
    elif native and frame_native:
        route = "use_native_after_review"
    elif item["adaptation_options"]:
        route = "use_with_explicit_adaptation"
    else:
        route = "research_or_manual_review"
    return {
        "adapter_id": item["adapter_id"],
        "rank": item["ranking_score"],
        "recommendation_status": item["recommendation_status"],
        "execution_status": item["execution_status"],
        "execution_evidence_status": item["execution_evidence_status"],
        "execution_eligible": item["execution_eligible"],
        "user_preference": item["user_preference"],
        "availability": item["availability"],
        "project_fit": item["project_fit"],
        "route": route,
        "why": item["rationale"],
        "rationale": item["rationale"],
        "agent_guidance": item["agent_guidance"],
        "adaptation_options": item["adaptation_options"],
        "hard_failures": item["hard_failures"],
        "approval": False,
        "target_canvas": [target["width"], target["height"]],
    }


def build_plan(request: dict[str, Any], registry: dict[str, Any], root: Path) -> dict[str, Any]:
    target = target_summary(request)
    policy = request.get("generation_policy") or {}
    adapters = registry.get("adapters") if isinstance(registry.get("adapters"), list) else []
    selection_policy = registry.get("selection_policy") if isinstance(registry.get("selection_policy"), dict) else {}
    preferences = preference_context(request)
    assessments = [assess_adapter(adapter, target, policy, request.get("asset_kind", "image"), selection_policy, preferences) for adapter in adapters if isinstance(adapter, dict)]
    known_ids = {item["adapter_id"] for item in assessments}
    unknown_preferred = sorted(preferences["preferred"] - known_ids)
    unknown_excluded = sorted(preferences["excluded"] - known_ids)
    rec_candidates = [item for item in assessments if item["recommendation_status"] != "not_recommended"]
    rec_candidates.sort(key=lambda item: (-item["ranking_score"], item["adapter_id"]))
    recommendations = [recommendation_view(item, target) for item in rec_candidates[:5]]
    execution_eligible = [item for item in assessments if item["execution_eligible"]]
    provisional = [item for item in assessments if item["execution_status"] == "provisional"]
    blocked = [item for item in assessments if item["execution_status"] == "blocked"]
    if execution_eligible and any(item["canvas"]["native"] and item["frames"]["status"] == "native" for item in execution_eligible):
        execution_decision = "compatible_execution_route_available"
    elif execution_eligible:
        execution_decision = "execution_route_requires_review_or_adaptation"
    else:
        execution_decision = "no_execution_eligible_route"
    decision = "recommendations_available" if recommendations else "no_safe_recommendation_available"
    if execution_eligible:
        decision = execution_decision
    warnings = [
        "Provider capability metadata is advisory until backed by real export and target-runtime evidence.",
        "A provider-native batch animation is not equivalent to isolated per-frame generation.",
        "Padding preserves content; crop and non-uniform stretch are forbidden by this request.",
    ]
    if unknown_preferred:
        warnings.append(f"requested adapter IDs are unknown to this registry: {', '.join(unknown_preferred)}")
    if unknown_excluded:
        warnings.append(f"excluded adapter IDs are unknown to this registry: {', '.join(unknown_excluded)}")
    if not execution_eligible:
        warnings.append("Normal planning still exposes compatible provisional/manual options; strict execution remains fail-closed because no route satisfies the active execution policy.")
    next_steps = [
        "Keep this MotionLoom assessment as a plan only; do not send credentials or invoke a provider from the planner.",
        "Resolve availability or connector access for any route marked unknown/unavailable before execution.",
        "If adaptation is selected, record source_canvas, target_canvas, anchor and transform in the export manifest.",
        "Generate or import each frame with its own hash-bound envelope when frame_isolation is required.",
        "Run MotionLoom frame geometry, asset consistency and action separation validation before Dev Lab review.",
        "Keep production_approved and approval false until a human reviews the runtime candidate.",
    ]
    return {
        "contract": CONTRACT,
        "schema_version": SCHEMA_VERSION,
        "producer": "MotionLoom",
        "source": "MotionLoom project-aware asset generation planner",
        "identity": {"product": "MotionLoom", "role": "project-aware decision and guidance layer"},
        "status": "plan_only",
        "decision": decision,
        "execution_decision": execution_decision,
        "approval": False,
        "production_approved": False,
        "request": {
            "request_id": request.get("request_id"),
            "asset_id": request.get("asset_id"),
            "asset_kind": request.get("asset_kind"),
            "target": target,
            "generation_policy": policy,
            "actions": request.get("actions", []),
            "project_context": request.get("project_context", {}),
            "provider_preferences": request.get("provider_preferences", {}),
        },
        "project": detect_project_contracts(root, request.get("project_context")),
        "registry": {
            "path": str((root / "artifact-adapter-registry.json").resolve()),
            "selection_policy": selection_policy,
        },
        "providers": assessments,
        "selection": {
            "policy": selection_policy,
            "eligible_count": len(execution_eligible),
            "eligible_adapter_ids": [item["adapter_id"] for item in execution_eligible],
            "provisional_count": len(provisional),
            "provisional_adapter_ids": [item["adapter_id"] for item in provisional],
            "blocked_count": len(blocked),
            "blocked_adapter_ids": [item["adapter_id"] for item in blocked],
            "recommendation_count": len(recommendations),
            "recommendation_adapter_ids": [item["adapter_id"] for item in recommendations],
            "unknown_preferred_adapter_ids": unknown_preferred,
            "unknown_excluded_adapter_ids": unknown_excluded,
        },
        "recommendations": recommendations,
        "agent_guidance": {
            "recommended_by": "MotionLoom",
            "summary": "MotionLoom assessed the project requirements first, then compared available metadata, user preference and execution policy.",
            "next_step": next_steps[1],
            "validation_route": ["MotionLoom frame geometry", "MotionLoom action separation", "MotionLoom Dev Lab review"],
        },
        "next_steps": next_steps,
        "warnings": warnings,
    }


def render_human(result: dict[str, Any]) -> str:
    target = result["request"]["target"]
    lines = [
        "MotionLoom Project Assessment",
        f"Target: {target['width']}x{target['height']} · {target['frame_count']} frames · isolation={result['request']['generation_policy'].get('frame_isolation')}",
        f"Decision: {result['decision']} · Execution: {result['execution_decision']}",
        "",
        "MotionLoom Recommendations",
    ]
    if not result["recommendations"]:
        lines.append("No safe recommendation is available under the declared project constraints.")
    for index, item in enumerate(result["recommendations"], start=1):
        lines.extend([
            f"{index}. {item['adapter_id']}",
            f"   Project fit: {item['project_fit']}",
            f"   Recommendation: {item['recommendation_status']}",
            f"   Execution status: {item['execution_status']}",
            f"   Availability: {item['availability']['status']}",
            f"   Why MotionLoom recommends it: {'; '.join(item['why'][:4])}",
            f"   Agent route: {item['route']}",
            f"   Guidance: {item['agent_guidance']['summary']}",
        ])
    not_recommended = [item for item in result["providers"] if item.get("recommendation_status") == "not_recommended"]
    if not_recommended:
        lines.extend(["", "MotionLoom Evaluated but Not Recommended"])
        for item in not_recommended:
            reason = (item.get("rationale") or item.get("hard_failures") or ["hard constraint or user preference boundary"])[0]
            lines.append(f"- {item['adapter_id']}: execution={item.get('execution_status')} · {reason}")
    lines.extend(["", "MotionLoom Agent Guidance", f"{result['agent_guidance']['summary']}", f"MotionLoom next step: {result['next_steps'][1]}"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a MotionLoom project-aware asset generation recommendation without invoking providers")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="build a provider/canvas recommendation and guarded execution plan")
    plan.add_argument("--request", required=True, type=Path)
    plan.add_argument("--registry", type=Path, default=None)
    plan.add_argument("--project-root", type=Path, default=Path.cwd())
    plan.add_argument("--output", type=Path, default=None)
    plan.add_argument("--strict", action="store_true", help="return non-zero when no execution-eligible route meets hard constraints")
    plan.add_argument("--json", action="store_true", help="emit machine-readable JSON; without it print a human-readable MotionLoom assessment")
    args = parser.parse_args(argv)
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
        print(json.dumps({"contract": CONTRACT, "schema_version": SCHEMA_VERSION, "producer": "MotionLoom", "status": "invalid", "approval": False, "errors": [str(exc)]}, indent=2))
        return 2
    if args.output:
        write_json(args.output.resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else render_human(result))
    if args.strict and result["execution_decision"] == "no_execution_eligible_route":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
