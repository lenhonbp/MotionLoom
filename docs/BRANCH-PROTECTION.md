# MotionLoom main branch protection recommendation

## Current observed state

As of the repository audit, `main` is not protected and the repository exposes no active rulesets. This document records the exact recommended configuration; it does not mutate GitHub settings automatically.

## Recommended configuration

Open **Settings → Rules → Rulesets → New branch ruleset** in `lenhonbp/MotionLoom` and create a ruleset named `protect-main-motionloom` with enforcement set to **Active** and target branch `main`.

| Setting | Recommended value |
|---|---|
| Target branches | Include `main`; do not target feature branches by default. |
| Restrict deletions | Enabled. |
| Require linear history | Enabled if the repository policy accepts squash/rebase-only integration; otherwise leave disabled and require the repository's chosen merge strategy consistently. |
| Require a pull request before merging | Enabled. Require at least 1 approving review; enable dismissal of stale approvals after new commits and require review from Code Owners when a CODEOWNERS file is adopted. |
| Block force pushes | Enabled. |
| Required status checks | Require the exact successful checks listed below, with no test-only bypass. |
| Conversation resolution | Enabled before merge. |
| Bypass actors | Keep to repository administrators/maintainers only, document emergency use, and do not use bypass as the normal merge path. |

The required status checks should include the following exposed check names:

| Required check | Why it is required |
|---|---|
| `MotionLoom Quality / quality` | Full regression, intelligence, runtime, attestation and quality gate. |
| `Security Analysis / CodeQL (javascript)` | JavaScript security analysis. |
| `Security Analysis / CodeQL (python)` | Python security analysis. |
| `Security Analysis / Dependency review` | Dependency change review. |
| `Documentation and Package Hygiene / Docs, metadata and npm package` | Docs, metadata and package-surface checks. |
| `Dev Lab Build / Run browser review harness` | Browser review harness integrity. |
| `Frame Generation Lock / Lock, compose and preflight` | Frame-lock and action-aware preflight contract. |
| `Published Consumer Frame Dogfood / Published package → 12 frames → Dev Lab` | Installed/published consumer integration proof. |
| `MotionLoom Apple / Swift packages and iOS Simulator compatibility` | Apple package and simulator compatibility. |

The exact check labels can change when workflow job names change. After creating the ruleset, open a test pull request and select the checks as GitHub exposes them for the current default branch; do not guess a check name that is not present in the branch's status context.

## Maintenance policy

Do not require a check that is intentionally skipped for a given path unless GitHub's ruleset semantics and workflow path filters are verified to keep the branch mergeable. If a required hosted environment is unavailable, fix or replace the check rather than bypassing the protection. The repository owner should review administrator bypass access periodically and record any emergency merge in the PR.

## Manual verification

After saving the ruleset, confirm that a direct push to `main` is rejected, a pull request without all required checks cannot merge, stale approvals are dismissed after a new commit, force-push/delete operations are blocked, and an administrator bypass is an explicit exceptional path rather than an implicit permission.
