#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { chromium } from "playwright";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputRoot = path.resolve(process.env.RUNTIME_EVIDENCE_DIR || path.join(ROOT, "artifacts/runtime-adapters"));
const outputPolicyRoot = path.resolve(process.env.MOTIONLOOM_RUNTIME_OUTPUT_ROOT || ROOT);
const port = Number(process.env.RUNTIME_HARNESS_PORT || 4179);
const supportedFrameworks = new Set(["rive", "gsap", "framer-motion"]);
const frameworks = (process.env.RUNTIME_FRAMEWORKS || "rive,gsap,framer-motion")
  .split(",").map((name) => name.trim()).filter(Boolean);
const unsupported = frameworks.filter((name) => !supportedFrameworks.has(name));
if (unsupported.length) {
  throw new Error(`unsupported runtime framework(s): ${unsupported.join(", ")}`);
}
function canonicalPath(target) {
  let existing = target;
  const missing = [];
  while (!fs.existsSync(existing)) {
    const parent = path.dirname(existing);
    if (parent === existing) break;
    missing.unshift(path.basename(existing));
    existing = parent;
  }
  const base = fs.existsSync(existing) ? fs.realpathSync(existing) : path.resolve(existing);
  return path.resolve(base, ...missing);
}

function isStrictChild(target, parent) {
  const relative = path.relative(parent, target);
  return Boolean(relative) && relative !== ".." && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

const canonicalOutputRoot = canonicalPath(outputRoot);
const canonicalPolicyRoot = canonicalPath(outputPolicyRoot);
if (!isStrictChild(canonicalOutputRoot, canonicalPolicyRoot)) {
  throw new Error(
    `RUNTIME_EVIDENCE_DIR must be a dedicated child of ${outputPolicyRoot}; ` +
    "set MOTIONLOOM_RUNTIME_OUTPUT_ROOT explicitly to authorize another parent",
  );
}
const baseUrl = `http://127.0.0.1:${port}`;
const runId = `${Date.now()}-${process.pid}`;
const runtimeScene = process.env.RUNTIME_SCENE || null;
const runtimeTaskId = process.env.RUNTIME_TASK_ID || null;
const runtimeSourcePath = process.env.RUNTIME_SOURCE_PATH ? path.resolve(process.env.RUNTIME_SOURCE_PATH) : null;
const runtimeManifestPath = process.env.RUNTIME_MANIFEST_PATH ? path.resolve(process.env.RUNTIME_MANIFEST_PATH) : null;
const runtimeMotionIrPath = process.env.RUNTIME_MOTION_IR_PATH ? path.resolve(process.env.RUNTIME_MOTION_IR_PATH) : null;

function sha256File(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function sha256Json(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

fs.rmSync(outputRoot, { recursive: true, force: true });
fs.mkdirSync(outputRoot, { recursive: true });
const viteBin = path.join(ROOT, "node_modules/vite/bin/vite.js");
const server = spawn(process.execPath, [viteBin, "--host", "127.0.0.1", "--port", String(port), "--strictPort"], {
  cwd: ROOT,
  stdio: ["ignore", "pipe", "pipe"],
});
let serverLog = "";
server.stdout.on("data", (chunk) => { serverLog += chunk.toString(); });
server.stderr.on("data", (chunk) => { serverLog += chunk.toString(); });

try {
  await waitForServer(`${baseUrl}/tests/runtime-harness/index.html`);
  const browser = await chromium.launch({ headless: true });
  const summary = [];
  for (const framework of frameworks) {
    summary.push(await testFramework(browser, framework));
  }
  await browser.close();
  const report = {
    schema_version: "1.1",
    run_id: runId,
    generated_at: new Date().toISOString(),
    mode: "runtime",
    harness: "tests/runtime-harness",
    status: summary.every((item) => item.status === "pass") ? "pass" : "fail",
    frameworks: summary,
  };
  if (runtimeScene) report.scene = runtimeScene;
  if (runtimeTaskId) report.task_id = runtimeTaskId;
  if (runtimeSourcePath) report.source_sha256 = sha256File(runtimeSourcePath);
  if (runtimeManifestPath) report.manifest_sha256 = sha256File(runtimeManifestPath);
  if (runtimeMotionIrPath) report.motion_ir_sha256 = sha256File(runtimeMotionIrPath);
  fs.writeFileSync(path.join(outputRoot, "runtime-evidence.json"), `${JSON.stringify(report, null, 2)}\n`);
  const failed = summary.filter((item) => item.status !== "pass");
  if (failed.length) {
    console.error(JSON.stringify(report, null, 2));
    process.exitCode = 1;
  } else {
    console.log(JSON.stringify(report, null, 2));
  }
} finally {
  server.kill("SIGTERM");
  await sleep(100);
  if (!server.killed) server.kill("SIGKILL");
}

async function waitForServer(url) {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Vite is still starting.
    }
    await sleep(100);
  }
  throw new Error(`runtime harness did not start on ${url}\n${serverLog}`);
}

async function testFramework(browser, framework) {
  const sceneDir = path.join(outputRoot, framework);
  fs.mkdirSync(sceneDir, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 512, height: 512 }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  const url = `${baseUrl}/tests/runtime-harness/index.html?framework=${encodeURIComponent(framework)}`;
  const result = { run_id: runId, framework, url, status: "fail", ready: false, runtime: null, frames: [], console_errors: consoleErrors };
  try {
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForFunction(() => Boolean(window.__animationAdapter?.ready), null, { timeout: 30000 });
    result.ready = true;
    result.runtime = await page.evaluate(() => window.__animationAdapter.runtime);
    const telemetrySamples = [];
    for (const [sequence, percent] of [0, 50, 100].entries()) {
      const timing = await page.evaluate(async (value) => {
        window.__animationAdapter.setProgress(value / 100);
        const timestamps = await new Promise((resolve) => {
          const values = [];
          const collect = (timestamp) => {
            values.push(timestamp);
            if (values.length >= 4) resolve(values);
            else requestAnimationFrame(collect);
          };
          requestAnimationFrame(collect);
        });
        return {
          captured_at_ms: performance.now(),
          raf_intervals_ms: timestamps.slice(1).map((timestamp, index) => Math.max(0, timestamp - timestamps[index])),
        };
      }, percent);
      const state = await page.evaluate(() => window.__animationAdapter.getState());
      const file = path.join(sceneDir, `frame-${String(percent).padStart(2, "0")}.png`);
      await page.screenshot({ path: file });
      result.frames.push({ percent, file: path.relative(ROOT, file), state });
      telemetrySamples.push({
        sequence,
        percent,
        captured_at_ms: Number(timing.captured_at_ms),
        raf_intervals_ms: timing.raf_intervals_ms.map(Number),
        state_sha256: sha256Json(state),
        state,
      });
    }
    if (consoleErrors.length) throw new Error(consoleErrors.join("; "));
    const intervals = telemetrySamples.flatMap((sample) => sample.raf_intervals_ms);
    const sortedIntervals = [...intervals].sort((a, b) => a - b);
    const p95Index = Math.min(sortedIntervals.length - 1, Math.max(0, Math.ceil(sortedIntervals.length * 0.95) - 1));
    const telemetry = {
      schema_version: "1.0",
      run_id: runId,
      generated_at: new Date().toISOString(),
      mode: "runtime-telemetry",
      ...(runtimeTaskId ? { task_id: runtimeTaskId } : {}),
      ...(runtimeScene ? { scene: runtimeScene } : {}),
      framework,
      runtime: result.runtime,
      ...(runtimeSourcePath ? { source_sha256: sha256File(runtimeSourcePath) } : {}),
      ...(runtimeManifestPath ? { manifest_sha256: sha256File(runtimeManifestPath) } : {}),
      ...(runtimeMotionIrPath ? { motion_ir_sha256: sha256File(runtimeMotionIrPath) } : {}),
      samples: telemetrySamples,
      metrics: {
        sample_count: telemetrySamples.length,
        raf_interval_count: intervals.length,
        max_raf_interval_ms: Math.max(...intervals),
        p95_raf_interval_ms: sortedIntervals[p95Index],
      },
      status: "pass",
    };
    const telemetryPath = path.join(sceneDir, "runtime-telemetry.json");
    fs.writeFileSync(telemetryPath, `${JSON.stringify(telemetry, null, 2)}\n`);
    result.telemetry = {
      file: path.relative(outputRoot, telemetryPath),
      sha256: sha256File(telemetryPath),
      metrics: telemetry.metrics,
    };
    result.status = "pass";
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  } finally {
    await page.close();
  }
  fs.writeFileSync(path.join(sceneDir, "runtime-evidence.json"), `${JSON.stringify(result, null, 2)}\n`);
  return result;
}
