#!/usr/bin/env python3
"""Regression checks for the Apple review boundary.

This test intentionally uses only the standard library.  It verifies the
fixtures consumed by native clients are identity-bound and cannot silently
express production approval, PR intent or a machine reviewer.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APPLE = ROOT / "contracts" / "apple"
SHA256 = re.compile(r"^[a-f0-9]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        return
    FAILURES.append(label)
    print(f"FAIL: {label}{': ' + detail if detail else ''}")


def load(relative: str) -> dict:
    return json.loads((APPLE / relative).read_text(encoding="utf-8"))


def assert_exact_keys(payload: dict, expected: set[str], label: str) -> None:
    check(label, set(payload) == expected, f"found={sorted(payload)}")


def assert_evidence(payload: dict, label: str) -> None:
    check(f"{label} evidence keys", set(payload) == {"runtime_evidence_sha256", "candidate_report_sha256"})
    for name, value in payload.items():
        check(f"{label} {name} digest", isinstance(value, str) and SHA256.fullmatch(value) is not None)


def test_schema_policy() -> None:
    launch_schema = load("review-launch-descriptor.schema.json")
    decision_schema = load("review-decision.schema.json")
    check("launch schema is fail-closed", launch_schema.get("additionalProperties") is False)
    check("decision schema is fail-closed", decision_schema.get("additionalProperties") is False)
    check("launch schema allows only read or annotate", launch_schema["properties"]["review_mode"].get("enum") == ["read_only", "annotate"])
    decisions = decision_schema["properties"]["decision"].get("enum", [])
    check("decision schema cannot grant production approval", "production_approved" not in decisions)
    check("decision schema cannot request PR opening", "open_pr" not in decision_schema["properties"])
    reviewer = decision_schema["properties"]["reviewer"]["properties"]["kind"]
    check("decision schema requires human reviewer", reviewer.get("const") == "human")


def test_runtime_pilot_fixture_binding() -> None:
    launch = load("fixtures/review-launch-runtime-pilot.json")
    decision = load("fixtures/review-decision-request-changes.json")
    assert_exact_keys(launch, {"schema_version", "task_id", "candidate_id", "scene", "artifact_base", "task_base", "review_mode", "evidence"}, "launch fixture keys")
    assert_exact_keys(decision, {"schema_version", "decision_id", "task_id", "candidate_id", "evidence", "decision", "annotations", "created_at", "reviewer"}, "decision fixture keys")
    for label, payload in (("launch task", launch["task_id"]), ("launch candidate", launch["candidate_id"]), ("decision task", decision["task_id"]), ("decision candidate", decision["candidate_id"])):
        check(label + " identifier", IDENTIFIER.fullmatch(payload) is not None)
    check("fixture keeps task identity", launch["task_id"] == decision["task_id"])
    check("fixture keeps candidate identity", launch["candidate_id"] == decision["candidate_id"])
    check("fixture keeps evidence identity", launch["evidence"] == decision["evidence"])
    check("fixture decision requests changes", decision["decision"] == "request_changes")
    check("fixture reviewer is human", decision["reviewer"] == {"kind": "human", "display_name": "Fixture Reviewer", "device_id": "fixture-device"})
    assert_evidence(launch["evidence"], "launch")
    assert_evidence(decision["evidence"], "decision")

    runtime_digest = hashlib.sha256((ROOT / "artifacts/runtime-pilot-001/runtime-adapters/runtime-evidence.json").read_bytes()).hexdigest()
    report_digest = hashlib.sha256((ROOT / "artifacts/runtime-pilot-001/runtime-candidate-report.json").read_bytes()).hexdigest()
    check("fixture runtime evidence digest matches bytes", launch["evidence"]["runtime_evidence_sha256"] == runtime_digest)
    check("fixture candidate report digest matches bytes", launch["evidence"]["candidate_report_sha256"] == report_digest)


if __name__ == "__main__":
    test_schema_policy()
    test_runtime_pilot_fixture_binding()
    if FAILURES:
        print(f"apple contract tests: FAIL ({', '.join(FAILURES)})")
        sys.exit(1)
    print("apple contract tests: PASS")
