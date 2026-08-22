#!/usr/bin/env node
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const expectedVersion = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8")).version;
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "motionloom-consumer-"));
const consumer = path.join(temporary, "consumer");
fs.mkdirSync(consumer);
fs.writeFileSync(
  path.join(consumer, "package.json"),
  `${JSON.stringify({ name: "motionloom-package-smoke", private: true }, null, 2)}\n`,
);

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || root,
    encoding: "utf8",
    env: process.env,
    ...options,
  });
  if (result.status !== 0) {
    throw new Error(
      `${command} ${args.join(" ")} failed (${result.status})\n${result.stdout || ""}\n${result.stderr || ""}`,
    );
  }
  return result.stdout.trim();
}

try {
  const packOutput = JSON.parse(run("npm", ["pack", "--json", "--pack-destination", temporary]));
  const tarball = path.join(temporary, packOutput[0].filename);
  run("npm", ["install", "--ignore-scripts", "--no-audit", "--no-fund", tarball], { cwd: consumer });

  const bin = process.platform === "win32"
    ? path.join(consumer, "node_modules", ".bin", "motionloom.cmd")
    : path.join(consumer, "node_modules", ".bin", "motionloom");
  const installedRoot = path.dirname(fs.realpathSync(path.join(consumer, "node_modules", "motionloom", "package.json")));
  const help = run(bin, ["--help"], { cwd: consumer });
  const init = JSON.parse(run(bin, ["init", "--dry-run", "--json"], { cwd: consumer }));
  const doctor = JSON.parse(run(bin, ["doctor", "--json"], { cwd: consumer }));

  if (!help.startsWith(`MotionLoom ${expectedVersion}`)) throw new Error(`unexpected help version: ${help.split("\n")[0]}`);
  if (fs.realpathSync(init.project_root || ".") !== fs.realpathSync(consumer)) {
    throw new Error(`installed CLI used the wrong project_root: ${init.project_root}`);
  }
  if (doctor.status !== "pass") throw new Error(`installed doctor failed: ${JSON.stringify(doctor.errors)}`);
  for (const relative of [
    "requirements.txt",
    "dev-lab/public/index.html",
    "dev-lab/public/devlab.js",
    "tests/runtime-harness/index.html",
  ]) {
    if (!fs.existsSync(path.join(installedRoot, relative))) throw new Error(`tarball omitted ${relative}`);
  }
  const scene = "browser-review-smoke";
  const consumerScene = path.join(consumer, "src", "output", scene);
  fs.mkdirSync(path.dirname(consumerScene), { recursive: true });
  fs.cpSync(path.join(installedRoot, "src", "output", scene), consumerScene, { recursive: true });
  const candidatePath = path.join(consumerScene, "browser-review.json");
  const candidate = JSON.parse(fs.readFileSync(candidatePath, "utf8"));
  candidate.expires_at = "2099-01-01T00:00:00Z";
  fs.writeFileSync(candidatePath, `${JSON.stringify(candidate, null, 2)}\n`);
  run(bin, ["devlab", scene, "--prepare-only"], { cwd: consumer });
  if (!fs.existsSync(path.join(installedRoot, "dev-lab", "public", "scenes", scene, "browser-review.json"))) {
    throw new Error("installed Dev Lab did not prepare the consumer scene");
  }
  const requestSource = path.join(installedRoot, "examples", "agent-consumer", "asset-planning", "pixellab-hero-256x448-request.json");
  const requestCopy = path.join(consumer, "asset-generation-request.json");
  const registryCopy = path.join(consumer, "artifact-adapter-registry.json");
  fs.copyFileSync(requestSource, requestCopy);
  fs.copyFileSync(path.join(installedRoot, "artifact-adapter-registry.json"), registryCopy);
  const plan = JSON.parse(run(bin, ["asset-generation-plan", "plan", "--request", requestCopy, "--registry", registryCopy, "--project-root", consumer.toString(), "--json"], { cwd: consumer }));
  if (plan.contract !== "motionloom-asset-generation-plan" || plan.approval !== false) throw new Error("installed planner contract failed");

  const sourceImage = path.join(installedRoot, "examples", "agent-consumer", "asset-consistency", "assets", "hero-frame-00.png");
  const adaptedImage = path.join(consumer, "adapted-frame.png");
  const adaptationReport = path.join(consumer, "adaptation-report.json");
  const adaptation = JSON.parse(run(bin, ["asset-adapt", "pad", "--input", sourceImage, "--output", adaptedImage, "--width", "256", "--height", "448", "--anchor", "footline", "--report", adaptationReport, "--json"], { cwd: consumer }));
  if (adaptation.contract !== "motionloom-asset-adaptation" || adaptation.approval !== false || adaptation.output.canvas[0] !== 256 || adaptation.output.canvas[1] !== 448) throw new Error("installed Node asset-adapt contract failed");
  if (!fs.existsSync(adaptedImage) || !fs.existsSync(adaptationReport)) throw new Error("installed asset-adapt omitted output/report");

  run(process.execPath, ["--input-type=module", "-e", "await import('playwright'); await import('vite');"], { cwd: consumer });
  console.log(JSON.stringify({ status: "pass", project_root: init.project_root, installed_root: installedRoot }, null, 2));
} finally {
  fs.rmSync(temporary, { recursive: true, force: true });
}
