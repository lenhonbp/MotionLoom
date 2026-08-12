# Browser review contract

Browser review is a required post-render handoff, not a separate skill. The Animation Skill prepares a candidate, then triggers or suggests a browser-capable Agent to open the internal Dev Lab URL. The browser Agent must inspect the exact candidate scene, not a demo scene or a different build.

```text
rendered → review_required → candidate prepared → internal browser opened
         → user reviews/fixes → review.json approved or changes_requested
         → validated → ready_for_pr → explicit confirmation
```

Prepare a candidate with:

```bash
python3 scripts/review-hook.py prepare \
  --task-dir artifacts/<task-id> \
  --lab-url http://127.0.0.1:3300
```

The command writes `browser-review.json` into the task bundle and scene output, records a deterministic `candidate_id`, binds the candidate to the context and animation source SHA-256, and emits JSON containing the exact URL and the next browser Agent action.

The browser-capable Agent must open the emitted URL, inspect frames 0/50/100, scrub the timeline, check the quality checklist, record notes, and ask the user for approval. The page exposes `window.__lab.getReview()` so the Agent can capture the review payload without relying on a downloaded file. Persist the captured payload with:

```bash
python3 scripts/report.py review \
  --task-dir artifacts/<task-id> \
  --decision approved \
  --candidate-id <candidate-id> \
  --reviewer user \
  --notes "Reviewed in the internal Dev Lab"
```

`ready_for_pr` and `confirmed` are rejected unless the review decision is `approved` and the candidate identity still matches the source, context and task. If the user requests a change, record `changes_requested`, add the issue, return to generation/rendering, and prepare a new candidate. Opening a browser is allowed as a review side effect; commit, push and PR remain explicit confirmation side effects.
