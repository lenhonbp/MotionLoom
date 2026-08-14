import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "runtime-candidate.py"
CANDIDATE_PATH = ROOT / "examples/agent-consumer/runtime-candidate/hero-walk-candidate.json"


def load_module():
    spec = importlib.util.spec_from_file_location("runtime_candidate", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load runtime candidate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def evaluate(path: Path, strict: bool = False) -> dict:
    return MODULE.validate_candidate(SimpleNamespace(root=ROOT, input=path, strict=strict))


def write(path: Path, document: dict) -> Path:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        temp = Path(td)
        candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
        public = evaluate(CANDIDATE_PATH)
        check(public["runtime_test_ready"] and public["status"] == "review_required", "hash-bound public candidate must be runtime-test-ready and review-required")
        check(not public["runtime_verified"], "candidate without runtime evidence must not self-assert runtime verification")
        check(not public["production_eligible"] and not public["production_approved"], "candidate bridge must never grant production authority")

        strict = evaluate(CANDIDATE_PATH, strict=True)
        check(not strict["runtime_test_ready"] and any(item["code"] == "runtime_evidence_required" for item in strict["errors"]), "strict candidate validation must require passing runtime evidence")

        wrong_asset = copy.deepcopy(candidate)
        wrong_asset["asset_id"] = "character/not-hero"
        wrong_asset_path = write(temp / "wrong-asset.json", wrong_asset)
        mismatch = evaluate(wrong_asset_path)
        check(not mismatch["runtime_test_ready"] and any(item["code"] in {"asset_id_mismatch", "consistency_asset_id_mismatch"} for item in mismatch["errors"]), "candidate asset ID must bind receipt, export and consistency contracts")

        missing_geometry = copy.deepcopy(candidate)
        del missing_geometry["consistency"]["frame_geometry"]
        missing_geometry_path = write(temp / "missing-geometry.json", missing_geometry)
        geometry = evaluate(missing_geometry_path)
        check(not geometry["runtime_test_ready"] and any(item["code"] == "missing_profile_contract" for item in geometry["errors"]), "frame sequence candidate must require frame geometry evidence")

        no_review = copy.deepcopy(candidate)
        no_review["runtime"]["review_required"] = False
        no_review_path = write(temp / "no-review.json", no_review)
        review = evaluate(no_review_path)
        check(not review["runtime_test_ready"] and any(item["code"] == "review_required" for item in review["errors"]), "candidate cannot suppress human review")

        evidence = {
            "schema_version": "1.0", "run_id": "fixture-runtime", "generated_at": "2026-08-15T00:00:00Z",
            "mode": "runtime", "harness": "fixture", "status": "pass",
            "frameworks": [{"run_id": "fixture-runtime", "framework": "sprite", "runtime": "fixture", "status": "pass", "ready": True, "frames": [0, 50, 100]}]
        }
        evidence_path = temp / "runtime-evidence.json"
        write(evidence_path, evidence)
        verified_candidate = copy.deepcopy(candidate)
        verified_candidate["runtime"]["runtime_evidence_ref"] = f"{temp.name}/runtime-evidence.json"
        verified_path = write(temp / "verified.json", verified_candidate)
        verified = evaluate(verified_path, strict=True)
        check(verified["runtime_test_ready"] and verified["runtime_verified"], "strict candidate may be runtime-verified only with passing evidence")

        cli = subprocess.run([sys.executable, str(MODULE_PATH), "validate", "--root", str(ROOT), "--input", str(CANDIDATE_PATH), "--json"], capture_output=True, text=True)
        cli_result = json.loads(cli.stdout)
        check(cli.returncode == 0 and cli_result["status"] == "review_required", "CLI must expose review-required candidate evidence")
    print("runtime candidate contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
