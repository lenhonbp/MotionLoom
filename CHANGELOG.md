# Changelog

All notable MotionLoom changes are documented here. The project follows semantic versioning for the npm package and keeps major contract changes in dedicated release notes under [`docs/releases/`](docs/releases/).

## [Unreleased]

- No unreleased changes are currently tracked.

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
[2.1.0]: docs/releases/2.1.0.md
[2.0.0]: docs/releases/2.0.0.md
