import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "rig-compatibility.py"
REGISTRY = ROOT / "rig-adapter-registry.json"
FIXTURE = ROOT / "examples/agent-consumer/rig-compatibility/hero-walk-fixture-rig.json"


def load_module():
    spec = importlib.util.spec_from_file_location("rig_compatibility", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rig compatibility")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write(path: Path, document: dict) -> Path:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def evaluate(path: Path, strict: bool = False) -> dict:
    return MODULE.validate(SimpleNamespace(root=ROOT, input=path, registry=REGISTRY, strict=strict))


def main() -> int:
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        temp = Path(td)
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        valid = evaluate(FIXTURE)
        check(valid["ready"] and valid["status"] == "review_required", "public fixture must be contract-valid and review-required")
        check(not valid["runtime_verified"] and not valid["production_eligible"] and not valid["production_approved"], "valid rig evidence must not self-grant runtime or production authority")

        strict = evaluate(FIXTURE, strict=True)
        check(not strict["ready"] and any(item["code"] == "runtime_evidence_required" for item in strict["errors"]), "strict rig validation must require matching runtime evidence")

        bad_hash = copy.deepcopy(fixture)
        bad_hash["source"]["sha256"] = "0" * 64
        bad_hash_path = write(temp / "bad-hash.json", bad_hash)
        hash_result = evaluate(bad_hash_path)
        check(not hash_result["ready"] and any(item["code"] == "sha256_mismatch" for item in hash_result["errors"]), "source hash tampering must fail closed")

        duplicate_socket = copy.deepcopy(fixture)
        duplicate_socket["sockets"].append(dict(duplicate_socket["sockets"][0]))
        duplicate_socket_path = write(temp / "duplicate-socket.json", duplicate_socket)
        socket_result = evaluate(duplicate_socket_path)
        check(not socket_result["ready"] and any(item["code"] == "invalid_socket" for item in socket_result["errors"]), "duplicate sockets must fail")

        missing_event = copy.deepcopy(fixture)
        missing_event["actions"][0]["events"] = ["footstep.left"]
        missing_event_path = write(temp / "missing-event.json", missing_event)
        event_result = evaluate(missing_event_path)
        check(not event_result["ready"] and any(item["code"] == "required_event_missing" for item in event_result["errors"]), "required rig events must be explicit")

        unknown_adapter = copy.deepcopy(fixture)
        unknown_adapter["runtime"]["adapter_id"] = "unknown.adapter"
        unknown_adapter_path = write(temp / "unknown-adapter.json", unknown_adapter)
        adapter_result = evaluate(unknown_adapter_path)
        check(not adapter_result["ready"] and any(item["code"] == "unknown_adapter" for item in adapter_result["errors"]), "unknown rig adapter must fail closed")

        no_review = copy.deepcopy(fixture)
        no_review["runtime"]["review_required"] = False
        no_review_path = write(temp / "no-review.json", no_review)
        review_result = evaluate(no_review_path)
        check(not review_result["ready"] and any(item["code"] == "review_required" for item in review_result["errors"]), "rig contract cannot suppress human review")

        evidence = {
            "schema_version": "1.1", "run_id": "rig-fixture", "generated_at": "2026-08-15T00:00:00Z",
            "mode": "runtime", "harness": "fixture", "status": "pass",
            "frameworks": [{"framework": "sprite", "status": "pass", "ready": True, "frames": [0, 50, 100]}]
        }
        evidence_path = write(temp / "runtime-evidence.json", evidence)
        verified = copy.deepcopy(fixture)
        verified["runtime"]["runtime_evidence_ref"] = f"{temp.name}/{evidence_path.name}"
        verified_path = write(temp / "verified.json", verified)
        verified_result = evaluate(verified_path, strict=True)
        check(verified_result["ready"] and verified_result["runtime_verified"], "strict rig pass requires a matching ready runtime evidence artifact")

        cli = subprocess.run([sys.executable, str(MODULE_PATH), "validate", "--root", str(ROOT), "--input", str(FIXTURE), "--registry", str(REGISTRY), "--json"], capture_output=True, text=True)
        cli_result = json.loads(cli.stdout)
        check(cli.returncode == 0 and cli_result["status"] == "review_required", "rig CLI must return evidence-only review-required state")
    print("rig compatibility contract tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
