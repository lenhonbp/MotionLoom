#!/usr/bin/env python3
"""One-shot guarded metadata preparation for MotionLoom 2.6.1.

This file is intentionally removed by its own successful run. It exists only to
apply a deterministic version/release-note update without hand-editing large
Agent metadata files through the GitHub API.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.6.1"
PREVIOUS = "2.6.0"


def replace_once(path: str, old: str, new: str) -> None:
    file = ROOT / path
    text = file.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"{path}: expected text not found: {old!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_json(path: str, mutate) -> None:
    file = ROOT / path
    data = json.loads(file.read_text(encoding="utf-8"))
    mutate(data)
    file.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# Package and canonical Agent metadata.
write_json("package.json", lambda data: data.__setitem__("version", VERSION))
replace_once("SKILL.md", 'version: "2.6.0"', 'version: "2.6.1"')


def mutate_card(data: dict) -> None:
    data["version"] = VERSION
    for capability in [
        "asset.frame-generation-lock.validate",
        "asset.frame-generation-lock.compose",
        "asset.frame-set-preflight",
    ]:
        if capability not in data["capabilities"]:
            insert_at = data["capabilities"].index("asset.consistency.validate") if "asset.consistency.validate" in data["capabilities"] else len(data["capabilities"])
            data["capabilities"].insert(insert_at, capability)
    for artifact in ["frame-generation-lock"]:
        if artifact not in data["input_artifacts"]:
            data["input_artifacts"].append(artifact)
    for artifact in ["frame-generation-instruction", "generated-frame-set-preflight-report"]:
        if artifact not in data["output_artifacts"]:
            data["output_artifacts"].append(artifact)
    entrypoints = data.setdefault("entrypoints", {})
    entrypoints["frame_generation_lock_validate"] = "motionloom frame-generation-lock validate --input <frame-generation-lock.json> --root <asset-root> --json"
    entrypoints["frame_generation_lock_compose"] = "motionloom frame-generation-lock compose --input <frame-generation-lock.json> --frame-id <frame-id> --root <asset-root> --json"
    entrypoints["frame_set_preflight"] = "motionloom frame-set-preflight --input <frame-geometry.json> --root <asset-root> --json"


write_json("agent-card.json", mutate_card)
write_json("agent-surfaces.json", lambda data: data.__setitem__("version", VERSION))

# Protected release workflow default.
replace_once(".github/workflows/release.yml", "default: 2.6.0", "default: 2.6.1")

# README release posture: keep the 2.6.0 Dev Lab note in its focused section,
# but make the top-level current release posture accurately describe 2.6.1.
readme = ROOT / "README.md"
text = readme.read_text(encoding="utf-8")
old = "> **Release posture:** MotionLoom 2.6.0 upgrades Dev Lab into an interactive runtime review workbench with live playback controls, arbitrary project-defined Action Libraries and optional state/transition testing, while preserving deterministic snapshots and explicit human approval. The native macOS/iOS review app remains an unsigned source alpha under `apps/apple/`; the npm package remains the cross-platform Node/Python Skill and documentation surface. Verify npm/GitHub publication metadata separately; passing runtime evidence never implies user approval."
new = "> **Release posture:** MotionLoom 2.6.1 keeps the interactive Dev Lab from 2.6.0 and adds a proactive Frame Generation Lock for generated multi-frame animation assets. Agents now hash-bind one accepted identity/reference, compose one isolated provider instruction per frame from locked canvas/scale/pivot/footline geometry, and run measured frame-set preflight before atlas packing. The native macOS/iOS review app remains an unsigned source alpha under `apps/apple/`; the npm package remains the cross-platform Node/Python Skill and documentation surface. Generation, runtime and validation evidence never imply artist authorship or user approval. See the [2.6.1 release note](docs/releases/2.6.1.md)."
if new not in text:
    if old not in text:
        raise SystemExit("README.md: 2.6.0 release posture paragraph not found")
    text = text.replace(old, new, 1)
readme.write_text(text, encoding="utf-8")

# Current status posture.
status = ROOT / "docs/STATUS.md"
text = status.read_text(encoding="utf-8")
old = "MotionLoom's repository source and package manifest carry **2.6.0 release metadata**. The publication state of the npm registry and GitHub Release/tag must be verified against the latest release workflow rather than inferred from this document. The repository has a cross-platform CLI, one-command project onboarding, durable Project Memory, Agent interoperability surfaces, artifact-first handoff, runtime evidence, Visual Truth, Remediation Learning, signed attestation, AI-first asset provenance, a truthful code-authored runtime lane and an interactive browser-based Dev Lab review workbench. Dev Lab now supports hash-bound live playback, arbitrary project-defined action libraries, and optional state/transition review flows in addition to deterministic snapshot evidence. The protected manual release workflow verifies package/changelog/release-note alignment before publication."
new = "MotionLoom's repository source and package manifest carry **2.6.1 release metadata**. The publication state of the npm registry and GitHub Release/tag must be verified against the latest release workflow rather than inferred from this document. The repository has a cross-platform CLI, one-command project onboarding, durable Project Memory, Agent interoperability surfaces, artifact-first handoff, runtime evidence, Visual Truth, Remediation Learning, signed attestation, AI-first asset provenance, a truthful code-authored runtime lane and an interactive browser-based Dev Lab review workbench. Dev Lab supports hash-bound live playback, arbitrary project-defined action libraries and optional state/transition review flows; generated frame sequences additionally use a machine-readable Frame Generation Lock plus fail-closed measured preflight so isolated source geometry is controlled before and after generation. The protected manual release workflow verifies package/changelog/release-note alignment before publication."
if new not in text:
    if old not in text:
        raise SystemExit("docs/STATUS.md: current 2.6.0 release posture not found")
    text = text.replace(old, new, 1)
old2 = "The bounded analyzer has been exercised against a labeled external corpus; see the [dated evidence note](audits/external-project-corpus-2026-08-13.md). The 2.5.x publication chain established npm/GitHub release provenance, and 2.6.0 adds a substantially richer Dev Lab review surface without weakening the human approval boundary. The highest-value next evidence work is consumer-project review of real action sets and transitions, followed by paired product evaluation across more real projects and repeating the same provenance verification for each new release."
new2 = "The bounded analyzer has been exercised against a labeled external corpus; see the [dated evidence note](audits/external-project-corpus-2026-08-13.md). The 2.5.x publication chain established npm/GitHub release provenance, 2.6.0 added the richer Dev Lab review surface, and 2.6.1 adds proactive machine-readable frame-generation geometry control without weakening the human approval boundary. The highest-value next evidence work is consumer-project review of real action sets, transitions and generated frame sequences, followed by paired product evaluation across more real projects and repeating the same provenance verification for each new release."
if new2 not in text:
    if old2 not in text:
        raise SystemExit("docs/STATUS.md: known-next-work paragraph not found")
    text = text.replace(old2, new2, 1)
status.write_text(text, encoding="utf-8")

# Changelog entry.
changelog = ROOT / "CHANGELOG.md"
text = changelog.read_text(encoding="utf-8")
section = """## [2.6.1] - 2026-08-21

### Added

- Add a machine-readable `frame-generation-lock` contract that hash-binds the accepted identity/reference and locks canvas, alpha/color space, apparent size, pivot, footline, safe rectangle, transparent padding, camera/orientation and per-frame output identity before later frames are generated.
- Add provider-neutral `motionloom frame-generation-lock validate|compose|compose-all` commands and public Agent routing so every pose instruction is deterministically rebuilt from the same lock instead of relying on repeated prose prompts.
- Expose the strict generated `motionloom frame-set-preflight` command through the public CLI for post-generation alpha-bounds, scale, pivot/footline, guard-band, contamination and source-isolation checks.

### Hardened

- Default generated multi-frame source policy to one isolated PNG per frame; six-frame-or-longer actions must not use one generated pose sheet/contact sheet as production source material.
- Fail closed on stale reference hashes, duplicate frame outputs, pose-sheet policy violations, path escape, shared/non-isolated sources, post-generation resize and measured apparent-size drift beyond tolerance.
- Keep atlas packing as a later, separate gate: a clean atlas cannot repair inconsistent or contaminated source frames.

### Verified

- Dedicated Frame Generation Lock CI validates the public CLI, provider instruction composition and strict post-generation preflight.
- Pull request #18 passed MotionLoom Quality, Security Analysis, Documentation and Package Hygiene, plus the dedicated Frame Generation Lock workflow before merge.

### Boundary

- Frame locks, generated prompts, SHA-256 bindings, preflight passes and atlas checks are deterministic evidence only. They never grant artist authorship, production eligibility, runtime approval, licence authority or user approval.

See the [2.6.1 release note](docs/releases/2.6.1.md) for the generation/preflight contract and migration guidance.

"""
if "## [2.6.1]" not in text:
    marker = "## [Unreleased]\n\n"
    if marker not in text:
        raise SystemExit("CHANGELOG.md: Unreleased marker not found")
    text = text.replace(marker, marker + section, 1)
if "[2.6.1]: docs/releases/2.6.1.md" not in text:
    link_marker = "[2.6.0]: docs/releases/2.6.0.md"
    if link_marker not in text:
        raise SystemExit("CHANGELOG.md: 2.6.0 link marker not found")
    text = text.replace(link_marker, "[2.6.1]: docs/releases/2.6.1.md\n" + link_marker, 1)
changelog.write_text(text, encoding="utf-8")

# Versioned release note.
release_note = ROOT / "docs/releases/2.6.1.md"
release_note.write_text("""# MotionLoom 2.6.1

MotionLoom 2.6.1 closes the generated multi-frame consistency gap discovered during real Codex animation work. The release makes frame consistency proactive: the Agent binds one accepted identity/reference into a machine-readable Frame Generation Lock before producing later poses, then validates the real PNG bytes after every generated frame before any atlas is packed.

## What changed

### Frame Generation Lock before generation

Generated frame sequences now have a provider-neutral contract in `schemas/frame-generation-lock.schema.json`. The lock records and verifies:

- accepted identity/reference path and SHA-256;
- exact canvas dimensions, alpha mode and color space;
- camera/orientation and apparent character scale;
- pivot and baseline/footline;
- safe rectangle, transparent padding and geometry tolerances;
- ordered frame ids, pose intent and one unique isolated output path per frame.

Agents use `motionloom frame-generation-lock validate` before generation and `motionloom frame-generation-lock compose` (or `compose-all`) to build each provider-facing pose instruction from the same lock. This removes dependence on an Agent remembering or rewriting the geometry prose consistently across frame 2, frame 6 or frame 20.

### Strict preflight after each generated frame

`motionloom frame-set-preflight` is now a public CLI command. It re-measures actual PNG bytes and blocks shared/non-isolated source canvases, stale hashes, contamination, guard-band violations, pivot/footline drift and apparent-size drift beyond the declared tolerance.

The default source policy is deliberately strict: generate one isolated source PNG per frame, validate it, and only then continue. For long actions (including six or more frames), a generated contact sheet or multi-pose sheet must not be cropped into production source frames. Atlas/sprite-sheet packing happens only after all isolated source frames pass.

## Agent behavior

`AGENTS.md` and the canonical Skill route Codex and other compatible Agents through this workflow automatically. The user does not need to remember to ask for equal scale, separate frames, padding, baseline consistency or pose-sheet avoidance.

If one frame fails, the Agent regenerates or repairs that frame under the same lock. It must not silently resize previously accepted frames or weaken tolerances merely to make the set pass.

## Verification

PR #18 passed:

- the dedicated Frame Generation Lock workflow;
- MotionLoom Quality (including engine tests and cross-platform package checks);
- Security Analysis / CodeQL;
- Documentation and Package Hygiene.

The dedicated regression suite covers stale reference hashes, duplicate outputs, pose-sheet policy, path escape, post-generation resize, public CLI composition and strict preflight.

## Trust boundary

This release improves source consistency and evidence quality; it does not change authority. A generator prompt, reference hash, frame lock, preflight pass, atlas pass, runtime render or signed evidence record does **not** create artist authorship, licence authority, production eligibility, production approval or user approval. Human review remains a separate bounded decision.

## Updating a project

After `motionloom@2.6.1` is published, update the project-local development dependency and refresh the managed Agent surface:

```bash
npm install --save-dev motionloom@2.6.1
npx --no-install motionloom repair --yes
npx --no-install motionloom status --json
```

For a generated multi-frame task, the Agent should then use the Frame Generation Lock before later frames and `frame-set-preflight` after each accepted frame.
""", encoding="utf-8")

# Remove the temporary preparer and trigger workflow from the resulting commit.
for relative in ["scripts/prepare-release-2.6.1.py", ".github/workflows/prepare-release-2.6.1.yml"]:
    path = ROOT / relative
    if path.exists():
        path.unlink()

print("prepared MotionLoom 2.6.1 release metadata")
