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


def request(canvas=(256, 448), frame_count=8, isolation="required"):
    return {
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


def verified_adapter(canvas=(256, 448), frame_count=8):
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


def main() -> int:
    production_registry = json.loads((ROOT / "artifact-adapter-registry.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        request_path = root / "request.json"
        request_path.write_text(json.dumps(request()))
        registry_path = root / "registry.json"
        registry_path.write_text(json.dumps(production_registry))

        plan = MODULE.build_plan(json.loads(request_path.read_text()), production_registry, root)
        check(plan["approval"] is False and plan["production_approved"] is False, "planner must never grant approval")
        check(plan["decision"] == "no_eligible_provider_meets_hard_constraints", "verified-only policy must not promote scaffold providers")
        check(plan["selection"]["eligible_count"] == 0, "default registry must have no eligible runtime provider")
        check(plan["selection"]["provisional_count"] >= 3, "scaffold/manual adapters must remain informational provisional")
        check(not any(item["adapter_id"].startswith("pixellab") for item in plan["recommendations"]), "scaffold PixelLab must not be ranked as eligible when policy forbids it")
        pix = next(item for item in plan["providers"] if item["adapter_id"] == "pixellab.animate-skeleton")
        check(pix["selection_status"] == "provisional" and pix["eligible"] is False, "PixelLab scaffold adapter must be provisional under verified-only policy")
        check(pix["canvas"]["status"] == "adaptation_required", "PixelLab skeleton must reject non-square native target")
        check(pix["frames"]["status"] == "provisional_batch_only", "batch PixelLab output must remain provisional under required isolation")
        pad = next(option for option in pix["adaptation_options"] if option["id"] == "deterministic-pad-to-target")
        check(pad["source_canvas"] == [256, 256] and pad["target_canvas"] == [256, 448], "planner must propose explicit 256x256 to 256x448 padding")
        check(pad["crop"] is False and pad["stretch"] is False, "planner must forbid crop and stretch")
        check("action-separation" in pad["requires_validation"], "adaptation must require action separation validation")
        manual = next(item for item in plan["providers"] if item["adapter_id"] == "manual.import-frame-sequence")
        check(manual["selection_status"] == "provisional", "manual fallback is not verified runtime eligibility under default policy")

        cli = subprocess.run([
            sys.executable, str(MODULE_PATH), "plan", "--request", str(request_path), "--registry", str(registry_path), "--project-root", str(root), "--json", "--strict"
        ], capture_output=True, text=True)
        check(cli.returncode == 2 and json.loads(cli.stdout)["decision"] == "no_eligible_provider_meets_hard_constraints", "strict mode must fail without eligible provider")

        permitted = copy.deepcopy(production_registry)
        permitted["selection_policy"] = {"require_verified": False, "allow_scaffold_only": True}
        permitted_plan = MODULE.build_plan(request(), permitted, root)
        permitted_pix = next(item for item in permitted_plan["providers"] if item["adapter_id"] == "pixellab.animate-skeleton")
        check(permitted_pix["selection_status"] == "eligible" and permitted_pix["eligible"] is True, "policy must explicitly permit scaffold provider before eligibility")
        check(any(item["adapter_id"] == "pixellab.animate-skeleton" for item in permitted_plan["recommendations"]), "permitted scaffold provider may be ranked")

        verified = verified_adapter()
        verified_plan = MODULE.build_plan(request(), registry_with([verified]), root)
        check(verified_plan["decision"] == "compatible_provider_available", "verified native provider must be eligible")
        check(verified_plan["selection"]["eligible_adapter_ids"] == ["verified.single-frame"], "verified provider must be the only eligible adapter")
        check(verified_plan["recommendations"][0]["route"] == "use_native", "exact verified target should use native route")

        unknown = copy.deepcopy(production_registry)
        unknown["adapters"] = [next(item for item in production_registry["adapters"] if item["adapter_id"] == "internal.imagegen")]
        unknown_plan = MODULE.build_plan(request(), unknown, root)
        check(unknown_plan["decision"] == "no_eligible_provider_meets_hard_constraints", "unknown provider capabilities must not be treated as compatible")
        check(any("does not declare canvas capability" in warning for item in unknown_plan["providers"] for warning in item["warnings"]), "unknown canvas must be surfaced")

        text_adapter = next(item for item in production_registry["adapters"] if item["adapter_id"] == "pixellab.animate-text")
        text_assessment = MODULE.assess_adapter(text_adapter, MODULE.target_summary(request()), request()["generation_policy"], "frame_sequence", {"require_verified": False, "allow_scaffold_only": True})
        integer = next(option for option in text_assessment["adaptation_options"] if option["id"] == "integer-upscale-and-pad")
        check(integer["source_canvas"] == [128, 128] and integer["scale"] == 2, "128x128 source may use safe integer scale 2 into 256x448")
        check(text_assessment["frames"]["frame_count_policy"] == "depends_on_canvas_size", "PixelLab text frame limits must remain canvas-dependent")

        oversized = copy.deepcopy(next(item for item in production_registry["adapters"] if item["adapter_id"] == "pixellab.animate-skeleton"))
        oversized["adapter_id"] = "provider.oversized-square"
        oversized["capabilities"]["canvas"]["allowed_sizes"] = [[384, 384]]
        oversized_plan = MODULE.build_plan(request(), registry_with([oversized], require_verified=False, allow_scaffold_only=True), root)
        oversized_assessment = oversized_plan["providers"][0]
        check(not oversized_assessment["adaptation_options"], "384x384 source must not be recommended for 256x448 padding")
        check("no declared safe canvas adaptation strategy" in oversized_assessment["hard_failures"], "source exceeding target width must be blocked")

        landscape_plan = MODULE.build_plan(request(canvas=(448, 256), frame_count=2), registry_with([text_adapter], require_verified=False, allow_scaffold_only=True), root)
        landscape = landscape_plan["providers"][0]
        check(any(option["target_canvas"] == [448, 256] for option in landscape["adaptation_options"]), "landscape target must receive explicit adaptation assessment")

        request_path.write_text(json.dumps(request(canvas=(128, 128), frame_count=1)))
        cli_native = subprocess.run([
            sys.executable, str(MODULE_PATH), "plan", "--request", str(request_path), "--registry", str(registry_path), "--project-root", str(root), "--json"
        ], capture_output=True, text=True)
        check(cli_native.returncode == 0 and json.loads(cli_native.stdout)["approval"] is False, "CLI must preserve approval=false")
    print("asset generation planner contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
