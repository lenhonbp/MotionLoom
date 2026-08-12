# Animation Studio Skill

**name:** animation-studio
**description:** End-to-end animation production agent. Understand the host project's context (brand, palette, tech stack, existing motion language), generate production-ready animation assets (motion, character body rigs, UI/scene assets), render them against official standards (Lottie/dotLottie, Rive, GSAP, Framer Motion, Spine, Three.js), launch the Dev Lab for live preview/testing, iterate on fixes, and deliver through a confirm-into-PR workflow.
**author:** Manus AI
**license:** MIT
**metadata:**
  - target_frameworks: lottie, dotlottie, rive, gsap, framer-motion, spine, threejs
  - domains: motion-graphics, character-body-rigging, ui-animation, scene-asset

## When to use this skill

Invoke this skill whenever the user asks to create, improve, fix, or deliver animation content: UI micro-interactions, loading states, hero scenes, character avatars with body rigs, icon animations, scroll-linked motion, data-viz motion, or any asset with time-based movement.

## The six-step pipeline

ALWAYS follow this pipeline. Never skip step 1. Every generated asset must be traceable back to a project constraint and a standards-compliant source.

1. **Understand** — read the project manifest (see `docs/PROJECT-MANIFEST.md`), extract brand tokens, tech stack, motion language, and target runtime. Build `project-context.json`.
2. **Plan** — classify the requested animation into a category (see `docs/CATEGORIES.md`), pick the optimal framework per `docs/FRAMEWORK-SELECTION.md`, and produce a context-bound `motion-spec.json` (duration, FPS, easing, size, loop, interactivity, accessibility policy).
3. **Source** — pull the exact source asset from `assets/library/` or the project repo. Never invent geometry from memory when an authoritative source exists.
4. **Generate** — scaffold from the matching template in `templates/`, apply the motion spec, and rig body hierarchies using `src/rig/`.
5. **Dev Lab** — render runtime evidence into `src/output/<scene>/`, boot the self-contained Dev Lab (`scripts/devlab.sh`), scrub the 0/50/100% frames, run the checklist (`docs/CHECKLIST.md`), record fix notes, and export the review JSON.
6. **Confirm or fix** — collect feedback, iterate in the lab, and when confirmed run `scripts/pr.sh` to commit + open the PR with the rendered frames and spec attached.

## Core conventions

Use motion-design terminology (ease-in, ease-out, ease-in-out, overshoot, anticipation) when writing specs; describe camera moves (push, pan, tilt) for scenes. Specify FPS and total frame count explicitly (default 60 fps, durations 0.4–1.2 s for UI, up to 4 s for hero). Prefer `.lottie`/dotLottie over raw Lottie JSON (smaller, multi-animation, embedded assets, state machines, theme slots). Use Web Workers (`DotLottieWorker`) when multiple animations run simultaneously. Set `autoplay: false` + `setFrame()` for static frame extraction (thumbnails, snapshot tests).

For character bodies, use cutout rigging: group each limb into a `<g>` with an explicit `transform-origin` pivot and `data-bone` attribute; animate rotations in a strict parent-first order. See `src/rig/README.md`.

## Output contract

Every delivered scene must contain in `src/output/<scene>/`:
- the compiled animation file (`.lottie`, `.riv`, or code module)
- `manifest.json` (scene metadata, framework, source file, license note, spec hash, and completed checks)
- `snapshot/` with PNG frames (0%, 50%, 100%) for visual diffing
- `snapshot/.render-meta.json` with `mode: runtime` (placeholders are rejected)
- `motion-spec.json` (the context-bound spec that was implemented)

## CLI quick reference

```
npx skills add <owner>/animation-skill-kit          # install into a coding agent
bash scripts/devlab.sh <scene>                       # copy + serve the self-contained Dev Lab
bash scripts/analyze.sh <project-path>               # step 1: write context in target project
python3 src/core/spec.py generate loading --context /path/to/project/project-context.json
bash scripts/render.sh <scene>                       # runtime render; fails if renderer is unavailable
python3 scripts/quality-gate.py --scene <scene> --context /path/to/project/project-context.json
bash scripts/pr.sh <scene>                           # gate, commit, push + optionally open PR
```
