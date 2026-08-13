/**
 * snapshot.mjs — Headless Chromium harness for code-based scenes (GSAP,
 * Framer Motion, CSS). Loads the Dev Lab page for a given scene, seeks the
 * animation to N% progress via the lab's seek API, and screenshots the
 * canvas/element at deterministic points so PR reviews stay bit-exact.
 *
 * Usage: node scripts/snapshot.mjs --scene <name> --progress 0,50,100 --out <dir>
 * Requires: playwright (dev dependency of dev-lab)
 */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");

const argv = Object.fromEntries(
  process.argv.slice(2).map((a, i, arr) => [a.replace(/^--/, ""), arr[i + 1]]),
);
const scene = argv.scene;
const taskId = argv["task-id"] || "unbound";
const candidateId = argv["candidate-id"] || "";
const progress = (argv.progress || "0,50,100").split(",").map(Number);
const outDir = path.resolve(argv.out || `${ROOT}/../src/output/${scene}/snapshot`);

if (!scene) {
  console.error("usage: node snapshot.mjs --scene <name> --progress 0,50,100 --out <dir>");
  process.exit(1);
}
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ args: ["--no-sandbox", "--disable-dev-shm-usage"] });
const page = await browser.newPage({ viewport: { width: 800, height: 600 } });

// Boot the local dev-lab server (spawned by scripts/devlab.sh) or fall back to a static file.
const base = process.env.LAB_URL || "http://localhost:3300";
const query = new URLSearchParams({
  scene,
  mode: "snapshot",
  task_id: taskId,
  candidate_id: candidateId,
});
await page.goto(`${base}/?${query.toString()}`, {
  waitUntil: "networkidle",
  timeout: 30_000,
});
await page.waitForFunction(() => window.__lab?.ready === true, null, { timeout: 10_000 });

for (const pct of progress) {
  // The Dev Lab exposes window.__lab.seek(pct) — a uniform API across frameworks.
  const seekOk = await page.evaluate((p) => {
    if (!window.__lab?.seek) return false;
    window.__lab.seek(p / 100);
    return true;
  }, pct);
  if (!seekOk) throw new Error("Dev Lab contract missing window.__lab.seek");
  await page.waitForTimeout(200);
  const el = await page.$("[data-snapshot]");
  if (!el) throw new Error("Dev Lab contract missing [data-snapshot]");
  await el.screenshot({ path: path.join(outDir, `frame-${String(pct).padStart(2, "0")}.png`) });
}

await browser.close();
console.log(`snapshots written to ${outDir}`);
