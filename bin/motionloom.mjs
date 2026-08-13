#!/usr/bin/env node
/**
 * MotionLoom npm entrypoint.
 * Style: Timeline Desk — terse command routing, explicit evidence verbs and
 * no hidden approval side effects. The CLI delegates to the shipped Python
 * contracts so npm installation and repository execution use one surface.
 */
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PYTHON = process.env.MOTIONLOOM_PYTHON || (process.platform === "win32" ? "python" : "python3");

const PYTHON_COMMANDS = {
  analyze: "scripts/analyze.sh",
  attestation: "scripts/attestation.py",
  "verify-attestation": "scripts/attestation-verifier.py",
  doctor: "scripts/skill-doctor.py",
  intelligence: "scripts/intelligence.py",
  "eval-intelligence": "scripts/eval-intelligence.py",
  "evidence-verify": "scripts/evidence-verifier.py",
  "quality-gate": "scripts/quality-gate.py",
  "report-contract": "scripts/report-contract.py",
  report: "scripts/report.py",
  "review-hook": "scripts/review-hook.py",
  "validate-lottie": "scripts/validate-lottie.py",
  manifest: "scripts/manifest.py",
};

function printHelp() {
  console.log(`MotionLoom 2.0.0 — project-aware animation production and evidence contracts

Usage:
  motionloom <command> [args...]

Commands:
  doctor                 Validate the installed Skill package
  analyze                Run project analysis (delegates to scripts/analyze.sh)
  intelligence           Build or validate Intelligence Core artifacts
  attestation            Build/validate canonical signed-attestation artifacts
  verify-attestation     Verify an attestation against a trust policy
  evidence-verify        Verify runtime evidence externally
  quality-gate           Run the strict scene acceptance gate
  report-contract        Validate task bundle completeness
  review-hook            Prepare or validate browser review handoff
  report                 Read or update task review reports
  validate-lottie        Validate a Lottie animation
  manifest               Build or validate a production manifest
  eval-intelligence      Run adversarial Intelligence Core evaluation

The CLI never grants approval or opens a pull request by itself. User review
and explicit repository side-effect confirmation remain separate gates.
`);
}

const [command, ...args] = process.argv.slice(2);
if (!command || command === "help" || command === "--help" || command === "-h") {
  printHelp();
  process.exit(0);
}

const script = PYTHON_COMMANDS[command];
if (!script) {
  console.error(`Unknown MotionLoom command: ${command}`);
  printHelp();
  process.exit(2);
}

const executable = script.endsWith(".sh") ? "bash" : PYTHON;
const result = spawnSync(executable, [resolve(ROOT, script), ...args], {
  cwd: ROOT,
  stdio: "inherit",
  env: process.env,
});

if (result.error) {
  console.error(`MotionLoom could not start ${executable}: ${result.error.message}`);
  process.exit(2);
}
process.exit(result.status ?? 1);
