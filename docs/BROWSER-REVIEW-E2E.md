# MotionLoom Browser Review — End-to-End Runbook

This runbook defines the controlled path from a rendered scene to a user-approved, local-only confirm-to-PR commit. The Dev Lab is a mandatory post-render handoff, not a separate skill or autonomous approval agent.

## Contract

> A scene is not ready for PR until the exact browser-review candidate has been opened, the reviewer has inspected the runtime checkpoints, every checklist item has been explicitly selected, `review.json` has been persisted, and the context-bound quality gate has passed.

The candidate is bound to the task ID, scene ID, source checksum, project-context checksum, reviewer identity and expiry timestamp. The quality gate rejects stale or foreign evidence. `OPEN_PR=0` is the safe default: confirm-to-PR creates a local commit only and never pushes or opens a pull request implicitly.

## Operational sequence

From the repository root, prepare the task lifecycle with the official report CLI, render the scene, and stage the candidate through `review-hook.py prepare`. The resulting URL must include the candidate ID, artifact base and task base; do not replace it with a hand-written URL.

Open the candidate URL in the internal browser Dev Lab. Inspect the runtime at frames **0, 50 and 100**. Then select every checklist input explicitly. A checklist row being visible is not approval; the Dev Lab intentionally starts every input unchecked. Click **Confirm review** only after the user has approved the inspected candidate.

Persist the browser decision and run the gates in this order:

```bash
TASK_DIR=artifacts/<task-id>
SCENE=<scene-id>
CONTEXT=artifacts/<task-id>/project-context.json

python3 scripts/report.py review \
  --task-dir "$TASK_DIR" \
  --decision approved \
  --reviewer user \
  --candidate-id <candidate-id> \
  --notes "Approved after inspecting frames 0, 50 and 100." \
  --feedback "All checklist checks passed."

python3 scripts/review-hook.py validate \
  --task-dir "$TASK_DIR" \
  --require-approved

python3 scripts/quality-gate.py \
  --scene "$SCENE" \
  --context "$CONTEXT" \
  --task-dir "$TASK_DIR" \
  --require-browser-review

python3 scripts/report.py transition --task-dir "$TASK_DIR" --state validated
python3 scripts/report.py transition --task-dir "$TASK_DIR" --state ready_for_pr
python3 scripts/report.py check --task-dir "$TASK_DIR"

CONTEXT_PATH="$CONTEXT" TASK_DIR="$TASK_DIR" OPEN_PR=0 \
  bash scripts/pr.sh "$SCENE" "feat(animation): approved scene in Dev Lab"
```

After `pr.sh` returns the local commit SHA, record the final task state explicitly:

```bash
python3 scripts/report.py transition \
  --task-dir "$TASK_DIR" \
  --state confirmed \
  --commit-sha <local-commit-sha>
```

Do not set `OPEN_PR=1` unless the user separately requests a real push and pull request. A local-only confirmation is the default evidence boundary for this workflow.

## Evidence expected in the task bundle

| Artifact | Purpose |
| --- | --- |
| `task.json` | Lifecycle state, scene, project and context identity. |
| `browser-review.json` | Candidate identity, expiry, source/context hashes and approval status. |
| `review.json` | User decision, reviewer, timestamp, notes and candidate binding. |
| `quality-report.json` | Quality gate status and acceptance checks. |
| `execution-report.json` | Completed, verified, unresolved and next-agent evidence. |
| `REPORT.md` | Human-readable report generated from the task ledger. |
| `browser-observation.md` | Durable record of inspected runtime checkpoints and browser safety events. |
| `artifact-manifest.json` | SHA-256 inventory for task artifacts. |

## Verified reference run

The professional execution fixture is `artifacts/professional-review-e2e/`. It used scene `browser-review-smoke`, candidate `88a2f2f18ba45a07f56e`, and local commit `74a9ea6` on branch `fix/browser-review-smoke`. The candidate was inspected at frames 0, 50 and 100. The first confirm attempt was rejected because the checklist inputs were not selected; after all four checks were explicitly selected and the user confirmed, the browser review was approved.

The acceptance side of this run is covered by `test_approved_browser_review_e2e_contract` in `tests/scripts/run_tests.py`. That test copies the task into a clean temporary root and re-runs candidate validation, the context-bound quality gate and the confirmed-task report contract.
