# MotionLoom Agent Router

This repository exposes one canonical Agent Skill: [`SKILL.md`](SKILL.md). Load it when the task concerns animation production, motion design, asset binding, runtime rendering, Dev Lab review or PR handoff. Use [`agent-card.json`](agent-card.json) for machine-readable capabilities and [`agent-surfaces.json`](agent-surfaces.json) for installation/discovery compatibility.

## First action

Run the offline discovery check from the checkout root:

```text
motionloom discovery check --root . --json
```

Then follow the lifecycle in `SKILL.md`. The repository may coordinate Lottie, dotLottie, Rive, GSAP and Framer Motion, but it does not replace those runtimes. Render evidence, provenance, semantic checks and browser review are separate states. **Do not infer user approval from a passing heuristic, signature, screenshot or quality gate.**

## Source of truth

Do not duplicate or edit Agent-specific copies of the workflow. If this router conflicts with `SKILL.md`, the canonical root Skill and machine-readable schemas win. Use `references/agent-interoperability.md` for discovery details and `docs/AGENT-INTEGRATION.md` for installation examples.
