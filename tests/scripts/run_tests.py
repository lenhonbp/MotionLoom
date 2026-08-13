#!/usr/bin/env python3
"""
run_tests.py — Deterministic test suite for the skill's core engine.
Runs without any network or heavy dependencies (pure stdlib).

Usage: python3 tests/scripts/run_tests.py
"""

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FAILED = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILED.append(name)


def test_analyzer_on_fixture():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "package.json").write_text(json.dumps({
            "name": "fixture-app",
            "dependencies": {"framer-motion": "^11.0.0", "react": "^19.0.0"},
        }))
        (p / "tailwind.config.js").write_text(
            "module.exports = { theme: { extend: { colors: { primary: '#2563eb', accent: '#f59e0b' } } } };"
        )
        subprocess.run(
            [sys.executable, str(ROOT / "src/core/analyzer.py"), td],
            check=True, capture_output=True, cwd=td,
        )
        ctx = json.loads((Path(td) / "project-context.json").read_text())
        check("analyzer emits context", ctx.get("name") == "fixture-app")
        check("analyzer detects react stack", ctx.get("stack", {}).get("react") is True)
        check("analyzer detects framer-motion preference", ctx.get("stack", {}).get("framework") == "framer-motion")
        check("analyzer extracts brand primary", ctx.get("brand", {}).get("primary") == "#2563EB")


def test_spec_generate_and_validate():
    with tempfile.TemporaryDirectory() as td:
        ctx = Path(td) / "project-context.json"
        ctx.write_text(json.dumps({
            "schema_version": "1.1",
            "name": "fixture-app",
            "project_root": td,
            "brand": {"primary": "#2563EB", "accent": "#F59E0B"},
            "stack": {"framework": "lottie"},
            "motion_language": {"recommendation": "ease-in-out"},
            "source_authority": "manifest",
        }))
        out = Path(td) / "motion-spec.json"
        subprocess.run(
            [sys.executable, str(ROOT / "src/core/spec.py"), "generate", "loading",
             "--context", str(ctx), "--output", str(out), "--loop"],
            check=True, capture_output=True,
        )
        spec = json.loads(out.read_text())
        check("spec binds category", spec["category"] == "loading")
        check("spec binds framework from stack", spec["framework"] == "lottie")
        check("spec binds brand primary", spec["theme"]["primary"] == "#2563EB")
        check("spec computes total frames", spec["total_frames"] == round(spec["duration_s"] * spec["fps"]))
        check("spec defaults loading to loop", spec["loop"] is True)
        check("spec contains context hash", len(spec.get("context_binding", {}).get("context_sha256", "")) == 64)
        r = subprocess.run([sys.executable, str(ROOT / "src/core/spec.py"), "validate", str(out),
                            "--context", str(ctx)],
                           capture_output=True, text=True)
        check("spec validates clean", r.returncode == 0, r.stdout.strip())


def test_rig_build_and_pose():
    with tempfile.TemporaryDirectory() as td:
        rigged = Path(td) / "rigged.svg"
        subprocess.run(
            [sys.executable, str(ROOT / "src/rig/cutout_rig.py"), "build",
             "--input", str(ROOT / "assets/library/avatar-base.svg"),
             "--output", str(rigged)],
            check=True, capture_output=True,
        )
        doc = rigged.read_text()
        check("rig contains data-bone markers", 'data-bone="hip"' in doc)
        check("rig wraps in data-rig group", 'data-rig="cutout-v1"' in doc)
        try:
            xml_root = ET.fromstring(doc)
            head = xml_root.find('.//*[@data-bone="head"]')
            check("rig is valid XML", head is not None and len(list(head)) == 1)
        except ET.ParseError as exc:
            check("rig is valid XML", False, str(exc))

        clip = Path(td) / "walk.json"
        subprocess.run(
            [sys.executable, str(ROOT / "src/rig/cutout_rig.py"), "pose", str(rigged),
             "--pose", "walk", "--duration", "1.2", "--fps", "30", "--out", str(clip)],
            check=True, capture_output=True,
        )
        data = json.loads(clip.read_text())
        check("pose clip has frames", data["frames"] == 36)
        check("clip starts at rest", data["keyframes"][0]["angles"]["l_thigh"] > 0)
        check("clip reverses at seam", data["keyframes"][-1]["angles"]["l_thigh"] > 0)


def test_lottie_scaffold_valid():
    scaffold = ROOT / "templates/lottie/scaffold/animation.json"
    doc = json.loads(scaffold.read_text())
    check("scaffold has version header", doc.get("v") == "5.12.0")
    check("scaffold has frame metadata", doc.get("fr") == 60 and doc.get("op") == 60)
    check("scaffold has at least one layer", len(doc.get("layers", [])) >= 1)


def test_dotlottie_manifest_selection():
    with tempfile.TemporaryDirectory() as td:
        archive = Path(td) / "multi.lottie"
        valid = {"v": "5.12.0", "fr": 60, "ip": 0, "op": 60, "layers": []}
        unrelated = {"not": "an animation"}
        manifest = {"version": "2", "initial": {"animation": "chosen"}, "animations": [{"id": "chosen"}]}
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest))
            zf.writestr("a/chosen.json", json.dumps(valid))
            zf.writestr("random.json", json.dumps(unrelated))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/validate-lottie.py"), str(archive)],
                                capture_output=True, text=True)
        check("dotLottie follows manifest animation", result.returncode == 0, result.stdout.strip())


def test_dotlottie_packager():
    with tempfile.TemporaryDirectory() as td:
        check("dotLottie packager script is executable", (ROOT / "scripts/to-dotlottie.sh").is_file())
        smoke = ROOT / "src/output/browser-review-smoke"
        archive = Path(td) / "smoke.lottie"
        result = subprocess.run([
            "bash", str(ROOT / "scripts/to-dotlottie.sh"), "browser-review-smoke", str(archive),
        ], cwd=ROOT, capture_output=True, text=True)
        check("dotLottie packager exits cleanly", result.returncode == 0, result.stderr)
        if result.returncode == 0:
            with zipfile.ZipFile(archive) as zf:
                names = set(zf.namelist())
                manifest = json.loads(zf.read("manifest.json"))
                check("dotLottie packager emits root manifest", "manifest.json" in names)
                check("dotLottie packager emits initial animation", "a/animation.json" in names)
                check("dotLottie packager sets v2 initial id", manifest.get("version") == "2" and manifest.get("initial", {}).get("animation") == "animation")
            validate = subprocess.run([
                sys.executable, str(ROOT / "scripts/validate-lottie.py"), str(archive),
                "--spec", str(smoke / "motion-spec.json"),
            ], capture_output=True, text=True)
            check("packaged dotLottie passes validator", validate.returncode == 0, validate.stdout.strip())


def test_source_binding_contract():
    manifest = json.loads((ROOT / "src/output/browser-review-smoke/manifest.json").read_text())
    binding = manifest.get("source_binding", {})
    source = ROOT / "src/output/browser-review-smoke" / manifest.get("file", "")
    import hashlib
    check("scene manifest includes source binding", all(binding.get(key) for key in ("kind", "source_path", "authority", "license", "sha256")))
    check("source binding path matches scene file", binding.get("source_path") == manifest.get("file"))
    check("source binding checksum matches bytes", binding.get("sha256") == hashlib.sha256(source.read_bytes()).hexdigest())

    with tempfile.TemporaryDirectory() as td:
        scene = Path(td) / "src/output/unbound"
        scene.mkdir(parents=True)
        context = Path(td) / "project-context.json"
        context.write_text(json.dumps({"name": "unbound", "project_root": td, "brand": {"primary": "#2563EB"}, "stack": {"framework": "lottie"}, "source_authority": "test"}))
        spec = scene / "motion-spec.json"
        subprocess.run([sys.executable, str(ROOT / "src/core/spec.py"), "generate", "loading", "--context", str(context), "--output", str(spec)], check=True, capture_output=True)
        (scene / "animation.json").write_text((ROOT / "templates/lottie/scaffold/animation.json").read_text())
        (scene / "manifest.json").write_text(json.dumps({"framework": "lottie", "category": "loading", "file": "animation.json", "checks": [{"id": "ok", "pass": True}]}))
        snap = scene / "snapshot"
        snap.mkdir()
        for pct in (0, 50, 100): (snap / f"frame-{pct:02d}.png").write_bytes(b"runtime")
        (snap / ".render-meta.json").write_text(json.dumps({"mode": "runtime", "scene": "unbound"}))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/quality-gate.py"), "--root", td, "--scene", "unbound", "--context", str(context)], capture_output=True, text=True)
        check("quality gate rejects missing source binding", result.returncode != 0 and "source_binding" in result.stdout)


def test_placeholder_is_not_runtime_evidence():
    with tempfile.TemporaryDirectory() as td:
        scene = Path(td) / "src/output/placeholder"
        scene.mkdir(parents=True)
        context = Path(td) / "project-context.json"
        context.write_text(json.dumps({
            "name": "placeholder-test", "project_root": td,
            "brand": {"primary": "#2563EB"}, "stack": {"framework": "lottie"},
            "source_authority": "test",
        }))
        spec = Path(scene / "motion-spec.json")
        subprocess.run([sys.executable, str(ROOT / "src/core/spec.py"), "generate", "loading",
                         "--context", str(context), "--output", str(spec)], check=True, capture_output=True)
        (scene / "animation.json").write_text((ROOT / "templates/lottie/scaffold/animation.json").read_text())
        (scene / "manifest.json").write_text(json.dumps({
            "framework": "lottie", "category": "loading", "file": "animation.json",
            "checks": [{"id": "check", "pass": True}],
        }))
        snap = scene / "snapshot"
        snap.mkdir()
        for pct in (0, 50, 100):
            (snap / f"frame-{pct:02d}.png").write_bytes(b"not-a-real-png")
        (snap / ".render-meta.json").write_text(json.dumps({"mode": "placeholder", "scene": "placeholder"}))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/quality-gate.py"), "--root", td,
                                 "--scene", "placeholder", "--context", str(context)],
                                capture_output=True, text=True)
        check("quality gate rejects placeholder evidence", result.returncode != 0)


def test_runtime_evidence_binding():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        scene = root / "src/output/browser-review-smoke"
        shutil.copytree(ROOT / "src/output/browser-review-smoke", scene)
        context = root / "project-context.json"
        shutil.copy(ROOT / "artifacts/browser-review-smoke-task/project-context.json", context)

        spec_path = scene / "motion-spec.json"
        spec = json.loads(spec_path.read_text())
        spec["framework"] = "gsap"
        spec["category"] = "hero-scene"
        spec_path.write_text(json.dumps(spec, indent=2) + "\n")

        manifest_path = scene / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["framework"] = "gsap"
        manifest["category"] = "hero-scene"
        manifest["runtime_evidence"] = "runtime-evidence.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

        source_sha = hashlib.sha256((scene / "animation.json").read_bytes()).hexdigest()
        manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        evidence = {
            "schema_version": "1.0", "run_id": "test-runtime-run", "mode": "runtime",
            "status": "pass", "scene": scene.name, "source_sha256": source_sha,
            "manifest_sha256": manifest_sha,
            "frameworks": [{"framework": "gsap", "status": "pass", "ready": True}],
        }
        (scene / "runtime-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        accepted = subprocess.run([
            sys.executable, str(ROOT / "scripts/quality-gate.py"), "--root", str(root),
            "--scene", scene.name, "--context", str(context),
        ], capture_output=True, text=True)
        check("quality gate accepts bound runtime evidence", accepted.returncode == 0, accepted.stdout.strip())

        manifest["description"] = "stale manifest mutation"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        stale = subprocess.run([
            sys.executable, str(ROOT / "scripts/quality-gate.py"), "--root", str(root),
            "--scene", scene.name, "--context", str(context),
        ], capture_output=True, text=True)
        check("quality gate rejects stale runtime evidence", stale.returncode != 0 and "manifest_sha256" in stale.stdout)


def test_deep_audit_contracts():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        shutil.copytree(ROOT / "artifacts/browser-review-smoke-task", root / "artifacts/browser-review-smoke-task")
        scenes = root / "changed-scenes"
        scenes.write_text("browser-review-smoke\n")
        contract = subprocess.run([
            sys.executable, str(ROOT / "scripts/report-contract.py"),
            "--root", str(root), "--scenes-file", str(scenes),
        ], capture_output=True, text=True)
        check("report contract accepts tracked smoke bundle", contract.returncode == 0, contract.stdout.strip())

        candidate_path = root / "artifacts/browser-review-smoke-task/browser-review.json"
        candidate = json.loads(candidate_path.read_text())
        candidate["expires_at"] = "2000-01-01T00:00:00Z"
        candidate_path.write_text(json.dumps(candidate))
        expired = subprocess.run([
            sys.executable, str(ROOT / "scripts/review-hook.py"), "validate",
            "--task-dir", str(root / "artifacts/browser-review-smoke-task"), "--require-approved",
        ], capture_output=True, text=True)
        check("review hook rejects expired candidate", expired.returncode != 0 and "expired" in expired.stdout)

    unsafe_runtime = subprocess.run(
        ["node", str(ROOT / "scripts/runtime-adapters.mjs")],
        env={**os.environ, "RUNTIME_FRAMEWORKS": "../../escape"},
        capture_output=True, text=True,
    )
    check("runtime adapter rejects unsupported framework path", unsafe_runtime.returncode != 0 and "unsupported" in (unsafe_runtime.stderr + unsafe_runtime.stdout))


def test_approved_browser_review_e2e_contract():
    """Re-run the acceptance side of a real approved task from a clean copy."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        task_dir = root / "artifacts/professional-review-e2e"
        shutil.copytree(ROOT / "artifacts/professional-review-e2e", task_dir)
        shutil.copytree(ROOT / "src/output/browser-review-smoke", root / "src/output/browser-review-smoke")
        shutil.copy(ROOT / "artifacts/browser-review-smoke-task/project-context.json", root / "project-context.json")

        candidate_path = task_dir / "browser-review.json"
        candidate = json.loads(candidate_path.read_text())
        candidate["expires_at"] = "2099-01-01T00:00:00Z"
        candidate_path.write_text(json.dumps(candidate, indent=2) + "\n")

        review = json.loads((task_dir / "review.json").read_text())
        task = json.loads((task_dir / "task.json").read_text())
        check(
            "e2e task binds approved candidate",
            review.get("candidate_id") == candidate.get("candidate_id")
            and candidate.get("task_id") == task.get("task_id")
            and candidate.get("scene") == task.get("scene"),
        )
        check("e2e task is confirmed", task.get("state") == "confirmed")

        review_hook = subprocess.run([
            sys.executable, str(ROOT / "scripts/review-hook.py"), "validate",
            "--task-dir", str(task_dir), "--require-approved",
        ], capture_output=True, text=True)
        check("e2e review hook accepts approved candidate", review_hook.returncode == 0, review_hook.stdout.strip())

        quality = subprocess.run([
            sys.executable, str(ROOT / "scripts/quality-gate.py"), "--root", str(root),
            "--scene", "browser-review-smoke", "--context", str(root / "project-context.json"),
            "--task-dir", str(task_dir), "--require-browser-review",
        ], capture_output=True, text=True)
        check("e2e quality gate accepts task evidence", quality.returncode == 0, quality.stdout.strip())

        report_check = subprocess.run([
            sys.executable, str(ROOT / "scripts/report.py"), "check", "--task-dir", str(task_dir),
        ], capture_output=True, text=True)
        check("e2e report contract accepts confirmed task", report_check.returncode == 0, report_check.stdout.strip())


def test_intelligence_core_contracts():
    """Exercise the deterministic intelligence layer and its adversarial boundary."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        task_dir = root / "artifacts/professional-review-e2e"
        shutil.copytree(ROOT / "artifacts/professional-review-e2e", task_dir)

        intelligence = ROOT / "scripts/intelligence.py"
        motion_ir = subprocess.run([
            sys.executable, str(intelligence), "motion-ir", "build", "--task-dir", str(task_dir),
            "--spec", str(ROOT / "src/output/browser-review-smoke/motion-spec.json"),
        ], capture_output=True, text=True)
        check("intelligence Motion IR builds", motion_ir.returncode == 0, motion_ir.stdout.strip())
        motion_ir_check = subprocess.run([
            sys.executable, str(intelligence), "motion-ir", "validate",
            "--path", str(task_dir / "motion-ir.json"),
        ], capture_output=True, text=True)
        check("intelligence Motion IR validates", motion_ir_check.returncode == 0, motion_ir_check.stdout.strip())
        graph = subprocess.run([
            sys.executable, str(intelligence), "graph", "build", "--task-dir", str(task_dir),
        ], capture_output=True, text=True)
        check("intelligence graph builds", graph.returncode == 0, graph.stdout.strip())
        graph_check = subprocess.run([
            sys.executable, str(intelligence), "graph", "validate",
            "--path", str(task_dir / "project-graph.json"),
        ], capture_output=True, text=True)
        check("intelligence graph validates", graph_check.returncode == 0, graph_check.stdout.strip())

        provenance = subprocess.run([
            sys.executable, str(intelligence), "provenance", "build", "--task-dir", str(task_dir),
        ], capture_output=True, text=True)
        check("intelligence provenance builds", provenance.returncode == 0, provenance.stdout.strip())
        provenance_check = subprocess.run([
            sys.executable, str(intelligence), "provenance", "validate",
            "--task-dir", str(task_dir), "--path", str(task_dir / "provenance.json"),
        ], capture_output=True, text=True)
        check("intelligence provenance validates", provenance_check.returncode == 0, provenance_check.stdout.strip())

        registry = root / "capability-registry.json"
        capability = subprocess.run([
            sys.executable, str(intelligence), "capabilities", "build",
            "--evidence", str(ROOT / "artifacts/browser-review-smoke-task/quality-report.json"),
            "--evidence-kind", "ci", "--output", str(registry),
        ], capture_output=True, text=True)
        check("intelligence capability registry builds", capability.returncode == 0, capability.stdout.strip())
        registry_check = subprocess.run([
            sys.executable, str(intelligence), "capabilities", "validate", "--path", str(registry),
        ], capture_output=True, text=True)
        check("intelligence capability registry validates", registry_check.returncode == 0, registry_check.stdout.strip())
        selected = subprocess.run([
            sys.executable, str(intelligence), "capabilities", "select",
            "--registry", str(registry), "--capability", "runtime.rive",
        ], capture_output=True, text=True)
        check("intelligence selects verified runtime", selected.returncode == 0 and '"status": "verified"' in selected.stdout)
        scaffold = subprocess.run([
            sys.executable, str(intelligence), "capabilities", "select",
            "--registry", str(registry), "--capability", "runtime.spine",
        ], capture_output=True, text=True)
        check("intelligence blocks scaffold-only runtime", scaffold.returncode != 0)

        stale_registry = json.loads(registry.read_text())
        for entry in stale_registry["capabilities"]:
            if entry.get("status") == "verified":
                entry["last_verified_at"] = "2000-01-01T00:00:00Z"
        stale_path = root / "stale-capability-registry.json"
        stale_path.write_text(json.dumps(stale_registry, indent=2) + "\n")
        stale_select = subprocess.run([
            sys.executable, str(intelligence), "capabilities", "select",
            "--registry", str(stale_path), "--capability", "runtime.rive",
        ], capture_output=True, text=True)
        check("intelligence blocks stale capability evidence", stale_select.returncode != 0)

        tampered_registry = json.loads(registry.read_text())
        rive_entry = next(entry for entry in tampered_registry["capabilities"] if entry.get("id") == "runtime.rive")
        rive_entry["evidence"][0]["sha256"] = "0" * 64
        tampered_path = root / "tampered-capability-registry.json"
        tampered_path.write_text(json.dumps(tampered_registry, indent=2) + "\n")
        tampered_select = subprocess.run([
            sys.executable, str(intelligence), "capabilities", "select",
            "--registry", str(tampered_path), "--capability", "runtime.rive",
        ], capture_output=True, text=True)
        check("intelligence blocks tampered capability evidence", tampered_select.returncode != 0)

        replay = subprocess.run([
            sys.executable, str(intelligence), "replay", "capture",
            "--root", str(root), "--task-dir", str(task_dir),
        ], capture_output=True, text=True)
        check("intelligence replay captures bundle", replay.returncode == 0, replay.stdout.strip())
        replay_check = subprocess.run([
            sys.executable, str(intelligence), "replay", "verify",
            "--root", str(root), "--bundle", str(task_dir / "replay-bundle.json"),
        ], capture_output=True, text=True)
        check("intelligence replay verifies clean bundle", replay_check.returncode == 0, replay_check.stdout.strip())
        review = task_dir / "review.json"
        review.write_text(review.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        tampered = subprocess.run([
            sys.executable, str(intelligence), "replay", "verify",
            "--root", str(root), "--bundle", str(task_dir / "replay-bundle.json"),
        ], capture_output=True, text=True)
        check("intelligence replay rejects tampered artifact", tampered.returncode != 0 and "hash_mismatch" in tampered.stdout)


def test_malformed_spec_is_rejected_cleanly():
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.json"
        bad.write_text(json.dumps({"category": "loading", "framework": "lottie"}))
        result = subprocess.run([sys.executable, str(ROOT / "src/core/spec.py"), "validate", str(bad)],
                                capture_output=True, text=True)
        check("malformed spec exits non-zero", result.returncode != 0)
        check("malformed spec reports issues", "ISSUES:" in result.stdout and "duration_s" in result.stdout)


def test_p1_semantic_continuity_fix_plan():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        task_dir = root / "professional-review-e2e"
        shutil.copytree(ROOT / "artifacts/professional-review-e2e", task_dir)
        intelligence = ROOT / "scripts/intelligence.py"

        lint = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "build", "--task-dir", str(task_dir),
        ], capture_output=True, text=True)
        lint_data = json.loads((task_dir / "semantic-lint-report.json").read_text())
        check("P1 semantic lint builds report", lint.returncode == 0)
        check("P1 semantic lint preserves human keyboard review", lint_data.get("status") == "warn" and any(item.get("id") == "accessibility-keyboard-review" and item.get("basis") == "human" for item in lint_data.get("findings", [])))
        lint_validate = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "validate", "--path", str(task_dir / "semantic-lint-report.json"),
        ], capture_output=True, text=True)
        check("P1 semantic lint validates report", lint_validate.returncode == 0)

        duration_task = root / "duration-budget-task"
        shutil.copytree(task_dir, duration_task)
        duration_ir_path = duration_task / "motion-ir.json"
        duration_ir = json.loads(duration_ir_path.read_text())
        duration_ir["duration_ms"] = 600
        duration_ir_path.write_text(json.dumps(duration_ir, indent=2) + "\n")
        duration_lint = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "build", "--task-dir", str(duration_task),
        ], capture_output=True, text=True)
        duration_report = json.loads((duration_task / "semantic-lint-report.json").read_text())
        check("P1 semantic lint warns on UI animation budget", duration_lint.returncode == 0 and any(item.get("id") == "perf-animation-budget" and item.get("severity") == "warning" and not item.get("approval_blocking") for item in duration_report.get("findings", [])))

        fps_task = root / "fps-task"
        shutil.copytree(task_dir, fps_task)
        fps_ir_path = fps_task / "motion-ir.json"
        fps_ir = json.loads(fps_ir_path.read_text())
        fps_ir["fps"] = 24
        fps_ir_path.write_text(json.dumps(fps_ir, indent=2) + "\n")
        fps_lint = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "build", "--task-dir", str(fps_task),
        ], capture_output=True, text=True)
        fps_report = json.loads((fps_task / "semantic-lint-report.json").read_text())
        check("P1 semantic lint warns below 30 FPS", fps_lint.returncode == 0 and any(item.get("id") == "perf-frame-rate" for item in fps_report.get("findings", [])))

        easing_task = root / "easing-task"
        shutil.copytree(task_dir, easing_task)
        easing_ir_path = easing_task / "motion-ir.json"
        easing_ir = json.loads(easing_ir_path.read_text())
        for keyframe in easing_ir.get("tracks", [])[0].get("keyframes", []):
            keyframe["easing"] = "linear"
        easing_ir_path.write_text(json.dumps(easing_ir, indent=2) + "\n")
        easing_lint = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "build", "--task-dir", str(easing_task),
        ], capture_output=True, text=True)
        easing_report = json.loads((easing_task / "semantic-lint-report.json").read_text())
        check("P1 semantic lint warns on linear UI easing", easing_lint.returncode == 0 and any(item.get("id") == "perceptual-easing-linear" and item.get("severity") == "warning" for item in easing_report.get("findings", [])))

        reduced_task = root / "reduced-motion-task"
        shutil.copytree(task_dir, reduced_task)
        reduced_ir_path = reduced_task / "motion-ir.json"
        reduced_ir = json.loads(reduced_ir_path.read_text())
        reduced_ir.setdefault("accessibility", {})["reduced_motion"] = "none"
        reduced_ir_path.write_text(json.dumps(reduced_ir, indent=2) + "\n")
        reduced_lint = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "build", "--task-dir", str(reduced_task),
        ], capture_output=True, text=True)
        reduced_report = json.loads((reduced_task / "semantic-lint-report.json").read_text())
        check("P1 semantic lint warns on absent reduced-motion fallback", reduced_lint.returncode == 0 and any(item.get("id") == "perceptual-reduced-motion-missing" and not item.get("approval_blocking") for item in reduced_report.get("findings", [])))

        benchmark_path = task_dir / "semantic-lint-benchmark.json"
        benchmark = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "benchmark", "--task-dir", str(task_dir),
            "--iterations", "10", "--threshold-ms", "500", "--output", str(benchmark_path),
        ], capture_output=True, text=True)
        benchmark_data = json.loads(benchmark_path.read_text())
        check("P1 semantic lint benchmark passes threshold", benchmark.returncode == 0 and benchmark_data.get("status") == "pass" and benchmark_data.get("p95_ms", 999999) < benchmark_data.get("threshold_ms", 0))
        benchmark_validate = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "benchmark", "--task-dir", str(task_dir),
            "--iterations", "2", "--threshold-ms", "500", "--output", str(task_dir / "semantic-lint-benchmark-2.json"),
        ], capture_output=True, text=True)
        check("P1 semantic lint benchmark is repeatable", benchmark_validate.returncode == 0)

        ir = json.loads((task_dir / "motion-ir.json").read_text())
        ir["intent"] = "motion"
        (task_dir / "motion-ir.json").write_text(json.dumps(ir, indent=2) + "\n")
        generic_lint = subprocess.run([
            sys.executable, str(intelligence), "semantic-lint", "build", "--task-dir", str(task_dir),
            "--output", str(task_dir / "generic-lint.json"),
        ], capture_output=True, text=True)
        generic_data = json.loads((task_dir / "generic-lint.json").read_text())
        check("P1 semantic lint detects low-specificity intent", generic_lint.returncode == 0 and any(item.get("id") == "intent-low-specificity" for item in generic_data.get("findings", [])))

        fix_plan = subprocess.run([
            sys.executable, str(intelligence), "fix-plan", "build", "--task-dir", str(task_dir),
            "--reports", "generic-lint.json",
        ], capture_output=True, text=True)
        plan = json.loads((task_dir / "fix-plan.json").read_text())
        check("P1 fix plan binds semantic report", fix_plan.returncode == 0 and plan.get("status") == "proposed", f"rc={fix_plan.returncode} stdout={fix_plan.stdout.strip()} stderr={fix_plan.stderr.strip()}")
        check("P1 fix plan declares selective lint rerun", any(issue.get("rerun_scope") == ["lint"] and "intent-low-specificity" in issue.get("finding_ref", "") for issue in plan.get("issues", []) if isinstance(issue, dict)))
        plan_validate = subprocess.run([
            sys.executable, str(intelligence), "fix-plan", "validate", "--path", str(task_dir / "fix-plan.json"),
        ], capture_output=True, text=True)
        check("P1 fix plan validates", plan_validate.returncode == 0)

        first = root / "scene-a"
        second = root / "scene-b"
        shutil.copytree(task_dir, first)
        shutil.copytree(task_dir, second)
        for path, task_id, scene, order in ((first, "p1-scene-a", "scene-a", 0), (second, "p1-scene-b", "scene-b", 1)):
            task = json.loads((path / "task.json").read_text())
            task.update({"task_id": task_id, "scene": scene, "scene_order": order, "project_name": "p1-continuity"})
            (path / "task.json").write_text(json.dumps(task, indent=2) + "\n")
            ir = json.loads((path / "motion-ir.json").read_text())
            ir.update({"task_id": task_id, "scene": scene, "context_hash": task.get("context_hash")})
            (path / "motion-ir.json").write_text(json.dumps(ir, indent=2) + "\n")

        continuity = subprocess.run([
            sys.executable, str(intelligence), "continuity", "build", "--task-dirs", str(first), str(second),
        ], capture_output=True, text=True)
        continuity_data = json.loads((first / "continuity-report.json").read_text())
        check("P1 continuity builds multi-scene report", continuity.returncode == 0 and continuity_data.get("summary", {}).get("transition_count") == 1)
        check("P1 continuity passes matching context", continuity_data.get("status") == "pass")

        second_ir = json.loads((second / "motion-ir.json").read_text())
        second_ir["context_hash"] = "f" * 64
        (second / "motion-ir.json").write_text(json.dumps(second_ir, indent=2) + "\n")
        drift = subprocess.run([
            sys.executable, str(intelligence), "continuity", "build", "--task-dirs", str(first), str(second),
        ], capture_output=True, text=True)
        drift_data = json.loads((first / "continuity-report.json").read_text())
        check("P1 continuity detects context drift", drift.returncode == 0 and drift_data.get("status") == "warn" and "context hash changes between adjacent scenes" in drift_data["transitions"][0].get("findings", []))


def test_category_coverage():
    from src.core.analyzer import CATEGORIES  # noqa
    from docs import __file__ as _  # noqa: guard import path
    required = {"ui-micro", "loading", "hero-scene", "character-body", "icon-animation",
                "scroll-linked", "data-viz", "3d-scene"}
    check("all categories defined", required <= set(CATEGORIES))


def test_observability_contract():
    with tempfile.TemporaryDirectory() as td:
        task_dir = Path(td) / "task"
        report_script = ROOT / "scripts/report.py"
        subprocess.run([
            sys.executable, str(report_script), "init", "--task-id", "observability-fixture",
            "--scene", "wave", "--intent", "Test report contract", "--output", str(task_dir),
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "add", "--task-dir", str(task_dir), "--section", "completed",
            "--id", "context", "--summary", "Project context analyzed", "--status", "pass",
            "--evidence", "project-context.json",
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "add", "--task-dir", str(task_dir), "--section", "verified",
            "--id", "runtime", "--summary", "Runtime frame rendered", "--status", "pass",
            "--evidence", "snapshot/frame-50.png",
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "add", "--task-dir", str(task_dir), "--section", "problems",
            "--id", "asset-license", "--summary", "Asset license needs confirmation", "--status", "open",
            "--severity", "P1", "--next-action", "Ask user to confirm source license",
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "add", "--task-dir", str(task_dir), "--section", "next_agent",
            "--id", "review", "--summary", "Review scene in Dev Lab", "--status", "pending",
            "--agent", "animation-review-agent", "--skill", "motionloom",
            "--evidence-needed", "review.json",
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "structure", "--task-dir", str(task_dir),
            "--missing-file", "project-context.json", "--broken-reference", "src/output/wave/animation.json",
        ], check=True, capture_output=True)

        for state in ("planning", "sourcing", "generating", "rendering", "review_required"):
            subprocess.run([
                sys.executable, str(report_script), "transition", "--task-dir", str(task_dir), "--state", state,
            ], check=True, capture_output=True)

        (task_dir / "quality-report.json").write_text(json.dumps({"status": "pass", "rules": []}))
        subprocess.run([
            sys.executable, str(report_script), "transition", "--task-dir", str(task_dir), "--state", "validated",
        ], check=True, capture_output=True)
        (task_dir / "browser-review.json").write_text(json.dumps({
            "schema_version": "1.0",
            "candidate_id": "fixture-candidate",
            "task_id": "observability-fixture",
            "scene": "wave",
            "status": "prepared",
            "requires_user_approval": True,
            "expires_at": "2099-01-01T00:00:00Z",
        }))
        subprocess.run([
            sys.executable, str(report_script), "review", "--task-dir", str(task_dir),
            "--candidate-id", "fixture-candidate", "--decision", "approved", "--reviewer", "fixture", "--notes", "Evidence looks consistent.",
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "transition", "--task-dir", str(task_dir), "--state", "ready_for_pr",
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "transition", "--task-dir", str(task_dir), "--state", "confirmed",
            "--commit-sha", "0123456789abcdef0123456789abcdef01234567",
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "collect", "--task-dir", str(task_dir),
        ], check=True, capture_output=True)
        subprocess.run([
            sys.executable, str(report_script), "render", "--task-dir", str(task_dir),
        ], check=True, capture_output=True)
        report_check = subprocess.run([
            sys.executable, str(report_script), "check", "--task-dir", str(task_dir),
        ], capture_output=True, text=True)

        task = json.loads((task_dir / "task.json").read_text())
        report = (task_dir / "REPORT.md").read_text()
        manifest = json.loads((task_dir / "artifact-manifest.json").read_text())
        check("task lifecycle reaches confirmed", task.get("state") == "confirmed")
        check("confirmed task records commit", task.get("commit_sha", "").startswith("01234567"))
        check("execution report exposes required sections", all(section in report for section in ("## Completed", "## Verified", "## Not completed", "## Problems to fix", "## Structure review")))
        check("execution report includes recorded problem", "Asset license needs confirmation" in report)
        check("report removes initial placeholder after progress", "Task has not run yet." not in report)
        check("report includes structure findings", "project-context.json" in report and "src/output/wave/animation.json" in report)
        check("artifact manifest has checksums", bool(manifest.get("artifacts")) and all(len(item.get("sha256", "")) == 64 for item in manifest["artifacts"]))
        check("semantic report check passes", report_check.returncode == 0 and json.loads(report_check.stdout).get("status") == "pass")

        candidate = json.loads((task_dir / "browser-review.json").read_text())
        candidate["status"] = "prepared"
        candidate["task_id"] = "foreign-task"
        (task_dir / "browser-review.json").write_text(json.dumps(candidate))
        foreign_review = subprocess.run([
            sys.executable, str(report_script), "review", "--task-dir", str(task_dir),
            "--candidate-id", "fixture-candidate", "--decision", "approved", "--reviewer", "fixture",
        ], capture_output=True, text=True)
        check("review rejects foreign task candidate", foreign_review.returncode != 0 and "task_id" in foreign_review.stderr)

    doctor = subprocess.run([sys.executable, str(ROOT / "scripts/skill-doctor.py"), "--json"], capture_output=True, text=True)
    doctor_data = json.loads(doctor.stdout)
    check("skill doctor passes package structure", doctor.returncode == 0 and doctor_data.get("status") == "pass")


if __name__ == "__main__":
    print("== MotionLoom engine tests ==")
    test_analyzer_on_fixture()
    test_spec_generate_and_validate()
    test_rig_build_and_pose()
    test_lottie_scaffold_valid()
    test_dotlottie_manifest_selection()
    test_dotlottie_packager()
    test_source_binding_contract()
    test_placeholder_is_not_runtime_evidence()
    test_runtime_evidence_binding()
    test_deep_audit_contracts()
    test_approved_browser_review_e2e_contract()
    test_intelligence_core_contracts()
    test_malformed_spec_is_rejected_cleanly()
    test_p1_semantic_continuity_fix_plan()
    sys.path.insert(0, str(ROOT))
    test_category_coverage()
    test_observability_contract()
    print()
    if FAILED:
        print(f"{len(FAILED)} test(s) FAILED: {', '.join(FAILED)}")
        sys.exit(1)
    print("all tests passed")
