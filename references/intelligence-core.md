# Intelligence Core v0.1

Use this reference when an Agent needs to understand or extend MotionLoom's task-bound intelligence contracts. The core is deterministic and artifact-first: it indexes relationships, attests pipeline steps, filters runtime capabilities, describes framework-neutral motion intent and verifies replay integrity. It does not make an aesthetic claim or replace human review.

## Contract map

| Artifact | Command | Acceptance role |
| --- | --- | --- |
| `project-graph.json` | `python3 scripts/intelligence.py graph build --task-dir <task>` | Links project, intent, scene, context, artifacts and review with task identity and hashes. |
| `provenance.json` | `python3 scripts/intelligence.py provenance build --task-dir <task>` | Records step actor, builder, materials, products, policy, result and parent chain hash. |
| `capability-registry.json` | `python3 scripts/intelligence.py capabilities build --output <path>` | Describes verified/scaffold-only adapters, evidence freshness, compatibility, fallback and side effects. |
| `motion-ir.json` | `python3 scripts/intelligence.py motion-ir build --task-dir <task>` | Binds framework-neutral tracks and accessibility policy to task, scene, context and source. |
| `replay-bundle.json` | `python3 scripts/intelligence.py replay capture --root <root> --task-dir <task>` | Captures clean-root artifact hashes and environment metadata; verification fails on mutation or omission. |
| `semantic-lint-report.json` | `python3 scripts/intelligence.py semantic-lint build --task-dir <task>` | Reports intent, timing, easing, accessibility, performance and anti-pattern findings with severity, confidence and evidence. |
| `semantic-lint-benchmark.json` | `python3 scripts/intelligence.py semantic-lint benchmark --task-dir <task>` | Measures in-process semantic-lint execution, rule coverage and p95 against a deterministic threshold; it is a performance contract, not visual approval. |
| `runtime-telemetry.json` | `bash scripts/capture-runtime-telemetry.sh <scene> artifacts/<task-id>` | Records deterministic scrub-point observations, RAF timing, runtime state hashes and source/manifest/Motion IR bindings from the real adapter harness. |
| `evidence-verifier-report.json` | `python3 scripts/evidence-verifier.py --scene-dir <scene-dir> --task-dir <task> --runtime-evidence <path>` | Read-only external verification result for task/scene/path/hash/age integrity; `approval` is always `false`. |
| `attestation-statement.json` | `python3 scripts/attestation.py statement --scene-dir <scene-dir> --task-dir <task> --context <context>` | Derives canonical task/scene/source/manifest/Motion IR/evidence hash bindings before signing. |
| `attestation.json` | `python3 scripts/attestation.py build --statement <statement> --private-key <key> --key-id <id>` | DSSE-compatible Ed25519 envelope over the versioned statement; `approval` is always `false`. |
| `trust-policy.json` | `python3 scripts/attestation.py validate-policy --path <policy>` | Declares trusted keys, validity, rotation and fail-closed revocation behavior. |
| `attestation-verifier-report.json` | `python3 scripts/attestation-verifier.py --attestation <bundle> --trust-policy <policy>` | Independent verifier result with stable exit codes 0/10/11/12/13/14; verification never grants approval. |
| `continuity-report.json` | `python3 scripts/intelligence.py continuity build --task-dirs <task>...` | Checks context, intent, Motion IR and transition continuity across an ordered scene set. |
| `fix-plan.json` | `python3 scripts/intelligence.py fix-plan build --task-dir <task> --reports <report>...` | Converts findings into root cause, patch scope, selective rerun scope, verification and user-review requirements. |

## Agent operating rules

The Agent must build the graph, Motion IR, provenance, replay bundle, P1 feedback reports and semantic-lint benchmark after render and before the strict quality gate. For a strict observability run it must also capture runtime telemetry and run the external verifier before `--require-telemetry`. For a production trust run it must derive/sign `attestation.json`, copy or resolve a managed `trust-policy.json`, run the independent attestation verifier and use `--require-attestation`. It must run the report completeness contract for changed scenes; that contract selects one deterministic passing task bundle and fails on ambiguous ties. It may use a verified capability only when the registry evidence is fresh, its hash matches the referenced file and the target environment is compatible. `scaffold_only` is a planning option, never a production acceptance result.

The graph and provenance are evidence indexes, not approval tokens. A valid graph cannot bypass source binding, runtime assertions, browser review, reviewer consent or the `OPEN_PR=0` default. A confidence or risk value can prioritize investigation but cannot replace a deterministic rule or human decision.

All task-bound paths are resolved under their declared root and symlink traversal is rejected. Replay additionally binds `task_dir`, `task_id`, scene and every recorded file to the same task bundle. Browser-review and Dev Lab handoffs must use same-origin artifact/task bases and must agree on task, scene and candidate identity; expiry or mismatch is a review failure, not a warning to ignore.

## Strict validation

```bash
python3 scripts/intelligence.py graph validate --path artifacts/<task-id>/project-graph.json
python3 scripts/intelligence.py motion-ir validate --path artifacts/<task-id>/motion-ir.json
python3 scripts/intelligence.py provenance validate --task-dir artifacts/<task-id>
python3 scripts/intelligence.py replay verify \
  --root . --bundle artifacts/<task-id>/replay-bundle.json
python3 scripts/intelligence.py semantic-lint validate \
  --path artifacts/<task-id>/semantic-lint-report.json
python3 scripts/intelligence.py semantic-lint benchmark \
  --task-dir artifacts/<task-id> --iterations 25 --threshold-ms 500
python3 scripts/evidence-verifier.py \
  --scene-dir src/output/<scene> \
  --task-dir artifacts/<task-id> \
  --runtime-evidence runtime-adapters/runtime-evidence.json \
  --max-age-days 1 \
  --output artifacts/<task-id>/evidence-verifier-report.json
python3 scripts/attestation.py statement \
  --scene-dir src/output/<scene> \
  --task-dir artifacts/<task-id> \
  --context <project-context.json> \
  --output artifacts/<task-id>/attestation-statement.json
python3 scripts/attestation.py build \
  --statement artifacts/<task-id>/attestation-statement.json \
  --private-key <managed-ed25519-key> --key-id <key-id> \
  --output artifacts/<task-id>/attestation.json
python3 scripts/attestation-verifier.py \
  --attestation artifacts/<task-id>/attestation.json \
  --trust-policy artifacts/<task-id>/trust-policy.json \
  --expected-task-id <task-id> --expected-scene <scene> \
  --output artifacts/<task-id>/attestation-verifier-report.json
python3 scripts/intelligence.py continuity validate \
  --path artifacts/<task-id>/continuity-report.json
python3 scripts/intelligence.py fix-plan validate \
  --path artifacts/<task-id>/fix-plan.json
python3 scripts/quality-gate.py \
  --scene <scene> \
  --context <project-context.json> \
  --task-dir artifacts/<task-id> \
  --require-browser-review --require-intelligence --require-p1 --require-benchmark --require-telemetry --require-attestation
python3 scripts/eval-intelligence.py
```

The replay policy excludes generated reports and manifests because `report.py collect` and `report.py render` legitimately rewrite them. Source, spec, runtime evidence, review, graph, provenance and Motion IR remain integrity-bound. If any bound artifact changes, replay must be captured again or the gate must reject it.

## Failure semantics

| Failure | Meaning | Agent action |
| --- | --- | --- |
| `missing project-graph.json` or `missing motion-ir.json` | Intelligence artifacts were not built | Run the corresponding build command; do not mark the task validated. |
| `no capability satisfies the registry selection policy` | Runtime is stale, unsupported, scaffold-only or tampered | Choose another verified adapter or ask the user for an explicit exception. |
| `project graph edge references an unknown node` | Relationship index is corrupt | Rebuild the graph from the task bundle and inspect changed artifacts. |
| `replay bundle has mismatch(es)` | A bound artifact changed after capture | Identify the changed path, rerun only the affected pipeline scope, then capture replay again. |
| `semantic lint status: warn` | A heuristic or human-review finding exists | Preserve the finding, generate `fix-plan.json`, and request review; do not turn a warning into approval. |
| `semantic lint benchmark status: fail` | Semantic-lint p95 execution is at or above its declared threshold | Reduce lint complexity or raise the threshold only with an explicit contract change and new eval evidence; do not treat the benchmark as a visual-quality score. |
| `continuity report has drift` | Scene context, intent, asset or transition contract changed | Rerun only the affected scenes and transitions, then verify the updated continuity report. |
| `fix-plan source report hash mismatch` | The plan no longer describes the reports that produced it | Regenerate the plan from current reports before proposing a patch. |
| Browser review or approval failure | Candidate is not approved by the right reviewer/task | Return to Dev Lab review; never synthesize `review.json`. |
| `artifact is missing or outside task bundle` | A graph, provenance or replay record attempts to escape its declared task root or traverse a symlink | Stop the task, inspect the path and rebuild the artifact from a clean task bundle. |
| `ambiguous passing task bundles share the same state and updated_at` | More than one task bundle could supply evidence for the same changed scene | Resolve the duplicate explicitly and rerun the report contract; never merge evidence by filename order. |
| `artifact_base must share the Dev Lab origin` or identity binding failure | Dev Lab query parameters would mix an external or foreign task/candidate bundle | Reject the handoff and regenerate the review URL from the canonical task bundle. |
| `runtime telemetry verification failed` | Scrub-point evidence is stale, tampered, missing, cross-task, path-escaped or bound to different source/manifest/Motion IR bytes | Re-run the real runtime capture from the canonical scene/task bundle, then verify again; never treat the verifier as approval. |
| `attestation verification failed` | Payload hash, DSSE signature, signer validity/revocation, policy lookup, path binding or expected task/scene binding failed | Regenerate the statement from current artifacts, re-run the external verifier against a managed policy and investigate signer lifecycle; never flip `approval` or bypass user review. |

The public eval corpus is `tests/evals/intelligence-cases.json`. It covers positive verified selection plus scaffold-only, stale evidence, tampering, graph corruption, replay tamper and foreign-task candidate failures. P1 extends the acceptance surface with semantic warning preservation, generic-intent detection, multi-scene context drift, selective rerun binding, performance budget/frame-rate warnings, perceptual easing/reduced-motion warnings and benchmark execution time. The 1.9.0 slice adds runtime telemetry happy-path, state tamper, cross-task identity, stale evidence and symlink escape cases. The 2.0.0 slice adds clean attestation, payload tamper, binding mismatch, revoked signer and unknown signer cases without weakening the approval=false and human-review invariants.
