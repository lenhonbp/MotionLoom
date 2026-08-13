---
name: motionloom
description: Load the canonical MotionLoom Skill from the repository root for project-aware animation production, runtime evidence, Dev Lab review and review-first PR handoff.
---

# MotionLoom Agent Skills surface

This is a **portable discovery alias**, not a second copy of the Skill. Load the canonical [`SKILL.md`](../../../SKILL.md) from the repository root and use [`agent-card.json`](../../../agent-card.json) for machine-readable capabilities. Before using the Skill, run:

```text
motionloom discovery check --root <motionloom-checkout> --json
```

Keep the review boundary intact: a candidate may be rendered and reviewed, but approval is never inferred and a PR is never opened without explicit user confirmation.
