# Changelog

All notable MotionLoom changes are documented here. The project follows semantic versioning for the npm package and keeps major contract changes in dedicated release notes under [`docs/releases/`](docs/releases/).

## [Unreleased]

## [2.5.0] - 2026-08-17

### Added

- Read-only `motionloom capability card --format json` discovery surface. It exports the evidence-validated runtime registry for an Agent, including runtime status, adapter/version, compatibility, verification timestamp, inputs/outputs, evidence references, limitations, fallback, risk and side-effect metadata.
- `pnpm intelligence:card` shortcut and `agent-card.json` command/capability declarations for machine-readable discovery without a parallel capability policy.
- `capability-registry.json` is included in the npm package allowlist, so the default card command has its verified registry after a normal package installation.
- Benchmark research ledger comparing public agent workflow, model-serving and AI/video repositories; the release applies the low-risk capability-card lesson and records deferred generation-profile and hash-bound workflow-template work with explicit gates.
- Native `apps/apple/` alpha in the GitHub source release: shared Swift packages for contracts, review state, macOS bridge, review UI and local-first CloudKit metadata sync, plus unsigned macOS Studio and iOS/iPadOS Review build targets and Apple CI.

### Verified

- Capability-card export validates registry evidence before output and fails closed for missing, altered or out-of-repository evidence. It does not select a runtime or infer review/production approval.
- The repository release target passes the full regression suite, Skill/doctor and documentation gates, package artifact inspection, and GitHub Quality, Security, Documentation and Apple CI checks.

### Boundary

- The Apple deliverable is an alpha source release. It has no Apple Developer signing, CloudKit production container, TestFlight distribution or iOS Simulator UI-smoke claim.
- Capability discovery is not execution authority. Runtime selection still validates current evidence, and attestation/production approval remain non-derived human decisions.

## [2.4.0] - 2026-08-15

### Added

- Deterministic Asset Consistency Compiler with identity, action-set, frame-geometry, atlas and layered-map schemas.
- Standard-library PNG measurement for alpha bounds, pivot/footline/bbox drift, frame/atlas contamination, region overlap, tile seams, parallax ordering and camera-safe bounds.
- Cross-platform `motionloom asset-consistency validate|analyze|report` commands, npm smoke scripts, public examples and regression coverage.
- Provider-neutral Artifact Intake contracts for generation receipts, control tracks, export manifests and hash-bound adapter registry evidence, including an internal-ImageGen-shaped scaffold that makes no provider API call.
- Control-to-runtime `runtime-candidate` bridge, rig compatibility contracts/registry, public fixtures and cross-platform CLI smoke scripts for skeleton/socket/action/event/export bindings.
- Dev Lab evidence rail and Pipeline handoff support for Artifact Intake, runtime candidate and rig compatibility findings before a user review decision.
- Truthful `code_authored` provenance lane for runtime scenes, with a hash-bound Framer Motion pilot rendered by Playwright at 0/50/100%, integrity verification, local-only attestation and a pending human Dev Lab review.
- Fail-closed task-bundle resolver for Quality CI that binds `task.json.scene` to the changed scene rather than inferring a directory name from the scene slug.

### Fixed

- Quality Gate and task reports can validate an explicitly declared `consistency_ref` without forcing legacy scenes to invent a contract; strict production runs fail closed on a non-ready contract.
- Quality Gate and reports accept explicitly declared Artifact Intake evidence without breaking legacy scenes, and preserve `review_required` rather than flattening adapter/candidate/rig findings to a pass.
- Quality CI correctly discovers valid task bundles whose task ID differs from the scene slug, including the runtime-first pilot shape.

### Boundary

- Consistency evidence measures and reports artifact agreement only. It never grants artist authority, production eligibility, production approval or PR authorization.
- A provider name, internal-skill metadata, generation receipt, control plan, compatible rig or runtime candidate never grants artist authority, production eligibility, production approval or PR authorization.

## [2.3.0] - 2026-08-14

### Added

- AI-first, human-governed asset provenance contract with explicit authority/origin tiers, readiness states, generator/derivation metadata, per-file SHA-256, license/source records, runtime evidence and human-review boundaries.
- Cross-platform `motionloom asset-provenance` commands for validation, classification, reporting and runtime/production checks, plus a transparent AI-generated pilot fixture.
- One-command `npx --yes motionloom setup` onboarding for real projects, with package-manager detection, local devDependency installation, project-bound context and durable Project Memory bootstrap.
- Read-only `motionloom status`, safe `motionloom repair`, dry-run JSON output and an idempotent managed `AGENTS.md` router for Agent integration.
- Canonical `npx` installation recipe in Agent discovery plus Ubuntu/macOS/Windows onboarding regressions and package/docs guards.

### Fixed

- Production quality and PR preflight now fail closed when an asset is unknown, self-asserted as artist-authored, not production-eligible or missing a manifest-bound provenance record; `production_approved` remains human-only.
- Setup JSON output no longer mixes package-manager logs with machine-readable results, and repair/status routing does not trigger an unintended full setup.

### Verified

- Full regression, onboarding and installation-matrix tests, discovery contract, docs audit, Skill Doctor, skill-creator validation, quality validation, npm tarball dry-run and diff hygiene pass.

### Boundary

- Setup never commits, pushes, opens a PR, grants approval or promotes asset provenance. User review remains required before any PR handoff.

## [2.2.0] - 2026-08-13

### Added

- Canonical Agent interoperability surfaces for `.agents/skills`, `.claude`, `.codex`, source discovery and cross-platform installation checks.
- Consumer fixtures for Lottie/dotLottie, Rive, GSAP, Framer Motion, body rigs and multi-scene continuity.
- Visual Truth Contract with frame hashes, runtime/source provenance, deterministic perceptual signals, region explanations and review-required semantics.
- Append-only, hash-chained Remediation Learning ledger for user-confirmed outcomes, correction counts, first-pass acceptance, issue-class outliers and benchmark provenance.

### Fixed

- Quality CI now rebuilds the context-bound replay bundle after runtime, report and attestation artifacts are generated, preventing stale replay hashes from rejecting an otherwise valid changed-scene gate.

### Verified

- Mainline Quality, Documentation and Package Hygiene, and Security workflows pass on the replay-remediation commit.
- The local release candidate passes the full regression, docs/Skill validation, runtime adapter, discovery, installation matrix, Visual Truth, Remediation Learning, attestation and npm tarball checks.

### Boundary

- This is a release candidate prepared from the green mainline. Remote tag creation, GitHub Release creation and npm publication remain explicit maintainer actions; evidence and heuristics never grant user approval.

## [2.1.0] - 2026-08-13

### Added

- Durable, relocatable Project Memory with schema validation, atomic writes, canonical integrity and stable lifecycle exit codes.
- Cross-platform npm CLI routing for Ubuntu, macOS and Windows without Bash-only user commands or system `zip`/`unzip` dependencies.
- Memory loader integration for project analysis, reports, review hooks, handoff and downstream Agent continuity.
- Ubuntu/macOS/Windows CI matrix for Project Memory recovery, CLI routing and npm tarball inspection.
- Public repository governance documents, contribution workflow, security policy, support guide, roadmap, issue forms and pull-request template.

### Fixed

- Rebinding a relocated checkout no longer invalidates integrity merely because `project.root_path` changed.
- Recovery atomically refreshes runtime path, repository and package metadata while preserving the durable project identity contract.

### Verified

- Full regression, Intelligence Core evaluation, Skill Doctor, strict quality gate, npm package dry-run and Dev Lab production build pass.
- Relocation coverage includes Git remote identity, Unicode paths, spaces in paths, stale context and user-confirmed outcome invariants.

See the [2.1.0 release note](docs/releases/2.1.0.md) for scope, trust boundaries and remaining work.

## [2.0.0] - 2026-08-12

### Added

- DSSE-compatible Ed25519 signed attestation and fail-closed trust policy verification.
- External verifier, attestation report contract and Dev Lab attestation rail.

See the [2.0.0 release note](docs/releases/2.0.0.md).

## Earlier releases

The 1.5.0–1.9.0 milestones established runtime evidence, browser review, Intelligence Core, semantic lint, continuity, telemetry and trust-boundary hardening. Their detailed notes are available in [`docs/releases/`](docs/releases/).

[2.2.0]: docs/releases/2.2.0.md
[2.5.0]: docs/releases/2.5.0.md
[2.4.0]: docs/releases/2.4.0.md
[2.3.0]: docs/releases/2.3.0.md
[2.1.0]: docs/releases/2.1.0.md
[2.0.0]: docs/releases/2.0.0.md
