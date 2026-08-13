# Security Policy

## Supported versions

| Version | Security fixes |
|---|---|
| `2.1.x` | Supported |
| `2.0.x` | Best effort while upgrading |
| `<2.0.0` | Not supported |

## Reporting a vulnerability

Please do not open a public issue for an exploitable vulnerability, credential exposure, path escape, evidence-bypass bug or supply-chain concern. Use [GitHub Private Vulnerability Reporting](https://github.com/lenhonbp/MotionLoom/security/advisories/new) when available. Include the affected version/commit, operating system, minimal reproduction, impact and a proposed mitigation if known. Redact project names, tokens, private assets, private keys and customer data.

If private reporting is unavailable, open a minimal issue titled **Security contact requested** without exploit details and ask the maintainer to enable a private channel. The maintainer will acknowledge a valid report, triage severity, coordinate a fix and publish a release note when disclosure is safe.

## Security boundaries

MotionLoom can read and write files in the host project, invoke runtimes and prepare Git operations. The npm CLI does not silently push, open a PR or turn evidence into approval. Treat project context, artifact bundles, trust policies, private keys and browser sessions as sensitive. Keep managed signing keys outside the repository and never use CI fixture keys as production trust anchors.

Path guards, task identity, source/manifest hashes, evidence freshness, signer policy and approval invariants are security-relevant contracts. Report any bypass that allows cross-project memory, cross-task evidence, stale runtime output or unreviewed Git side effects.

See the [signed attestation reference](references/signed-attestation.md), [browser review contract](references/browser-review-contract.md) and [2.1.0 release note](docs/releases/2.1.0.md) for the current threat model and limitations.

## CI/CD controls

GitHub Actions workflows default to read-only repository permissions. The publication workflow is manual-only, uses the protected `npm-release` environment, requests OIDC only for the release job, and keeps npm credentials in environment secrets. Dependency updates are proposed by Dependabot as pull requests rather than applied directly to `main`.
