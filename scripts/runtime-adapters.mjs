#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import { chromium } from "playwright";

const ROOT = path.resolve(new URL("..", import.meta.url).pathname);
const outputRoot = path.resolve(process.env.RUNTIME_EVIDENCE_DIR || path.join(ROOT, "artifacts/runtime-adapters"));
const port = Number(process.env.RUNTIME_HARNESS_PORT || 4179);
const frameworks = (process.env.RUNTIME_FRAMEWORKS || "rive,gsap,framer-motion")
  .split(",").map((name) => name.trim()).filter(Boolean);
const baseUrl = `http://127.0.0.1:${port}`;

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
    schema_version: "1.0",
    generated_at: new Date().toISOString(),
    mode: "runtime",
    harness: "tests/runtime-harness",
    frameworks: summary,
  };
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
  const result = { framework, url, status: "fail", runtime: null, frames: [], console_errors: consoleErrors };
  try {
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForFunction(() => Boolean(window.__animationAdapter?.ready), null, { timeout: 30000 });
    result.runtime = await page.evaluate(() => window.__animationAdapter.runtime);
    for (const percent of [0, 50, 100]) {
      await page.evaluate(async (value) => {
        window.__animationAdapter.setProgress(value / 100);
        await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      }, percent);
      const state = await page.evaluate(() => window.__animationAdapter.getState());
      const file = path.join(sceneDir, `frame-${String(percent).padStart(2, "0")}.png`);
      await page.screenshot({ path: file });
      result.frames.push({ percent, file: path.relative(ROOT, file), state });
    }
    if (consoleErrors.length) throw new Error(consoleErrors.join("; "));
    result.status = "pass";
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  } finally {
    await page.close();
  }
  fs.writeFileSync(path.join(sceneDir, "runtime-evidence.json"), `${JSON.stringify(result, null, 2)}\n`);
  return result;
}
