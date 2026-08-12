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

## Agent operating rules

The Agent must build the graph, Motion IR, provenance and replay bundle after render and before the strict quality gate. It may use a verified capability only when the registry evidence is fresh, its hash matches the referenced file and the target environment is compatible. `scaffold_only` is a planning option, never a production acceptance result.

The graph and provenance are evidence indexes, not approval tokens. A valid graph cannot bypass source binding, runtime assertions, browser review, reviewer consent or the `OPEN_PR=0` default. A confidence or risk value can prioritize investigation but cannot replace a deterministic rule or human decision.

## Strict validation

```bash
python3 scripts/intelligence.py graph validate --path artifacts/<task-id>/project-graph.json
python3 scripts/intelligence.py motion-ir validate --path artifacts/<task-id>/motion-ir.json
python3 scripts/intelligence.py provenance validate --task-dir artifacts/<task-id>
python3 scripts/intelligence.py replay verify \
  --root . --bundle artifacts/<task-id>/replay-bundle.json
python3 scripts/quality-gate.py \
  --scene <scene> \
  --context <project-context.json> \
  --task-dir artifacts/<task-id> \
  --require-browser-review --require-intelligence
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
| Browser review or approval failure | Candidate is not approved by the right reviewer/task | Return to Dev Lab review; never synthesize `review.json`. |

The public eval corpus is `tests/evals/intelligence-cases.json`. It is intentionally small in v0.1 and covers positive verified selection plus scaffold-only, stale evidence, tampering, graph corruption, replay tamper and foreign-task candidate failures. P1 should add multi-scene continuity and semantic intent cases without weakening these safety assertions.
