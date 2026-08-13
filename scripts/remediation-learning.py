#!/usr/bin/env python3
"""Record and summarize user-confirmed remediation and benchmark history.

The history is an append-only JSONL ledger. Each event carries a hash of its
canonical payload and the hash of the previous event. This makes the ledger
portable and inspectable without introducing a database or treating metrics as
approval. Only explicitly user-confirmed remediation outcomes contribute to
acceptance metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "0.1"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def event_digest(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_sha256"}
    return sha256_bytes(canonical(payload))


def history_path(raw: str | None) -> Path:
    return (Path(raw).expanduser() if raw else ROOT / "artifacts" / "remediation-history.jsonl").resolve()


def output_path(raw: str | None, default_name: str) -> Path:
    return (Path(raw).expanduser() if raw else ROOT / "artifacts" / default_name).resolve()


def read_history(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], []
    if path.is_symlink():
        return [], ["history path must not be a symlink"]
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    previous: str | None = None
    seen: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        return [], [f"history read failed: {error}"]
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            errors.append(f"line {line_number}: invalid JSON: {error.msg}")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {line_number}: event must be an object")
            continue
        event_id = str(event.get("event_id", ""))
        if not event_id:
            errors.append(f"line {line_number}: event_id is required")
        if event_id in seen:
            errors.append(f"line {line_number}: duplicate event_id {event_id}")
        seen.add(event_id)
        if event.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"line {line_number}: unsupported schema_version")
        if event.get("previous_event_sha256") != previous:
            errors.append(f"line {line_number}: previous_event_sha256 does not match ledger head")
        expected = event_digest(event)
        if event.get("event_sha256") != expected:
            errors.append(f"line {line_number}: event_sha256 mismatch")
        previous = expected
        events.append(event)
    return events, errors


def append_event(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    events, errors = read_history(path)
    if errors:
        raise ValueError("cannot append to invalid history: " + "; ".join(errors))
    event = dict(event)
    event.setdefault("schema_version", SCHEMA_VERSION)
    event.setdefault("recorded_at", now())
    event["previous_event_sha256"] = events[-1].get("event_sha256") if events else None
    event["event_sha256"] = event_digest(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise ValueError("history path must not be a symlink")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return event


def file_ref(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    result: dict[str, Any] = {"path": str(path)}
    if path.is_file():
        result["sha256"] = sha256_bytes(path.read_bytes())
        result["bytes"] = path.stat().st_size
        result["exists"] = True
    else:
        result["exists"] = False
    return result


def cmd_record_outcome(args: argparse.Namespace) -> int:
    if args.correction_count < 0:
        raise ValueError("correction-count must be >= 0")
    event = append_event(history_path(args.history), {
        "event_id": args.event_id,
        "event_type": "remediation_outcome",
        "issue_id": args.issue_id,
        "issue_class": args.issue_class or args.issue_id.split(".", 1)[0],
        "summary": args.summary,
        "root_cause": args.root_cause or "",
        "resolution": args.resolution or "",
        "result": args.result,
        "correction_count": args.correction_count,
        "first_pass_accepted": args.result == "pass" and args.correction_count == 0,
        "rerun_scope": args.rerun_scope or [],
        "user_confirmed": True,
        "source_task_id": args.source_task_id,
        "evidence": [ref for raw in (args.evidence or []) if (ref := file_ref(raw))],
    })
    emit({"status": "recorded", "event": event}, args.json)
    return 0


def cmd_record_benchmark(args: argparse.Namespace) -> int:
    if args.iterations <= 0 or args.p95_ms < 0 or args.threshold_ms <= 0:
        raise ValueError("benchmark iterations must be > 0, p95-ms must be >= 0 and threshold-ms must be > 0")
    event = append_event(history_path(args.history), {
        "event_id": args.event_id,
        "event_type": "benchmark_run",
        "operation": args.operation,
        "task_id": args.task_id,
        "scene": args.scene,
        "iterations": args.iterations,
        "p95_ms": args.p95_ms,
        "threshold_ms": args.threshold_ms,
        "status": args.status or ("pass" if args.p95_ms < args.threshold_ms else "fail"),
        "provenance": file_ref(args.evidence),
    })
    emit({"status": "recorded", "event": event}, args.json)
    return 0


def percentile(values: list[int | float], fraction: float) -> int | float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return ordered[index]


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def cmd_summary(args: argparse.Namespace) -> int:
    path = history_path(args.history)
    events, errors = read_history(path)
    if errors:
        emit({"status": "fail", "history": str(path), "errors": errors}, args.json)
        return 1
    outcomes = [event for event in events if event.get("event_type") == "remediation_outcome"]
    confirmed = [event for event in outcomes if event.get("user_confirmed") is True]
    benchmarks = [event for event in events if event.get("event_type") == "benchmark_run"]
    passes = [event for event in confirmed if event.get("result") == "pass"]
    first_passes = [event for event in confirmed if event.get("first_pass_accepted") is True]
    corrections = [int(event.get("correction_count", 0)) for event in confirmed]
    p95_corrections = percentile(corrections, 0.95)
    outlier_threshold = max(3, int(p95_corrections or 0))
    outliers = [
        {"event_id": event.get("event_id"), "issue_id": event.get("issue_id"), "correction_count": event.get("correction_count")}
        for event in confirmed if int(event.get("correction_count", 0)) >= outlier_threshold and int(event.get("correction_count", 0)) > 0
    ]
    by_issue_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in confirmed:
        by_issue_class[str(event.get("issue_class") or "unknown")].append(event)
    issue_summary = {}
    for issue_class, items in sorted(by_issue_class.items()):
        issue_passes = sum(item.get("result") == "pass" for item in items)
        issue_first_passes = sum(item.get("first_pass_accepted") is True for item in items)
        issue_summary[issue_class] = {
            "outcomes": len(items),
            "passes": issue_passes,
            "success_rate": rate(issue_passes, len(items)),
            "first_pass_acceptance_rate": rate(issue_first_passes, len(items)),
            "average_correction_count": round(sum(int(item.get("correction_count", 0)) for item in items) / len(items), 4),
        }
    benchmark_passes = sum(event.get("status") == "pass" for event in benchmarks)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "summary_id": f"remediation-summary-{path.stem}",
        "status": "pass",
        "history_path": str(path),
        "history_sha256": sha256_bytes(path.read_bytes()) if path.is_file() else None,
        "generated_at": now(),
        "ledger": {"event_count": len(events), "outcomes": len(outcomes), "confirmed_outcomes": len(confirmed), "ignored_unconfirmed_outcomes": len(outcomes) - len(confirmed), "benchmarks": len(benchmarks)},
        "remediation": {
            "passes": len(passes),
            "success_rate": rate(len(passes), len(confirmed)),
            "first_pass_acceptances": len(first_passes),
            "first_pass_acceptance_rate": rate(len(first_passes), len(confirmed)),
            "average_correction_count": round(sum(corrections) / len(corrections), 4) if corrections else None,
            "p95_correction_count": p95_corrections,
            "outlier_threshold": outlier_threshold,
            "outliers": outliers,
            "by_issue_class": issue_summary,
        },
        "benchmarks_summary": {
            "runs": len(benchmarks),
            "passes": benchmark_passes,
            "pass_rate": rate(benchmark_passes, len(benchmarks)),
            "operations": sorted({str(event.get("operation")) for event in benchmarks}),
        },
        "approval": False,
    }
    if args.output:
        write_json(output_path(args.output, "remediation-summary.json"), summary)
    emit(summary, args.json)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = history_path(args.history)
    events, errors = read_history(path)
    result = {"status": "pass" if not errors else "fail", "history": str(path), "event_count": len(events), "errors": errors, "approval": False}
    emit(result, args.json)
    return 0 if not errors else 1


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def emit(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(value, ensure_ascii=False))


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--history", help="Append-only JSONL history path")
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MotionLoom remediation and benchmark history")
    sub = parser.add_subparsers(dest="command", required=True)
    outcome = sub.add_parser("record-outcome", help="Record an explicitly user-confirmed remediation outcome")
    add_common(outcome)
    outcome.add_argument("--event-id", required=True)
    outcome.add_argument("--issue-id", required=True)
    outcome.add_argument("--issue-class")
    outcome.add_argument("--summary", required=True)
    outcome.add_argument("--root-cause")
    outcome.add_argument("--resolution")
    outcome.add_argument("--result", choices=["pass", "fail", "partial", "unknown"], required=True)
    outcome.add_argument("--correction-count", type=int, default=0)
    outcome.add_argument("--rerun-scope", action="append")
    outcome.add_argument("--source-task-id")
    outcome.add_argument("--evidence", action="append")
    outcome.add_argument("--user-confirmed", action="store_true", required=True)
    outcome.set_defaults(func=cmd_record_outcome)
    benchmark = sub.add_parser("record-benchmark", help="Record a deterministic benchmark run")
    add_common(benchmark)
    benchmark.add_argument("--event-id", required=True)
    benchmark.add_argument("--operation", required=True)
    benchmark.add_argument("--task-id", required=True)
    benchmark.add_argument("--scene", required=True)
    benchmark.add_argument("--iterations", type=int, required=True)
    benchmark.add_argument("--p95-ms", type=float, required=True)
    benchmark.add_argument("--threshold-ms", type=float, required=True)
    benchmark.add_argument("--status", choices=["pass", "fail"])
    benchmark.add_argument("--evidence")
    benchmark.set_defaults(func=cmd_record_benchmark)
    summary = sub.add_parser("summary", help="Aggregate confirmed outcomes and benchmark history")
    add_common(summary)
    summary.add_argument("--output")
    summary.set_defaults(func=cmd_summary)
    validate = sub.add_parser("validate", help="Verify the append-only hash chain")
    add_common(validate)
    validate.set_defaults(func=cmd_validate)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError) as error:
        print(f"MotionLoom remediation contract error: {error}", file=sys.stderr)
        return 11


if __name__ == "__main__":
    raise SystemExit(main())
