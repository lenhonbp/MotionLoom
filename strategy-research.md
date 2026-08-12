# Strategy research — differentiating Animation Skill Kit

## Evidence log

### Anthropic Agent Skills repository

Source: https://github.com/anthropics/skills

The repository describes Skills as folders of instructions, scripts, and resources that an agent loads dynamically for specialized, repeatable tasks. Each skill is self-contained and contains a `SKILL.md` with instructions and metadata. The repository also includes examples ranging from creative work to testing web apps and MCP server generation, and links to the Agent Skills specification at agentskills.io.

Implication for this project: portability starts with a conventional self-contained skill package, but differentiation cannot be only the `SKILL.md`. Animation Skill Kit should add machine-readable input/output contracts, capability discovery, runtime evidence, provenance, deterministic tests, and a clean handoff protocol so other Agents can compose it safely.

The same repository labels its public skills as demonstration and educational material. That is a useful warning for this project: a repository can be popular and useful while still not proving production correctness for every runtime. Our positioning should separate **template coverage** from **runtime-verified coverage**.

### VS Code Agent Skills documentation

Source: https://code.visualstudio.com/docs/agent-customization/agent-skills

VS Code describes Agent Skills as an open standard of folders containing instructions, scripts, and resources. It emphasizes portability across VS Code, Copilot CLI, and Copilot cloud agent; composition of multiple skills; and efficient loading of only relevant content. Skills are distinguished from static custom instructions because they can package specialized workflows and executable support material.

Implication for this project: the skill should expose a small, stable discovery surface and keep deep references and scripts lazy-loadable. Its interoperability contract should make clear what it consumes and produces, so another Agent can call Animation Skill Kit as one stage in a larger workflow without absorbing the entire repository or prompt.

### Agent Skills specification

Source: https://agentskills.io/specification

The specification requires a skill directory with at least `SKILL.md`; optional `scripts/`, `references/`, and `assets/` directories support executable code, documentation, and resources. `SKILL.md` requires YAML frontmatter with `name` and `description`; the specification also defines optional metadata such as license, compatibility, and allowed tools. It recommends progressive disclosure and provides `skills-ref validate ./my-skill` for format validation.

Implication for this project: the repo should retain a minimal, standards-compatible `SKILL.md` at the discoverable boundary, while moving deep animation framework knowledge into references and keeping executable checks in scripts. It should add a CI step using the reference validator, not rely only on custom tests.

### Model Context Protocol specification

Source: https://modelcontextprotocol.io/specification/2026-07-28

MCP separates server capabilities into **resources** (context and data), **prompts** (templated messages and workflows), and **tools** (functions the model can execute). The protocol also defines progress, cancellation, error reporting, and optional long-running task extensions. Its security guidance emphasizes user consent, data privacy, and treating tool execution as potentially arbitrary code execution.

Implication for this project: an Agent-compatible Animation Skill should expose the same conceptual separation even when used as a local repo. Project context, manifest, asset catalog and render evidence are resources; motion-spec scaffolds are prompts/workflows; analyze, rig, render, validate and quality-gate are tools. Destructive operations such as commit/push must be explicit and require user confirmation. This makes the Skill composable with MCP hosts without confusing documentation with executable authority.

### Google Agent2Agent interoperability

Source: https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/

Google's A2A announcement frames multi-agent collaboration around capability discovery through an Agent Card, task objects with a lifecycle, artifacts as task outputs, messages that carry context/replies/artifacts/user instructions, and content parts whose types support UI capability negotiation.

Implication for this project: Animation Skill Kit should publish an `agent-card.json` or equivalent capability manifest and represent every animation run as a task with explicit states such as `needs_context`, `planning`, `generating`, `rendering`, `review_required`, `blocked`, `validated`, and `ready_for_pr`. The output should be an artifact bundle with a manifest, motion spec, source asset, runtime snapshots, quality report and provenance—not an untyped folder of files.

### GitHub Awesome Copilot repository

Source: https://github.com/github/awesome-copilot

The repository aggregates community-contributed instructions, agents, skills, hooks, workflows and plugins. Its layout shows that a modern Agent ecosystem is broader than a single `SKILL.md`, and the repository warns users to inspect third-party agents and their documentation before installing them.

Implication for this project: being listed in a large skill directory is not the same as being trustworthy or production-ready. Animation Skill Kit should ship a trust boundary: pinned versions, changelog, license/attribution, dependency and permission inventory, signed or hashable release artifacts, compatibility matrix, deterministic smoke tests, and a clear distinction between local preview and destructive GitHub actions.

### Wiggle logo animation skill

Source: https://github.com/talknerdytome-labs/wiggle-claude-skill

This specialized Claude skill focuses on logo animation with Lottie and advertises a practical workflow: define motion philosophy, analyze logo structure, prepare assets, create Lottie JSON, validate/preview, and render final GIF/MP4. Its repository includes `SKILL.md`, references, helper scripts, requirements, examples, asset validation, preview frames, test render, loop validation, and output verification.

Implication for this project: the best community skills already go beyond prompt-only instructions by bundling executable helpers and preview checks. Animation Skill Kit should not compete by merely adding more presets. Its differentiation must be the project-bound layer around those helpers: context hash, framework selection, body/asset semantics, runtime evidence, Dev Lab review state, cross-Agent artifacts, and PR gates. We should also describe claims as capability levels unless they are independently tested in CI.
