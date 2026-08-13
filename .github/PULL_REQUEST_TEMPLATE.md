## Summary

Describe the user or Agent workflow this pull request improves.

## Contract impact

- [ ] No schema, evidence, runtime or Git side-effect contract changes.
- [ ] Schema or artifact contract changes are documented and covered by fixtures.
- [ ] Runtime capability claims remain accurate (`verified` vs `scaffold_only`).
- [ ] Approval remains a user decision; no heuristic, signature or benchmark was promoted to approval.

## Validation

- [ ] `python3 scripts/skill-doctor.py --json`
- [ ] `python3 tests/scripts/run_tests.py`
- [ ] Relevant runtime adapter, report contract and quality gate checks
- [ ] Cross-platform impact considered for Ubuntu, macOS and Windows
- [ ] `npm publish --dry-run --access public` when package contents or metadata changed

## Evidence and limitations

List commands, fixtures, artifact paths, screenshots/review evidence and any remaining warnings. Never attach private project context, credentials, private signing keys or private source assets.
