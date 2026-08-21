#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { chromium } from "playwright";

const labRoot = path.resolve(new URL("..", import.meta.url).pathname);
const evidenceRoot = path.resolve(process.env.MOTIONLOOM_FRAME_CONSUMER_OUT || path.join(os.tmpdir(), "motionloom-frame-consumer-dogfood"));
const assetsRoot = path.join(evidenceRoot, "consumer-project", "motion-assets");
const contractReport = JSON.parse(fs.readFileSync(path.join(evidenceRoot, "consumer-dogfood-report.json"), "utf8"));
const consumerVersion = String(contractReport.motionloom_version || "unknown");
const sourceFrames = Array.from({ length: 12 }, (_, index) => path.join(assetsRoot, "generated", `scout-run-${String(index).padStart(2, "0")}.png`));
for (const file of sourceFrames) {
  if (!fs.existsSync(file)) throw new Error(`Consumer frame dogfood source is missing: ${file}`);
}

const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), "motionloom-devlab-frame-consumer-"));
const publicRoot = path.join(fixtureRoot, "public");
const scene = "published-consumer-run-12";
const taskId = "published-consumer-run-12-review";
const candidateId = "f6a12e00000000000001";
const sceneRoot = path.join(publicRoot, "scenes", scene);
const browserOut = path.join(evidenceRoot, "devlab");

fs.mkdirSync(sceneRoot, { recursive: true });
fs.mkdirSync(browserOut, { recursive: true });
for (const file of ["index.html", "devlab.js", "action-library.js"]) {
  fs.copyFileSync(path.join(labRoot, "public", file), path.join(publicRoot, file));
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}

function sha256File(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

const runtimeFrames = [];
for (let index = 0; index < sourceFrames.length; index += 1) {
  const relative = `frames/scout-run-${String(index).padStart(2, "0")}.png`;
  const target = path.join(sceneRoot, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(sourceFrames[index], target);
  runtimeFrames.push(relative);
}
const frameHashes = runtimeFrames.map((relative) => sha256File(path.join(sceneRoot, relative)));
const bundleSha256 = crypto.createHash("sha256").update(frameHashes.join("\n")).digest("hex");

writeJson(path.join(sceneRoot, "manifest.json"), {
  scene,
  name: "Published package 12-frame consumer dogfood",
  description: "A 12-frame pixel-art run cycle produced by the isolated consumer contract dogfood and reviewed through the live Dev Lab runtime.",
  framework: "sprite-sequence",
  category: "character",
  checks: [
    {
      id: "source-isolation",
      label: "Source frames stay isolated and consistently framed",
      detail: "Review the run cycle for scale, baseline, crop and neighboring-pose contamination.",
    },
    {
      id: "runtime-motion",
      label: "12-frame playback reads continuously",
      detail: "Use playback, scrub and frame-step rather than relying only on captured checkpoints.",
    },
  ],
});
writeJson(path.join(sceneRoot, "motion-spec.json"), {
  framework: "sprite-sequence",
  category: "character",
  duration_s: 1,
  fps: 12,
  loop: true,
  context_binding: { context_sha256: "d".repeat(64) },
});
writeJson(path.join(sceneRoot, "devlab-runtime.json"), {
  schema_version: "1.0",
  mode: "sprite-sequence",
  files: runtimeFrames,
  default_animation: "run-12",
  groups: [{ id: "locomotion", label: "Locomotion", order: 10 }],
  animations: [
    {
      id: "run-12",
      label: "Run · 12 frames",
      group: "locomotion",
      tags: ["run", "12-frame", "frame-generation-lock", "consumer-dogfood"],
      fps: 12,
      frames: runtimeFrames,
      loop: true,
      review_required: true,
      events: ["foot-contact-right@0", "foot-contact-left@6"],
    },
  ],
  controls: { play: true, pause: true, restart: true, seek: true, step: true, speed: true, loop: true },
  viewport: {
    canvas_width: 64,
    canvas_height: 64,
    pixel_art: true,
    baseline_y: 51,
    pivot: { x: 32, y: 54 },
    background: "checker",
  },
  review_policy: { require_all_animations: true },
});
writeJson(path.join(sceneRoot, "browser-review.json"), {
  schema_version: "1.0",
  candidate_id: candidateId,
  task_id: taskId,
  scene,
  url: "http://127.0.0.1/",
  status: "prepared",
  context_sha256: "d".repeat(64),
  source_sha256: frameHashes[0],
  runtime: "sprite-sequence",
  checkpoints: [0, 50, 100],
  review_artifact: "review.json",
  requires_user_approval: true,
  prepared_at: "2026-08-21T00:00:00Z",
  expires_at: "2099-01-01T00:00:00Z",
  runtime_review: {
    live: true,
    mode: "sprite-sequence",
    descriptor: "devlab-runtime.json",
    bundle_sha256: bundleSha256,
    animations: ["run-12"],
    review_policy: { require_all_animations: true },
  },
});

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".png", "image/png"],
]);
const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const target = path.resolve(publicRoot, relative);
  if (target !== publicRoot && !target.startsWith(`${publicRoot}${path.sep}`)) {
    response.writeHead(403, { "Cache-Control": "no-store" }).end("forbidden");
    return;
  }
  let body;
  try {
    body = fs.readFileSync(target);
  } catch {
    response.writeHead(404, { "Cache-Control": "no-store" }).end("not found");
    return;
  }
  response.writeHead(200, {
    "Content-Type": contentTypes.get(path.extname(target)) || "application/octet-stream",
    "Cache-Control": "no-store",
  });
  response.end(body);
});

let browser;
try {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}/?scene=${scene}&task_id=${taskId}&candidate_id=${candidateId}`;
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => window.__lab?.ready === true, null, { timeout: 10000 });

  const initial = await page.evaluate(() => ({
    mode: window.__lab.mode,
    actionIds: [...document.querySelectorAll(".animation-btn")].map((node) => node.dataset.animation),
    approveDisabled: document.querySelector("#confirm").disabled,
    modeBadge: document.querySelector("#mode-badge").textContent,
    frame: window.__lab.getRuntimeState(),
  }));
  if (initial.mode !== "live-runtime" || initial.modeBadge !== "LIVE RUNTIME") {
    throw new Error(`12-frame consumer dogfood did not open live runtime: ${JSON.stringify(initial)}`);
  }
  if (initial.actionIds.join(",") !== "run-12" || !initial.approveDisabled) {
    throw new Error(`12-frame consumer action/review gate mismatch: ${JSON.stringify(initial)}`);
  }

  const checkpoints = [
    { name: "frame-00", progress: 0, expectedFrame: 0 },
    { name: "frame-06", progress: 6 / 11, expectedFrame: 6 },
    { name: "frame-11", progress: 1, expectedFrame: 11 },
  ];
  const checkpointStates = {};
  for (const checkpoint of checkpoints) {
    await page.evaluate(async (progress) => window.__lab.seek(progress), checkpoint.progress);
    await page.waitForFunction(() => {
      const image = document.querySelector("#frame");
      return image && !image.hidden && image.complete && image.naturalWidth > 0;
    });
    const state = await page.evaluate(() => window.__lab.getRuntimeState());
    if (state.frame !== checkpoint.expectedFrame) {
      throw new Error(`Expected ${checkpoint.name} to resolve frame ${checkpoint.expectedFrame}: ${JSON.stringify(state)}`);
    }
    checkpointStates[checkpoint.name] = state;
    await page.locator("#stage-shell").screenshot({ path: path.join(browserOut, `${checkpoint.name}.png`) });
  }

  await page.evaluate(async () => {
    await window.__lab.seek(0);
    await window.__lab.setSpeed(2);
    await window.__lab.setLoop(true);
    await window.__lab.play();
  });
  await page.waitForTimeout(180);
  await page.evaluate(async () => window.__lab.pause());
  const played = await page.evaluate(() => window.__lab.getRuntimeState());
  if (!(played.frame > 0) || played.playing || played.speed !== 2 || played.loop !== true) {
    throw new Error(`12-frame play/pause/speed/loop failed: ${JSON.stringify(played)}`);
  }
  const pausedProgress = played.progress;
  await page.waitForTimeout(120);
  const stillPaused = await page.evaluate(() => window.__lab.getRuntimeState());
  if (Math.abs(stillPaused.progress - pausedProgress) > 0.001) throw new Error("Paused 12-frame runtime continued advancing");

  await page.evaluate(async () => window.__lab.restart());
  const restarted = await page.evaluate(() => window.__lab.getRuntimeState());
  if (restarted.frame !== 0 || restarted.progress > 0.001) throw new Error(`Restart did not return to frame zero: ${JSON.stringify(restarted)}`);
  await page.evaluate(async () => window.__lab.stepFrames(1));
  const stepped = await page.evaluate(() => window.__lab.getRuntimeState());
  if (stepped.frame !== 1) throw new Error(`+1 frame did not reach frame 1: ${JSON.stringify(stepped)}`);
  await page.evaluate(async () => window.__lab.stepFrames(-1));
  const steppedBack = await page.evaluate(() => window.__lab.getRuntimeState());
  if (steppedBack.frame !== 0) throw new Error(`-1 frame did not return to frame 0: ${JSON.stringify(steppedBack)}`);

  await page.selectOption("#background", "light");
  for (const id of ["grid", "bounds", "baseline", "pivot"]) await page.click(`#${id}`);
  await page.click("#zoom-in");
  await page.locator("body").screenshot({ path: path.join(browserOut, "workbench-12-frame.png"), fullPage: true });

  const coverage = await page.evaluate(() => ({
    visited: [...document.querySelectorAll(".animation-btn.visited")].map((node) => node.dataset.animation),
    progress: document.querySelector("#review-progress").textContent,
    approveDisabled: document.querySelector("#confirm").disabled,
  }));
  if (coverage.visited.join(",") !== "run-12" || !coverage.progress.includes("1/1") || !coverage.approveDisabled) {
    throw new Error(`12-frame review coverage mismatch before checklist: ${JSON.stringify(coverage)}`);
  }
  const checkboxes = page.locator("#checks input[type=checkbox]");
  const checkboxCount = await checkboxes.count();
  for (let index = 0; index < checkboxCount; index += 1) await checkboxes.nth(index).check();
  const reviewReady = await page.evaluate(() => ({
    approveDisabled: document.querySelector("#confirm").disabled,
    review: window.__lab.getReview(),
  }));
  if (reviewReady.approveDisabled) throw new Error("Approval control did not become available after explicit review gates");
  if (reviewReady.review?.decision === "approved") throw new Error("Automated 12-frame dogfood must never mint user approval");

  const report = {
    status: "pass",
    scene,
    source: `published motionloom@${consumerVersion} consumer dogfood output`,
    runtime_mode: "sprite-sequence",
    animation: "run-12",
    frame_count: 12,
    unique_frame_hashes: new Set(frameHashes).size,
    bundle_sha256: bundleSha256,
    checkpoints: checkpointStates,
    play_pause_restart: "pass",
    frame_step: "pass",
    scrub: "pass",
    speed: "pass",
    loop: "pass",
    stage_tools: "pass",
    review_coverage: "1/1 action",
    approval: "not_granted_by_test",
    screenshots: ["frame-00.png", "frame-06.png", "frame-11.png", "workbench-12-frame.png"],
  };
  writeJson(path.join(browserOut, "devlab-consumer-report.json"), report);
  console.log(JSON.stringify(report, null, 2));
  await page.close();
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
  fs.rmSync(fixtureRoot, { recursive: true, force: true });
}
