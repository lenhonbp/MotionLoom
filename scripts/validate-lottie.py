#!/usr/bin/env python3
"""
validate-lottie.py — Acceptance gate for generated Lottie files.

Checks the Bodymovin version header, frame count against the signed spec,
layer count against the performance budget, and (optionally) slot names
against the brand spec. Exit 0 = accepted, exit 1 = rejected with reasons.

Usage:
    python3 scripts/validate-lottie.py <animation.json|animation.lottie> \
        --spec motion-spec.json --max-layers 80
"""

import argparse
import json
import zipfile
import sys
from pathlib import Path


def load_lottie(path: Path, animation_id: str | None = None) -> dict:
    if path.suffix == ".lottie":
        with zipfile.ZipFile(path) as zf:
            if "manifest.json" not in zf.namelist():
                raise ValueError("dotLottie manifest.json is required")
            manifest = json.loads(zf.read("manifest.json"))
            entries = manifest.get("animations")
            if not isinstance(entries, list) or not entries:
                raise ValueError("dotLottie manifest must declare at least one animation")
            chosen = animation_id or ((manifest.get("initial") or {}).get("animation"))
            entry = next((item for item in entries if item.get("id") == chosen), None) if chosen else entries[0]
            if entry is None:
                raise ValueError(f"animation id not found in manifest: {chosen}")
            ident = str(entry.get("id", ""))
            candidates = [f"a/{ident}", f"a/{ident}.json", ident, f"{ident}.json"]
            name = next((candidate for candidate in candidates if candidate in zf.namelist()), None)
            if not name:
                raise ValueError(f"animation '{ident}' has no JSON payload under a/")
            return json.loads(zf.read(name))
    return json.loads(path.read_text(encoding="utf-8"))


def validate(path: Path, spec: dict | None, max_layers: int, animation_id: str | None = None) -> list:
    issues = []
    try:
        doc = load_lottie(path, animation_id or ((spec or {}).get("animation_id")))
    except Exception as e:
        return [f"cannot parse file: {e}"]

    if not doc.get("v"):
        issues.append("missing Bodymovin version header (v)")
    op = doc.get("op")
    fr = doc.get("fr")
    if op is None or fr is None:
        issues.append("missing frame metadata (fr/op)")
    elif spec and abs(op - spec.get("total_frames", op)) > 3:
        issues.append(f"frame count {op} deviates from spec total_frames {spec.get('total_frames')}")

    layers = len(doc.get("layers", []))
    if layers > max_layers:
        issues.append(f"layer count {layers} exceeds budget {max_layers}")

    kb = path.stat().st_size / 1024
    budget_kb = 1500 if (spec and spec.get("category") == "hero-scene") else 300
    if kb > budget_kb:
        issues.append(f"file size {kb:.0f}KB exceeds budget {budget_kb}KB")

    if spec:
        expected_slots = set(spec.get("slots", []))
        found_slots = set()
        for slot in (doc.get("themes") or {}).get("slots", []):
            found_slots.add(slot.get("id") or slot.get("p"))
        missing = expected_slots - found_slots
        if missing:
            issues.append(f"brand slots missing: {sorted(missing)}")

    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--spec")
    parser.add_argument("--max-layers", type=int, default=80)
    parser.add_argument("--animation-id")
    args = parser.parse_args()

    spec = None
    if args.spec:
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))

    issues = validate(Path(args.path), spec, args.max_layers, args.animation_id)
    if issues:
        print("REJECTED:")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    print("ACCEPTED — lottie passes validation")


if __name__ == "__main__":
    main()
