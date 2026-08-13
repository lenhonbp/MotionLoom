# CI Replay Remediation — 2026-08-13

## Evidence

The `MotionLoom Quality` workflow for commit [`d148f21`](https://github.com/lenhonbp/MotionLoom/commit/d148f2175e47e3fc32f7156fc83af82c749b47ed) completed with failure in run [`31709781319`](https://github.com/lenhonbp/MotionLoom/actions/runs/31709781319). Documentation and Package Hygiene and Security Analysis completed successfully on the same commit.

The failing step was **Enforce context-bound quality gate**. The recorded rejection was:

> `replay bundle has 11 mismatch(es)`

The preceding Intelligence, project graph, Motion IR and provenance checks were valid. The failure therefore represented stale replay hashes, not an approval decision or a request to weaken the verifier.

## Root cause

The Quality workflow treated `replay-bundle.json` as a committed integrity snapshot, but earlier steps intentionally regenerate runtime telemetry, semantic-lint benchmark output, report/manifest output, signed attestation output and rendered runtime evidence for changed scenes. The quality gate then verified the old replay bundle against those newly generated files. A local verification before the generated-artifact phase could pass while the same sequence in CI correctly reported mismatches.

## Remediation

The workflow now runs the canonical command below after runtime snapshot rendering and before the context-bound quality gate:

```text
python3 scripts/intelligence.py replay capture \
  --task-dir "artifacts/${scene}-task" --root . \
  --output "artifacts/${scene}-task/replay-bundle.json"
```

The change does not remove replay verification, expand exclusions, or turn heuristic evidence into approval. A regression assertion checks that replay capture follows runtime rendering and precedes the quality gate. A temporary task-bundle test also confirms that tampered evidence is rejected, canonical capture rebuilds its hashes, and the rebuilt bundle verifies successfully.

## Local verification

After the remediation, the following checks passed locally: engine regression, docs audit, Skill Doctor, skill-creator validator, runtime adapter smoke, Agent discovery, installation matrix, Visual Truth validation, Remediation Learning validation, quality attestation with Visual Truth required, npm dry-run, Python syntax compilation and `git diff --check`.

This audit records the CI incident and its fix as evidence; it does not change the published `motionloom@2.1.0` version or grant user approval.
