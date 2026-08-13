# Dev Lab Quality Checklist

A scene is only ready for the confirm-into-PR step when every item below passes. The Dev Lab UI renders this checklist live against the active scene, and CI re-runs it on every PR.

## Motion correctness
- [ ] The implemented animation matches `motion-spec.json` exactly: duration, easing, loop, interactivity and reduced-motion policy.
- [ ] Easing uses a canonical name from the easing canon (no invented bezier constants without comment).
- [ ] Bone rotations follow parent-first order; no child rotates before its parent (body rigs).
- [ ] No frame pops at loop seam — first and last frames are visually continuous (looping scenes).

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

## PR readiness
- [ ] Snapshot PNGs exist for 0/50/100%.
- [ ] `visual-truth.json` binds real baseline/candidate frames to source, manifest and available runtime/Motion IR hashes; `approval` remains `false`.
- [ ] `motion-spec.json` is bound to the exact `project-context.json` hash (implements == planned).
- [ ] Dev Lab URL tested on mobile viewport and desktop.
- [ ] The production provenance check passes with `--mode production` and reports `production_eligible: true`.
- [ ] `production_approved` and browser-review approval are recorded only from the user's explicit review; attestation approval remains `false`.
