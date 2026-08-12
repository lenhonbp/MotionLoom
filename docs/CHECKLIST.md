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
- [ ] `manifest.json` records framework, source path, license note, spec hash, and completed checklist entries.

## PR readiness
- [ ] Snapshot PNGs exist for 0/50/100%.
- [ ] `motion-spec.json` is bound to the exact `project-context.json` hash (implements == planned).
- [ ] Dev Lab URL tested on mobile viewport and desktop.
