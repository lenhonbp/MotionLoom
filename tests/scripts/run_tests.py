#!/usr/bin/env python3
"""
run_tests.py — Deterministic test suite for the skill's core engine.
Runs without any network or heavy dependencies (pure stdlib).

Usage: python3 tests/scripts/run_tests.py
"""

import json
import os
import subprocess
import sys
import tempfile
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


def test_category_coverage():
    from src.core.analyzer import CATEGORIES  # noqa
    from docs import __file__ as _  # noqa: guard import path
    required = {"ui-micro", "loading", "hero-scene", "character-body", "icon-animation",
                "scroll-linked", "data-viz", "3d-scene"}
    check("all categories defined", required <= set(CATEGORIES))


if __name__ == "__main__":
    print("== Animation Studio engine tests ==")
    test_analyzer_on_fixture()
    test_spec_generate_and_validate()
    test_rig_build_and_pose()
    test_lottie_scaffold_valid()
    test_dotlottie_manifest_selection()
    test_placeholder_is_not_runtime_evidence()
    sys.path.insert(0, str(ROOT))
    test_category_coverage()
    print()
    if FAILED:
        print(f"{len(FAILED)} test(s) FAILED: {', '.join(FAILED)}")
        sys.exit(1)
    print("all tests passed")
