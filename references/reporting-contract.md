# Reporting and handoff contract

Use this reference when a task needs to be continued by another Agent or reviewed by a human.

## Required artifact roles

| File | Purpose |
|---|---|
| `task.json` | Current lifecycle state, task identity, project binding and commit/PR pointers |
| `execution-report.json` | Completed, verified, not completed, problems, structure review and next Agent |
| `decision-log.jsonl` | Append-only decisions with reason, evidence and actor |
| `artifact-manifest.json` | Paths, types, byte sizes and SHA-256 checksums |
| `quality-report.json` | Machine-readable quality gate result and rule-level evidence |
| `issue-register.json` | Problems, severity, status, owner and next action |
| `review.json` | Human/Agent review decision and categorized feedback |
| `handoff.json` | What the next Agent should read, do, verify or ask the user |

## Status semantics

Use `blocked` when required input, permission or consent is missing. Use `failed` when an attempted operation produced a technical error. Use `review_required` when the artifact exists but a human or downstream Agent must inspect it. Use `validated` only when the quality gate passes. Use `ready_for_pr` only when validation and review are both complete.

Never mark an item completed without an evidence path or command result. Never convert a scaffold-only runtime into a verified runtime in prose.

## CLI recording contract

Use `python3 scripts/report.py add` for facts that belong in `completed`, `verified`, `not_completed`, `problems` or `next_agent`. Use `python3 scripts/report.py structure` for missing files, broken references and untracked artifacts. Run `collect` to create deterministic SHA-256 entries, `check` to enforce semantic completeness, and `render` to create the human-readable `REPORT.md`.

The initial `not_completed` entry is removed automatically after the first completed or verified item is recorded. Explicit unfinished work must still be added to `not_completed`; this prevents an empty template from looking like a complete task while preserving a visible record of work that remains.

The report is an evidence index, not a chat transcript. Each item should point to a file, command output, test name, runtime metadata or review decision that another Agent can inspect.

## Handoff rule

The receiving Agent should be able to continue from `handoff.json`, `task.json`, `quality-report.json` and the artifact manifest without reconstructing the previous conversation. If that is not possible, the handoff is incomplete.
