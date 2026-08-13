# Contributing to MotionLoom

Thank you for helping make animation workflows more reliable for coding agents. Contributions are welcome in code, schemas, tests, runtime adapters, documentation, fixtures and reproducible bug reports. Please read the [Code of Conduct](CODE_OF_CONDUCT.md) and [Security Policy](SECURITY.md) before contributing.

## Before opening an issue or pull request

Search existing issues and documentation first. For a bug, include the operating system, Node/Python versions, exact command, minimal fixture or artifact bundle, expected behavior and observed output. Never attach private project context, credentials, private source assets or trust-policy private keys.

For a feature, explain which Agent failure mode it addresses, which contract or schema changes, what evidence would demonstrate correctness, and how the change preserves explicit user approval. A template without a runtime or validation path is not sufficient for a production capability.

## Local setup

```bash
git clone https://github.com/lenhonbp/MotionLoom.git
cd MotionLoom
npm install
python3 -m pip install --requirement requirements.txt
python3 scripts/skill-doctor.py --json
```

Node.js 18+ and Python 3.11+ are required. On Windows, use `python` if `python3` is not available or set `MOTIONLOOM_PYTHON` for the npm wrapper. Runtime adapter tests may require the Playwright browser installation described by the CI workflow.

## Validation commands

Run the smallest relevant checks while iterating, then run the complete suite before opening a pull request:

```bash
python3 -m py_compile scripts/*.py tests/scripts/*.py
python3 tests/scripts/test_project_memory.py
python3 tests/scripts/run_tests.py
python3 scripts/eval-intelligence.py
python3 scripts/skill-doctor.py --json
npm run runtime:test
npm publish --dry-run --access public
```

For changes to a scene or evidence contract, also run the appropriate report contract, browser-review validation, quality gate and `npm run audit:deep`. Keep generated local runtime state and temporary project memory out of the commit.

## Pull request expectations

Use a focused branch and a conventional commit-style title such as `feat(memory): ...`, `fix(runtime): ...` or `docs: ...`. A pull request should explain the user-visible change, list changed contracts, identify platform coverage, link tests and state limitations or remaining warnings. Schema changes must include fixtures and backward/forward compatibility notes where relevant.

Do not claim a runtime is verified unless real adapter evidence exists. Do not convert a heuristic, benchmark, valid signature or successful build into an approval statement. Do not change `approval` to `true` in fixtures or bypass the user-review gate to make a test pass.

## Review and merge policy

CI must pass before merge. Changes that affect `SKILL.md`, `agent-card.json`, schemas, quality gates, evidence verification, attestations, runtime adapters or Git side effects require explicit contract review. Maintainers may request a focused adversarial fixture when a change can affect stale evidence, cross-task contamination, path safety or approval invariants.

The repository's PR template is a checklist, not a substitute for evidence. Maintainers merge only after the behavior, documentation and trust boundary are clear.

## Release process

1. Update `CHANGELOG.md` and a dedicated `docs/releases/<version>.md` note.
2. Update `package.json`, `SKILL.md`, `agent-card.json` and relevant schema/reference versions.
3. Run the full validation suite and `npm publish --dry-run --access public`.
4. Create a local commit and obtain explicit maintainer confirmation before pushing.
5. Publish from the authenticated maintainer workstation, then verify the npm version and GitHub release state.

See [ROADMAP.md](ROADMAP.md) for future work and [SUPPORT.md](SUPPORT.md) for help with setup or usage.
