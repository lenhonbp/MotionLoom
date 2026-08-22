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


def main() -> int:
    registry = json.loads((ROOT / "artifact-adapter-registry.json").read_text())
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "scripts").mkdir()
        (root / "schemas").mkdir()
        for name in ("action-separation.py",):
            (root / "scripts" / name).write_text("fixture")
        for name in ("frame-generation-lock.schema.json", "asset-identity.schema.json", "frame-geometry.schema.json", "asset-provenance.schema.json", "generation-receipt.schema.json"):
            (root / "schemas" / name).write_text("{}")
        request_path = root / "request.json"
        request_path.write_text(json.dumps(request()))
        registry_path = root / "registry.json"
        registry_path.write_text(json.dumps(registry))
        plan = MODULE.build_plan(json.loads(request_path.read_text()), registry, root)
        check(plan["approval"] is False and plan["production_approved"] is False, "planner must never grant approval")
        check(plan["decision"] == "adaptation_required_or_review_required", "256x448 PixelLab route should require adaptation/review")
        pix = next(item for item in plan["providers"] if item["adapter_id"] == "pixellab.animate-skeleton")
        check(pix["canvas"]["status"] == "adaptation_required", "PixelLab skeleton must reject non-square native target")
        check(pix["frames"]["status"] == "provisional_batch_only", "batch PixelLab output must remain provisional under required isolation")
        pad = next(option for option in pix["adaptation_options"] if option["id"] == "deterministic-pad-to-target")
        check(pad["source_canvas"] == [256, 256] and pad["target_canvas"] == [256, 448], "planner must propose explicit 256x256 to 256x448 padding")
        check(pad["crop"] is False and pad["stretch"] is False, "planner must forbid crop and stretch")
        check("action-separation" in pad["requires_validation"], "adaptation must require action separation validation")
        check(any(item["adapter_id"] == "manual.import-frame-sequence" for item in plan["providers"]), "planner must expose manual import fallback")
        
        unknown = copy.deepcopy(registry)
        unknown["adapters"] = [next(item for item in registry["adapters"] if item["adapter_id"] == "internal.imagegen")]
        unknown_plan = MODULE.build_plan(request(), unknown, root)
        check(unknown_plan["decision"] == "no_provider_meets_hard_constraints", "unknown provider capabilities must not be treated as compatible")
        check(any("does not declare canvas capability" in warning for item in unknown_plan["providers"] for warning in item["warnings"]), "unknown canvas must be surfaced")

        exact_plan = MODULE.build_plan(request(canvas=(128, 128), frame_count=1), registry, root)
        manual = next(item for item in exact_plan["providers"] if item["adapter_id"] == "manual.import-frame-sequence")
        check(manual["canvas"]["native"] is True and manual["frames"]["single_frame"] is True, "manual single-frame import should fit exact target")

        cli = subprocess.run([
            sys.executable, str(MODULE_PATH), "plan", "--request", str(request_path), "--registry", str(registry_path), "--project-root", str(root), "--json"
        ], capture_output=True, text=True)
        check(cli.returncode == 0, f"planner CLI should emit a plan: {cli.stderr}")
        cli_doc = json.loads(cli.stdout)
        check(cli_doc["contract"] == "motionloom-asset-generation-plan", "CLI contract should be stable")
    print("asset generation planner contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
