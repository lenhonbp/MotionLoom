# Agent Protocol Findings

## Model Context Protocol

Source: <https://modelcontextprotocol.io/specification/2026-07-28>

The current MCP specification separates contextual data/resources, prompts/workflows and tools/capabilities. This maps cleanly to MotionLoom's future surface: project context and artifact bundles should be exposed as resources, workflow recipes as prompts or instructions, and side-effecting operations such as prepare-review or confirm-to-PR as tools with explicit input/output schemas.

Source: <https://modelcontextprotocol.io/specification/2026-07-28/server/tools>

The Tools specification distinguishes malformed protocol requests from actionable tool execution errors. Execution errors should carry self-correcting feedback for the model. It also states that tool invocations should preserve a human-in-the-loop ability to deny invocation. MotionLoom should therefore return structured diagnostics for invalid context, stale evidence, missing source binding and failed runtime checks, while keeping review approval and real PR side effects behind an explicit user confirmation boundary.

## Design implication for MotionLoom

MotionLoom should not expose one opaque “make animation” action. It should expose typed stages with discoverable capabilities, machine-readable error classes, resource references to the exact task/artifact bundle, and explicit side-effect levels. The protocol layer must preserve the existing `OPEN_PR=0` default and add an approval token or equivalent short-lived authority for any remote write.

## Provenance and attestations

Source: <https://slsa.dev/spec/v1.0/provenance>

SLSA models provenance as verifiable information about how an artifact was produced. The model separates the artifact `subject`, the parameterized `buildType`/build definition, the builder identity, and resolved dependencies/materials. Verification is based on trusted signer-builder pairs rather than a generic “generated successfully” flag.

Source: <https://github.com/in-toto/docs/blob/master/in-toto-spec.md>

in-toto describes a supply chain as an ordered set of steps with explicit actors, materials, products and inspections. Its core value is detecting a step that was omitted, replaced, added or performed by the wrong actor, not merely checking the final file hash.

## Design implication for MotionLoom

The current `artifact-manifest.json` is a useful checksum inventory but not yet a complete provenance attestation. A deeper design should add a signed or attestable `provenance.json` containing `materials`, `products`, `step`, `actor`, `builder`, `build_type`, `inputs`, `outputs` and verification policy. The chain should cover analyze, spec, source, generate, render, runtime adapter, browser review, quality gate and confirm—not just the final scene.

## Agent Skill packaging and evaluation

Source: <https://agentskills.io/specification>

The Agent Skills specification defines a small `SKILL.md` frontmatter contract and recommends progressive disclosure: short metadata for discovery, an instructions body kept below roughly 500 lines, and on-demand resources in `scripts/`, `references/` or `assets/`. MotionLoom should keep the activation contract concise and move framework-specific rules, schemas and long runbooks into referenced files.

Source: <https://agentskills.io/skill-creation/evaluating-skills>

The evaluation guidance recommends realistic prompts, expected outputs, input files, varied wording and at least one boundary or ambiguous case. It also describes an iterative loop of running evaluations, writing assertions, grading outputs and reviewing patterns with a human.

## Design implication for MotionLoom

The current regression suite validates scripts and artifacts, but it does not yet measure whether an Agent selected the correct capability, preserved project intent or produced a useful fix plan. MotionLoom needs an `evals/` corpus with project contexts, animation intents, ambiguous requests, stale source, unsupported runtime and review rejection cases. Each case should grade both machine contracts and human-facing report quality.
