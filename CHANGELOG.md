# Changelog

All notable MotionLoom changes are documented here. The project follows semantic versioning for the npm package and keeps major contract changes in dedicated release notes under [`docs/releases/`](docs/releases/).

## [Unreleased]

No unreleased changes.

## [2.7.0] - 2026-08-22

### Added

- Add action-scoped frame separation contracts with schema `0.2`, immutable sequence/action identity, forbidden competitor actions, per-frame envelopes and separate verifier evidence artifacts.
- Add `motionloom asset-generation-plan plan`, a project-aware recommendation layer that evaluates tool/provider routes against the real project target before an Agent executes them.
- Separate MotionLoom recommendation status from execution status, evidence status, availability and execution eligibility, so provisional routes can be suggested without being misrepresented as verified.
- Add explicit `preferred`, `neutral` and `excluded` provider preference handling; user preference influences ranking but cannot override hard project, canvas, isolation or evidence constraints.
- Add deterministic transparent padding and integer nearest-neighbour scaling through `motionloom asset-adapt`, with hash-bound adaptation reports and no silent crop/stretch.
- Expose the new MotionLoom planning/action-separation capabilities, inputs, outputs and entrypoints in `agent-card.json` so compatible Agents can discover the workflow from an installed package.

### Hardened

- Treat generator-created verifier envelopes as `declared` and quarantined; only hash-bound separate verifier artifacts may become `independently_bound` evidence, and machine paths preserve `approval: false`.
- Enforce hash-bound scene/task browser-review candidate consistency in review-hook validation, quality gates and ready-for-PR report checks.
- Add an opt-in `doctor --runtime` preflight and `doctor:runtime` npm script that verifies the installed Playwright Chromium executable and prints a concrete remediation command.
- Require capability registry identifiers and adapter evidence versions to align with the package version during release verification.
- Keep normal asset planning useful when only provisional/manual routes exist while `--strict` stays fail-closed unless an execution-eligible route satisfies the active MotionLoom policy.
- Model provider availability separately from registry presence so unknown/unavailable tools are explained instead of being silently treated as executable.

### Changed

- MotionLoom is now the explicit project-aware decision and guidance layer in asset-generation plans: it assesses project constraints, ranks routes, explains tradeoffs, produces MotionLoom Agent Guidance and routes generated output back through MotionLoom validation/review.
- No provider is a hard-coded default. PixelLab routes remain scaffold metadata and are represented as provider choices inside MotionLoom recommendations rather than as a product dependency.

### Verified

- Pull requests #21 and #22 passed hosted MotionLoom Quality, Security Analysis, Documentation and Package Hygiene, Dev Lab Build, Frame Generation Lock and Apple compatibility checks before integration.
- Planner/adaptation regression tests cover user-preferred provisional tools, incompatible preferred tools, strict-mode failure, availability states, safe canvas adaptation and MotionLoom-branded Agent guidance.
- Deep audit remains green at 6,900/6,900 with 0 false positives and 0 false negatives, preserving the approval-false invariant.
- Add adversarial regression coverage proving foreign/divergent browser-review candidates and malformed or self-declared verifier evidence fail closed.

### Boundary

- Recommendation is not execution authority. A provisional/scaffold provider may be useful to suggest but never becomes verified merely because MotionLoom ranks it highly or the user prefers it.
- MotionLoom planning does not invoke provider APIs, store credentials, publish assets or grant human approval. Provider output must return through MotionLoom provenance, geometry/action-separation, runtime and Dev Lab review gates.

See the [2.7.0 release note](docs/releases/2.7.0.md) for the project-aware recommendation model, trust boundaries and project update steps.

## [2.6.1] - 2026-08-21

### Added

- Add a machine-readable `frame-generation-lock` contract that hash-binds the accepted identity/reference and locks canvas, alpha/color space, apparent size, pivot, footline, safe rectangle, transparent padding, camera/orientation and per-frame output identity before later frames are generated.
- Add provider-neutral `motionloom frame-generation-lock validate|compose|compose-all` commands and public Agent routing so every pose instruction is deterministically rebuilt from the same lock instead of relying on repeated prose prompts.
- Expose the strict generated `motionloom frame-set-preflight` command through the public CLI for post-generation alpha-bounds, scale, pivot/footline, guard-band, contamination and source-isolation checks.

### Hardened

- Default generated multi-frame source policy to one isolated PNG per frame; six-frame-or-longer actions must not use one generated pose sheet/contact sheet as production source material.
- Fail closed on stale reference hashes, duplicate frame outputs, pose-sheet policy violations, path escape, shared/non-isolated sources, post-generation resize and measured apparent-size drift beyond tolerance.
- Keep atlas packing as a later, separate gate: a clean atlas cannot repair inconsistent or contaminated source frames.

### Verified

- Dedicated Frame Generation Lock CI validates the public CLI, provider instruction composition and strict post-generation preflight.
- Pull request #18 passed MotionLoom Quality, Security Analysis, Documentation and Package Hygiene, plus the dedicated Frame Generation Lock workflow before merge.

### Boundary

- Frame locks, generated prompts, SHA-256 bindings, preflight passes and atlas checks are deterministic evidence only. They never grant artist authorship, production eligibility, runtime approval, licence authority or user approval.

See the [2.6.1 release note](docs/releases/2.6.1.md) for the generation/preflight contract and migration guidance.

## [2.6.0] - 2026-08-21

### Added

- Upgrade Dev Lab from checkpoint-oriented review to an interactive live-runtime workbench with Play, Pause, Restart, scrub, frame-step, speed and loop controls plus fullscreen, zoom/fit, background, grid, bounds, baseline and pivot inspection tools.
- Discover arbitrary project-defined actions from `devlab-runtime.json` instead of hard-coding `idle`, `walk`, `run` or `attack`; add groups/categories, tags, search, collapsible sections and review-state filters for large action libraries.
- Add the hash-bound `devlab-state-machine.json` contract, legal transition controls, transition history and bounded multi-step review sequences for flows such as `Idle -> Run -> Attack -> Hurt -> Idle`.
- Add strict iframe `runtime-trigger` support through `triggerTransition(request)` and portable `select-animation` transitions for sprite/clip runtimes.

### Hardened

- Bind declared live-runtime and state-machine bytes into the browser-review candidate so runtime drift invalidates stale review links.
- Fail closed on unsafe/missing runtime paths, duplicate animation ids, mismatched candidate/runtime action sets and unsupported runtime triggers; a failed live runtime remains inspectable only through explicit captured-evidence fallback and cannot be approved.
- Keep Action Library search/group/filter presentation independent from review coverage so hidden required actions do not disappear from the approval gate.
- Count runtime-trigger transitions only after the target state is observable; never silently replace a failed runtime state transition with a clip switch.
- Ship `runtime-bridge.js` with the npm package so installed-package iframe/state-machine review uses the same bridge as the repository harness.

### Verified

- Dev Lab CI covers deterministic snapshots, live sprite and iframe runtimes, a four-action interactive dogfood candidate, a twelve-action Action Library fixture, sprite state transitions, real iframe runtime-trigger transitions and browser-security smoke tests.
- Pull requests #13, #14 and #15 passed Dev Lab Build, MotionLoom Quality, Security Analysis and Documentation and Package Hygiene before this release candidate was prepared.

### Boundary

- Runtime playback, action/transition/sequence coverage, successful triggers, hashes, snapshots and automated checks are evidence only. `approved` remains an explicit user decision bound to the exact candidate.
- MotionLoom does not promote AI-generated material to artist-authored or production-approved status, and this release does not change the unsigned source-alpha status of the Apple companion apps.

See the [2.6.0 release note](docs/releases/2.6.0.md) for the Dev Lab runtime contract, verification scope and trust boundaries.

## [2.5.1] - 2026-08-18

### Fixed

- Preserve the caller's working directory through the npm CLI router, so default onboarding targets the consumer project instead of the installed package directory.
- Ship Dev Lab assets, the runtime harness, Python requirements and optional browser runtime dependencies in the npm tarball; verify the installed package from an isolated consumer project before release.
- Render Dev Lab metadata and checks with safe DOM APIs, enforce a same-origin script CSP, and reject invalid, terminal or expired browser-review candidates before enabling review.
- Restrict runtime evidence cleanup to a dedicated child of an explicit policy root and preserve caller data outside that boundary.
- Read the CLI version from `package.json` so displayed status stays aligned with release metadata.
- Publish from GitHub Actions through npm Trusted Publishing/OIDC with a pinned compatible npm client, without a long-lived `NPM_TOKEN`; provenance is generated automatically by npm.

### Verified

- Pass the full Python/Node regression suite, quality and signed-attestation gate, isolated installed-package smoke test, Dev Lab browser-security smoke test, real Rive/GSAP/Framer Motion runtime capture, 6,900-case deep stress run and twelve Swift package tests.
- Pass the pull-request Quality, Security Analysis, Documentation and Package Hygiene, Dev Lab and Apple workflows before preparing this patch release.

### Boundary

- This patch does not add framework capability, Apple signing, TestFlight distribution or production approval. Browser review and remote release actions remain explicit human-governed steps.

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

[2.7.0]: docs/releases/2.7.0.md
[2.6.1]: docs/releases/2.6.1.md
[2.6.0]: docs/releases/2.6.0.md
[2.5.1]: docs/releases/2.5.1.md
[2.5.0]: docs/releases/2.5.0.md
[2.4.0]: docs/releases/2.4.0.md
[2.3.0]: docs/releases/2.3.0.md
[2.2.0]: docs/releases/2.2.0.md
[2.1.0]: docs/releases/2.1.0.md
[2.0.0]: docs/releases/2.0.0.md
