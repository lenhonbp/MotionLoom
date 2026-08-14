# MotionLoom Roadmap

MotionLoom's roadmap is organized around one question: **does this reduce incorrect animation iterations while keeping the user in control of quality and Git side effects?** A roadmap item is not complete because a prompt or template exists; it is complete when the contract, evidence, regression coverage and Agent handoff are inspectable.

## Current baseline: 2.3.0 release target

The current repository baseline includes project-aware analysis, durable Project Memory, context-bound Motion Spec, source binding, real runtime adapters for Lottie/dotLottie/SVG cutout/Rive/GSAP/Framer Motion, Dev Lab browser review, Intelligence Core, semantic and continuity feedback, runtime telemetry, external evidence verification, signed attestation, Agent interoperability surfaces, Visual Truth, Remediation Learning, AI-first asset provenance and cross-platform CLI/CI contracts. The `2.3.0` release target adds one-command project onboarding without weakening review or Git side-effect boundaries.

## Next milestones

| Milestone | Focus | Acceptance signal | Status |
|---|---|---|---|
| **2.2** | Visual Truth Contract | Provenance-bound frame comparison with `pass`, `fail`, `warn` and `unknown`; no automatic user approval | Included in 2.2.0 candidate |
| **2.3** | Remediation Learning | User-confirmed correction count, first-pass acceptance and rerender-avoidance ledger | Included in 2.2.0 candidate |
| **2.4** | Runtime Scale | Multi-project, browser and device corpus with capability compatibility explanations | Planned |
| **2.5** | Agent Interoperability | Versioned schemas, compatibility matrix and replayable task bundles across Agents | Included in 2.2.0 candidate |
| **2.6** | Agent-created Asset Provenance | Explicit origin/authority/readiness tiers; runtime ingest without automatic production approval; fail-closed production gate | Included in 2.3.0 release target |
| **2.7** | One-command Onboarding | Project-bound setup/status/repair, Agent router merge, durable memory bootstrap and cross-platform installation recipe | Included in 2.3.0 release target |
| **2.8** | Asset Consistency Compiler | Measured frame geometry, atlas contamination and layered-map contracts with fail-closed regression and optional scene quality-gate binding | Implemented in working tree; pending validation/release |
| **2.9** | Provider-neutral Artifact Intake | Hash-bound generation receipt, control track and export manifest for internal skills/providers, with no embedded credentials or automatic authority | Implemented in working tree; pending validation/release |
| **3.0** | Control-to-runtime and rig evidence | Runtime candidate bridge plus skeleton/socket/action/event/export compatibility evidence surfaced in Dev Lab before user review | Implemented in working tree; pending validation/release |

## Working-tree implementation status

The current implementation pass has delivered the contracts behind milestones 2.2, 2.3, 2.5, 2.6 and 2.7, and has implemented the 2.8–3.0 layers in the working tree: canonical Agent discovery/install surfaces, consumer fixtures and a Ubuntu/macOS/Windows matrix; Visual Truth is bound into scene manifests, Dev Lab handoff and the review-first quality gate; Remediation Learning records hash-chained benchmark/outcome history; CI replay evidence is rebuilt after generated artifacts; asset provenance remains production fail-closed; `npx --yes motionloom setup` bootstraps a project without overwriting its Agent guidance; consistency contracts measure actual frame/atlas/map artifacts; Artifact Intake binds provider/internal-skill records to actual exports; runtime candidates require compatible contract references; and rig evidence validates adapter/skeleton/socket/event compatibility before review. The remaining work is full validation, maintainer release verification and paired evaluation on additional real projects.

## Product principles

MotionLoom will remain project-bound, evidence-first and review-first. Heuristics may prioritize risk but cannot become approval. Attestations may prove signer and byte identity but cannot replace a user. Dev Lab remains a post-render handoff in the pipeline rather than a separate Skill with its own authority. Framework support will be promoted only after real adapter evidence and cross-platform checks pass.

## Metrics that matter

The project will track acceptance precision, false-approval rate, provenance completeness, replay success, time-to-fix, correction count, first-pass acceptance and rerender avoidance. Metrics must remain tied to labeled fixtures or user-confirmed review records; synthetic scores will not be presented as human visual approval.

## Explicitly out of scope

MotionLoom will not silently open or push pull requests, claim visual approval from a signature, hide a missing runtime behind a static placeholder, copy memory across projects, or treat a public asset catalog as a license authority. See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md) and the [trust-boundary reference](references/signed-attestation.md) before proposing a roadmap change.

## Proposing a roadmap change

Open a feature request with the problem, affected Agent workflow, proposed contract, evidence needed, failure modes and how user authority is preserved. A roadmap proposal that cannot explain its trust boundary is not ready for implementation.
