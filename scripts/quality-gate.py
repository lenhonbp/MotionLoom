#!/usr/bin/env python3
"""Acceptance gate for a scene in src/output.

This gate is intentionally stricter than the exploratory Dev Lab: it requires
one project context, a JSON motion spec bound to that context, a manifest,
runtime snapshots (not placeholders), and a completed checklist.
"""

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFE_SCENE = re.compile(r"^[A-Za-z0-9._-]+$")
sys.path.insert(0, str(ROOT / "scripts"))
from intelligence import validate_task_benchmark, validate_task_intelligence, validate_task_p1  # noqa: E402
sys.path.insert(0, str(ROOT / "src"))
from core.spec import validate_spec  # noqa: E402


def _load_validator():
    path = ROOT / "scripts" / "validate-lottie.py"
    loader = importlib.util.spec_from_file_location("validate_lottie", path)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    return module


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}")


def validate_scene(scene_dir: Path, context_path: Path, require_review: bool = False, task_dir: Path | None = None, require_intelligence: bool = False, require_p1: bool = False, require_benchmark: bool = False) -> list[str]:
    issues = []
    manifest_path = scene_dir / "manifest.json"
    spec_path = scene_dir / "motion-spec.json"
    if not manifest_path.exists():
        issues.append("missing manifest.json")
        return issues
    if not spec_path.exists():
        issues.append("missing motion-spec.json; markdown specs cannot prove context binding")
        return issues
    if not context_path.exists():
        issues.append(f"missing project context: {context_path}")
        return issues
    try:
        manifest = _json(manifest_path)
        spec = _json(spec_path)
    except ValueError as exc:
        return [str(exc)]

    issues.extend(validate_spec(str(spec_path), str(context_path)))
    context = _json(context_path)
    if spec.get("context_binding", {}).get("name") != context.get("name"):
        issues.append("spec context name does not match project-context.json")
    if spec.get("theme", {}).get("primary") != (context.get("brand") or {}).get("primary"):
        issues.append("spec primary color does not match project-context.json")
    if manifest.get("framework") and manifest["framework"] != spec.get("framework"):
        issues.append("manifest.framework does not match motion-spec.framework")
    if manifest.get("category") and manifest["category"] != spec.get("category"):
        issues.append("manifest.category does not match motion-spec.category")
    if not spec.get("source_binding"):
        issues.append("motion spec has no source_binding")
    if not (spec.get("accessibility") or {}).get("reduced_motion"):
        issues.append("motion spec has no reduced-motion policy")

    checks = manifest.get("checks")
    if not isinstance(checks, list) or not checks:
        issues.append("manifest.checks must contain the Dev Lab quality checklist")
    else:
        failed = [c.get("id", "unnamed") for c in checks if c.get("pass") is not True]
        if failed:
            issues.append(f"Dev Lab checklist has failing/unconfirmed checks: {', '.join(failed)}")

    snapshot_dir = scene_dir / "snapshot"
    required = [snapshot_dir / f"frame-{p:02d}.png" for p in (0, 50, 100)]
    for frame in required:
        if not frame.is_file() or frame.stat().st_size == 0:
            issues.append(f"missing snapshot frame: {frame.name}")
    meta_path = snapshot_dir / ".render-meta.json"
    if not meta_path.exists():
        issues.append("missing snapshot/.render-meta.json")
    else:
        try:
            meta = _json(meta_path)
            if meta.get("mode") != "runtime":
                issues.append("snapshot evidence is not runtime-rendered (placeholder is rejected)")
            if meta.get("scene") != scene_dir.name:
                issues.append("snapshot metadata scene mismatch")
        except ValueError as exc:
            issues.append(str(exc))

    source_name = manifest.get("file")
    source_path_for_evidence = (scene_dir / source_name).resolve() if source_name else scene_dir / "__missing-source__"
    source_sha_for_evidence = ""
    if source_path_for_evidence.is_file() and scene_dir.resolve() in source_path_for_evidence.parents:
        source_sha_for_evidence = hashlib.sha256(source_path_for_evidence.read_bytes()).hexdigest()
    manifest_sha_for_evidence = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    if spec.get("framework") in {"rive", "gsap", "framer-motion"}:
        evidence_name = manifest.get("runtime_evidence")
        if not evidence_name:
            issues.append(f"manifest.runtime_evidence is required for {spec.get('framework')} scenes")
        else:
            evidence_path = (scene_dir / evidence_name).resolve()
            if not evidence_path.is_file() or scene_dir.resolve() not in evidence_path.parents:
                issues.append("manifest.runtime_evidence must point to an existing file inside the scene directory")
            else:
                try:
                    evidence = _json(evidence_path)
                    if evidence.get("mode") != "runtime":
                        issues.append("runtime evidence mode must be runtime")
                    if not evidence.get("run_id"):
                        issues.append("runtime evidence run_id is required")
                    if evidence.get("status") != "pass":
                        issues.append("runtime evidence top-level status must be pass")
                    if evidence.get("framework") and evidence.get("framework") != spec.get("framework"):
                        issues.append("runtime evidence framework does not match motion-spec.framework")
                    if evidence.get("scene") != scene_dir.name:
                        issues.append("runtime evidence scene does not match scene directory")
                    if evidence.get("source_sha256") != source_sha_for_evidence:
                        issues.append("runtime evidence source_sha256 does not match manifest.file")
                    if evidence.get("manifest_sha256") != manifest_sha_for_evidence:
                        issues.append("runtime evidence manifest_sha256 does not match manifest.json")
                    if evidence.get("frameworks"):
                        match = next((item for item in evidence["frameworks"] if item.get("framework") == spec.get("framework")), None)
                        if not match or match.get("status") != "pass" or match.get("ready") is not True:
                            issues.append("runtime evidence does not contain a passing adapter result")
                except ValueError as exc:
                    issues.append(str(exc))

    source_binding = manifest.get("source_binding")
    if not isinstance(source_binding, dict):
        issues.append("manifest.source_binding is required for production scenes")
    else:
        for field in ("kind", "source_path", "authority", "license", "sha256"):
            if not str(source_binding.get(field, "")).strip():
                issues.append(f"manifest.source_binding.{field} is required")
        if source_binding.get("kind") not in {"project", "library", "generated", "fixture", "remote"}:
            issues.append("manifest.source_binding.kind is invalid")

    source = manifest.get("file")
    if not source:
        issues.append("manifest.file is required")
    else:
        source_path = (scene_dir / source).resolve()
        if not source_path.is_file() or scene_dir.resolve() not in source_path.parents:
            issues.append("manifest.file must point to an existing file inside the scene directory")
        else:
            if isinstance(source_binding, dict):
                if source_binding.get("source_path") != source:
                    issues.append("manifest.source_binding.source_path must match manifest.file")
                source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
                if source_binding.get("sha256") != source_sha:
                    issues.append("manifest.source_binding.sha256 does not match manifest.file")
            if spec.get("framework") in ("lottie", "dotlottie") and source_path.suffix in (".json", ".lottie"):
                validator = _load_validator()
                issues.extend(validator.validate(source_path, spec, int(spec.get("performance", {}).get("max_layers", 80))))

        candidate_path = (task_dir / "browser-review.json") if task_dir else (scene_dir / "browser-review.json")
        if not candidate_path.is_file():
            issues.append("missing browser-review.json; runtime render must hand off to the internal browser Agent")
        else:
            try:
                candidate = _json(candidate_path)
                source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
                context_sha = hashlib.sha256(context_path.read_bytes()).hexdigest()
                if candidate.get("scene") != scene_dir.name:
                    issues.append("browser review candidate scene mismatch")
                if task_dir:
                    task = _json(task_dir / "task.json")
                    if candidate.get("task_id") != task.get("task_id"):
                        issues.append("browser review candidate task_id mismatch")
                if candidate.get("source_sha256") != source_sha:
                    issues.append("browser review candidate source_sha256 is stale")
                if candidate.get("context_sha256") not in {context_sha, spec.get("context_binding", {}).get("context_sha256")}:
                    issues.append("browser review candidate context_sha256 is stale")
                if candidate.get("status") not in {"prepared", "opened", "reviewed", "approved"}:
                    issues.append(f"browser review candidate status is not reviewable: {candidate.get('status')}")
                expires_at = candidate.get("expires_at")
                if not expires_at:
                    issues.append("browser review candidate expiry is required")
                else:
                    try:
                        if datetime.now(timezone.utc) > datetime.fromisoformat(expires_at.replace("Z", "+00:00")):
                            issues.append("browser review candidate has expired")
                    except (TypeError, ValueError):
                        issues.append("browser review candidate expiry is invalid")
                if require_review:
                    review_path = (task_dir / "review.json") if task_dir else (scene_dir / "review.json")
                    if not review_path.is_file():
                        issues.append("PR gate requires review.json captured by the browser Agent")
                    else:
                        review = _json(review_path)
                        if review.get("decision") != "approved":
                            issues.append("PR gate requires browser review decision=approved")
                        if review.get("candidate_id") != candidate.get("candidate_id"):
                            issues.append("browser review approves a different candidate")
                        if task_dir:
                            task = _json(task_dir / "task.json")
                            if review.get("task_id") != task.get("task_id"):
                                issues.append("browser review task_id mismatch")
                        if not str(review.get("reviewer") or "").strip():
                            issues.append("browser review reviewer is required")
                        reviewed_at = review.get("reviewed_at")
                        if reviewed_at:
                            try:
                                if datetime.fromisoformat(reviewed_at.replace("Z", "+00:00")) > datetime.fromisoformat(expires_at.replace("Z", "+00:00")):
                                    issues.append("browser review was recorded after candidate expiry")
                            except (TypeError, ValueError):
                                issues.append("browser review reviewed_at is invalid")
                        if candidate.get("status") != "approved":
                            issues.append("PR gate requires browser-review.json status=approved")
            except (ValueError, OSError) as exc:
                issues.append(str(exc))
    if require_intelligence:
        if not task_dir:
            issues.append("Intelligence Core gate requires --task-dir")
        else:
            issues.extend(validate_task_intelligence(task_dir, scene_dir.name))
    if require_p1:
        if not task_dir:
            issues.append("P1 gate requires --task-dir")
        else:
            p1_issues = validate_task_p1(task_dir, scene_dir.name)
            if not all((task_dir / name).is_file() for name in ("semantic-lint-report.json", "continuity-report.json", "fix-plan.json")):
                p1_issues.append("P1 gate requires semantic-lint-report.json, continuity-report.json and fix-plan.json")
            issues.extend(p1_issues)
    if require_benchmark:
        if not task_dir:
            issues.append("benchmark gate requires --task-dir")
        else:
            issues.extend(validate_task_benchmark(task_dir, scene_dir.name))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scene")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--context", default="project-context.json")
    parser.add_argument("--task-dir")
    parser.add_argument("--require-browser-review", action="store_true")
    parser.add_argument("--require-intelligence", action="store_true")
    parser.add_argument("--require-p1", action="store_true")
    parser.add_argument("--require-benchmark", action="store_true")
    args = parser.parse_args()
    if args.scene and (args.scene in {".", ".."} or not SAFE_SCENE.fullmatch(args.scene)):
        print("QUALITY GATE: unsafe scene identifier")
        return 1
    root = Path(args.root).resolve()
    context = Path(args.context)
    if not context.is_absolute():
        context = root / context
    output_root = root / "src" / "output"
    task_dir = Path(args.task_dir).resolve() if args.task_dir else None
    scenes = [root / "src" / "output" / args.scene] if args.scene else sorted(p for p in output_root.iterdir() if p.is_dir()) if output_root.exists() else []
    if not scenes:
        print("QUALITY GATE: no scene outputs found")
        return 0
    failed = False
    for scene_dir in scenes:
        issues = validate_scene(scene_dir, context, args.require_browser_review, task_dir, args.require_intelligence, args.require_p1, args.require_benchmark)
        if issues:
            failed = True
            print(f"REJECTED {scene_dir.name}:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"ACCEPTED {scene_dir.name}: context + spec + runtime snapshots + browser-review candidate + checklist")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
