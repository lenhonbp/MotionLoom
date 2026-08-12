---
name: animation-studio
description: >-
  Project-aware animation production and verification for UI motion, Lottie/dotLottie,
  Rive, GSAP, Framer Motion, character body rigs, scene assets, runtime rendering,
  Dev Lab review, and confirm-to-PR workflows. Use when an Agent must create, fix,
  validate, review, or deliver animation inside an existing project.
license: MIT
metadata:
  version: "1.2.0"
  target_frameworks: "lottie,dotlottie,rive,gsap,framer-motion,spine,threejs"
  verified_runtimes: "lottie-json,svg-cutout-rig"
---

# Animation Studio Skill

Treat every animation request as a production task, not as an isolated asset-generation prompt. Always bind the work to the host project's context, emit machine-readable artifacts, render through the target runtime, expose review evidence in Dev Lab, and stop before commit when a required gate or user confirmation is missing.

## Required workflow

1. **Understand** — read the host project manifest and run `bash scripts/analyze.sh <project-path>`. Load `project-context.json` from the audited project. If context is missing or ambiguous, stop at `needs_context`.
2. **Plan** — classify the animation, select a framework, and generate a context-bound `motion-spec.json` with timing, easing, loop, accessibility, performance and source authority.
3. **Source** — resolve an authoritative asset from the project or `assets/library/`. Record attribution, license and checksum. Do not promote an unknown or placeholder asset to production.
4. **Generate** — use the matching template or rig implementation. For body animation, preserve named anatomy, pivot and parent-first hierarchy.
5. **Render** — run `bash scripts/render.sh <scene>`. Acceptance requires runtime evidence at 0/50/100%, not a static placeholder. Keep the render metadata beside the snapshots.
6. **Review** — run `bash scripts/devlab.sh <scene>`, inspect the same scene output, persist `review.json`, and classify feedback as timing, easing, pose, brand, accessibility, performance or asset.
7. **Validate** — run `python3 scripts/quality-gate.py --scene <scene> --context <context-path>` and `python3 scripts/skill-doctor.py --json` when validating the Skill package itself.
8. **Report** — create or update an artifact bundle with `python3 scripts/report.py`. Record facts with `report.py add`, structural defects with `report.py structure`, collect checksums with `report.py collect`, and run `report.py check` before rendering the final report. The final report must state completed, verified, not completed, blocked/failed, structure problems, evidence and the recommended next Agent/Skill.
9. **Confirm** — only after human review and a passing quality gate run `bash scripts/pr.sh <scene>`. Commit, push and open PR are explicit side effects.

## Progressive disclosure

- Read `references/reporting-contract.md` when creating task, execution, issue or handoff artifacts.
- Read `references/runtime-capability.md` before claiming a framework is production-verified.
- Read `docs/FRAMEWORK-SELECTION.md` and `docs/CATEGORIES.md` when selecting a runtime.
- Read `docs/CHECKLIST.md` before marking a scene ready for review.
- Read `src/rig/README.md` for character body hierarchy and pose rules.

## Non-negotiable contracts

- Every task has a lifecycle state: `created`, `needs_context`, `planning`, `sourcing`, `generating`, `rendering`, `review_required`, `blocked`, `failed`, `validated`, `ready_for_pr`, or `confirmed`.
- Every production scene has context, motion spec, manifest, source binding, runtime metadata, 0/50/100 snapshots, checklist result and review artifact.
- `scaffold` and `static-validated` are not equivalent to `runtime-verified` or `project-integrated`.
- Never hide a missing dependency, failed render, missing license, context drift, incomplete review or unimplemented framework behind a successful prose response.
- Use JSON output and stable exit codes for Agent-to-Agent composition; do not require another Agent to parse chat text.
- Destructive Git actions require explicit confirmation. Use `OPEN_PR=0` for local review-only runs.

## Framework boundary

The audited production path is **Lottie JSON runtime rendering plus SVG cutout rigging**. Rive, GSAP, Framer Motion, Spine and Three.js are scaffold/selection paths until their adapter-specific runtime tests pass and their capability level is upgraded in `agent-card.json`.

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
python3 scripts/report.py check --task-dir artifacts/<task-id>
python3 scripts/report.py render --task-dir artifacts/<task-id>
```

The bundle should contain `task.json`, `execution-report.json`, `decision-log.jsonl`, `artifact-manifest.json`, `quality-report.json`, `issue-register.json`, `review.json` and `handoff.json` as applicable. Reports must never convert “not run” into “passed”: an absent runtime artifact is a `not_completed` item or a blocker, while an invalid path belongs in `structure_review`.
