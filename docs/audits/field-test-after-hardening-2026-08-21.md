# Field test after hardening

## Browser pass 1

Candidate `9130000e6b6bc610c8d8` loaded from `http://127.0.0.1:4190` as `LIVE RUNTIME` / `LIVE SPRITE RUNTIME`. It was bound to task `browser-review-smoke-task`, used the sprite bundle hash `d8c2cb98a5cc089637b289580d773108199865b3707a196f54ecd943c71659a7`, and exposed the two required actions `idle` and `reverse`.

Selecting `reverse` reset the runtime to `reverse-00.png`, changed the inspector to `animation=reverse`, and moved review coverage from `1/2` to `2/2`. The inspector showed `playing=false`, `frame=0`, `totalFrames=3`, `fps=6`, `loop=false`, `mode=live-runtime`, and `runtime=sprite-sequence`.

## Browser pass 2

The live controls behaved correctly in browser: `restart` returned to frame 1, `stepFrames(1)` moved to frame 2 at 50%, setting speed `2x` and loop `true` updated the runtime, and play/pause ended at frame 3 with `playing=false`. The image source followed the declared sprite files, no console errors were observed, all four checklist checkboxes remained unchecked, and Approve remained disabled. This confirms the human review gate was not bypassed by live runtime success.

## Browser pass 3

With live coverage already at `2/2`, Approve was initially disabled because all four review checklist items were unchecked. Clicking all four checkboxes changed `Approve` to enabled and all four boxes to `true`, confirming the gate requires explicit checklist confirmation in addition to runtime coverage. A subsequent Reset action triggered a page navigation/reload, so the browser context was reloaded rather than returning a synchronous DOM payload; this is recorded as an observed reset behavior and will be checked again after the page settles.

## Browser pass 4

After the reset reload settled, the candidate remained bound to the same task and hash. Runtime returned to `idle`, frame 1/3, progress 0, `playing=false`, speed 1, loop true; coverage returned to `1/2`, all four checklist items were unchecked, Approve was disabled, and no console errors were observed. Reset therefore clears review progress rather than preserving an accidental approval-ready state.

## Fresh field test after CI fix

A fresh detached worktree from commit `e146164` was prepared through `review-hook prepare --root ...`; the previously observed external-root failure no longer occurred after passing `MOTIONLOOM_PROJECT_ROOT` and `cwd` to the internal Dev Lab/report subprocesses. The resulting candidate was `9130000e6b6bc610c8d8`, bound to `browser-review-smoke-task`, with live sprite bundle hash `d8c2cb98a5cc089637b289580d773108199865b3707a196f54ecd943c71659a7`.

The fresh browser load showed `LIVE RUNTIME` / `LIVE SPRITE RUNTIME`, two required actions, and coverage `1/2`. Selecting `reverse` reset to `reverse-00.png`, changed the inspector to `animation=reverse`, and moved coverage to `2/2`; the candidate/task identity remained consistent.
