# Publish MotionLoom to npm from your workstation

This guide publishes the prepared `motionloom@2.5.1` package from your own computer. The npm password, authenticator code and access token must stay on your computer; never paste them into chat, GitHub issues or repository files.

## 1. Install prerequisites

Use Node.js 18 or newer, npm 10 or newer, Git and Python 3.11 or newer. Verify them before cloning:

```bash
node --version
npm --version
git --version
python3 --version
```

## 2. Clone the prepared GitHub release

After the npm packaging commit has been pushed to `main`, clone the repository and enter it:

```bash
git clone https://github.com/lenhonbp/MotionLoom.git
cd MotionLoom
git checkout main
git pull --ff-only origin main
git log -1 --oneline
```

The latest commit must be the npm packaging release announced in the task. Do not publish from an older checkout or from a different fork. This repository declares `pnpm` as its package manager and intentionally does not ship a `package-lock.json`; do **not** run `npm ci` in the repository. The release verifier and package dry-run do not require a dependency install. If a full workspace install is needed, use the declared package manager with `pnpm install --frozen-lockfile`.

## 3. Authenticate npm locally

Start the official npm login flow on your computer:

```bash
npm login --registry=https://registry.npmjs.org/
npm whoami
```

Complete the browser login and 2FA challenge if npm requests them. The second command must print your npm username. If the account uses an organization, confirm that the account has publish permission for the unscoped package name `motionloom`.

## 4. Inspect the package before publishing

Run the package checks from the cloned repository:

```bash
node -e 'JSON.parse(require("fs").readFileSync("package.json", "utf8")); console.log("package.json: valid")'
npm pack --dry-run --json --ignore-scripts
npm publish --dry-run --access public
```

The dry-run should report `motionloom@2.5.1`, public access, and the current package file list. Do not hard-code a historical file count: inspect the JSON output and compare it with the checked-in package allowlist. The prepack hook removes generated Python bytecode before packaging. Do not publish if the dry-run shows private keys, `.env` files, `artifacts/`, `dev-lab/` or `__pycache__/` entries.

## 5. Publish the package

When the dry-run is correct and `npm whoami` shows the intended account, publish the unscoped package publicly:

```bash
npm publish --access public
```

Do not add `--provenance` unless the local npm client and its CI/provider integration explicitly support automatic npm provenance. Some workstation setups report `Automatic provenance generation not supported for provider: null`; in that case the package itself is still valid, and the supported fallback for this release is the command above without `--provenance`. Never retry by changing the version or by bypassing the package verification steps.

The version `2.5.1` becomes immutable on npm after a successful publish. If npm reports that the version already exists, stop and verify the registry instead of trying to overwrite it.

## 6. Verify the registry publication

Run the following commands and confirm that they return `2.5.1` and a tarball URL:

```bash
npm view motionloom version --registry=https://registry.npmjs.org/
npm view motionloom@2.5.1 name version license dist.tarball dist.shasum --json \
  --registry=https://registry.npmjs.org/
```

Then test installation in a clean temporary directory:

```bash
TMP_DIR="$(mktemp -d)"
cd "$TMP_DIR"
npm init --yes
npm install motionloom@2.5.1
motionloom --help
motionloom doctor
```

The CLI should print the MotionLoom command surface. `motionloom doctor` should validate the installed package contract. The Python runtime remains a prerequisite for commands that delegate to Python scripts.

## Troubleshooting

If `npm whoami` returns `ENEEDAUTH`, repeat `npm login` on the same computer and registry. If `npm ci` reports that no `package-lock.json` exists, skip it and use the release verifier directly; this repository is pnpm-managed. If `npm publish --provenance` reports that the provider is `null` or unsupported, retry `npm publish --access public` without that flag. If publishing returns `E404` on the `PUT` request, do not change the package name or version yet. First run these read-only checks against the public registry:

```bash
npm config get registry
npm whoami --registry=https://registry.npmjs.org/
npm view motionloom name version maintainers --json --registry=https://registry.npmjs.org/
npm access list collaborators motionloom --json --registry=https://registry.npmjs.org/
```

The `npm whoami` result must be the intended publisher, and the collaborators result must show that account with publish-capable access. A mismatch usually means the workstation is authenticated as a different npm user, is using a stale token, or the package is owned by another account or team. Re-authenticate only on the workstation with `npm logout` followed by `npm login --registry=https://registry.npmjs.org/`; never paste the token into chat. If the account is correct but publish access is absent, the package owner must grant the account read-write access or publish from the owner account. If publishing returns `E403`, check package ownership, organization publish permission and 2FA policy; do not disable security controls. If the package name is already claimed by an account you do not control, stop and do not rename this release without an explicit release decision. Never place an npm token in `package.json`, `.npmrc` committed to Git, shell history or chat.
