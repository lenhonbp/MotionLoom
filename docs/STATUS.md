# MotionLoom Current Status

> **Authority:** This document describes the current repository contract. Historical audit snapshots and benchmark reports remain valuable evidence, but they must not be read as claims about the latest checkout.

## Current release posture

MotionLoom's repository source and package manifest carry **2.6.0 release metadata**. The publication state of the npm registry and GitHub Release/tag must be verified against the latest release workflow rather than inferred from this document. The repository has a cross-platform CLI, one-command project onboarding, durable Project Memory, Agent interoperability surfaces, artifact-first handoff, runtime evidence, Visual Truth, Remediation Learning, signed attestation, AI-first asset provenance, a truthful code-authored runtime lane and an interactive browser-based Dev Lab review workbench. Dev Lab now supports hash-bound live playback, arbitrary project-defined action libraries, and optional state/transition review flows in addition to deterministic snapshot evidence. The protected manual release workflow verifies package/changelog/release-note alignment before publication.

The repository is **engineering-ready for continued integration work**, not a universal production certification for every animation framework or every host project. CI status must be read from the latest GitHub Actions run, not inferred from historical audit prose.

## Evidence levels

| Capability | Current evidence level | What is actually proven | What is not implied |
|---|---|---|---|
| Lottie JSON and SVG cutout rig | End-to-end contract evidence | Context binding, source binding, runtime snapshots, Dev Lab review, quality gate and PR preflight have deterministic fixtures | Visual quality for every brand, asset or device |
| Rive, GSAP and Framer Motion | Adapter and fixture evidence | Framework-specific runtime adapters and smoke checks can render representative scenes through browser/runtime paths | Equivalent coverage to the Lottie path across arbitrary projects |
| Project Memory | Contract and relocation evidence | Stable project identity, atomic persistence, integrity guard, freshness states and path rebinding after relocation | Automatic correctness of an Agent's inferred decision |
| Semantic intelligence | Deterministic evaluation evidence | Project graph, provenance, Motion IR, continuity, fix-plan and adversarial/deep-stress contracts; bounded analyzer reports scan budgets and truncation | Human-level design judgment, external-project product-value evidence or guaranteed first-pass acceptance |
| Dev Lab | Interactive review infrastructure evidence | Identity-bound candidate loading, live runtime playback controls, arbitrary Action Library discovery, state/transition and review-sequence testing, deterministic snapshots, user checklist and review export | A full visual authoring editor, automatic approval or PR authorization |

## Normative sources

Use the following order when sources disagree:

1. The active schemas, validators and executable tests define machine-enforced behavior.
2. `SKILL.md`, `agent-card.json` and the current README define the Agent-facing contract.
3. This status document defines current capability posture and evidence boundaries.
4. Versioned release notes and focused audit reports explain a release or milestone at the time it was produced.
5. Root-level historical audit snapshots are context only and must be labeled historical.

## Known next work

The bounded analyzer has been exercised against a labeled external corpus; see the [dated evidence note](audits/external-project-corpus-2026-08-13.md). The 2.5.x publication chain established npm/GitHub release provenance, and 2.6.0 adds a substantially richer Dev Lab review surface without weakening the human approval boundary. The highest-value next evidence work is consumer-project review of real action sets and transitions, followed by paired product evaluation across more real projects and repeating the same provenance verification for each new release. Missing external projects are reported as `insufficient_evidence`, never as a pass. None of these items should weaken the user-review gate or convert runtime success or heuristic warnings into approval.
