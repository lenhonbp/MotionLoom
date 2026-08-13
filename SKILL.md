---
name: motionloom
description: >-
  Project-aware animation production and verification for UI motion, Lottie/dotLottie,
  Rive, GSAP, Framer Motion, character body rigs, scene assets, runtime rendering,
  Dev Lab browser review, and confirm-to-PR workflows. Use when an Agent must create, fix,
  validate, review, or deliver animation inside an existing project.
license: MIT
metadata:
  version: "1.9.0"
  target_frameworks: "lottie,dotlottie,rive,gsap,framer-motion,spine,threejs"
  verified_runtimes: "lottie-json,dotlottie-package,svg-cutout-rig,rive,gsap,framer-motion"
---

# MotionLoom Skill

Treat every animation request as a production task, not as an isolated asset-generation prompt. Always bind the work to the host project's context, emit machine-readable artifacts, render through the target runtime, expose review evidence in Dev Lab, and stop before commit when a required gate or user confirmation is missing.

## Required workflow

1. **Understand** — read the host project manifest and run `bash scripts/analyze.sh <project-path>`. Load `project-context.json` from the audited project. If context is missing or ambiguous, stop at `needs_context`.
2. **Plan** — classify the animation, select a framework, and generate a context-bound `motion-spec.json` with timing, easing, loop, accessibility, performance and source authority.
3. **Source** — resolve an authoritative asset from the project or `assets/library/`. Record attribution, license and checksum in the scene manifest's required `source_binding`; the binding's SHA-256 must match the bytes referenced by `manifest.file`. Do not promote an unknown or placeholder asset to production.
4. **Generate** — use the matching template or rig implementation. For body animation, preserve named anatomy, pivot and parent-first hierarchy.
5. **Render** — run `bash scripts/render.sh <scene>` for scene output, or `node scripts/runtime-adapters.mjs` for the verified Rive/GSAP/Framer Motion adapter matrix. Acceptance requires runtime evidence at 0/50/100%, not a static placeholder. Keep the render metadata beside the snapshots.
6. **Bind Intelligence Core** — build a framework-neutral `motion-ir.json`, `project-graph.json`, `provenance.json`, `replay-bundle.json`, `semantic-lint-report.json` and `semantic-lint-benchmark.json` with `python3 scripts/intelligence.py`. Select only a capability registry entry whose status is `verified`, whose evidence is fresh and whose compatibility matches the target environment. A confidence score or benchmark result can prioritize investigation; neither can replace deterministic or human acceptance.
6a. **Harden the trust boundary** — keep artifact and task bundles inside the repository/task root, reject symlinked evidence, bind replay to its exact `task_dir`, `task_id` and scene, select one deterministic report bundle per scene, and require browser candidate/review identity and expiry checks before readiness. The Dev Lab must reject cross-origin or identity-mismatched artifact bases. In strict runtime-observability runs, capture `runtime-telemetry.json` and a read-only `evidence-verifier-report.json`; verifier output must preserve `approval: false`. These checks expose risk and prevent evidence mixing, but do not turn heuristics or evidence integrity into approval.
7. **Browser review handoff** — run `python3 scripts/review-hook.py prepare --task-dir artifacts/<task-id> --lab-url <internal-lab-url>`. The hook prepares the exact candidate and emits a JSON action for a browser-capable Agent. Trigger or suggest that Agent to open the emitted URL, inspect frames 0/50/100, scrub the timeline and ask the user to review. This is not a separate Dev Lab Skill; it is a required post-render handoff.
8. **Review capture** — the browser Agent calls `window.__lab.getReview()` after the user approves or requests changes, then persists it with `python3 scripts/report.py review --task-dir artifacts/<task-id> --candidate-id <id> --decision approved|changes_requested --reviewer user`. A change request returns to generation; no approval means no PR.
9. **Validate** — run `python3 scripts/review-hook.py validate --task-dir artifacts/<task-id>`, `python3 scripts/intelligence.py semantic-lint benchmark --task-dir artifacts/<task-id> --iterations 25 --threshold-ms 500`, `bash scripts/capture-runtime-telemetry.sh <scene> artifacts/<task-id>`, `python3 scripts/report-contract.py --root . --scenes-file <changed-scenes>`, `python3 scripts/quality-gate.py --scene <scene> --context <context-path> --task-dir artifacts/<task-id> --require-intelligence --require-p1 --require-benchmark --require-telemetry`, and `python3 scripts/skill-doctor.py --json` when validating the Skill package itself.
10. **Report** — create or update an artifact bundle with `python3 scripts/report.py`. Record facts with `report.py add`, structural defects with `report.py structure`, collect checksums with `report.py collect`, and run `report.py check` before rendering the final report. The final report must state completed, verified, not completed, blocked/failed, structure problems, browser candidate/review evidence and the recommended next Agent/Skill.
11. **Confirm** — only after approved browser review and a passing quality gate run `TASK_DIR=artifacts/<task-id> bash scripts/pr.sh <scene>`. Commit, push and open PR are explicit side effects.

## Progressive disclosure

- Read `references/reporting-contract.md` when creating task, execution, issue or handoff artifacts.
- Read `references/runtime-capability.md` before claiming a framework is production-verified.
- Read `docs/FRAMEWORK-SELECTION.md` and `docs/CATEGORIES.md` when selecting a runtime.
- Read `docs/CHECKLIST.md` before marking a scene ready for review.
- Read `src/rig/README.md` for character body hierarchy and pose rules.
- Read `references/dotlottie-source-notes.md` when packaging or validating `.lottie` archives.
- Read `docs/ROADMAP-INTELLIGENCE.md` before extending graph, provenance, capability or replay behavior.
- Read `references/intelligence-core.md` before building or validating Intelligence Core artifacts.
- Read `docs/research/AGENT-PROTOCOL-FINDINGS.md` before exposing MotionLoom through Agent tools or MCP resources.

## Non-negotiable contracts

- Every task has a lifecycle state: `created`, `needs_context`, `planning`, `sourcing`, `generating`, `rendering`, `review_required`, `blocked`, `failed`, `validated`, `ready_for_pr`, or `confirmed`.
- Every production scene has context, motion spec, manifest, source binding, runtime metadata, 0/50/100 snapshots, browser-review candidate, checklist result and review artifact.
- `scaffold` and `static-validated` are not equivalent to `runtime-verified` or `project-integrated`.
- Never hide a missing dependency, failed render, missing license, context drift, incomplete review or unimplemented framework behind a successful prose response.
- Use JSON output and stable exit codes for Agent-to-Agent composition; do not require another Agent to parse chat text. The external evidence verifier is read-only and must never emit an approval decision.
- Destructive Git actions require explicit confirmation. Use `OPEN_PR=0` for local review-only runs.
- Intelligence Core artifacts are task-bound: graph, provenance, Motion IR and replay evidence must not be reused across tasks without revalidation.
- Provenance hashes materials and products; replay must fail on tampered or missing files; stale capability evidence must not be selected for production acceptance.
- Browser-review candidates are single-use, time-bounded and bound to the exact task, scene and candidate identity; Dev Lab artifact/task bases must be same-origin and identity-consistent before staging a review decision.
- Report completeness must select one deterministic passing task bundle per scene and fail on ambiguous ties; a valid artifact is never sufficient to bypass explicit user approval.
- Runtime telemetry must bind task, scene, source, manifest, Motion IR and deterministic scrub points; tampered, stale, missing or cross-task telemetry is a verification failure.

## Framework boundary

The audited production paths are **Lottie JSON runtime rendering, dotLottie v2 packaging, SVG cutout rigging, Rive Canvas, GSAP and Framer Motion**. Their evidence is generated by `node scripts/runtime-adapters.mjs` and includes deterministic scrub points, runtime state and PNG snapshots. Spine and Three.js remain scaffold/selection paths until their adapter-specific runtime tests pass and their capability level is upgraded in `agent-card.json`.

## Provenance and runtime commands

Every production `src/output/<scene>/manifest.json` must include a `source_binding` object matching `schemas/scene-manifest.schema.json`. The acceptance gate rejects a missing binding, a mismatched source path, an unknown license/authority or a stale SHA-256.

The Intelligence Core contracts are defined in `schemas/project-graph.schema.json`, `schemas/provenance.schema.json`, `schemas/capability-registry.schema.json` and `schemas/motion-ir.schema.json`. They make project relationships, supply-chain steps, runtime selection and framework-neutral intent inspectable without relying on prose.

```bash
# Package a Lottie JSON scene as a dotLottie v2 archive.
bash scripts/to-dotlottie.sh <scene> [output.lottie]

# Run the official runtime adapters in a real browser harness.
node scripts/runtime-adapters.mjs

# Build the task-bound Intelligence Core artifacts.
python3 scripts/intelligence.py motion-ir build --task-dir artifacts/<task-id>
python3 scripts/intelligence.py graph build --task-dir artifacts/<task-id>
python3 scripts/intelligence.py provenance build --task-dir artifacts/<task-id>
python3 scripts/intelligence.py replay capture --task-dir artifacts/<task-id>
```

`runtime-evidence.json` records the runtime package, three scrub points, observed state and generated snapshots. A template alone is never enough to upgrade a framework from `scaffold_only` to `verified`.

For an observability-enabled run, `bash scripts/capture-runtime-telemetry.sh <scene> artifacts/<task-id>` regenerates the real-browser evidence and writes telemetry under the task bundle. `scripts/evidence-verifier.py` then checks task/scene/hash/path/age bindings with stable machine-readable output. A verifier pass means the evidence is internally consistent; it does not mean the animation is approved.

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

The bundle should contain `task.json`, `execution-report.json`, `decision-log.jsonl`, `artifact-manifest.json`, `quality-report.json`, `issue-register.json`, `review.json` and `handoff.json` as applicable. Telemetry-enabled bundles additionally expose `runtime-adapters/runtime-evidence.json`, `runtime-adapters/runtime-telemetry.json` and `evidence-verifier-report.json`. Reports must never convert “not run” into “passed”: an absent runtime artifact is a `not_completed` item or a blocker, while an invalid path belongs in `structure_review`.
