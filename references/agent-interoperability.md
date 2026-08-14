# Agent interoperability reference

Read this reference when installing MotionLoom into a new Agent environment or when adding a new discovery surface.

## Contract hierarchy

1. `SKILL.md` is the canonical workflow and must stay below the skill context budget.
2. `agent-card.json` is the machine-readable capability and side-effect contract.
3. `agent-surfaces.json` is the discovery/install/compatibility contract.
4. `.agents/skills`, `.claude`, `.codex` and `AGENTS.md` are short routers that point to the canonical sources.
5. `docs/AGENT-INTEGRATION.md` is user-facing installation and troubleshooting documentation.

Do not put divergent workflow rules into an Agent-specific file. Add reusable domain detail to `references/` or `docs/`, then update the canonical Skill navigation.

## Discovery check output

The JSON result contains `status`, `source`, `surface_count`, `installation_count`, `errors` and `warnings`. `status=pass` means the local package has the expected files and contract values. It does not assert that the host project has been analyzed, that runtime dependencies are installed, that a candidate rendered correctly or that a user approved a change.

## One-command onboarding

For a host project that has not installed MotionLoom, prefer:

```bash
npx --yes motionloom setup --project-root <project-path>
npx --no-install motionloom status --project-root <project-path> --json
```

`setup` is idempotent. It detects the project root and package manager, installs a local development dependency when needed, merges only the managed router block in `AGENTS.md`, runs discovery and bootstraps project context plus `.motionloom/project-memory.json`. Use `--dry-run --json` to preview and `repair --yes --json` to restore missing managed pieces. A setup result of `blocked` is actionable failure, not permission to continue with guessed context. Setup never commits, pushes, opens a PR or infers approval.

## Adding a new Agent surface

Add one manifest entry with a safe relative path, a supported agent identifier, `canonical: SKILL.md` and either `load_mode: alias` or `load_mode: router`. Create a short file at that path. Add or update the installation/discovery test and run `motionloom discovery check --root . --json`, `python3 scripts/docs-audit.py` and the full test suite. Never silently overwrite an existing surface with a copied version of `SKILL.md`.

## Source and version binding

When a user reports a discovery issue, capture the package version, source kind, resolved path, Git remote/commit where available and the discovery JSON. Treat a version mismatch as a structural problem, not as a runtime animation failure. Do not use network access in the check command; registry/Git availability belongs to the installation step.

## Approval boundary

Discovery is deliberately orthogonal to approval. The discovery command can only tell an Agent how to load MotionLoom. It cannot transition an animation task to `ready_for_pr` or `confirmed`, and it cannot change `approval` from `false` to `true`.
