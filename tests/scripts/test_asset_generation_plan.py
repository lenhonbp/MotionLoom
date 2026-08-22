from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "asset-generation-plan.py"


def load_module():
    spec = importlib.util.spec_from_file_location("asset_generation_plan", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load asset generation planner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def request(canvas=(256, 448), frame_count=8, isolation="required", preferences=None):
    value = {
        "schema_version": "0.1",
        "request_id": "test-request",
        "asset_id": "test-hero-attack",
        "asset_kind": "frame_sequence",
        "target": {
            "canvas": {"width": canvas[0], "height": canvas[1]},
            "frame_count": frame_count,
            "fps": 8,
            "alpha_mode": "straight",
            "pixel_art": True,
            "anchor": "footline",
        },
        "generation_policy": {
            "frame_isolation": isolation,
            "allow_crop": False,
            "allow_stretch": False,
            "allow_silent_resize": False,
            "allow_provider_batch_as_provisional": True,
            "integer_scale_only": True,
        },
        "actions": [{"action_id": "attack", "positive_cues": ["sword swing"], "negative_cues": ["walk", "jump"]}],
    }
    if preferences is not None:
        value["provider_preferences"] = preferences
    return value


def verified_adapter(canvas=(256, 448)):
    return {
        "adapter_id": "verified.single-frame",
        "kind": "external_provider",
        "status": "verified",
        "adapter_version": "0.1",
        "invocation_mode": "api",
        "cost_class": "external",
        "inputs": ["reference"],
        "outputs": ["frame_sequence"],
        "compatibility": {"os": ["linux"]},
        "availability": {"status": "available", "environment": "test"},
        "capabilities": {
            "canvas": {"shapes": ["portrait" if canvas[1] > canvas[0] else "landscape" if canvas[0] > canvas[1] else "square"], "allowed_sizes": [[canvas[0], canvas[1]]], "max_width": canvas[0], "max_height": canvas[1]},
            "frame_behavior": {"mode": "single_frame", "single_frame": True, "max_frames_per_request": 1},
            "adaptation": [],
        },
        "evidence": [{"path": "evidence.md", "sha256": "a" * 64, "kind": "static"}],
        "limitations": [],
        "risk_level": "low",
        "side_effect_level": "read",
    }


def registry_with(adapters, require_verified=True, allow_scaffold_only=False):
    return {
        "schema_version": "0.1",
        "registry_id": "test-registry",
        "generated_at": "2026-08-22T00:00:00Z",
        "selection_policy": {"require_verified": require_verified, "allow_scaffold_only": allow_scaffold_only},
        "adapters": adapters,
    }


def by_id(plan, adapter_id):
    return next(item for item in plan["providers"] if item["adapter_id"] == adapter_id)


def main() -> int:
    production_registry = json.loads((ROOT / "artifact-adapter-registry.json").read_text())
    plan_schema = json.loads((ROOT / "schemas" / "asset-generation-plan.schema.json").read_text())
    check(plan_schema["properties"]["producer"]["const"] == "MotionLoom" and plan_schema["properties"]["schema_version"]["const"] == "0.2", "published plan schema must bind MotionLoom identity and version")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = root / "request.json"
        request_path.write_text(json.dumps(request()))
        registry_path = root / "registry.json"
        registry_path.write_text(json.dumps(production_registry))

        plan = MODULE.build_plan(request(), production_registry, root)
        check(plan["contract"] == "motionloom-asset-generation-plan" and plan["schema_version"] == "0.2", "plan contract must identify MotionLoom plan 0.2")
        check(plan["producer"] == "MotionLoom" and plan["identity"]["product"] == "MotionLoom", "structured plan must preserve MotionLoom identity")
        check(plan["approval"] is False and plan["production_approved"] is False, "planner must never grant approval")
        check(plan["decision"] == "recommendations_available", "normal planning must remain useful without verified execution provider")
        check(plan["execution_decision"] == "no_execution_eligible_route", "default verified-only execution must remain fail-closed")
        check(plan["selection"]["eligible_count"] == 0, "default registry must have no eligible execution provider")
        check(plan["selection"]["provisional_count"] >= 4, "scaffold/manual routes must remain visible as provisional")
        check(plan["selection"]["recommendation_count"] >= 3, "normal planning must expose useful ranked recommendations")
        check("fixture.local-artifact-intake" not in plan["selection"]["recommendation_adapter_ids"], "regression fixture must not be recommended as a generation route")
        check(plan["recommendations"], "normal planning must not collapse to no provider available")
        check(all(item["recommendation_status"] in {"recommended", "acceptable"} for item in plan["recommendations"]), "recommendation list must exclude not-recommended routes")
        check(all(item["approval"] is False for item in plan["recommendations"]), "recommendations must preserve approval=false")
        check(plan["agent_guidance"]["recommended_by"] == "MotionLoom", "plan-level guidance must identify MotionLoom")
        check(plan["project"]["runtime"] is None and plan["project"]["framework"] is None, "synthetic test request without project context should remain explicit")
        check(any("MotionLoom" in step for step in plan["next_steps"]), "next steps must use MotionLoom workflow identity")

        pix = by_id(plan, "pixellab.animate-skeleton")
        check(pix["recommendation_status"] == "recommended" and pix["execution_status"] == "provisional", "PixelLab may be recommended while execution remains provisional")
        check(pix["execution_eligible"] is False, "PixelLab must not be execution-eligible under verified-only policy")
        check(pix["canvas"]["status"] == "adaptation_required", "PixelLab skeleton must reject non-square native target")
        check(pix["frames"]["status"] == "provisional_batch_only", "batch PixelLab output must remain provisional under required isolation")
        pad = next(option for option in pix["adaptation_options"] if option["id"] == "deterministic-pad-to-target")
        check(pad["source_canvas"] == [256, 256] and pad["target_canvas"] == [256, 448], "planner must propose explicit 256x256 to 256x448 padding")
        check(pad["crop"] is False and pad["stretch"] is False, "planner must forbid crop and stretch")
        check("action-separation" in pad["requires_validation"], "adaptation must require action separation validation")
        check(pix["availability"]["status"] == "unknown", "PixelLab availability must not be fabricated")
        check(pix["agent_guidance"]["recommended_by"] == "MotionLoom", "route guidance must identify MotionLoom")

        manual = by_id(plan, "manual.import-frame-sequence")
        check(manual["recommendation_status"] in {"recommended", "acceptable"}, "manual fallback must remain a normal planning option")
        check(manual["execution_status"] == "provisional", "manual route remains provisional without runtime evidence")
        check(manual["availability"]["status"] == "known", "manual route availability should be explicit")

        create_text = by_id(plan, "pixellab.create-animated-object-character")
        check(create_text["frames"]["frame_count_policy"] == "depends_on_canvas_size", "PixelLab create-from-text frame policy must be dynamic")
        create_text_adapter = next(item for item in production_registry["adapters"] if item["adapter_id"] == "pixellab.create-animated-object-character")
        small_canvas_frames = MODULE.frame_assessment(create_text_adapter, MODULE.target_summary(request(canvas=(128, 128), frame_count=4)), request()["generation_policy"])
        check(small_canvas_frames["max_frames_per_request"] == 4 and small_canvas_frames["limits_by_canvas"], "planner must resolve declared dynamic frame limit for an exact PixelLab canvas")
        existing_text_adapter = next(item for item in production_registry["adapters"] if item["adapter_id"] == "pixellab.animate-with-text")
        existing_text = by_id(plan, "pixellab.animate-with-text")
        check(existing_text["frames"]["frame_count_policy"] == "fixed" and existing_text["frames"]["max_frames_per_request"] == 4, "PixelLab animate-existing-reference route must model its documented four-frame output")

        preferred_request = request(preferences={"preferred_adapter_ids": ["pixellab.animate-skeleton"]})
        preferred_plan = MODULE.build_plan(preferred_request, production_registry, root)
        preferred_pix = by_id(preferred_plan, "pixellab.animate-skeleton")
        check(preferred_pix["user_preference"] == {"state": "preferred", "requested": True}, "explicit user preference must be visible")
        check(preferred_pix["recommendation_status"] == "recommended", "preferred provisional provider may be recommended")
        check(preferred_pix["execution_status"] == "provisional" and preferred_pix["execution_eligible"] is False, "preference must not promote provisional execution")
        check(any("preferred by the user" in reason for reason in preferred_pix["rationale"]), "rationale must explain preferred route")
        check(preferred_pix["ranking_score"] >= 8 and any(item["adapter_id"] == "pixellab.animate-skeleton" for item in preferred_plan["recommendations"]), "preferred compatible provisional route should receive a strong explainable ranking signal without overriding a safer native route")

        incompatible_request = request(preferences={"preferred_adapter_ids": ["internal.imagegen"]})
        incompatible_plan = MODULE.build_plan(incompatible_request, production_registry, root)
        incompatible = by_id(incompatible_plan, "internal.imagegen")
        check(incompatible["user_preference"]["state"] == "preferred", "incompatible preference must remain visible")
        check(incompatible["recommendation_status"] == "not_recommended" and incompatible["execution_status"] == "blocked", "hard-incompatible preferred route must be blocked")
        check("internal.imagegen" not in incompatible_plan["selection"]["recommendation_adapter_ids"], "incompatible preferred route must not be recommended")
        check(incompatible_plan["recommendations"], "safer alternatives must remain available")
        check(any("does not declare canvas capability" in reason for reason in incompatible["rationale"]), "incompatibility rationale must explain missing canvas capability")

        excluded_request = request(preferences={"excluded_adapter_ids": ["manual.import-frame-sequence"]})
        excluded_plan = MODULE.build_plan(excluded_request, production_registry, root)
        excluded = by_id(excluded_plan, "manual.import-frame-sequence")
        check(excluded["user_preference"]["state"] == "excluded" and excluded["recommendation_status"] == "not_recommended", "excluded preference must be honored without affecting other routes")
        check("manual.import-frame-sequence" not in excluded_plan["selection"]["recommendation_adapter_ids"], "excluded route must not be recommended")

        unavailable_registry = registry_with([copy.deepcopy(next(item for item in production_registry["adapters"] if item["adapter_id"] == "pixellab.animate-skeleton"))], require_verified=False, allow_scaffold_only=True)
        unavailable_registry["adapters"][0]["availability"] = {"status": "unavailable", "reason": "connector not configured"}
        unavailable_plan = MODULE.build_plan(request(), unavailable_registry, root)
        unavailable = unavailable_plan["providers"][0]
        check(unavailable["recommendation_status"] == "recommended" and unavailable["execution_status"] == "blocked", "unavailable compatible route may remain a recommendation but cannot execute")
        check(unavailable_plan["recommendations"][0]["route"] == "resolve_availability_first", "unavailable route must instruct the Agent to resolve availability")

        unknown_preference = request(preferences={"preferred_adapter_ids": ["future.provider"]})
        unknown_plan = MODULE.build_plan(unknown_preference, production_registry, root)
        check(unknown_plan["selection"]["unknown_preferred_adapter_ids"] == ["future.provider"], "unknown preferred provider must be surfaced without fabrication")
        check(any("future.provider" in warning for warning in unknown_plan["warnings"]), "unknown preference warning must be human-readable")

        cli = subprocess.run([
            sys.executable, str(MODULE_PATH), "plan", "--request", str(request_path), "--registry", str(registry_path), "--project-root", str(root), "--json", "--strict"
        ], capture_output=True, text=True)
        strict_output = json.loads(cli.stdout)
        check(cli.returncode == 2 and strict_output["execution_decision"] == "no_execution_eligible_route", "strict mode must fail without execution-eligible provider")

        human = subprocess.run([
            sys.executable, str(MODULE_PATH), "plan", "--request", str(request_path), "--registry", str(registry_path), "--project-root", str(root)
        ], capture_output=True, text=True)
        check(human.returncode == 0 and "MotionLoom Project Assessment" in human.stdout and "MotionLoom Recommendations" in human.stdout and "MotionLoom Agent Guidance" in human.stdout, "human CLI must expose MotionLoom identity and guidance")

        permitted = copy.deepcopy(production_registry)
        permitted["selection_policy"] = {"require_verified": False, "allow_scaffold_only": True}
        next(item for item in permitted["adapters"] if item["adapter_id"] == "pixellab.animate-skeleton")["availability"] = {"status": "available", "environment": "test-connector"}
        permitted_plan = MODULE.build_plan(request(), permitted, root)
        permitted_pix = by_id(permitted_plan, "pixellab.animate-skeleton")
        check(permitted_pix["execution_status"] == "provisional" and permitted_pix["execution_eligible"] is True, "policy may authorize scaffold execution while preserving provisional status")
        check(any(item["adapter_id"] == "pixellab.animate-skeleton" for item in permitted_plan["recommendations"]), "permitted scaffold provider may be ranked")

        verified = verified_adapter()
        verified_plan = MODULE.build_plan(request(), registry_with([verified]), root)
        check(verified_plan["decision"] == "compatible_execution_route_available", "verified native provider must produce execution route")
        check(verified_plan["selection"]["eligible_adapter_ids"] == ["verified.single-frame"], "verified provider must be execution-eligible")
        check(verified_plan["recommendations"][0]["execution_status"] == "verified" and verified_plan["recommendations"][0]["route"] == "use_native", "verified native route must be recommended with verified status")

        unknown = copy.deepcopy(production_registry)
        unknown["adapters"] = [next(item for item in production_registry["adapters"] if item["adapter_id"] == "internal.imagegen")]
        unknown_plan = MODULE.build_plan(request(), unknown, root)
        unknown_item = unknown_plan["providers"][0]
        check(unknown_plan["decision"] == "no_safe_recommendation_available", "unknown-only provider set must not produce a false recommendation")
        check(unknown_item["execution_status"] == "blocked" and any("does not declare canvas capability" in warning for warning in unknown_item["warnings"]), "unknown capabilities must be blocked and surfaced")

        oversized = copy.deepcopy(next(item for item in production_registry["adapters"] if item["adapter_id"] == "pixellab.animate-skeleton"))
        oversized["adapter_id"] = "provider.oversized-square"
        oversized["capabilities"]["canvas"]["allowed_sizes"] = [[384, 384]]
        oversized_plan = MODULE.build_plan(request(), registry_with([oversized], require_verified=False, allow_scaffold_only=True), root)
        oversized_assessment = oversized_plan["providers"][0]
        check(oversized_assessment["execution_status"] == "blocked", "source exceeding target width must be blocked")
        check(not oversized_assessment["adaptation_options"] and "no declared safe canvas adaptation strategy" in oversized_assessment["hard_failures"], "384x384 source must not be recommended for 256x448 padding")

        landscape_plan = MODULE.build_plan(request(canvas=(448, 256), frame_count=2), registry_with([existing_text_adapter], require_verified=False, allow_scaffold_only=True), root)
        landscape = landscape_plan["providers"][0]
        check(any(option["target_canvas"] == [448, 256] for option in landscape["adaptation_options"]), "landscape target must receive explicit adaptation assessment")

        request_path.write_text(json.dumps(request(canvas=(128, 128), frame_count=1)))
        contextual = copy.deepcopy(request())
        contextual["project_context"] = {"runtime": "game-runtime", "framework": "canvas", "existing_assets": ["assets/hero.png"], "rig_requirements": ["footline"], "provenance_requirements": ["receipt"], "validation_requirements": ["MotionLoom Dev Lab"]}
        contextual_plan = MODULE.build_plan(contextual, production_registry, root)
        check(contextual_plan["project"]["runtime"] == "game-runtime" and contextual_plan["project"]["framework"] == "canvas", "project context must flow into MotionLoom assessment")
        check(contextual_plan["project"]["requested_existing_assets"] == ["assets/hero.png"] and contextual_plan["project"]["validation_requirements"] == ["MotionLoom Dev Lab"], "project asset and validation requirements must remain visible")

        cli_native = subprocess.run([
            sys.executable, str(MODULE_PATH), "plan", "--request", str(request_path), "--registry", str(registry_path), "--project-root", str(root), "--json"
        ], capture_output=True, text=True)
        check(cli_native.returncode == 0 and json.loads(cli_native.stdout)["approval"] is False, "CLI must preserve approval=false")
    print("asset generation planner contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
