/**
 * snapshot.mjs — Headless Chromium harness for the exact Dev Lab candidate.
 *
 * For live candidates this drives the same window.__lab runtime controller used
 * by human review. Legacy scenes without devlab-runtime.json remain supported
 * through the captured-evidence compatibility driver.
 *
 * Usage:
 *   node scripts/snapshot.mjs --scene <name> --progress 0,50,100 --out <dir>
 *   node scripts/snapshot.mjs --scene <name> --animation walk --progress 0,50,100 --out <dir>
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");

function parseArgs(values) {
  const out = {};
  for (let index = 0; index < values.length; index += 1) {
    const token = values[index];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = values[index + 1];
    if (next && !next.startsWith("--")) { out[key] = next; index += 1; }
    else out[key] = true;
  }
  return out;
}

const argv = parseArgs(process.argv.slice(2));
const scene = argv.scene;
const taskId = argv["task-id"] || "unbound";
const candidateId = argv["candidate-id"] || "";
const animation = typeof argv.animation === "string" ? argv.animation : null;
const base = process.env.LAB_URL || "http://localhost:3300";
const progress = String(argv.progress || "0,50,100").split(",").map(Number);
const outDir = path.resolve(argv.out || `${ROOT}/../src/output/${scene}/snapshot`);
const diagnosticsDir = path.resolve(argv.diagnostics || process.env.LAB_DIAGNOSTICS_DIR || `${outDir}-diagnostics`);

if (!scene) {
  console.error("usage: node snapshot.mjs --scene <name> [--animation <id>] --progress 0,50,100 --out <dir>");
  process.exit(1);
}
if (progress.some((value) => !Number.isFinite(value) || value < 0 || value > 100)) {
  throw new Error("--progress values must be numbers between 0 and 100");
}
fs.mkdirSync(outDir, { recursive: true });
fs.mkdirSync(diagnosticsDir, { recursive: true });

const browser = await chromium.launch({ args: ["--no-sandbox", "--disable-dev-shm-usage"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
const diagnostics = {
  scene, taskId, candidateId, animation, base, progress,
  console: [], pageErrors: [], failedRequests: [], httpErrors: [], runtimeStates: []
};
page.on("console", (message) => diagnostics.console.push({ type: message.type(), text: message.text() }));
page.on("pageerror", (error) => diagnostics.pageErrors.push({ message: error.message, stack: error.stack }));
page.on("requestfailed", (request) => diagnostics.failedRequests.push({ url: request.url(), error: request.failure()?.errorText || "unknown" }));
page.on("response", (response) => { if (response.status() >= 400) diagnostics.httpErrors.push({ url: response.url(), status: response.status() }); });

async function writeDiagnostics(error) {
  diagnostics.error = error ? { name: error.name, message: error.message, stack: error.stack } : null;
  diagnostics.readyState = await page.evaluate(() => ({
    href: location.href,
    title: document.title,
    lab: window.__lab ? {
      ready: window.__lab.ready,
      taskId: window.__lab.taskId,
      candidateId: window.__lab.candidateId,
      mode: window.__lab.mode,
      runtimeState: window.__lab.getRuntimeState?.()
    } : null
  })).catch(() => null);
  await fs.promises.writeFile(path.join(diagnosticsDir, "browser-diagnostics.json"), `${JSON.stringify(diagnostics, null, 2)}\n`);
  await fs.promises.writeFile(path.join(diagnosticsDir, "page.html"), await page.content().catch(() => ""));
}

const query = new URLSearchParams({ scene, mode: "snapshot", task_id: taskId, candidate_id: candidateId });
try {
  await page.goto(`${base}/?${query.toString()}`, { waitUntil: "networkidle", timeout: 30_000 });
  await page.waitForFunction(() => window.__lab?.ready === true, null, { timeout: 12_000 });

  if (animation) {
    const selected = await page.evaluate(async (id) => {
      if (!window.__lab?.selectAnimation) return false;
      await window.__lab.selectAnimation(id);
      return true;
    }, animation);
    if (!selected) throw new Error("Dev Lab contract missing window.__lab.selectAnimation");
  }

  await page.evaluate(async () => { if (window.__lab?.pause) await window.__lab.pause().catch(() => {}); });

  for (const pct of progress) {
    const state = await page.evaluate(async (p) => {
      if (!window.__lab?.seek) throw new Error("Dev Lab contract missing window.__lab.seek");
      await window.__lab.seek(p / 100);
      return window.__lab.getRuntimeState?.() || null;
    }, pct);
    diagnostics.runtimeStates.push({ percent: pct, state });
    await page.waitForTimeout(100);
    const el = await page.$("[data-snapshot]");
    if (!el) throw new Error("Dev Lab contract missing [data-snapshot]");
    const suffix = animation ? `-${animation}` : "";
    await el.screenshot({ path: path.join(outDir, `frame${suffix}-${String(pct).padStart(2, "0")}.png`) });
  }
  await writeDiagnostics(null);
} catch (error) {
  await writeDiagnostics(error);
  throw error;
} finally {
  await browser.close();
}
console.log(`snapshots written to ${outDir}`);
