# Agent interoperability and installation contract

MotionLoom is distributed as one Skill with several **discovery surfaces**, not as several independent Skills. The root `SKILL.md` is canonical. `agent-card.json` is the capability contract. `agent-surfaces.json` records the supported surfaces, installation sources and compatibility policy.

## Install sources

| Source | Typical command | Verification | Provenance to retain |
|---|---|---|---|
| npm registry | `npm install --save-dev motionloom` | `motionloom discovery check --root . --json` | lockfile and resolved package version |
| Git checkout | `git clone https://github.com/lenhonbp/MotionLoom.git` | `node bin/motionloom.mjs discovery check --root . --json` | remote URL and commit SHA |
| Local source | invoke `<checkout>/bin/motionloom.mjs` | `python3 scripts/discovery.py check --root . --json` | source path and local commit if present |

The check is offline and read-only. Installation, source identity and capability compatibility are separate from network authentication. A passing check means that the package is structurally discoverable; it does not mean that a scene is runtime-verified or approved.

## Agent surfaces

| Surface | Path | Role |
|---|---|---|
| Agent Skills | `.agents/skills/motionloom/SKILL.md` | Portable alias for Agent Skills discovery |
| Claude Code | `.claude/skills/motionloom.md` | Claude-specific router to the canonical Skill |
| Codex | `.codex/skills/motionloom.md` | Codex-specific router to the canonical Skill |
| Repository router | `AGENTS.md` | Short first-load instructions for repository-aware Agents |

These files deliberately remain short. They must not become a second instruction source. Every surface points back to `SKILL.md`; drift is a contract failure and is checked by `motionloom discovery check` and the documentation audit.

## Agent compatibility matrix

| Agent | Discovery surface | Expected first action | Review boundary |
|---|---|---|---|
| Codex | `.codex/skills/motionloom.md`, `.agents/skills/motionloom/SKILL.md` | Run discovery check, load root Skill and Agent Card | No commit/push/PR without explicit user confirmation |
| Claude Code | `.claude/skills/motionloom.md`, `.agents/skills/motionloom/SKILL.md` | Run discovery check, load root Skill and Agent Card | Same review-first gate |
| Cursor | `.agents/skills/motionloom/SKILL.md`, `AGENTS.md` | Load canonical Skill through repository rules | Same review-first gate |
| OpenCode | `.agents/skills/motionloom/SKILL.md`, `AGENTS.md` | Load canonical Skill and run discovery check | Same review-first gate |

Support here means that the repository exposes a deterministic discovery contract. It does not claim that every Agent version automatically loads every convention. The Agent must report when a surface is unavailable or when it cannot open the internal Dev Lab.

## Required first-run sequence

Run `motionloom discovery check --root <checkout> --json`, inspect `source`, then run project analysis with `motionloom analyze <project> --init-memory`. Load the project context and durable Project Memory before planning. After selecting or generating an asset, create `asset-provenance.json` and run the runtime-mode check before ingest. An AI-generated pilot may proceed to the real runtime and Dev Lab, but it must remain non-production-eligible. After rendering, prepare a task-bound browser candidate and suggest or trigger the internal Dev Lab. Capture user feedback separately from runtime evidence. A valid signature, quality gate or screenshot is not a user approval.

## AI-first asset workflow

The Agent must distinguish these transitions rather than collapsing them into one `approved` flag:

| Transition | Allowed actor | Required evidence |
|---|---|---|
| `blocked` → `runtime_ready` | Agent or runtime validator | Safe paths, valid schema, license/source, file hashes and real runtime evidence |
| `runtime_ready` → `production_eligible` | Contract gate plus human review where the authority tier requires it | Full quality/visual/runtime gate and valid authority record |
| `production_eligible` → `production_approved` | User or designated human reviewer only | Explicit review decision persisted outside the Agent's self-assertion |

Never rewrite `ai_generated` as `artist_authored`, never infer human review from a signature, and never set `production_approved` from `quality-gate`. Use `motionloom asset-provenance report` to show the boundary in a handoff.

## Portability policy

The npm entrypoint is the public cross-platform surface. Ubuntu, macOS and Windows must use Node argument arrays, Python `pathlib`, UTF-8 JSON and no required Bash, POSIX `/tmp`, system `zip` or system `unzip`. Bash wrappers may remain convenience scripts for repository contributors, but the discovery and validation commands must work through Node/Python on all supported operating systems.

## Troubleshooting

If discovery fails, do not continue as if the Skill were loaded. Inspect the JSON `errors`, verify that the checkout has not mixed files from different versions, and rerun from the intended root. If the package version and `agent-surfaces.json` disagree, use the same source checkout or reinstall the package. If a runtime dependency is missing, report it as a blocker; do not replace runtime evidence with a static placeholder.
