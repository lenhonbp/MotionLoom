# MotionLoom Deep Audit — Working Notes

## Confirmed findings

- The tracked browser-review smoke bundle is discoverable by `report-contract.py`, but its execution report still says `review_required`, retains the initial pending placeholder, and contains duplicate pending browser-review next-agent entries even though the candidate and review artifact are approved.
- The tracked smoke task points `context_path` at `/tmp/animation-review-context.json`, so a clean checkout cannot reproduce the report bundle without an external transient file.
- `review-hook.py` verifies a manifest source is inside `src/output`, but does not yet require it to remain inside the selected scene directory; a scene manifest could therefore bind another scene's source.
- `review-hook.py validate` computes the expected context hash differently from `prepare` when a spec has no context binding, creating an inconsistent fallback path.
- `pr.sh` validates the scene and review candidate but does not require `TASK_DIR` to be inside the repository or stage the task/report bundle with the scene, so a PR can omit the evidence that the gate just consumed.
- Runtime evidence has run identity and framework status, but the report is not yet cryptographically bound to a scene/source/manifest identity; a same-framework evidence file could be copied between scenes if the manifest path is changed.
- The first runtime-evidence quality-gate path referenced `source_sha` before its later assignment; Python's function-local import semantics made this an `UnboundLocalError` for Rive/GSAP/Framer Motion scenes. The branch now computes shared source and manifest hashes before evidence validation and has regression coverage for fresh and stale evidence.

## Audit direction

Prioritize provenance and PR-handoff hardening before adding more runtime features. The Dev Lab artifact-backed mode is implemented and should remain honest: demo catalog fallback is acceptable only when no `artifact_base` is supplied, while browser-review candidates must use the real artifact bundle.

## Remediation status

- [x] Scene confinement, candidate expiry, task/candidate identity and duplicate review handoff entries are hardened.
- [x] `pr.sh` requires an in-repository task bundle, matching `task.scene`, semantic report validation and evidence staging.
- [x] Runtime evidence records `run_id`, scene, source checksum and manifest checksum; quality gate rejects stale or mismatched files.
- [x] A regression test covers both accepted evidence and stale manifest rejection.
