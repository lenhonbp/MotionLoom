# MotionLoom Roadmap

MotionLoom's roadmap is organized around one question: **does this reduce incorrect animation iterations while keeping the user in control of quality and Git side effects?** A roadmap item is not complete because a prompt or template exists; it is complete when the contract, evidence, regression coverage and Agent handoff are inspectable.

## Current baseline: 2.1.0

The current repository baseline includes project-aware analysis, durable Project Memory, context-bound Motion Spec, source binding, real runtime adapters for Lottie/dotLottie/SVG cutout/Rive/GSAP/Framer Motion, Dev Lab browser review, Intelligence Core, semantic and continuity feedback, runtime telemetry, external evidence verification, signed attestation and cross-platform CLI/CI contracts.

## Next milestones

| Milestone | Focus | Acceptance signal | Status |
|---|---|---|---|
| **2.2** | Visual Truth Contract | Provenance-bound frame comparison with `pass`, `fail`, `warn` and `unknown`; no automatic user approval | Planned |
| **2.3** | Remediation Learning | User-confirmed correction count, first-pass acceptance and rerender-avoidance ledger | Planned |
| **2.4** | Runtime Scale | Multi-project, browser and device corpus with capability compatibility explanations | Planned |
| **2.5** | Agent Interoperability | Versioned schemas, compatibility matrix and replayable task bundles across Agents | Planned |

## Product principles

MotionLoom will remain project-bound, evidence-first and review-first. Heuristics may prioritize risk but cannot become approval. Attestations may prove signer and byte identity but cannot replace a user. Dev Lab remains a post-render handoff in the pipeline rather than a separate Skill with its own authority. Framework support will be promoted only after real adapter evidence and cross-platform checks pass.

## Metrics that matter

The project will track acceptance precision, false-approval rate, provenance completeness, replay success, time-to-fix, correction count, first-pass acceptance and rerender avoidance. Metrics must remain tied to labeled fixtures or user-confirmed review records; synthetic scores will not be presented as human visual approval.

## Explicitly out of scope

MotionLoom will not silently open or push pull requests, claim visual approval from a signature, hide a missing runtime behind a static placeholder, copy memory across projects, or treat a public asset catalog as a license authority. See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md) and the [trust-boundary reference](references/signed-attestation.md) before proposing a roadmap change.

## Proposing a roadmap change

Open a feature request with the problem, affected Agent workflow, proposed contract, evidence needed, failure modes and how user authority is preserved. A roadmap proposal that cannot explain its trust boundary is not ready for implementation.
