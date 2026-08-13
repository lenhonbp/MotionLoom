# Publish MotionLoom to npm from your workstation

This guide publishes the prepared `motionloom@2.0.0` package from your own computer. The npm password, authenticator code and access token must stay on your computer; never paste them into chat, GitHub issues or repository files.

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

The latest commit must be the npm packaging release announced in the task. Do not publish from an older checkout or from a different fork.

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

The dry-run should report `motionloom@2.0.0`, public access, approximately 260 kB compressed size and 111 files. The prepack hook removes generated Python bytecode before packaging. Do not publish if the dry-run shows private keys, `.env` files, `artifacts/`, `dev-lab/` or `__pycache__/` entries.

## 5. Publish the package

When the dry-run is correct and `npm whoami` shows the intended account, publish the unscoped package publicly:

```bash
npm publish --access public
```

The version `2.0.0` becomes immutable on npm after a successful publish. If npm reports that the version already exists, stop and verify the registry instead of trying to overwrite it.

## 6. Verify the registry publication

Run the following commands and confirm that they return `2.0.0` and a tarball URL:

```bash
npm view motionloom version --registry=https://registry.npmjs.org/
npm view motionloom@2.0.0 name version license dist.tarball dist.shasum --json \
  --registry=https://registry.npmjs.org/
```

Then test installation in a clean temporary directory:

```bash
TMP_DIR="$(mktemp -d)"
cd "$TMP_DIR"
npm init --yes
npm install motionloom@2.0.0
motionloom --help
motionloom doctor
```

The CLI should print the MotionLoom command surface. `motionloom doctor` should validate the installed package contract. The Python runtime remains a prerequisite for commands that delegate to Python scripts.

## Troubleshooting

If `npm whoami` returns `ENEEDAUTH`, repeat `npm login` on the same computer and registry. If publishing returns `E403`, check package ownership, organization publish permission and 2FA policy; do not disable security controls. If the package name is already claimed, stop and choose a scoped name such as `@your-npm-user/motionloom`, then update `name` and `publishConfig` before publishing a new package identity. Never place an npm token in `package.json`, `.npmrc` committed to Git, shell history or chat.
