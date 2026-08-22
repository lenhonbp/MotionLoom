---
name: motionloom
description: >-
  Project-aware animation production and verification for UI motion, Lottie/dotLottie,
  Rive, GSAP, Framer Motion, character body rigs, scene assets, runtime rendering,
  Dev Lab browser review, and confirm-to-PR workflows. Use when an Agent must create, fix,
  validate, review, or deliver animation inside an existing project.
license: MIT
metadata:
  version: "2.6.1"
  target_frameworks: "lottie,dotlottie,rive,gsap,framer-motion,spine,threejs"
  verified_runtimes: "lottie-json,dotlottie-package,svg-cutout-rig,rive,gsap,framer-motion"
---

# MotionLoom Skill

> Public repository: [github.com/lenhonbp/MotionLoom](https://github.com/lenhonbp/MotionLoom) · npm: [motionloom](https://www.npmjs.com/package/motionloom) · release navigation: [CHANGELOG.md](CHANGELOG.md) · future work: [ROADMAP.md](ROADMAP.md)

Treat every animation request as a production task, not as an isolated asset-generation prompt. Always bind the work to the host project's context, emit machine-readable artifacts, render through the target runtime, expose review evidence in Dev Lab, and stop before commit when a required gate or user confirmation is missing.

## Fast onboarding for a real project

When MotionLoom is not installed in the host project, prefer the single cross-platform entrypoint `npx --yes motionloom init`. It detects the project root and package manager, installs a local devDependency, safely merges a marked MotionLoom router block into `AGENTS.md`, runs discovery, creates project-bound context and durable memory, and returns `ready`, `needs_setup` or `blocked`. `init` is a quiet quick start: it must not create a scene, trigger asset/runtime gates, open Dev Lab, commit, push, open a PR, grant approval or promote asset provenance. Use `npx --yes motionloom init --dry-run --json` before mutation, `npx --no-install motionloom status --json` for read-only checks, and `npx --no-install motionloom repair --yes` to re-apply only missing managed pieces. Keep `setup` as a compatible alias.

For Agent or CI composition, consume JSON and preserve the exit code. If the project is already a source checkout, use `node bin/motionloom.mjs setup --project-root <project> --motionloom-root <motionloom-checkout> --skip-install`; do not copy `project-context.json` or `.motionloom/project-memory.json` from the MotionLoom repository.

## Required workflow

1. **Understand** — run `motionloom init` once for a new host project, then continue normal product work until an animation task exists. At animation-task start, read the host project manifest and load the generated `project-context.json` and `.motionloom/project-memory.json`. For an already configured project, run `motionloom status --json` and refresh with `motionloom analyze <project-path> --init-memory` when context is missing, stale or ambiguous. In a repository checkout, the equivalent is `node bin/motionloom.mjs init` or `python scripts/analyze.py <project-path> --init-memory`.
2. **Plan** — classify the animation, select a framework, and generate a context-bound `motion-spec.json` with timing, easing, loop, accessibility, performance and source authority.
3. **Source** — resolve an authoritative asset from the project or `assets/library/`. Record attribution, license and checksum in the scene manifest's required `source_binding`; the binding's SHA-256 must match the bytes referenced by `manifest.file`. Do not promote an unknown or placeholder asset to production.
3a. **Classify asset provenance** — create or load `asset-provenance.json` with `motionloom asset-provenance`. Treat Agent-created material as ingestible only when its origin, generator task, license, file hash and derivation chain are explicit. Use `code_authored` for an authored runtime scene such as GSAP or Framer Motion; it may be runtime-tested and marked `review_required`, but never self-promotes to production eligibility or approval. `ai_generated` may be runtime-tested but is never production-eligible; `ai_assisted` requires human sign-off; `artist_authored` and `production_approved` cannot be self-asserted by an Agent or quality gate. Use `check --mode runtime` for candidate ingest and `check --mode production` only for a full production gate.
3b. **Compile asset consistency and lock multi-frame generation** — when a task contains multi-frame character actions, sprite sheets/atlases or layered maps, create the matching identity, action-set, frame-geometry, atlas and layered-map contracts from `schemas/`. For Agent-generated frame sequences, read `references/multi-frame-asset-generation.md` before generating frame 2 and apply it automatically without waiting for the user to request consistency. Lock exact canvas, apparent scale, pivot, footline, safe rectangle, transparent guard band, camera/orientation and identity from the accepted anchor frame. Generate source frames as separate isolated images; actions with six or more frames must never use one generated contact sheet or multi-pose canvas as production source material. Validate every accepted frame incrementally with `python3 scripts/frame-set-preflight.py --input <frame-geometry.json> --root <asset-root> --action-manifest <action-manifest.json> --json`; a shared source image, non-isolated source rect, scale drift beyond `bbox_drift_tolerance_px`, pivot/footline drift, guard-band violation, contamination, cross-action envelope, low action-separation margin or hash mismatch blocks continuation. The enhanced `frame-generation-lock` schema 0.2 binds `sequence_id`, action cues, forbidden competitors and the manifest path; each frame must have a schema 0.2 envelope. A generator-created envelope is only `declared` evidence and remains quarantined; only a separate verifier artifact with hash-bound provenance may be bound as `independently_bound`. Low-confidence frames are quarantined and regenerated from the accepted anchor, never relabeled or moved automatically. Only after the isolated frames pass may the Agent pack a sprite sheet/atlas and run the normal atlas contract.
 For general consistency checks run `motionloom asset-consistency validate --kind <identity|action-set|frame-geometry|atlas|layered-map> --input <contract> --root <asset-root> --json`; for action identity run `motionloom action-separation validate --input <action-manifest.json> --root <asset-root> --json` and use `motionloom action-separation envelope` only to create a declared/quarantined generator envelope; bind a separate verifier artifact before treating a frame as independently-bound evidence.
 The compiler measures actual PNG alpha bounds, pivot/footline/bbox drift, frame and atlas contamination, region overlap, parallax/z-order, tile seams and camera-safe bounds. A pass is deterministic contract evidence only; it never upgrades provenance, artist authority, production eligibility or human approval.
3c. **Ingest generation artifacts** — before using output from an internal skill or external provider, bind it with a `generation-receipt`, `control-track` and `export-manifest`. Run `motionloom artifact-intake intake --root <project-root> --registry artifact-adapter-registry.json --receipt <receipt> --controls <controls> --export-manifest <export> --json`. For a single-character AI frame sequence, first run `motionloom build-ai-pilot`: it rejects painted checkerboards, all-opaque RGBA, insufficient measured padding and canvas-spanning detached residue. Visually inspect the isolated output too: edge-connected alpha removal cannot prove that disconnected opaque artifacts are absent. The core path makes no provider call and stores no secret; adapters are evidence descriptors. Use `--provider chatgpt` for user-provided ChatGPT bytes so the receipt records `openai.chatgpt` and `user-mediated`; never relabel them as `internal-imagegen`. Both adapters are scaffold-only metadata, not proof of runtime readiness, artist authority or approval.
3d. **Build the runtime candidate and rig proof** — bind the intake bundle to identity/action/frame contracts with `motionloom runtime-candidate validate --root <project-root> --input <runtime-candidate.json> --json`, then validate the declared skeleton, sockets, actions, events, export target and runtime adapter with `motionloom rig-compatibility validate --root <project-root> --registry rig-adapter-registry.json --input <rig-contract.json> --json`. A passing candidate is `runtime_test_ready` and remains review-required; it cannot stand in for a production rig, human review or `production_approved`.
4. **Generate** — use the matching template or rig implementation. For body animation, preserve named anatomy, pivot and parent-first hierarchy. For generated frame sequences, do not batch the whole action blindly: preserve the locked anchor geometry and accept each frame only after the multi-frame preflight passes; regenerate only the failing frame rather than resizing accepted frames to match it.
5. **Render** — run the platform-neutral Node entrypoint for scene output, or `node scripts/runtime-adapters.mjs` for the verified Rive/GSAP/Framer Motion adapter matrix. Acceptance requires runtime evidence at 0/50/100%, not a static placeholder. Keep the render metadata beside the snapshots.
6. **Bind Intelligence Core** — build a framework-neutral `motion-ir.json`, `project-graph.json`, `provenance.json`, `replay-bundle.json`, `semantic-lint-report.json` and `semantic-lint-benchmark.json` with `python3 scripts/intelligence.py`. Select only a capability registry entry whose status is `verified`, whose evidence is fresh and whose compatibility matches the target environment. A confidence score or benchmark result can prioritize investigation; neither can replace deterministic or human acceptance.
6a. **Harden the trust boundary** — keep artifact and task bundles inside the repository/task root, reject symlinked evidence, bind replay to its exact `task_dir`, `task_id` and scene, select one deterministic report bundle per scene, and require browser candidate/review identity and expiry checks before readiness. The Dev Lab must reject cross-origin or identity-mismatched artifact bases. In strict runtime-observability runs, capture `runtime-telemetry.json` and a read-only `evidence-verifier-report.json`; verifier output must preserve `approval: false`. These checks expose risk and prevent evidence mixing, but do not turn heuristics or evidence integrity into approval.
6b. **Attest** — derive a canonical statement from the exact scene/task hashes, sign it with an Ed25519 key through `scripts/attestation.py`, and verify it with the independent `scripts/attestation-verifier.py` against a fail-closed `trust-policy.json`. DSSE/SLSA-compatible attestation proves signer and binding integrity only; `approval` must remain `false` and never replaces user review.
7. **Visual truth and browser review handoff** — after runtime rendering, build `visual-truth.json` from real baseline/candidate PNGs with `motionloom visual-truth build`. The contract records frame hashes, dimensions, runtime/source/manifest provenance and region-level review explanations; a changed frame means `review_required`, never automatic failure or approval. Then run `python3 scripts/review-hook.py prepare --task-dir artifacts/<task-id> --lab-url <internal-lab-url>`. The hook prepares the exact candidate and emits a JSON action for a browser-capable Agent. Trigger or suggest that Agent to open the emitted URL. For live candidates, expose the declared Action Library and real playback controls (Play/Pause/Restart/scrub/frame-step/speed/loop); when `devlab-state-machine.json` is hash-bound, expose its legal transitions and required review sequences. Deterministic 0/50/100 snapshots remain evidence/fallback, not a substitute for live interaction. This is not a separate Dev Lab Skill; it is a required post-render handoff.

> **Runtime-first reference:** `examples/agent-consumer/runtime-pilot/` and `src/output/runtime-pilot-framer/` demonstrate a code-authored Framer Motion lane with hash-bound Intake controls, deterministic 0/50/100 Playwright frames, strict runtime candidate validation, verifier and `approval: false` attestation before a prepared Dev Lab review. It is evidence of the pipeline, not a release approval or a substitute for an imported art package.
8. **Review capture** — the browser Agent calls `window.__lab.getReview()` after the user approves or requests changes, then persists it with `python3 scripts/report.py review --task-dir artifacts/<task-id> --candidate-id <id> --decision approved|changes_requested --reviewer user`. A change request returns to generation; no approval means no PR. Playback, action coverage, transition coverage and sequence completion remain evidence only and must never mint the user's decision.
9. **Validate** — run `motionloom asset-provenance check --input src/output/<scene>/asset-provenance.json --root src/output/<scene> --mode runtime|production --manifest src/output/<scene>/manifest.json`, `motionloom visual-truth validate --root . --input src/output/<scene>/visual-truth.json --scene <scene> --task-id <task-id>`, `motionloom review-hook validate --task-dir artifacts/<task-id>`, `motionloom intelligence semantic-lint benchmark --task-dir artifacts/<task-id> --iterations 25 --threshold-ms 500`, `motionloom runtime-telemetry <scene> artifacts/<task-id>`, the independent attestation verifier, `motionloom report-contract --root . --scenes-file <changed-scenes> --require-attestation`, `motionloom quality-gate --scene <scene> --context <context-path> --task-dir artifacts/<task-id> --require-intelligence --require-p1 --require-benchmark --require-telemetry --require-attestation --require-visual-truth --require-asset-provenance`, and `motionloom doctor --json` when validating the Skill package itself.
10. **Report** — create or update an artifact bundle with `python3 scripts/report.py`. Record facts with `report.py add`, structural defects with `report.py structure`, collect checksums with `report.py collect`, and run `report.py check` before rendering the final report. The final report must state completed, verified, not completed, blocked/failed, structure problems, browser candidate/review evidence and the recommended next Agent/Skill.
11. **Learn** — after a user-confirmed fix or a deterministic benchmark, record it with `motionloom remediation-learning record-outcome|record-benchmark`. Run `summary` to expose correction count, first-pass acceptance, success rate, issue-class outliers and benchmark pass rate. Only `--user-confirmed` outcomes contribute to remediation acceptance metrics.
12. **Confirm** — only after approved browser review and a passing quality gate run the platform-neutral PR preparation command. Commit, push and open PR are explicit side effects.

## Durable Project Memory

MotionLoom does not treat chat history as durable project memory. At the beginning of an animation task, load `.motionloom/project-memory.json`, validate its project identity and freshness, then recover the current project context. The memory records motion principles, asset/runtime policy, accepted and rejected decisions, user-confirmed remediation outcomes and invalidation metadata. It must remain task/project-bound and must never be copied across projects merely because the files look similar.

Use the cross-platform CLI surface:

```text
motionloom memory init --project-root <project>
motionloom memory inspect --project-root <project> --json
motionloom memory refresh --project-root <project> --json
motionloom memory recover --project-root <project> --json
motionloom memory validate --project-root <project> --json
```

Only user-confirmed decisions and outcomes may become durable remediation memory. A stale or mismatched memory must produce a machine-readable failure/recovery state; it must not silently influence generation or approval. Ubuntu, macOS and Windows are supported through the Node CLI wrapper and Python path APIs. Do not require Bash, fixed `/tmp` paths, POSIX separators or system `zip`/`unzip` in the npm command surface.

## Progressive disclosure

- Read `references/reporting-contract.md` when creating task, execution, issue or handoff artifacts.
- Read `references/runtime-capability.md` before claiming a framework is production-verified.
- Read `docs/FRAMEWORK-SELECTION.md` and `docs/CATEGORIES.md` when selecting a runtime.
- Read `references/multi-frame-asset-generation.md` before creating the second generated frame of any multi-frame action; this is an automatic source-generation rule, not an optional user preference.
- Read `docs/CHECKLIST.md` before marking a scene ready for review.
- Read `docs/DEV-LAB-RUNTIME.md` before declaring live actions, playback controls, Action Library metadata or state/transition review flows.
- Read `src/rig/README.md` for character body hierarchy and pose rules.
- Read `references/dotlottie-source-notes.md` when packaging or validating `.lottie` archives.
- Read `docs/ROADMAP-INTELLIGENCE.md` before extending graph, provenance, capability or replay behavior.
- Read `references/intelligence-core.md` before building or validating Intelligence Core artifacts.
- Read `docs/research/AGENT-PROTOCOL-FINDINGS.md` before exposing MotionLoom through Agent tools or MCP resources.
- Read `references/agent-interoperability.md` when installing MotionLoom into Codex, Claude Code, Cursor, OpenCode or another Agent environment; run `motionloom discovery check --root <motionloom-checkout> --json` before relying on a surface.
- Read `docs/research/agent-skill-ecosystem-notes.md` and `docs/research/ai-animation-tools-2026-report.md` before selecting a provider or internal capability; use its evidence to distinguish a scaffold adapter from a verified runtime path.

## Non-negotiable contracts

- Every task has a lifecycle state: `created`, `needs_context`, `planning`, `sourcing`, `generating`, `rendering`, `review_required`, `blocked`, `failed`, `validated`, `ready_for_pr`, or `confirmed`.
- Every production scene has context, motion spec, manifest, source binding, runtime metadata, 0/50/100 snapshots, browser-review candidate, checklist result and review artifact.
- `scaffold` and `static-validated` are not equivalent to `runtime-verified` or `project-integrated`.
- Never hide a missing dependency, failed render, missing license, context drift, incomplete review or unimplemented framework behind a successful prose response.
- Use JSON output and stable exit codes for Agent-to-Agent composition; do not require another Agent to parse chat text. The external evidence verifier is read-only and must never emit an approval decision.
- Destructive Git actions require explicit confirmation. Use `OPEN_PR=0` for local review-only runs.
- Intelligence Core artifacts are task-bound: graph, provenance, Motion IR and replay evidence must not be reused across tasks without revalidation.
- Provenance hashes materials and products; replay must fail on tampered or missing files; stale capability evidence must not be selected for production acceptance.
- Asset provenance is tiered: `code_authored` is runtime-only and may be `review_required`; `ai_generated` is `runtime_ready` but not `production_eligible`; `ai_assisted` becomes eligible only after human sign-off; `ai_assisted_human_reviewed` remains review-bound; `artist_authored` requires a verified human/artist record and full gate; `unknown` is `blocked`.
- `production_approved` is a human decision only. An Agent, generator metadata, signed attestation or quality gate may preserve or verify a decision but may never mint it; `approval` remains `false` in machine-generated evidence.
- Asset provenance binds each declared file to a SHA-256, license/source metadata, generator or derivation chain, runtime evidence and, where applicable, human review. Production checks fail closed on unknown origin, self-asserted artist authority, missing evidence or hash drift.
- Generated multi-frame source assets are isolated-frame-first. Lock canvas/apparent scale/pivot/footline/safe-rect geometry before frame 2, validate every accepted frame incrementally, and pack atlases only after preflight. Six-frame-or-longer generated actions must not use a single multi-pose source sheet. Deterministic source-geometry failures are blockers and must not be weakened into approval-friendly tolerances.
- Asset consistency is artifact-first and fail-closed: declared frame geometry, hashes, atlas regions and layered-map bounds must agree with measured runtime/source files. Heuristic warnings remain visible and may become blocking under `--strict`; no consistency result is an approval decision.
- Artifact Intake is provider-neutral and hash-bound: receipt, control track, export manifest, provenance reference and adapter registry evidence must agree with the actual output bytes. Provider metadata, a prompt, a skill name, a model identifier or an adapter status cannot mint artist authority, production eligibility, runtime proof or approval.
- A runtime candidate may become `runtime_test_ready` only when its intake and referenced consistency contracts pass. Rig compatibility must bind a supported adapter, skeleton/socket/action/event requirements and runtime evidence; `static-validated` and `scaffold` remain non-production states.
- Browser-review candidates are single-use, time-bounded and bound to the exact task, scene and candidate identity; Dev Lab artifact/task bases must be same-origin and identity-consistent before staging a review decision.
- Live Dev Lab review is data-driven and hash-bound: declared runtime and state-machine files must stay inside the scene, Action Library filtering must not weaken review coverage, and unsupported `runtime-trigger` transitions must fail visibly rather than silently switching clips.
- Report completeness must select one deterministic passing task bundle per scene and fail on ambiguous ties; a valid artifact is never sufficient to bypass explicit user approval.
- Runtime telemetry must bind task, scene, source, manifest, Motion IR and deterministic scrub points; tampered, stale, missing or cross-task telemetry is a verification failure.
- Visual Truth must bind baseline/candidate PNG hashes, dimensions, source, manifest, runtime evidence and Motion IR where available; it explains changed regions for review but never emits approval.
- Remediation Learning history is append-only and hash-chained; correction counts and first-pass acceptance guide the next Agent but never approve an artifact or replace current-task evidence.
- Signed attestation must bind the same task, scene, context, source, manifest, Motion IR and evidence hashes; unknown, expired or revoked signers fail closed. Attestation verification is an integrity result only and must preserve `approval: false`.

## Framework boundary

The audited production paths are **Lottie JSON runtime rendering, dotLottie v2 packaging, SVG cutout rigging, Rive Canvas, GSAP and Framer Motion**. Their evidence is generated by `node scripts/runtime-adapters.mjs` and includes deterministic scrub points, runtime state and PNG snapshots. Spine and Three.js remain scaffold/selection paths until their adapter-specific runtime tests pass and their capability level is upgraded in `agent-card.json`.

## Provenance and runtime commands

Every production `src/output/<scene>/manifest.json` must include a `source_binding` object matching `schemas/scene-manifest.schema.json`. The acceptance gate rejects a missing binding, a mismatched source path, an unknown license/authority or a stale SHA-256.

Every production candidate that includes generated or assisted material must also reference `asset-provenance.json`. Validate it with `motionloom asset-provenance`; use runtime mode to allow safe ingest/testing and production mode to require `production_eligible`. This contract is deliberately separate from step-level `schemas/provenance.schema.json`: the former answers who/what created an asset and whether it may advance, while the latter records the pipeline steps that handled it.

For multi-frame or layered assets, reference a consistency contract from the scene manifest with `consistency_ref` and `consistency_kind` (`identity`, `action-set`, `frame-geometry`, `atlas` or `layered-map`). `quality-gate.py --require-asset-consistency` and `report.py` validate the reference only when declared; missing references remain visible rather than being silently inferred.

The Intelligence Core contracts are defined in `schemas/project-graph.schema.json`, `schemas/provenance.schema.json`, `schemas/capability-registry.schema.json`, `schemas/motion-ir.schema.json`, `schemas/signed-attestation.schema.json` and `schemas/trust-policy.schema.json`. They make project relationships, supply-chain steps, runtime selection, framework-neutral intent and signer trust inspectable without relying on prose.

```bash
# Package a Lottie JSON scene as a dotLottie v2 archive (Node/fflate; no system zip required).
node scripts/to-dotlottie.mjs --scene-dir src/output/<scene> --output src/output/<scene>/animation.lottie

# Initialize and recover durable project memory.
motionloom memory init --project-root <project-path>
motionloom memory recover --project-root <project-path> --json

# Generated multi-frame source preflight: isolated canvases, scale/pivot/footline and guard-band checks.
python3 scripts/frame-set-preflight.py \
  --input src/output/<scene>/hero-walk-frame-geometry.json \
  --root src/output/<scene> --json

# Measure multi-frame, atlas or layered-map consistency from real artifacts.
motionloom asset-consistency validate --kind frame-geometry \
  --input src/output/<scene>/hero-walk-frame-geometry.json \
  --root src/output/<scene> --json
motionloom asset-consistency validate --kind atlas \
  --input src/output/<scene>/hero-atlas-contract.json \
  --root src/output/<scene> --strict --json

# Run the official runtime adapters in a real browser harness.
node scripts/runtime-adapters.mjs

# Capture and verify runtime telemetry without Bash dependencies.
motionloom runtime-telemetry <scene> artifacts/<task-id>

# Build and validate a provenance-bound visual comparison from real runtime PNGs.
motionloom visual-truth build --root . --scene <scene> \
  --baseline src/output/<scene>/snapshot/frame-00.png \
  --candidate src/output/<scene>/snapshot/frame-100.png \
  --source src/output/<scene>/<source-file> \
  --manifest src/output/<scene>/manifest.json \
  --runtime-evidence artifacts/<task-id>/runtime-adapters/runtime-evidence.json \
  --motion-ir artifacts/<task-id>/motion-ir.json --task-id <task-id> \
  --output src/output/<scene>/visual-truth.json
motionloom visual-truth validate --root . --input src/output/<scene>/visual-truth.json \
  --scene <scene> --task-id <task-id>

# Record only a user-confirmed remediation outcome, then summarize durable learning.
motionloom remediation-learning record-outcome --history artifacts/remediation-history.jsonl \
  --event-id outcome-001 --issue-id easing-drift --summary "User accepted easing correction" \
  --result pass --correction-count 1 --source-task-id <task-id> --user-confirmed --json
motionloom remediation-learning summary --history artifacts/remediation-history.jsonl \
  --output artifacts/remediation-summary.json --json

# Build the task-bound Intelligence Core artifacts.
python3 scripts/intelligence.py motion-ir build --task-dir artifacts/<task-id>
python3 scripts/intelligence.py graph build --task-dir artifacts/<task-id>
python3 scripts/intelligence.py provenance build --task-dir artifacts/<task-id>
python3 scripts/intelligence.py replay capture --task-dir artifacts/<task-id>

# Derive, sign and independently verify the exact task-bound attestation.
python3 scripts/attestation.py statement --scene-dir src/output/<scene> \
  --task-dir artifacts/<task-id> --context <project-context.json> \
  --output artifacts/<task-id>/attestation-statement.json
python3 scripts/attestation.py build --statement artifacts/<task-id>/attestation-statement.json \
  --private-key <managed-key-file> --key-id <key-id> \
  --output artifacts/<task-id>/attestation.json
python3 scripts/attestation-verifier.py --attestation artifacts/<task-id>/attestation.json \
  --trust-policy artifacts/<task-id>/trust-policy.json \
  --expected-task-id <task-id> --expected-scene <scene>
```

`runtime-evidence.json` records the runtime package, three scrub points, observed state and generated snapshots. A template alone is never enough to upgrade a framework from `scaffold_only` to `verified`.

For an observability-enabled run, use the platform-neutral runtime telemetry entrypoint exposed by the package. It regenerates the real-browser evidence and writes telemetry under the task bundle. `scripts/evidence-verifier.py` then checks task/scene/hash/path/age bindings with stable machine-readable output. A verifier pass means the evidence is internally consistent; it does not mean the animation is approved.

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

The bundle should contain `task.json`, `execution-report.json`, `decision-log.jsonl`, `artifact-manifest.json`, `quality-report.json`, `issue-register.json`, `review.json` and `handoff.json` as applicable. Telemetry-enabled bundles additionally expose `runtime-adapters/runtime-evidence.json`, `runtime-adapters/runtime-telemetry.json` and `evidence-verifier-report.json`; strict trust bundles also expose `attestation.json`, `trust-policy.json` and `attestation-verifier-report.json`. Reports must never convert “not run” into “passed”: an absent runtime or attestation artifact is a `not_completed` item or a blocker, while an invalid path belongs in `structure_review`. A valid signature remains distinct from user approval.
