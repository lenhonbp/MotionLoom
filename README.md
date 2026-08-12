# MotionLoom

A coding-agent skill for professional animation development: motion, character body rigs and assets. It does not guess — it **understands the host project, plans from a signed motion spec, generates from vetted source assets, renders everything in the Dev Lab for live testing, and only then confirms into a pull request**.

## Quick start

```bash
# 1. Understand the project
bash scripts/analyze.sh /path/to/your/project

# 1b. Start a transparent task ledger for Agent/human handoff
python3 scripts/report.py init --task-id onboarding-wave \
  --scene my-scene --intent "Character wave in onboarding" \
  --project-name your-project

# 2. Plan & sign a spec (example: a loading animation)
python3 src/core/spec.py generate loading --context /path/to/your/project/project-context.json \
  --output motion-spec.json --loop

# 3. Generate a body rig, then pose it
python3 src/rig/cutout_rig.py build \
  --input assets/library/avatar-base.svg --output rigged.svg
python3 src/rig/cutout_rig.py pose rigged.svg --pose walk \
  --duration 1.2 --fps 30 --out walk.json

# 3b. Bind the scene source to an authoritative provenance record
python3 scripts/manifest.py bind-source --scene my-scene \
  --source animation.json --kind project \
  --authority "host project manifest" --license MIT

# 4. Render runtime verification snapshots (0/50/100%; placeholders fail)
bash scripts/render.sh my-scene

# 4b. Package the Lottie source as a dotLottie v2 archive when required
bash scripts/to-dotlottie.sh my-scene

# 4c. Verify Rive, GSAP and Framer Motion through the real browser harness
node scripts/runtime-adapters.mjs

# 5. Boot the Dev Lab to test & fix interactively
bash scripts/devlab.sh my-scene

# 6. Run the acceptance gate, then confirm and ship
python3 scripts/quality-gate.py --scene my-scene \
  --context /path/to/your/project/project-context.json

# 6. Collect evidence and render the user-facing report
python3 scripts/report.py collect --task-dir artifacts/onboarding-wave
python3 scripts/report.py render --task-dir artifacts/onboarding-wave

# 7. Confirm and ship only after review
bash scripts/pr.sh my-scene
```

The kit is intended to run from a Git clone. Copy `project-context.example.json` only as a schema reference; always generate the real context with `scripts/analyze.sh` against the host project. Do not commit a context containing a temporary path or another project's brand tokens.

## Pipeline

| Step | Module | What it does |
|------|--------|--------------|
| 01 · Understand | `src/core/analyzer.py` | Reads package.json, design tokens and existing motion language; emits `project-context.json` inside the target project |
| 02 · Plan | `src/core/spec.py` | Generates & validates the motion spec against the framework matrix, easing canon and performance budget |
| 03 · Source | `assets/library/` | Vetted, traceable source assets with an attribution table — the authoritative geometry |
| 04 · Generate | `src/rig/cutout_rig.py`, `templates/` | Canonical templates per framework; 20-bone cutout body rigs with parent-first order |
| 05 · Dev Lab | `dev-lab/` | Self-contained static workbench: preview rendered evidence, scrub, quality checklist, fix notes, review export |
| 06 · Confirm → PR | `scripts/pr.sh` | Commits scene + spec + snapshots, opens the PR with an evidence body |

## Repository layout

| Path | Purpose |
|------|---------|
| `SKILL.md` | The agent-skill definition (installable into any coding agent) |
| `src/core/` | Analyzer, spec validator, snapshot renderer |
| `src/rig/` | Cutout character body rig engine |
| `templates/` | Canonical Lottie / Rive / GSAP / Framer Motion templates |
| `assets/library/` | Vetted source assets + attribution, including the MIT Rive adapter fixture |
| `scripts/` | Pipeline CLI (`analyze`, `render`, `devlab`, `pr`, `quality-gate`, `validate-lottie`, `to-dotlottie`, `runtime-adapters`, `skill-doctor`, `report`) |
| `dev-lab/` | Self-contained static Dev Lab + Playwright snapshot harness |
| `agent-card.json` | Capability discovery, runtime levels and side-effect policy for other Agents |
| `schemas/` | Task, report, artifact-manifest, scene-manifest and handoff JSON Schemas |
| `references/` | Progressive-disclosure contracts for reporting, runtime capability and dotLottie packaging |
| `artifacts/<task-id>/` | Per-task ledger, evidence, review, issue register and handoff bundle |
| `tests/` | Deterministic engine tests |
| `.github/workflows/quality.yml` | CI that re-runs the quality gate on every PR |

## The quality gate

A scene is only "ready" when, together, the Dev Lab checklist passes, runtime snapshot frames exist at 0/50/100%, the context-bound JSON spec matches the implementation, brand tokens come from the target project's `project-context.json`, and the required `source_binding` traces `manifest.file` to an authoritative source with a matching checksum. CI reproduces these checks on every PR — see [CHECKLIST.md](docs/CHECKLIST.md).

## Transparent task reporting

The Skill does not end with a prose claim that an animation is complete. Each task can be represented by `artifacts/<task-id>/`, which records the lifecycle state, decisions, changed artifacts, checksums, quality result, review decision, open problems and the next Agent handoff. Generate the report with `python3 scripts/report.py render --task-dir artifacts/<task-id>`.

The report must distinguish **completed**, **verified**, **not completed**, **blocked/failed**, **structure problems** and **recommended next Agent/Skill**. A scaffold-only runtime must be reported as `scaffold`; it cannot be described as `runtime-verified` until its adapter test has produced evidence.

Run `python3 scripts/skill-doctor.py --json` when changing the Skill package. It checks the frontmatter, required directories, schemas, Agent Card and references. CI also requires a task report/handoff bundle for changed scenes, so a future Agent cannot silently modify a scene without leaving a reviewable trail.

## Agent interoperability and public skills

`agent-card.json` is the discovery surface. It declares inputs, outputs, verified versus scaffold-only runtimes and Git side effects. Use official or public skills as focused references and adapters rather than copying their prompts into this repository: [LottieFiles dotLottie Web](https://github.com/LottieFiles/dotlottie-web/blob/main/SKILL.md) for runtime APIs, [Diffusion Studio text-to-lottie](https://github.com/diffusionstudio/lottie) for optional scene scaffolding, [Claude Lottie Skill](https://github.com/b1rdmania/claude-lottie-skill/blob/main/SKILL.md) for optional brand-aware asset discovery, and the [Agent Skills specification](https://agentskills.io/specification) plus [GitHub Agent Skills documentation](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) for packaging and portability.

The project-specific value remains in context binding, Motion Spec, asset provenance, runtime evidence, quality policy, review memory and handoff artifacts. The runtime adapter harness delegates rendering to the official packages; it does not reimplement Lottie/Rive runtimes, MCP transport or GitHub authentication inside this Skill.

### Important trust boundary

`ALLOW_PLACEHOLDER=1 bash scripts/render.sh <scene>` is diagnostic only. It creates visibly marked placeholder frames and the quality gate rejects them. A PR cannot be confirmed until the official runtime or the Dev Lab browser renderer has produced `snapshot/.render-meta.json` with `mode: runtime`.

## Standards basis

The audit and templates are grounded in first-party references: [LottieFiles runtimes](https://docs.lottiefiles.com/en/runtimes), the [dotLottie v2 specification](https://dotlottie.io/spec/2.0/), [Rive Web runtime](https://rive.app/docs/runtimes/web/web-js), [Rive state machines](https://rive.app/docs/runtimes/state-machines), and [GSAP accessibility guidance](https://gsap.com/resources/a11y/). End-to-end adapter evidence currently covers **Lottie JSON, dotLottie packaging, SVG cutout rigs, Rive, GSAP and Framer Motion**. Spine and Three.js remain scaffold-only until framework-specific runtime adapters are implemented.

## License

MIT
