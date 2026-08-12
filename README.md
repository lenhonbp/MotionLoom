# Animation Studio Skill Kit

A coding-agent skill for professional animation development: motion, character body rigs and assets. It does not guess — it **understands the host project, plans from a signed motion spec, generates from vetted source assets, renders everything in the Dev Lab for live testing, and only then confirms into a pull request**.

## Quick start

```bash
# 1. Understand the project
bash scripts/analyze.sh /path/to/your/project

# 2. Plan & sign a spec (example: a loading animation)
python3 src/core/spec.py generate loading --context /path/to/your/project/project-context.json \
  --output motion-spec.json --loop

# 3. Generate a body rig, then pose it
python3 src/rig/cutout_rig.py build \
  --input assets/library/avatar-base.svg --output rigged.svg
python3 src/rig/cutout_rig.py pose rigged.svg --pose walk \
  --duration 1.2 --fps 30 --out walk.json

# 4. Render runtime verification snapshots (0/50/100%; placeholders fail)
bash scripts/render.sh my-scene

# 5. Boot the Dev Lab to test & fix interactively
bash scripts/devlab.sh my-scene

# 6. Run the acceptance gate, then confirm and ship
python3 scripts/quality-gate.py --scene my-scene \
  --context /path/to/your/project/project-context.json
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
| `assets/library/` | Vetted source assets + attribution |
| `scripts/` | Pipeline CLI (`analyze`, `render`, `devlab`, `pr`, `quality-gate`, `validate-lottie`) |
| `dev-lab/` | Self-contained static Dev Lab + Playwright snapshot harness |
| `tests/` | Deterministic engine tests |
| `.github/workflows/quality.yml` | CI that re-runs the quality gate on every PR |

## The quality gate

A scene is only "ready" when, together, the Dev Lab checklist passes, runtime snapshot frames exist at 0/50/100%, the context-bound JSON spec matches the implementation, brand tokens come from the target project's `project-context.json`, and every geometric asset traces to an authoritative source. CI reproduces these checks on every PR — see [CHECKLIST.md](docs/CHECKLIST.md).

### Important trust boundary

`ALLOW_PLACEHOLDER=1 bash scripts/render.sh <scene>` is diagnostic only. It creates visibly marked placeholder frames and the quality gate rejects them. A PR cannot be confirmed until the official runtime or the Dev Lab browser renderer has produced `snapshot/.render-meta.json` with `mode: runtime`.

## License

MIT
