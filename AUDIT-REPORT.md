# Animation Skill Kit — Audit Report

**Audit date:** 2026-08-12  
**Scope:** `MotionLoom` — project analysis, motion specification, source/rig generation, Lottie/dotLottie validation, runtime snapshot, Dev Lab, quality gate, and confirm-to-PR flow.
**Verdict:** **PASS for the audited Lottie/body-rig path**, with explicit limits for Rive/GSAP/Framer Motion runtime coverage described below.

## Executive conclusion

The skill now follows a verifiable sequence rather than treating a visually plausible demo as acceptance evidence:

> **Analyze the host project → bind a JSON motion spec to the exact context hash → resolve authoritative source assets → generate/rig → render through a runtime → review the same scene in Dev Lab → enforce the quality gate → commit or open a PR.**

The most important trust boundary is now enforced by `scripts/quality-gate.py`: a scene is rejected when it has no context-bound `motion-spec.json`, no completed checklist, no source file inside the scene directory, no required 0/50/100% frames, or snapshot metadata that is not explicitly marked `mode: runtime`.

## Pipeline audit

| Stage | Implementation | Audit result |
|---|---|---|
| Understand | `src/core/analyzer.py`, `scripts/analyze.sh` | **Pass.** Context is written to the target project, manifest brand values override inferred tokens, and framework/motion language are captured. |
| Plan | `src/core/spec.py` | **Pass.** Category, framework matrix, duration/FPS, easing canon, loop, accessibility policy, source authority, and SHA-256 context binding are emitted and validated. |
| Source | `assets/library/`, manifest/source binding | **Pass with policy boundary.** The gate requires a source binding and manifest file; attribution still depends on the asset library record being maintained by the project owner. |
| Generate / rig | `src/rig/cutout_rig.py`, `templates/` | **Pass for SVG cutout rig.** The audited source now produces well-formed XML with explicit anatomy mapping and parent-first bone structure. |
| Runtime render | `src/core/snapshot.py`, `scripts/render-node.mjs` | **Pass for Lottie JSON.** Node renderer produced real 512×512 PNGs. Local JSON is passed to dotLottie as `data`, not as an invalid filesystem URL. |
| Dev Lab | `scripts/devlab.sh`, `dev-lab/public/`, `dev-lab/scripts/snapshot.mjs` | **Pass.** The same `src/output/<scene>` is copied into the static lab, served, scrubbed, and captured at 0/50/100%. |
| Quality gate | `scripts/quality-gate.py` | **Pass.** It rejects placeholder evidence, context drift, missing checklist items, invalid source paths, invalid Lottie payloads, and manifest/spec mismatches. |
| Confirm → PR | `scripts/pr.sh`, `.github/workflows/quality.yml` | **Pass in local Git smoke test.** The script now works from any caller cwd, requires a Git clone, runs the gate before commit, prevents empty commits, and supports `OPEN_PR=0` for a local review-only commit. |

## Confirmed defects fixed

### 1. Local Lottie rendering used an invalid input contract

The Node renderer passed a filesystem path as `src` to the dotLottie runtime. The runtime attempted to parse it as a URL and failed with `Failed to parse URL from /tmp/.../animation.json`. The fix reads `.json` as an object and `.lottie` as bytes, then passes the result through the runtime `data` property.

### 2. `.lottie` validation ignored the package manifest

The validator previously selected the first JSON member in the ZIP archive. That could validate an unrelated JSON file instead of the declared animation. It now requires `manifest.json`, resolves `initial.animation` or the first declared manifest entry, and loads the corresponding file under `a/`. This follows the [dotLottie v2 file structure and manifest specification](https://dotlottie.io/spec/2.0/).

### 3. Cutout rig output was not valid XML

The geometry parser matched a primitive and then consumed an enclosing group, causing nested closing tags and a parse error. The parser now distinguishes `data-part` groups from self-closing primitives. The audit verifies the generated SVG with Python's XML parser and checks named bones such as `head`, `l_upper_arm`, and `r_foot`.

### 4. Placeholder frames could be mistaken for production evidence

The fallback renderer remains useful for diagnostics, but it is now marked as `mode: placeholder` and rejected by the quality gate. Production acceptance requires `snapshot/.render-meta.json` with `mode: runtime` and matching scene metadata.

### 5. Confirm-to-PR depended on the caller's working directory

`pr.sh` now changes to the kit root before Git operations, rejects unsafe scene IDs, checks that it is running in a Git clone, runs the context-bound quality gate before staging, and refuses empty commits. The `.gitignore` no longer ignores required PNG snapshots.

### 6. CI was not self-sufficient

The workflow now installs the Lottie runtime, `@napi-rs/canvas`, Dev Lab dependencies, and Chromium; prepares changed scenes; boots the Dev Lab HTTP server; renders runtime frames; and runs the context-aware quality gate. It fails clearly when a changed scene lacks the required project context.

## Verification evidence

The following checks were executed after the fixes:

| Check | Result |
|---|---|
| `python3 tests/scripts/run_tests.py` | **25 assertions passed**, including analyzer binding, spec hash, default loop, rig XML, dotLottie manifest resolution, placeholder rejection, malformed-spec rejection, and category coverage. |
| Lottie runtime smoke render | **Pass.** Real PNG output: 512×512 RGBA. |
| End-to-end context → spec → render → gate | **Pass.** Gate returned `ACCEPTED audit-lottie: context + spec + runtime snapshots + checklist`. |
| Dev Lab snapshot harness | **Pass.** Wrote `frame-00.png`, `frame-50.png`, and `frame-100.png` from the served scene. |
| Confirm-to-PR smoke test | **Pass.** `fix/pr-smoke` commit created with `OPEN_PR=0`; no remote push was attempted. |
| Shell syntax | **Pass.** `bash -n` passed for all `scripts/*.sh`. |
| CI YAML formatting | **Pass.** Prettier parsed and accepted `.github/workflows/quality.yml`. |

## Standards used for the audit

The audit criteria were grounded in official or first-party documentation: [LottieFiles runtimes](https://docs.lottiefiles.com/en/runtimes), [dotLottie v2 specification](https://dotlottie.io/spec/2.0/), [Rive state machines](https://rive.app/docs/runtimes/state-machines), and [GSAP accessibility guidance](https://gsap.com/resources/a11y/). These sources support the requirements for runtime entrypoint resolution, state-machine/input contracts, and `prefers-reduced-motion` behavior. The collected notes are retained in [`audit-research.md`](audit-research.md).

## Remaining limitations and recommended next work

The audit proves the **Lottie JSON plus SVG cutout rig path** end to end. The Rive, GSAP, Framer Motion, and Three.js entries currently provide selection guidance and templates, but they do not yet have equivalent runtime renderers and integration tests in this kit. They should not be described as having the same production evidence level until each receives a framework-specific browser/runtime adapter and at least one fixture test.

The Dev Lab is a self-contained preview and evidence workbench; it is not yet a full bone editor or visual keyframe authoring tool. Body pose changes are currently generated through the rig CLI. A future iteration should add an explicit scene schema for editable controls, persist review/fix notes, and make the browser editor write back a signed artifact rather than only exporting screenshots.

The local audit initialized a Git baseline, but no GitHub remote, authentication, or remote PR was used. To publish, add the user's GitHub remote, push `main`, and run `scripts/pr.sh <scene>` only after the user confirms the scene in Dev Lab. The default script opens a PR when `gh` is available; use `OPEN_PR=0` when a local commit is desired without pushing.
