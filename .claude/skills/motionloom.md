# MotionLoom for Claude Code

Use MotionLoom when the task creates, fixes, validates, renders or hands off animation inside an existing project. Load the repository-root [`SKILL.md`](../../SKILL.md) as the canonical instruction source and [`agent-card.json`](../../agent-card.json) for capability discovery. Do not copy or fork the workflow into this file.

Start with `motionloom discovery check --root <motionloom-checkout> --json`, then follow the required lifecycle: project context → source binding → runtime evidence → Dev Lab browser review → user-confirmed handoff. `approval` remains `false` until the user explicitly approves.
