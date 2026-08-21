# MotionLoom Current Status

> **Authority:** This document describes the current repository contract. Historical audit snapshots and benchmark reports remain valuable evidence, but they must not be read as claims about the latest checkout.

## Current release posture

MotionLoom's repository source and package manifest carry **2.6.1 release metadata**. The npm registry now resolves `motionloom@2.6.1`, and the `v2.6.1` Git tag is bound to the release-preparation main commit; future publication state must still be verified against the registry/tag rather than inferred from this document alone. The repository has a cross-platform CLI, one-command project onboarding, durable Project Memory, Agent interoperability surfaces, artifact-first handoff, runtime evidence, Visual Truth, Remediation Learning, signed attestation, AI-first asset provenance, a truthful code-authored runtime lane and an interactive browser-based Dev Lab review workbench. Dev Lab supports hash-bound live playback, arbitrary project-defined action libraries and optional state/transition review flows; generated frame sequences additionally use a machine-readable Frame Generation Lock plus fail-closed measured preflight so isolated source geometry is controlled before and after generation. The protected manual release workflow verifies package/changelog/release-note alignment before publication.

The repository is **engineering-ready for continued integration work**, not a universal production certification for every animation framework or every host project. CI status must be read from the latest GitHub Actions run, not inferred from historical audit prose.

## Evidence levels

| Capability | Current evidence level | What is actually proven | What is not implied |
|---|---|---|---|
| Lottie JSON and SVG cutout rig | End-to-end contract evidence | Context binding, source binding, runtime snapshots, Dev Lab review, quality gate and PR preflight have deterministic fixtures | Visual quality for every brand, asset or device |
| Rive, GSAP and Framer Motion | Adapter and fixture evidence | Framework-specific runtime adapters and smoke checks can render representative scenes through browser/runtime paths | Equivalent coverage to the Lottie path across arbitrary projects |
| Project Memory | Contract and relocation evidence | Stable project identity, atomic persistence, integrity guard, freshness states and path rebinding after relocation | Automatic correctness of an Agent's inferred decision |
| Generated multi-frame assets | Published-package consumer contract evidence | An isolated consumer installs `motionloom@2.6.1`, composes a 12-frame lock, validates 12 unique isolated PNG sources, blocks a deliberately shared neighboring source, and plays the accepted 12-frame set through live Dev Lab controls | Image-model art quality, identity fidelity on arbitrary generated assets, artist authorship, licence authority, production/runtime approval or user approval |
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

The bounded analyzer has been exercised against a labeled external corpus; see the [dated evidence note](audits/external-project-corpus-2026-08-13.md). The 2.5.x publication chain established npm/GitHub release provenance, 2.6.0 added the richer Dev Lab review surface, and 2.6.1 added proactive machine-readable frame-generation geometry control without weakening the human approval boundary. A published-package isolated consumer dogfood now covers a deterministic 12-frame generation/preflight/runtime/review path, including rejection of shared-source contamination; this deliberately remains synthetic contract evidence rather than a claim about image-generator visual quality. The highest-value next evidence work is user review inside a real consumer project with genuinely generated action frames and project-specific transitions, followed by paired product evaluation across more real projects and repeating the same provenance verification for each new release. Missing external projects are reported as `insufficient_evidence`, never as a pass. None of these items should weaken the user-review gate or convert runtime success or heuristic warnings into approval.
