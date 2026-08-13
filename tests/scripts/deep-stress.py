#!/usr/bin/env python3
"""Deterministic deep stress audit for MotionLoom Intelligence Core.

This is not a synthetic animation-quality claim and it does not replace real
browser renders. It repeatedly exercises the repository's existing contracts
against the canonical smoke task, with controlled mutations at trust
boundaries. The report separates clean acceptance, expected rejection,
false-positive and false-negative outcomes.

Usage:
  python3 tests/scripts/deep-stress.py --iterations 5000 \
    --report /tmp/motionloom-deep-stress.json
"""

from __future__ import annotations

import argparse
import base64
import copy
import io
import hashlib
import importlib.util
import json
import random
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
TASK_DIR = ROOT / "artifacts/browser-review-smoke-task"
SCENE_DIR = ROOT / "src/output/browser-review-smoke"
CONTEXT_PATH = TASK_DIR / "project-context.json"
ATTESTATION_PATH = TASK_DIR / "attestation.json"
POLICY_PATH = TASK_DIR / "trust-policy.json"

sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


attestation = load_module("attestation", SCRIPTS / "attestation.py")
verifier = load_module("motionloom_attestation_verifier", SCRIPTS / "attestation-verifier.py")
intelligence = load_module("motionloom_intelligence", SCRIPTS / "intelligence.py")
quality_gate = load_module("motionloom_quality_gate", SCRIPTS / "quality-gate.py")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def permute_mapping(value: object, rng: random.Random) -> object:
    if isinstance(value, dict):
        items = [(key, permute_mapping(child, rng)) for key, child in value.items()]
        rng.shuffle(items)
        return dict(items)
    if isinstance(value, list):
        return [permute_mapping(child, rng) for child in value]
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class StressAudit:
    def __init__(self, seed: int, requested_iterations: int) -> None:
        self.seed = seed
        self.requested_iterations = requested_iterations
        self.rng = random.Random(seed)
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.base_statement = read_json(TASK_DIR / "attestation-statement.json")
        self.base_attestation = read_json(ATTESTATION_PATH)
        self.base_policy = read_json(POLICY_PATH)
        self.base_replay = read_json(TASK_DIR / "replay-bundle.json")
        self.base_lint = read_json(TASK_DIR / "semantic-lint-report.json")
        self.base_continuity = read_json(TASK_DIR / "continuity-report.json")
        self.metrics: dict[str, dict] = {}
        self.failures: list[dict] = []

    def _category(self, name: str) -> dict:
        return self.metrics.setdefault(name, {
            "attempts": 0,
            "passed": 0,
            "failed": 0,
            "false_positive": 0,
            "false_negative": 0,
            "latency_ms": [],
            "codes": Counter(),
        })

    def record(self, category: str, expected_accept: bool, actual_accept: bool, code: object = None, detail: str = "", elapsed_ns: int = 0) -> None:
        metric = self._category(category)
        metric["attempts"] += 1
        metric["latency_ms"].append(elapsed_ns / 1_000_000)
        metric["codes"][str(code)] += 1
        correct = expected_accept == actual_accept
        if correct:
            metric["passed"] += 1
        else:
            metric["failed"] += 1
            if expected_accept and not actual_accept:
                metric["false_positive"] += 1
            if not expected_accept and actual_accept:
                metric["false_negative"] += 1
            if len(self.failures) < 100:
                self.failures.append({"category": category, "expected_accept": expected_accept, "actual_accept": actual_accept, "code": code, "detail": detail[:500]})

    def timed(self, category: str, expected_accept: bool, operation) -> None:
        start = time.perf_counter_ns()
        code = None
        detail = ""
        try:
            actual_accept, code, detail = operation()
        except Exception as exc:  # A clean-path exception is a measurable failure, not a harness crash.
            actual_accept = False
            code = "exception"
            detail = f"{type(exc).__name__}: {exc}"
        self.record(category, expected_accept, bool(actual_accept), code, detail, time.perf_counter_ns() - start)

    def run_canonicalization(self, count: int) -> None:
        original = self.base_statement
        expected = attestation.canonical_json_bytes(original)
        for _ in range(count):
            mutated_order = permute_mapping(original, self.rng)
            self.timed("canonical-json-metamorphic", True, lambda value=mutated_order: (
                attestation.canonical_json_bytes(value) == expected, "equal", ""
            ))

    def run_dsse(self, count: int) -> None:
        body = attestation.canonical_json_bytes(self.base_statement)
        pae = attestation.dsse_pae(attestation.PAYLOAD_TYPE, body)
        for index in range(count):
            signature = self.private_key.sign(pae)
            if index % 2 == 0:
                self.timed("dsse-ed25519-roundtrip", True, lambda sig=signature: self._verify_signature(sig, pae))
            else:
                tampered = pae[:-1] + bytes([pae[-1] ^ 1])
                self.timed("dsse-ed25519-tamper", False, lambda sig=signature, payload=tampered: self._verify_signature(sig, payload))

    def _verify_signature(self, signature: bytes, payload: bytes) -> tuple[bool, str, str]:
        try:
            self.public_key.verify(signature, payload)
            return True, "verified", ""
        except InvalidSignature:
            return False, "invalid-signature", "signature rejected"

    def run_statement_contract(self, count: int) -> None:
        for index in range(count):
            statement = copy.deepcopy(self.base_statement)
            expected_accept = index % 3 == 0
            if not expected_accept:
                predicate = statement["predicate"]
                mutation = index % 3
                if mutation == 1:
                    predicate["context_hash"] = "0" * 63
                elif mutation == 2:
                    predicate["evidence"].pop("runtime_telemetry_sha256", None)
            def operation(value=statement):
                try:
                    attestation.validate_statement(value)
                    return True, "valid", ""
                except (ValueError, TypeError, KeyError) as exc:
                    return False, "rejected", str(exc)
            self.timed("statement-contract", expected_accept, operation)

    def run_attestation_verifier(self, count: int) -> None:
        with tempfile.TemporaryDirectory(prefix="motionloom-stress-") as td:
            temp = Path(td)
            attestation_file = temp / "attestation.json"
            policy_file = temp / "trust-policy.json"
            for index in range(count):
                expected_accept = index % 4 == 0
                bundle = copy.deepcopy(self.base_attestation)
                policy = copy.deepcopy(self.base_policy)
                expected_task = "browser-review-smoke-task"
                expected_scene = "browser-review-smoke"
                variant = index % 4
                if variant == 1:
                    bundle["envelope"]["payload_sha256"] = "0" * 64
                elif variant == 2:
                    expected_task = "foreign-task"
                elif variant == 3:
                    key = policy["keys"][0]
                    key["status"] = "revoked"
                    key["revoked_at"] = "2026-08-13T00:00:00Z"
                    key["revocation_reason"] = "deep-stress fault injection"
                attestation_file.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
                policy_file.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
                def operation(task=expected_task, scene=expected_scene):
                    report, code = verifier.verify_attestation(str(attestation_file), str(policy_file), task, scene)
                    return code == verifier.EXIT_OK and report.get("verified") is True, code, "; ".join(report.get("issues", []))
                self.timed("attestation-verifier-boundary", expected_accept, operation)

    def run_quality_and_intelligence(self, count: int) -> None:
        for _ in range(count):
            def quality_operation():
                with redirect_stdout(io.StringIO()):
                    issues = quality_gate.validate_scene(
                        SCENE_DIR,
                        CONTEXT_PATH,
                        require_review=True,
                        task_dir=TASK_DIR,
                        require_intelligence=True,
                        require_p1=True,
                        require_benchmark=True,
                        require_telemetry=True,
                        require_attestation=True,
                    )
                return not issues, "accepted" if not issues else "rejected", "; ".join(issues)
            self.timed("strict-quality-gate-clean", True, quality_operation)

            def intelligence_operation():
                with redirect_stdout(io.StringIO()):
                    issues = intelligence.validate_task_intelligence(TASK_DIR, "browser-review-smoke")
                    issues.extend(intelligence.validate_task_p1(TASK_DIR, "browser-review-smoke"))
                return not issues, "accepted" if not issues else "rejected", "; ".join(issues)
            self.timed("intelligence-p1-clean", True, intelligence_operation)

    def run_fault_injection(self, count: int) -> None:
        """Mutate one canonical artifact at a time and require rejection."""
        categories = [
            "fault-graph-task-id",
            "fault-motion-ir-scene",
            "fault-provenance-task-id",
            "fault-replay-path-escape",
            "fault-p1-fix-plan-hash",
            "fault-p1-wrong-scene",
            "fault-continuity-structure",
            "fault-semantic-structure",
            "fault-attestation-approval",
            "fault-attestation-payload",
        ]
        per_category = max(1, count // len(categories))
        with tempfile.TemporaryDirectory(prefix="motionloom-fault-") as td:
            temp_task = Path(td) / "browser-review-smoke-task"
            shutil.copytree(TASK_DIR, temp_task)
            files = {
                "graph": temp_task / "project-graph.json",
                "motion_ir": temp_task / "motion-ir.json",
                "provenance": temp_task / "provenance.json",
                "replay": temp_task / "replay-bundle.json",
                "fix_plan": temp_task / "fix-plan.json",
                "continuity": temp_task / "continuity-report.json",
                "semantic": temp_task / "semantic-lint-report.json",
                "attestation": temp_task / "attestation.json",
            }
            originals = {name: path.read_text(encoding="utf-8") for name, path in files.items()}

            def write_mutation(name: str, mutate) -> None:
                path = files[name]
                value = json.loads(originals[name])
                mutate(value)
                path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

            def reset(name: str) -> None:
                files[name].write_text(originals[name], encoding="utf-8")

            for _ in range(per_category):
                write_mutation("graph", lambda value: value.__setitem__("task_id", "foreign-task"))
                self.timed("fault-graph-task-id", False, lambda: self._intelligence_reject(temp_task))
                reset("graph")

                write_mutation("motion_ir", lambda value: value.__setitem__("scene", "foreign-scene"))
                self.timed("fault-motion-ir-scene", False, lambda: self._intelligence_reject(temp_task))
                reset("motion_ir")

                write_mutation("provenance", lambda value: value.__setitem__("task_id", "foreign-task"))
                self.timed("fault-provenance-task-id", False, lambda: self._intelligence_reject(temp_task))
                reset("provenance")

                def mutate_replay(value):
                    if value.get("files"):
                        value["files"][0]["path"] = "../../outside.json"
                write_mutation("replay", mutate_replay)
                self.timed("fault-replay-path-escape", False, lambda: self._intelligence_reject(temp_task))
                reset("replay")

                def mutate_fix_plan(value):
                    if value.get("source_reports"):
                        value["source_reports"][0]["sha256"] = "0" * 64
                write_mutation("fix_plan", mutate_fix_plan)
                self.timed("fault-p1-fix-plan-hash", False, lambda: self._p1_reject(temp_task, "browser-review-smoke"))
                reset("fix_plan")

                self.timed("fault-p1-wrong-scene", False, lambda: self._p1_reject(temp_task, "foreign-scene"))

                write_mutation("continuity", lambda value: value.setdefault("summary", {}).__setitem__("scene_count", 99))
                self.timed("fault-continuity-structure", False, lambda: self._continuity_reject(files["continuity"]))
                reset("continuity")

                write_mutation(
                    "semantic",
                    lambda value: value.setdefault("summary", {}).__setitem__(
                        "total", len(value.get("findings", [])) + 1
                    ),
                )
                self.timed("fault-semantic-structure", False, lambda: self._semantic_reject(files["semantic"]))
                reset("semantic")

                write_mutation("attestation", lambda value: value.__setitem__("approval", True))
                self.timed("fault-attestation-approval", False, lambda: self._attestation_reject(files["attestation"]))
                reset("attestation")

                def mutate_payload(value):
                    payload = str(value["envelope"]["payload_base64"])
                    value["envelope"]["payload_base64"] = base64.b64encode(base64.b64decode(payload) + b" ").decode("ascii")
                write_mutation("attestation", mutate_payload)
                self.timed("fault-attestation-payload", False, lambda: self._attestation_reject(files["attestation"]))
                reset("attestation")

    def _intelligence_reject(self, task_dir: Path) -> tuple[bool, str, str]:
        with redirect_stdout(io.StringIO()):
            issues = intelligence.validate_task_intelligence(task_dir, "browser-review-smoke")
        return not issues, "accepted" if not issues else "rejected", "; ".join(issues)

    def _p1_reject(self, task_dir: Path, scene: str) -> tuple[bool, str, str]:
        with redirect_stdout(io.StringIO()):
            issues = intelligence.validate_task_p1(task_dir, scene)
        return not issues, "accepted" if not issues else "rejected", "; ".join(issues)

    def _continuity_reject(self, path: Path) -> tuple[bool, str, str]:
        value = read_json(path)
        issues = intelligence.continuity_validate_data(value)
        return not issues, "accepted" if not issues else "rejected", "; ".join(issues)

    def _semantic_reject(self, path: Path) -> tuple[bool, str, str]:
        value = read_json(path)
        issues = intelligence.semantic_lint_validate_data(value)
        return not issues, "accepted" if not issues else "rejected", "; ".join(issues)

    def _attestation_reject(self, path: Path) -> tuple[bool, str, str]:
        report, code = verifier.verify_attestation(
            str(path), str(POLICY_PATH), "browser-review-smoke-task", "browser-review-smoke"
        )
        return code == verifier.EXIT_OK and report.get("verified") is True, code, "; ".join(report.get("issues", []))

    def run_replay_semantic_and_approval(self, count: int) -> None:
        for _ in range(count):
            self.timed("replay-hash-clean", True, lambda: (
                not intelligence.replay_mismatches(self.base_replay, ROOT), "clean", ""
            ))
            self.timed("semantic-lint-clean", True, lambda: (
                not intelligence.semantic_lint_validate_data(self.base_lint), "clean", ""
            ))
            self.timed("continuity-clean", True, lambda: (
                not intelligence.continuity_validate_data(self.base_continuity), "clean", ""
            ))
            self.timed("approval-invariant", True, lambda: (
                self.base_attestation.get("approval") is False and read_json(TASK_DIR / "attestation-verifier-report.json").get("approval") is False,
                "approval=false", "approval invariant changed"
            ))

    def run(self) -> dict:
        # Exactly 5,000 logical cases at the default. Counts are scaled by the
        # requested budget while preserving broad coverage and deterministic mix.
        budget = max(5000, self.requested_iterations)
        scale = budget / 5000
        self.run_canonicalization(round(600 * scale))
        self.run_dsse(round(500 * scale))
        self.run_statement_contract(round(600 * scale))
        self.run_attestation_verifier(round(1500 * scale))
        self.run_quality_and_intelligence(round(400 * scale))
        self.run_replay_semantic_and_approval(round(475 * scale))
        self.run_fault_injection(round(1000 * scale))

        total = sum(item["attempts"] for item in self.metrics.values())
        passed = sum(item["passed"] for item in self.metrics.values())
        false_positive = sum(item["false_positive"] for item in self.metrics.values())
        false_negative = sum(item["false_negative"] for item in self.metrics.values())
        for item in self.metrics.values():
            latencies = sorted(item.pop("latency_ms"))
            item["p50_ms"] = latencies[len(latencies) // 2] if latencies else 0.0
            item["p95_ms"] = latencies[min(len(latencies) - 1, max(0, round(len(latencies) * 0.95) - 1))] if latencies else 0.0
            item["max_ms"] = latencies[-1] if latencies else 0.0
            item["codes"] = dict(item["codes"])
            item["pass_rate"] = item["passed"] / item["attempts"] if item["attempts"] else 0.0
        return {
            "schema_version": "1.0",
            "audit": "motionloom-deep-stress",
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "seed": self.seed,
            "requested_iterations": self.requested_iterations,
            "actual_iterations": total,
            "fixture": {"task_id": self.base_statement["predicate"]["task_id"], "scene": self.base_statement["predicate"]["scene"]},
            "summary": {
                "passed": passed,
                "failed": total - passed,
                "pass_rate": passed / total if total else 0.0,
                "false_positive": false_positive,
                "false_negative": false_negative,
                "clean_contracts_preserved": false_positive == 0,
                "faults_rejected_without_false_negative": false_negative == 0,
                "approval_false_invariant_preserved": self.metrics.get("approval-invariant", {}).get("failed", 1) == 0,
            },
            "metrics": self.metrics,
            "failures": self.failures,
            "interpretation": {
                "logical_trials": "Each trial executes a real repository validator/helper against canonical fixture bytes or a controlled mutation; this is not a claim that 5,000 browser renders were performed.",
                "false_positive": "A clean canonical case was rejected.",
                "false_negative": "A controlled tamper, binding, revocation or invalid-contract case was accepted.",
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    if args.iterations < 5000:
        parser.error("--iterations must be at least 5000 for the deep audit")
    started = time.perf_counter()
    report = StressAudit(args.seed, args.iterations).run()
    report["wall_time_s"] = round(time.perf_counter() - started, 6)
    output = Path(args.report).expanduser().absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "actual_iterations": report["actual_iterations"], "summary": report["summary"], "wall_time_s": report["wall_time_s"]}, ensure_ascii=False, indent=2))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
