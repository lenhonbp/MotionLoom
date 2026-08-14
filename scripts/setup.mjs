/**
 * MotionLoom onboarding wizard.
 * Style: Timeline Desk — one clear path, explicit states, no hidden side effects.
 * The wizard is intentionally Node-only at the entrypoint so npx can explain
 * missing Python before delegating to the canonical Python contracts.
 */
import { createRequire } from "node:module";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PACKAGE_JSON_PATH = join(PACKAGE_ROOT, "package.json");
const PACKAGE = JSON.parse(readFileSync(PACKAGE_JSON_PATH, "utf8"));
const VERSION = PACKAGE.version;
const PACKAGE_NAME = PACKAGE.name;
const MARKER_START = "<!-- MOTIONLOOM:START -->";
const MARKER_END = "<!-- MOTIONLOOM:END -->";

function usage() {
  console.log(`MotionLoom ${VERSION} — onboarding and project readiness

Usage:
  motionloom setup [options]       Install and bootstrap the current project
  motionloom status [options]      Read-only readiness report
  motionloom repair [options]      Re-apply safe missing setup pieces

Options:
  --project-root <path>            Host project (default: current directory)
  --package-manager <name>         auto, npm, pnpm or yarn (default: auto)
  --motionloom-root <path>         Use a local checkout instead of node_modules
  --dry-run                        Preview commands and file changes only
  --skip-install                   Do not install the npm package
  --skip-memory                    Do not analyze or initialize Project Memory
  --no-router                      Do not create or update AGENTS.md
  --yes                            Accept safe defaults without prompting
  --json                           Emit machine-readable JSON
  -h, --help                      Show this help

Safe defaults:
  - local devDependency, never a global install
  - idempotent AGENTS.md merge, never overwrite existing project guidance
  - Project Memory stays bound to the current project root
  - no commit, push, PR, approval or production promotion
`);
}

function parseArgs(argv) {
  const args = [...argv];
  let action = "setup";
  if (["setup", "status", "repair"].includes(args[0])) action = args.shift();
  const options = {
    action,
    projectRoot: process.cwd(),
    packageManager: "auto",
    motionloomRoot: null,
    dryRun: false,
    skipInstall: false,
    skipMemory: false,
    noRouter: false,
    yes: false,
    json: false,
  };

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "-h" || arg === "--help") {
      options.help = true;
      continue;
    }
    if (arg === "--dry-run") {
      options.dryRun = true;
      continue;
    }
    if (arg === "--skip-install") {
      options.skipInstall = true;
      continue;
    }
    if (arg === "--skip-memory") {
      options.skipMemory = true;
      continue;
    }
    if (arg === "--no-router") {
      options.noRouter = true;
      continue;
    }
    if (arg === "--yes") {
      options.yes = true;
      continue;
    }
    if (arg === "--json") {
      options.json = true;
      continue;
    }
    const next = args[index + 1];
    if (["--project-root", "--package-manager", "--motionloom-root"].includes(arg)) {
      if (!next || next.startsWith("--")) throw new Error(`${arg} requires a value`);
      index += 1;
      if (arg === "--project-root") options.projectRoot = next;
      if (arg === "--package-manager") options.packageManager = next;
      if (arg === "--motionloom-root") options.motionloomRoot = next;
      continue;
    }
    throw new Error(`unknown option: ${arg}`);
  }
  return options;
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function projectPackage(root) {
  return readJson(join(root, "package.json"));
}

function hasDependency(packageJson) {
  if (!packageJson) return false;
  return Boolean(
    packageJson.dependencies?.[PACKAGE_NAME] ||
      packageJson.devDependencies?.[PACKAGE_NAME] ||
      packageJson.optionalDependencies?.[PACKAGE_NAME],
  );
}

function detectPackageManager(root, requested) {
  if (requested !== "auto") return requested;
  if (existsSync(join(root, "pnpm-lock.yaml"))) return "pnpm";
  if (existsSync(join(root, "yarn.lock"))) return "yarn";
  if (existsSync(join(root, "package-lock.json"))) return "npm";
  const packageJson = projectPackage(root);
  const declared = String(packageJson?.packageManager || "").split("@")[0];
  return ["npm", "pnpm", "yarn"].includes(declared) ? declared : "npm";
}

function installCommand(manager) {
  if (manager === "pnpm") return ["pnpm", ["add", "--save-dev", `${PACKAGE_NAME}@${VERSION}`]];
  if (manager === "yarn") return ["yarn", ["add", "--dev", `${PACKAGE_NAME}@${VERSION}`]];
  return ["npm", ["install", "--save-dev", `${PACKAGE_NAME}@${VERSION}`]];
}

function run(program, args, cwd, capture = false) {
  const result = spawnSync(program, args, {
    cwd,
    encoding: "utf8",
    stdio: capture ? ["ignore", "pipe", "pipe"] : "inherit",
    env: process.env,
  });
  return {
    ok: !result.error && result.status === 0,
    status: result.status ?? 1,
    error: result.error?.message || null,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
  };
}

function pythonRuntime() {
  const candidates = process.platform === "win32" ? ["python", "python3"] : ["python3", "python"];
  for (const executable of candidates) {
    const result = run(executable, ["--version"], process.cwd(), true);
    if (!result.error && result.status === 0) {
      const version = `${result.stdout}\n${result.stderr}`.match(/Python\s+(\d+)\.(\d+)\.(\d+)/i);
      if (version) {
        const major = Number(version[1]);
        const minor = Number(version[2]);
        return { executable, version: `${major}.${minor}.${version[3]}`, supported: major > 3 || (major === 3 && minor >= 11) };
      }
    }
  }
  return { executable: null, version: null, supported: false };
}

function runtimeChecks() {
  const nodeMajor = Number(process.versions.node.split(".")[0]);
  const python = pythonRuntime();
  return {
    node: { version: process.versions.node, supported: nodeMajor >= 18 },
    python,
  };
}

function resolveMotionLoomRoot(projectRoot, explicitRoot) {
  if (explicitRoot) {
    const root = resolve(explicitRoot);
    return existsSync(join(root, "bin", "motionloom.mjs")) ? root : null;
  }
  const hostPackage = projectPackage(projectRoot);
  if (hostPackage?.name === PACKAGE_NAME && existsSync(join(projectRoot, "bin", "motionloom.mjs"))) {
    return projectRoot;
  }
  const local = join(projectRoot, "node_modules", PACKAGE_NAME);
  if (existsSync(join(local, "bin", "motionloom.mjs"))) return resolve(local);
  try {
    const require = createRequire(import.meta.url);
    const packageJson = require.resolve(`${PACKAGE_NAME}/package.json`, { paths: [projectRoot] });
    const root = dirname(packageJson);
    return existsSync(join(root, "bin", "motionloom.mjs")) ? root : null;
  } catch {
    return null;
  }
}

function localCli(motionloomRoot, args, projectRoot, capture = false) {
  return run(process.execPath, [join(motionloomRoot, "bin", "motionloom.mjs"), ...args], projectRoot, capture);
}

function routerBlock() {
  return `${MARKER_START}
## MotionLoom

When a task involves animation, motion, assets, runtime rendering or Dev Lab review:

- Read the installed MotionLoom package's canonical \`SKILL.md\` and \`agent-card.json\` first; do not copy them into the host project.
- Run \`npx --no-install motionloom status --json\` before planning animation work.
- Keep project context and \`.motionloom/project-memory.json\` bound to this project; never copy them from another project.
- After rendering, open the MotionLoom Dev Lab candidate for user review before any PR handoff.
- Treat runtime evidence, quality gates, attestation and heuristics as evidence only; they never imply user approval.
- Keep Git side effects local-only until the user explicitly confirms commit, push or PR.

${MARKER_END}`;
}

function routerState(projectRoot) {
  const path = join(projectRoot, "AGENTS.md");
  if (!existsSync(path)) return { status: "missing", path };
  const text = readFileSync(path, "utf8");
  if (text.includes(MARKER_START) && text.includes(MARKER_END)) return { status: "managed", path };
  if (/^##\s+MotionLoom\s*$/im.test(text)) return { status: "unmarked", path };
  return { status: "absent", path };
}

function ensureRouter(projectRoot, dryRun) {
  const state = routerState(projectRoot);
  const path = state.path;
  if (state.status === "managed") {
    const text = readFileSync(path, "utf8");
    const pattern = new RegExp(`${MARKER_START}[\\s\\S]*?${MARKER_END}`, "m");
    const updated = text.replace(pattern, routerBlock());
    if (updated !== text && !dryRun) writeFileSync(path, updated, "utf8");
    return { ...state, action: updated !== text ? (dryRun ? "would_update" : "updated") : "unchanged" };
  }
  if (state.status === "unmarked") return { ...state, action: "manual_review_required" };
  const prefix = existsSync(path) ? `\n\n${routerBlock()}\n` : `${routerBlock()}\n`;
  if (!dryRun) writeFileSync(path, prefix, { encoding: "utf8", flag: existsSync(path) ? "a" : "w" });
  return { ...state, action: dryRun ? "would_create" : "created" };
}

function checkMemory(motionloomRoot, projectRoot) {
  const result = localCli(motionloomRoot, ["memory", "validate", "--project-root", projectRoot, "--json"], projectRoot, true);
  let payload = null;
  try {
    payload = JSON.parse(result.stdout);
  } catch {
    payload = { raw: result.stdout.trim() };
  }
  return { ok: result.ok, payload, stderr: result.stderr.trim() };
}

function checkDiscovery(motionloomRoot) {
  const result = localCli(motionloomRoot, ["discovery", "check", "--root", motionloomRoot, "--json"], motionloomRoot, true);
  let payload = null;
  try {
    payload = JSON.parse(result.stdout);
  } catch {
    payload = { raw: result.stdout.trim() };
  }
  return { ok: result.ok, payload, stderr: result.stderr.trim() };
}

function statusReport(options) {
  const projectRoot = resolve(options.projectRoot);
  const packageJson = projectPackage(projectRoot);
  const motionloomRoot = resolveMotionLoomRoot(projectRoot, options.motionloomRoot);
  const runtime = runtimeChecks();
  const router = routerState(projectRoot);
  const context = existsSync(join(projectRoot, "project-context.json"));
  const memory = existsSync(join(projectRoot, ".motionloom", "project-memory.json"));
  const memoryCheck = motionloomRoot && memory ? checkMemory(motionloomRoot, projectRoot) : { ok: false, payload: null };
  const discovery = motionloomRoot ? checkDiscovery(motionloomRoot) : { ok: false, payload: null };
  const packageInstalled = Boolean(motionloomRoot && existsSync(join(motionloomRoot, "package.json")));
  const needsReview = Boolean(memory && !memoryCheck.ok);
  const ready = Boolean(
    packageInstalled &&
      runtime.node.supported &&
      runtime.python.supported &&
      discovery.ok &&
      ["managed"].includes(router.status) &&
      context &&
      memory &&
      memoryCheck.ok,
  );
  const status = ready ? "ready" : needsReview ? "needs_review" : "needs_setup";
  return {
    status,
    project_root: projectRoot,
    package: {
      declared: hasDependency(packageJson),
      installed: packageInstalled,
      version: motionloomRoot ? readJson(join(motionloomRoot, "package.json"))?.version || null : null,
      root: motionloomRoot,
    },
    runtime,
    router,
    context: { path: join(projectRoot, "project-context.json"), exists: context },
    memory: { path: join(projectRoot, ".motionloom", "project-memory.json"), exists: memory, validation: memoryCheck },
    discovery,
  };
}

function printStatus(report, json) {
  if (json) {
    console.log(JSON.stringify(report, null, 2));
    return;
  }
  const label = report.status === "ready" ? "READY" : report.status === "needs_review" ? "NEEDS REVIEW" : "NEEDS SETUP";
  console.log(`MotionLoom status: ${label}`);
  console.log(`Project: ${report.project_root}`);
  console.log(`Package: ${report.package.installed ? `installed ${report.package.version || "unknown"}` : "not installed locally"}`);
  console.log(`Runtime: Node ${report.runtime.node.version} ${report.runtime.node.supported ? "PASS" : "BLOCKED"}; Python ${report.runtime.python.version || "missing"} ${report.runtime.python.supported ? "PASS" : "BLOCKED"}`);
  console.log(`Agent router: ${report.router.status}`);
  console.log(`Project context: ${report.context.exists ? "present" : "missing"}`);
  console.log(`Project Memory: ${report.memory.exists ? (report.memory.validation.ok ? "valid" : "needs review") : "missing"}`);
  console.log(`Discovery: ${report.discovery.ok ? "PASS" : "BLOCKED"}`);
  if (report.status !== "ready") console.log("Next step: npx --yes motionloom setup");
}

function setup(options) {
  const projectRoot = resolve(options.projectRoot);
  const packageJson = projectPackage(projectRoot);
  const result = {
    command: options.action,
    status: "blocked",
    project_root: projectRoot,
    dry_run: options.dryRun,
    changed: [],
    planned: [],
    warnings: [],
    errors: [],
  };
  if (!packageJson) {
    result.errors.push("package.json is missing; run this command from the root of a Node project or pass --project-root");
    return result;
  }
  const runtime = runtimeChecks();
  if (!runtime.node.supported) result.errors.push(`Node.js ${runtime.node.version} is unsupported; MotionLoom requires Node.js 18+`);
  if (!runtime.python.supported) result.errors.push("Python 3.11+ was not found; install Python and ensure it is on PATH");
  if (result.errors.length) {
    result.runtime = runtime;
    return result;
  }

  const manager = detectPackageManager(projectRoot, options.packageManager);
  if (!["npm", "pnpm", "yarn"].includes(manager)) {
    result.errors.push(`unsupported package manager: ${manager}`);
    return result;
  }
  result.package_manager = manager;
  let motionloomRoot = resolveMotionLoomRoot(projectRoot, options.motionloomRoot);
  const needsInstall = !motionloomRoot || !hasDependency(packageJson);
  if (needsInstall && options.skipInstall) {
    result.errors.push("MotionLoom is not installed in this project; remove --skip-install or install the local devDependency first");
    return result;
  }
  if (needsInstall) {
    const [program, args] = installCommand(manager);
    result.planned.push({ step: "install", command: [program, ...args] });
    if (!options.dryRun) {
      const install = run(program, args, projectRoot, options.json);
      if (!install.ok) {
        const detail = install.stderr.trim() || install.stdout.trim();
        result.errors.push(detail || install.error || `package installation failed with exit code ${install.status}`);
        return result;
      }
      result.changed.push("installed local MotionLoom devDependency");
      motionloomRoot = resolveMotionLoomRoot(projectRoot, options.motionloomRoot);
    }
  } else {
    result.planned.push({ step: "install", action: "already_installed" });
  }
  if (!motionloomRoot && !options.dryRun) {
    result.errors.push("MotionLoom package root could not be resolved after installation");
    return result;
  }

  if (!options.noRouter) {
    const router = ensureRouter(projectRoot, options.dryRun);
    if (router.action === "manual_review_required") {
      result.warnings.push("AGENTS.md already contains an unmarked MotionLoom section; no automatic merge was attempted");
    } else if (router.action.startsWith("would_") || ["created", "updated"].includes(router.action)) {
      result[options.dryRun ? "planned" : "changed"].push({ step: "agent_router", action: router.action, path: relative(projectRoot, router.path) });
    }
  }

  if (!options.skipMemory && !options.dryRun && motionloomRoot) {
    const contextPath = join(projectRoot, "project-context.json");
    const memoryPath = join(projectRoot, ".motionloom", "project-memory.json");
    let bootstrap;
    if (!existsSync(contextPath)) {
      bootstrap = localCli(motionloomRoot, ["analyze", projectRoot, "--init-memory"], projectRoot, options.json);
      if (bootstrap.ok) result.changed.push("analyzed project and initialized Project Memory");
    } else if (!existsSync(memoryPath)) {
      bootstrap = localCli(motionloomRoot, ["memory", "init", "--project-root", projectRoot, "--context-path", contextPath, "--json"], projectRoot, options.json);
      if (bootstrap.ok) result.changed.push("initialized Project Memory from existing project context");
    }
    if (bootstrap && !bootstrap.ok) result.errors.push("Project Memory bootstrap failed; run `npx motionloom analyze . --init-memory` and inspect the reported project path");
  } else if (!options.skipMemory) {
    result.planned.push({ step: "project_memory", action: "analyze project and initialize .motionloom/project-memory.json" });
  }

  if (!options.dryRun && motionloomRoot) {
    const report = statusReport({ ...options, projectRoot, motionloomRoot });
    result.status = report.status;
    result.readiness = report;
    if (report.status === "needs_review") result.warnings.push("Project Memory exists but needs review; no destructive repair was attempted");
    if (report.status === "needs_setup") result.warnings.push("Setup completed partially; run `npx motionloom status --json` for the exact missing item");
  } else {
    result.status = "planned";
    result.planned.push({ step: "verification", action: "run discovery check, validate memory and print readiness" });
  }
  return result;
}

function printSetup(result, json) {
  if (json) {
    console.log(JSON.stringify(result, null, 2));
    return;
  }
  const label = result.status === "ready" ? "READY" : result.status === "planned" ? "DRY RUN" : result.status === "needs_review" ? "NEEDS REVIEW" : "BLOCKED";
  console.log(`MotionLoom setup: ${label}`);
  console.log(`Project: ${result.project_root}`);
  for (const item of result.changed) console.log(`  PASS  ${typeof item === "string" ? item : `${item.step}: ${item.action}`}`);
  for (const item of result.planned) console.log(`  PLAN  ${typeof item === "string" ? item : item.command ? item.command.join(" ") : `${item.step}: ${item.action || "planned"}`}`);
  for (const warning of result.warnings) console.log(`  WARN  ${warning}`);
  for (const error of result.errors) console.log(`  BLOCK ${error}`);
  if (result.status === "ready") {
    console.log("Next: ask your Agent to read the MotionLoom router, inspect project memory, then create a small animation candidate.");
    console.log("Review: open the Dev Lab candidate before any PR or Git side effect.");
  } else if (result.status === "planned") {
    console.log("Dry run only: rerun without --dry-run to apply the safe local setup.");
  } else {
    console.log("Next: run `npx --no-install motionloom status --json` and follow the reported missing or review-required item.");
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    usage();
    return 0;
  }
  if (options.action === "status") {
    const report = statusReport(options);
    printStatus(report, options.json);
    return report.status === "ready" ? 0 : report.status === "needs_review" ? 10 : 11;
  }
  const result = setup(options);
  printSetup(result, options.json);
  return ["ready", "planned"].includes(result.status) ? 0 : result.status === "needs_review" ? 10 : 11;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(`MotionLoom onboarding failed: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 2;
}
