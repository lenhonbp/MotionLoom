---
name: animation-studio
description: >-
  Project-aware animation production and verification for UI motion, Lottie/dotLottie,
  Rive, GSAP, Framer Motion, character body rigs, scene assets, runtime rendering,
  Dev Lab browser review, and confirm-to-PR workflows. Use when an Agent must create, fix,
  validate, review, or deliver animation inside an existing project.
license: MIT
metadata:
  version: "1.4.0"
  target_frameworks: "lottie,dotlottie,rive,gsap,framer-motion,spine,threejs"
  verified_runtimes: "lottie-json,dotlottie-package,svg-cutout-rig,rive,gsap,framer-motion"
---

# Animation Studio Skill

Treat every animation request as a production task, not as an isolated asset-generation prompt. Always bind the work to the host project's context, emit machine-readable artifacts, render through the target runtime, expose review evidence in Dev Lab, and stop before commit when a required gate or user confirmation is missing.

## Required workflow

1. **Understand** — read the host project manifest and run `bash scripts/analyze.sh <project-path>`. Load `project-context.json` from the audited project. If context is missing or ambiguous, stop at `needs_context`.
2. **Plan** — classify the animation, select a framework, and generate a context-bound `motion-spec.json` with timing, easing, loop, accessibility, performance and source authority.
3. **Source** — resolve an authoritative asset from the project or `assets/library/`. Record attribution, license and checksum in the scene manifest's required `source_binding`; the binding's SHA-256 must match the bytes referenced by `manifest.file`. Do not promote an unknown or placeholder asset to production.
4. **Generate** — use the matching template or rig implementation. For body animation, preserve named anatomy, pivot and parent-first hierarchy.
5. **Render** — run `bash scripts/render.sh <scene>` for scene output, or `node scripts/runtime-adapters.mjs` for the verified Rive/GSAP/Framer Motion adapter matrix. Acceptance requires runtime evidence at 0/50/100%, not a static placeholder. Keep the render metadata beside the snapshots.
6. **Browser review handoff** — run `python3 scripts/review-hook.py prepare --task-dir artifacts/<task-id> --lab-url <internal-lab-url>`. The hook prepares the exact candidate and emits a JSON action for a browser-capable Agent. Trigger or suggest that Agent to open the emitted URL, inspect frames 0/50/100, scrub the timeline and ask the user to review. This is not a separate Dev Lab Skill; it is a required post-render handoff.
7. **Review capture** — the browser Agent calls `window.__lab.getReview()` after the user approves or requests changes, then persists it with `python3 scripts/report.py review --task-dir artifacts/<task-id> --candidate-id <id> --decision approved|changes_requested --reviewer user`. A change request returns to generation; no approval means no PR.
8. **Validate** — run `python3 scripts/review-hook.py validate --task-dir artifacts/<task-id>`, `python3 scripts/quality-gate.py --scene <scene> --context <context-path>`, and `python3 scripts/skill-doctor.py --json` when validating the Skill package itself.
9. **Report** — create or update an artifact bundle with `python3 scripts/report.py`. Record facts with `report.py add`, structural defects with `report.py structure`, collect checksums with `report.py collect`, and run `report.py check` before rendering the final report. The final report must state completed, verified, not completed, blocked/failed, structure problems, browser candidate/review evidence and the recommended next Agent/Skill.
10. **Confirm** — only after approved browser review and a passing quality gate run `TASK_DIR=artifacts/<task-id> bash scripts/pr.sh <scene>`. Commit, push and open PR are explicit side effects.

## Progressive disclosure

- Read `references/reporting-contract.md` when creating task, execution, issue or handoff artifacts.
- Read `references/runtime-capability.md` before claiming a framework is production-verified.
- Read `docs/FRAMEWORK-SELECTION.md` and `docs/CATEGORIES.md` when selecting a runtime.
- Read `docs/CHECKLIST.md` before marking a scene ready for review.
- Read `src/rig/README.md` for character body hierarchy and pose rules.
- Read `references/dotlottie-source-notes.md` when packaging or validating `.lottie` archives.

## Non-negotiable contracts

- Every task has a lifecycle state: `created`, `needs_context`, `planning`, `sourcing`, `generating`, `rendering`, `review_required`, `blocked`, `failed`, `validated`, `ready_for_pr`, or `confirmed`.
- Every production scene has context, motion spec, manifest, source binding, runtime metadata, 0/50/100 snapshots, browser-review candidate, checklist result and review artifact.
- `scaffold` and `static-validated` are not equivalent to `runtime-verified` or `project-integrated`.
- Never hide a missing dependency, failed render, missing license, context drift, incomplete review or unimplemented framework behind a successful prose response.
- Use JSON output and stable exit codes for Agent-to-Agent composition; do not require another Agent to parse chat text.
- Destructive Git actions require explicit confirmation. Use `OPEN_PR=0` for local review-only runs.

## Framework boundary

The audited production paths are **Lottie JSON runtime rendering, dotLottie v2 packaging, SVG cutout rigging, Rive Canvas, GSAP and Framer Motion**. Their evidence is generated by `node scripts/runtime-adapters.mjs` and includes deterministic scrub points, runtime state and PNG snapshots. Spine and Three.js remain scaffold/selection paths until their adapter-specific runtime tests pass and their capability level is upgraded in `agent-card.json`.

## Provenance and runtime commands

Every production `src/output/<scene>/manifest.json` must include a `source_binding` object matching `schemas/scene-manifest.schema.json`. The acceptance gate rejects a missing binding, a mismatched source path, an unknown license/authority or a stale SHA-256.

```bash
# Package a Lottie JSON scene as a dotLottie v2 archive.
bash scripts/to-dotlottie.sh <scene> [output.lottie]

# Run the official runtime adapters in a real browser harness.
node scripts/runtime-adapters.mjs
```

`runtime-evidence.json` records the runtime package, three scrub points, observed state and generated snapshots. A template alone is never enough to upgrade a framework from `scaffold_only` to `verified`.

## Output contract

Create `artifacts/<task-id>/` for cross-Agent handoff. A minimal invocation is:

```bash
python3 scripts/report.py init --task-id <task-id> --scene <scene> \
  --intent "<intent>" --output artifacts/<task-id>
python3 scripts/report.py add --task-dir artifacts/<task-id> \
  --section completed --id context --summary "Project analyzed" \
  --status pass --evidence project-context.json
python3 scripts/report.py structure --task-dir artifacts/<task-id> \
  --missing-file <path> --broken-reference <path>
python3 scripts/report.py collect --task-dir artifacts/<task-id>
python3 scripts/review-hook.py prepare --task-dir artifacts/<task-id> --lab-url http://127.0.0.1:3300
# Browser Agent opens the emitted URL; user reviews; then persist the browser payload:
python3 scripts/report.py review --task-dir artifacts/<task-id> \
  --candidate-id <candidate-id> --decision approved --reviewer user
python3 scripts/report.py check --task-dir artifacts/<task-id>
python3 scripts/report.py render --task-dir artifacts/<task-id>
```

The bundle should contain `task.json`, `execution-report.json`, `decision-log.jsonl`, `artifact-manifest.json`, `quality-report.json`, `issue-register.json`, `review.json` and `handoff.json` as applicable. Reports must never convert “not run” into “passed”: an absent runtime artifact is a `not_completed` item or a blocker, while an invalid path belongs in `structure_review`.
