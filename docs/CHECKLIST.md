# Dev Lab Quality Checklist

A scene is only ready for the confirm-into-PR step when every item below passes. The Dev Lab UI renders this checklist live against the active scene, and CI re-runs it on every PR.

## Motion correctness
- [ ] The implemented animation matches `motion-spec.json` exactly: duration, easing, loop, interactivity and reduced-motion policy.
- [ ] Easing uses a canonical name from the easing canon (no invented bezier constants without comment).
- [ ] Bone rotations follow parent-first order; no child rotates before its parent (body rigs).
- [ ] No frame pops at loop seam — first and last frames are visually continuous (looping scenes).

## Interactive Dev Lab runtime
- [ ] Any candidate with runnable animation/action data exposes `src/output/<scene>/devlab-runtime.json` using `schemas/devlab-runtime.schema.json`; captured PNG checkpoints are fallback evidence, not a substitute for an available live runtime.
- [ ] Every reviewable action/clip declared by the candidate (for example idle, walk, run, attack, state-machine animation, marker segment or project-specific action) is discoverable in Dev Lab without hard-coded action names.
- [ ] The live candidate supports every control it declares: select action, play, pause, restart, normalized seek/scrub, frame step where meaningful, playback speed and loop. Unsupported controls are disabled and never simulated as a passing runtime feature.
- [ ] Sprite-sequence playback renders the exact declared frame bytes; iframe runtimes expose the `runtime-bridge.js` controller and report current animation/time/progress/frame state where the runtime can provide it.
- [ ] The stage is usable for visual inspection: selectable background, zoom/fit, fullscreen and optional grid/bounds/baseline/pivot overlays are available without altering candidate bytes.
- [ ] `scripts/review-hook.py` hash-binds `devlab-runtime.json` plus every declared runtime file into the browser candidate. Path traversal, symlinked runtime files, missing files, duplicate action IDs and runtime byte drift fail closed.
- [ ] If a hash-bound live runtime fails to load, Dev Lab says `LIVE RUNTIME UNAVAILABLE`, may show captured evidence for diagnosis, and blocks approval. It must never relabel snapshot fallback as live runtime.
- [ ] When `review_policy.require_all_animations` is true, the user must inspect every `review_required` action before approval; a change request remains available at any time.
- [ ] Deterministic snapshot capture drives the same `window.__lab.selectAnimation()` / `window.__lab.seek()` controller used by interactive review for live candidates.

See [`DEV-LAB-RUNTIME.md`](DEV-LAB-RUNTIME.md) for the descriptor and runtime bridge contracts.

## Brand binding
- [ ] Primary/accent colors come from `project-context.json` (or an explicit user override recorded in the spec).
- [ ] Theme slots are used for every user-tunable color, never hardcoded hex inside the animation payload.

## Performance
- [ ] File size within budget (UI ≤300 KB, hero ≤1500 KB for Lottie).
- [ ] Layer count ≤80.
- [ ] Runtime snapshot frames at 0/50/100% render in <3 s each on CI; placeholder frames are rejected.

## Accessibility
- [ ] `prefers-reduced-motion` honored: looping decorations pause; essential motion reduces to a single crossfade.
- [ ] Lottie players carry `role="img"` plus a descriptive `aria-label`.

## Source traceability
- [ ] Every geometric asset references an authoritative source (`assets/library/` or the host project) — flagged if invented.
- [ ] `manifest.json` records framework, source path, license note, spec hash, visual-truth path, and completed checklist entries.
- [ ] `asset-provenance.json` records origin/authority, generator or derivation chain, license/source, per-file SHA-256 and runtime evidence.
- [ ] `ai_generated` assets may be runtime-ready but are not production-eligible; `unknown` assets are blocked.
- [ ] `artist_authored` is backed by a verifiable human/artist record and is not merely an Agent-authored field.

## Asset consistency
- [ ] Multi-frame actions declare an `identity` and `action-set` contract when the asset has shared character/style identity or loop/event requirements.
- [ ] `frame-geometry` measures the real PNG bytes: canvas size, alpha bounds, frame SHA-256, pivot/footline drift and opaque pixels outside each frame rect.
- [ ] Sprite atlases declare non-overlapping regions, explicit rotation policy and transparent pixels outside regions; contamination is blocking in strict runs.
- [ ] Layered maps declare unique layer IDs/z-order, intentional parallax order, tile seam policy, layer/world bounds and camera-safe bounds.
- [ ] Consistency output is stored with the task evidence and remains separate from provenance authority, production eligibility and user approval.

## Provider-neutral intake and runtime candidate
- [ ] Every Agent/internal-skill/provider output used by the scene has a hash-bound generation receipt, control track and export manifest; no receipt stores secrets or self-asserts approval.
- [ ] The selected artifact adapter is declared in `artifact-adapter-registry.json`; `scaffold` or `static-validated` status is not presented as runtime verification or production eligibility.
- [ ] `runtime-candidate.json` binds the intake bundle to the matching asset identity, action-set and frame geometry/atlas/map contracts; mismatched refs or hashes block the candidate.
- [ ] A rigged or motion-capture candidate declares skeleton, sockets, action/event coverage, export target and adapter evidence in `rig-compatibility.json`.
- [ ] Artifact Intake, runtime candidate and rig findings are present in the task handoff/Dev Lab rail and visibly retain `review_required` until the user records a decision.

## PR readiness
- [ ] Snapshot PNGs exist for 0/50/100%.
- [ ] `visual-truth.json` binds real baseline/candidate frames to source, manifest and available runtime/Motion IR hashes; `approval` remains `false`.
- [ ] `motion-spec.json` is bound to the exact `project-context.json` hash (implements == planned).
- [ ] Dev Lab URL tested on mobile viewport and desktop, including live transport controls when `devlab-runtime.json` is present.
- [ ] The production provenance check passes with `--mode production` and reports `production_eligible: true`.
- [ ] If `manifest.json` declares `consistency_ref`, `quality-gate.py --require-asset-consistency` passes for its declared `consistency_kind`.
- [ ] If `manifest.json` declares an Artifact Intake bundle, `quality-gate.py --require-artifact-intake` passes and the selected adapter/runtime evidence meets the requested mode.
- [ ] `production_approved` and browser-review approval are recorded only from the user's explicit review; attestation approval remains `false`.
