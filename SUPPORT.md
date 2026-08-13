# Support

MotionLoom is a public Agent Skill and npm package. Start with the [README](README.md), [SKILL.md](SKILL.md), [production checklist](docs/CHECKLIST.md), [framework selection guide](docs/FRAMEWORK-SELECTION.md) and [runtime capability reference](references/runtime-capability.md).

## Choose the right channel

| Situation | Use |
|---|---|
| A reproducible defect in code, schema, CLI or runtime adapter | [Bug report](https://github.com/lenhonbp/MotionLoom/issues/new?template=bug_report.yml) |
| A proposed capability or workflow improvement | [Feature request](https://github.com/lenhonbp/MotionLoom/issues/new?template=feature_request.yml) |
| A security or privacy concern | [SECURITY.md](SECURITY.md), never a public issue with exploit details |
| A documentation correction | Open a small pull request or use a documentation issue |
| A usage question | Search the README/docs first, then open an issue with the exact command and environment if no answer exists |

## Troubleshooting order

Run `motionloom doctor --json`, confirm Node/Python versions, inspect the JSON exit code, check that the task bundle and project context belong to the same project, and rerun the smallest relevant contract test. A `needs_context`, `stale`, `invalid` or `blocked` state is an actionable result, not an invitation to bypass the gate.

When asking for help, include sanitized command output, the operating system, package version, runtime/framework, task state and a minimal fixture. Do not upload `.motionloom/project-memory.json`, private project context, private assets, credentials, signing keys or browser session data unless they are synthetic and safe to share.

## Maintainer response

The project is maintained on a best-effort basis. A response may request a reproducible fixture or a contract-level test before implementation. Feature requests are evaluated against the [roadmap](ROADMAP.md), user-control principles and the project's ability to produce verifiable runtime evidence.
