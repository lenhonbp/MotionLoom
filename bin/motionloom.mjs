#!/usr/bin/env node
/**
 * MotionLoom npm entrypoint.
 * Style: Timeline Desk — terse command routing, explicit evidence verbs and
 * no hidden approval side effects. The CLI delegates to shipped Python/Node
 * contracts so npm installation and repository execution use one surface.
 */
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PACKAGE = JSON.parse(readFileSync(resolve(ROOT, "package.json"), "utf8"));
const VERSION = PACKAGE.version || "unknown";
const PYTHON = process.env.MOTIONLOOM_PYTHON || (process.platform === "win32" ? "python" : "python3");

const PYTHON_COMMANDS = {
  analyze: "scripts/analyze.py",
  memory: "scripts/project-memory.py",
  attestation: "scripts/attestation.py",
  "attestation-keygen": "scripts/attestation-keygen.py",
  "verify-attestation": "scripts/attestation-verifier.py",
  doctor: "scripts/skill-doctor.py",
  intelligence: "scripts/intelligence.py",
  "eval-intelligence": "scripts/eval-intelligence.py",
  "evidence-verify": "scripts/evidence-verifier.py",
  "quality-gate": "scripts/quality-gate.py",
  "report-contract": "scripts/report-contract.py",
  report: "scripts/report.py",
  "review-hook": "scripts/review-hook.py",
  devlab: "scripts/devlab.py",
  "runtime-telemetry": "scripts/capture-runtime-telemetry.py",
  render: "scripts/render.py",
  pr: "scripts/pr.py",
  "validate-lottie": "scripts/validate-lottie.py",
  manifest: "scripts/manifest.py",
  discovery: "scripts/discovery.py",
  "visual-truth": "scripts/visual-truth.py",
  "remediation-learning": "scripts/remediation-learning.py",
  "asset-provenance": "scripts/asset-provenance.py",
  "asset-consistency": "scripts/asset-consistency.py",
  "frame-generation-lock": "scripts/frame-generation-lock.py",
  "frame-set-preflight": "scripts/frame-set-preflight.py",
  "action-separation": "scripts/action-separation.py",
  "asset-generation-plan": "scripts/asset-generation-plan.py",
  "asset-adapt": "scripts/asset-adapt.mjs",
  "artifact-intake": "scripts/artifact-intake.py",
  "runtime-candidate": "scripts/runtime-candidate.py",
  "rig-compatibility": "scripts/rig-compatibility.py",
  "rive-package-gate": "scripts/rive-package-gate.py",
  "pilot-build": "scripts/build-ai-pilot.py",
  "alpha-isolate": "scripts/isolate-alpha-background.py",
};

const NODE_COMMANDS = {
  init: "scripts/setup.mjs",
  setup: "scripts/setup.mjs",
  status: "scripts/setup.mjs",
  repair: "scripts/setup.mjs",
};

const COMMAND_ALIASES = {
  capability: { script: "scripts/intelligence.py", args: ["capabilities"] },
};

function printHelp() {
  console.log(`MotionLoom ${VERSION} — project-aware animation production and evidence contracts

Usage:
  motionloom <command> [args...]

Start here:
  init                   One safe project setup; no animation gate runs
  status                 Short read-only readiness report
  doctor                 Validate the installed Skill package
  doctor --runtime       Also verify the Playwright Chromium executable

Use when an animation task needs it:
  analyze                Run project analysis and refresh Project Memory
  memory                 Initialize, inspect, refresh, recover or validate memory
  intelligence           Build or validate Intelligence Core artifacts
  capability             Export or select evidence-bound runtime capabilities
  attestation            Build/validate canonical signed-attestation artifacts
  verify-attestation     Verify an attestation against a trust policy
  evidence-verify        Verify runtime evidence externally
  quality-gate           Run the strict scene acceptance gate
  report-contract        Validate task bundle completeness
  review-hook            Prepare or validate browser review handoff
  devlab                 Prepare or serve the internal Dev Lab cross-platform
  runtime-telemetry      Capture and externally verify runtime telemetry
  report                 Read or update task review reports
  validate-lottie        Validate a Lottie animation
  manifest               Build or validate a production manifest
  eval-intelligence      Run adversarial Intelligence Core evaluation
  discovery              Check Agent surfaces, source identity and install matrix
  visual-truth           Build or validate provenance-bound visual comparisons
  remediation-learning   Record or summarize user-confirmed remediation and benchmark history
  asset-provenance       Validate, classify or report asset origin and production readiness
  asset-consistency      Validate frame geometry, atlas contamination and layered-map contracts
  frame-generation-lock  Validate or compose locked per-frame generation instructions
  frame-set-preflight    Fail closed on shared canvases, scale drift, frame contamination and action manifest binding
  action-separation      Validate action-scoped frame manifests and independent competitor-action evidence
  asset-generation-plan  Recommend providers and explicit canvas/frame adaptation without invoking APIs
  asset-adapt             Apply deterministic transparent padding/integer upscale with a hash-bound report
  artifact-intake        Bind generation controls, provenance, adapter metadata and exported bytes
  runtime-candidate      Bind intake exports to consistency contracts before runtime testing
  rig-compatibility      Validate rig bones, sockets, actions, events and runtime adapter evidence
  rive-package-gate      Verify a real .riv package, runtime proof and provenance before testing
  pilot-build            Build a review-only hash-bound AI scout pilot from true-alpha PNG sources
  alpha-isolate          Isolate an edge-connected flat background; block residual edge contamination
  setup                  Alias for init (kept for compatibility)
  repair                 Re-apply safe missing setup pieces

Cross-platform examples:
  motionloom analyze . --init-memory
  motionloom memory recover --project-root .
  motionloom memory refresh --project-root . --json
  motionloom memory record-decision --project-root . --id ui-easing \\
    --status accepted --summary "Use ease-out for UI entry" --user-confirmed
  motionloom discovery check --root . --json
  motionloom doctor --runtime --json
  motionloom discovery install-matrix --root . --json
  motionloom capability card --format json
  motionloom visual-truth validate --root . --input src/output/<scene>/visual-truth.json
  motionloom remediation-learning summary --history artifacts/remediation-history.jsonl --json
  motionloom asset-provenance check --input <asset-provenance.json> --root <scene-dir> --mode runtime --json
  motionloom asset-consistency validate --kind frame-geometry --input <frame-geometry.json> --root <scene-dir> --json
  motionloom frame-generation-lock compose --input <frame-generation-lock.json> --root <asset-root> --frame-id walk.00 --json
  motionloom frame-set-preflight --input <frame-geometry.json> --root <asset-root> --action-manifest <action-sequence.json> --json
  motionloom action-separation validate --input <action-sequence.json> --root <asset-root> --json
  motionloom asset-generation-plan plan --request <asset-generation-request.json> --project-root . --json
  motionloom asset-adapt pad --input source.png --output target.png --width 256 --height 448 --anchor footline --report adaptation.json --json
  motionloom artifact-intake intake --root <asset-dir> --registry artifact-adapter-registry.json \\
    --receipt <generation-receipt.json> --controls <control-track.json> --export-manifest <export-manifest.json> --json
  motionloom alpha-isolate <opaque.png> <isolated.png> --report <alpha-report.json>
  motionloom rive-package-gate validate --root <package-dir> --registry rig-adapter-registry.json \\
    --input <rive-package-manifest.json> --strict --json

The CLI never grants approval or opens a pull request by itself. User review
and explicit repository side-effect confirmation remain separate gates.
`);
}

const [command, ...args] = process.argv.slice(2);
if (!command || command === "help" || command === "--help" || command === "-h") {
  printHelp();
  process.exit(0);
}

const alias = COMMAND_ALIASES[command];
const script = alias?.script || NODE_COMMANDS[command] || PYTHON_COMMANDS[command];
if (!script) {
  console.error(`Unknown MotionLoom command: ${command}`);
  printHelp();
  process.exit(2);
}

const executable = script.endsWith(".mjs") ? process.execPath : PYTHON;
const delegatedArgs = alias
  ? [...alias.args, ...args]
  : NODE_COMMANDS[command] && !["setup", "init"].includes(command)
    ? [command, ...args]
    : command === "init"
      ? ["init", ...args]
      : args;
const result = spawnSync(executable, [resolve(ROOT, script), ...delegatedArgs], {
  cwd: process.cwd(),
  stdio: "inherit",
  env: process.env,
});

if (result.error) {
  console.error(`MotionLoom could not start ${executable}: ${result.error.message}`);
  process.exit(2);
}
process.exit(result.status ?? 1);
