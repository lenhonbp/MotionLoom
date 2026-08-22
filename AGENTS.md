# MotionLoom Agent Router

This repository exposes one canonical Agent Skill: [`SKILL.md`](SKILL.md). Load it when the task concerns animation production, motion design, asset binding, runtime rendering, Dev Lab review or PR handoff. Use [`agent-card.json`](agent-card.json) for machine-readable capabilities and [`agent-surfaces.json`](agent-surfaces.json) for installation/discovery compatibility.

## First action

Run the offline discovery check from the checkout root:

```text
motionloom discovery check --root . --json
```

Then follow the lifecycle in `SKILL.md`. The repository may coordinate Lottie, dotLottie, Rive, GSAP and Framer Motion, but it does not replace those runtimes. Render evidence, provenance, semantic checks and browser review are separate states. **Do not infer user approval from a passing heuristic, signature, screenshot or quality gate.**

Before calling an image/animation provider for a generated asset, create an `asset-generation-request.json` and run `motionloom asset-generation-plan plan --request <request.json> --project-root <project-root> --json`. Read the plan as a recommendation: it must expose provider-native canvas limits, batch versus single-frame behavior, safe padding/upscale options, and a manual or alternate-provider fallback. Never hide an incompatible provider behind a generic error, silently crop/stretch to fit, or place a secret in a request/receipt. For generated multi-frame animation assets, read [`references/multi-frame-asset-generation.md`](references/multi-frame-asset-generation.md) **before generating frame 2**. Apply it automatically without waiting for the user to ask: keep generated source frames isolated, lock canvas/scale/pivot/baseline from the accepted anchor frame, and pack sprite sheets/atlases only after the isolated frames pass. Before generating any later pose, create or load a `schemas/frame-generation-lock.schema.json` contract and run `motionloom frame-generation-lock validate`; compose each provider-facing frame instruction from that same lock with `motionloom frame-generation-lock compose`. For enhanced lock schema 0.2, bind one immutable `sequence_id`, `action_id`, action cues, forbidden competitor actions and `action_manifest`; every image must have a schema 0.2 manifest-bound frame envelope. A generator-created envelope is declared evidence and remains quarantined; only a separate verifier artifact with hash-bound provenance may be classified as `independently_bound`. After each generated frame, update the bound frame-geometry evidence and run `motionloom frame-set-preflight --action-manifest <action-manifest.json>` plus `motionloom action-separation validate`. Low action-separation margins are quarantined, never relabeled or moved automatically. Six-frame-or-longer actions must never use one generated multi-pose sheet as their production source.

For Dev Lab work, also read [`docs/CHECKLIST.md`](docs/CHECKLIST.md), [`docs/DEV-LAB-RUNTIME.md`](docs/DEV-LAB-RUNTIME.md) and [`docs/ACTION-SEPARATION.md`](docs/ACTION-SEPARATION.md). A runnable animation candidate should expose the live runtime descriptor/controls defined there and, when action evidence exists, its action-separation summary; 0/50/100 PNGs remain evidence/fallback and must not be presented as an interactive runtime when live playback is available.

## Source of truth

Do not duplicate or edit Agent-specific copies of the workflow. If this router conflicts with `SKILL.md`, the canonical root Skill and machine-readable schemas win. Use `references/agent-interoperability.md` for discovery details and `docs/AGENT-INTEGRATION.md` for installation examples.
