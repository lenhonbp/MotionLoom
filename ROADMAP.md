# MotionLoom Roadmap

MotionLoom's roadmap is organized around one question: **does this reduce incorrect animation iterations while keeping the user in control of quality and Git side effects?** A roadmap item is not complete because a prompt or template exists; it is complete when the contract, evidence, regression coverage and Agent handoff are inspectable.

## Current baseline: 2.2.0 published; provenance contract unreleased

The current repository baseline includes project-aware analysis, durable Project Memory, context-bound Motion Spec, source binding, real runtime adapters for Lottie/dotLottie/SVG cutout/Rive/GSAP/Framer Motion, Dev Lab browser review, Intelligence Core, semantic and continuity feedback, runtime telemetry, external evidence verification, signed attestation, Agent interoperability surfaces, Visual Truth, Remediation Learning and cross-platform CLI/CI contracts. The package metadata and public npm/GitHub release baseline are `2.2.0`; the AI-first asset provenance tier contract is the current unreleased change.

## Next milestones

| Milestone | Focus | Acceptance signal | Status |
|---|---|---|---|
| **2.2** | Visual Truth Contract | Provenance-bound frame comparison with `pass`, `fail`, `warn` and `unknown`; no automatic user approval | Included in 2.2.0 candidate |
| **2.3** | Remediation Learning | User-confirmed correction count, first-pass acceptance and rerender-avoidance ledger | Included in 2.2.0 candidate |
| **2.4** | Runtime Scale | Multi-project, browser and device corpus with capability compatibility explanations | Planned |
| **2.5** | Agent Interoperability | Versioned schemas, compatibility matrix and replayable task bundles across Agents | Included in 2.2.0 candidate |
| **2.6** | Agent-created Asset Provenance | Explicit origin/authority/readiness tiers; runtime ingest without automatic production approval; fail-closed production gate | Implemented in working tree; pending validation/release |

## Working-tree implementation status

The current implementation pass has delivered the contracts behind milestones 2.2, 2.3 and 2.5: canonical Agent discovery/install surfaces, consumer fixtures and a Ubuntu/macOS/Windows matrix; Visual Truth is bound into scene manifests, Dev Lab handoff and the review-first quality gate; Remediation Learning records hash-chained benchmark/outcome history; and CI replay evidence is rebuilt after generated artifacts. Milestone 2.6 now adds an asset-level provenance contract and production fail-closed gate while preserving runtime ingest for AI-generated pilots. The remaining work is validation, maintainer release and paired evaluation on additional real projects.

## Product principles

MotionLoom will remain project-bound, evidence-first and review-first. Heuristics may prioritize risk but cannot become approval. Attestations may prove signer and byte identity but cannot replace a user. Dev Lab remains a post-render handoff in the pipeline rather than a separate Skill with its own authority. Framework support will be promoted only after real adapter evidence and cross-platform checks pass.

## Metrics that matter

The project will track acceptance precision, false-approval rate, provenance completeness, replay success, time-to-fix, correction count, first-pass acceptance and rerender avoidance. Metrics must remain tied to labeled fixtures or user-confirmed review records; synthetic scores will not be presented as human visual approval.

## Explicitly out of scope

MotionLoom will not silently open or push pull requests, claim visual approval from a signature, hide a missing runtime behind a static placeholder, copy memory across projects, or treat a public asset catalog as a license authority. See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md) and the [trust-boundary reference](references/signed-attestation.md) before proposing a roadmap change.

## Proposing a roadmap change

Open a feature request with the problem, affected Agent workflow, proposed contract, evidence needed, failure modes and how user authority is preserved. A roadmap proposal that cannot explain its trust boundary is not ready for implementation.
