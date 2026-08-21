#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { chromium } from "playwright";

const labRoot = path.resolve(new URL("..", import.meta.url).pathname);
const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), "motionloom-devlab-dogfood-"));
const publicRoot = path.join(fixtureRoot, "public");
const outRoot = path.resolve(process.env.MOTIONLOOM_DOGFOOD_OUT || path.join(os.tmpdir(), "motionloom-devlab-dogfood-output"));
const scene = "four-action-dogfood";
const taskId = "devlab-v2-four-action-dogfood";
const candidateId = "d0gf00d0000000000001";
const sceneRoot = path.join(publicRoot, "scenes", scene);

fs.rmSync(outRoot, { recursive: true, force: true });
fs.mkdirSync(sceneRoot, { recursive: true });
fs.mkdirSync(outRoot, { recursive: true });
for (const file of ["index.html", "devlab.js"]) {
  fs.copyFileSync(path.join(labRoot, "public", file), path.join(publicRoot, file));
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}

function robotSvg(action, phase) {
  const p = phase / 3;
  let bob = 0;
  let lean = 0;
  let leftArm = 5;
  let rightArm = -5;
  let leftLeg = 0;
  let rightLeg = 0;
  let bodyX = 0;

  if (action === "idle") {
    bob = Math.sin(p * Math.PI * 2) * 4;
    leftArm = 4 + Math.sin(p * Math.PI * 2) * 3;
    rightArm = -4 - Math.sin(p * Math.PI * 2) * 3;
  } else if (action === "walk") {
    const swing = Math.sin(p * Math.PI * 2);
    bob = Math.abs(swing) * 5;
    leftLeg = swing * 26;
    rightLeg = -swing * 26;
    leftArm = -swing * 24;
    rightArm = swing * 24;
  } else if (action === "run") {
    const swing = Math.sin(p * Math.PI * 2);
    bob = Math.abs(swing) * 9;
    lean = 7;
    bodyX = 10;
    leftLeg = swing * 44;
    rightLeg = -swing * 44;
    leftArm = -swing * 38 - 8;
    rightArm = swing * 38 - 8;
  } else if (action === "attack") {
    const reach = [0, 38, 78, 22][phase];
    bob = [0, -3, -6, -2][phase];
    lean = [0, 4, 9, 3][phase];
    rightArm = -8 - reach;
    leftArm = [8, 18, 28, 12][phase];
    leftLeg = [0, 6, 12, 5][phase];
    rightLeg = [0, -7, -16, -5][phase];
  }

  const transform = `translate(${400 + bodyX} ${320 + bob}) rotate(${lean})`;
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <g transform="${transform}" stroke-linecap="round" stroke-linejoin="round">
    <g transform="translate(0 -155)">
      <rect x="-86" y="-66" width="172" height="124" rx="42" fill="#f4dfb4" stroke="#171b25" stroke-width="12"/>
      <rect x="-61" y="-37" width="122" height="66" rx="18" fill="#061a31" stroke="#171b25" stroke-width="9"/>
      <rect x="-34" y="-14" width="15" height="29" rx="4" fill="#08d7ef"/>
      <rect x="20" y="-14" width="15" height="29" rx="4" fill="#08d7ef"/>
      <path d="M0 -68 V-94" stroke="#171b25" stroke-width="10"/>
      <rect x="-13" y="-112" width="26" height="22" rx="5" fill="#ff7a0b" stroke="#171b25" stroke-width="7"/>
    </g>
    <g>
      <rect x="-72" y="-90" width="144" height="126" rx="34" fill="#f4dfb4" stroke="#171b25" stroke-width="12"/>
      <rect x="-23" y="-58" width="46" height="52" rx="10" fill="#202635" stroke="#171b25" stroke-width="8"/>
      <circle cx="0" cy="-33" r="9" fill="#ff7a0b"/>
      <rect x="-96" y="-85" width="42" height="36" rx="13" fill="#ff7a0b" stroke="#171b25" stroke-width="9"/>
      <rect x="54" y="-85" width="42" height="36" rx="13" fill="#ff7a0b" stroke="#171b25" stroke-width="9"/>
    </g>
    <g transform="translate(-77 -60) rotate(${leftArm})">
      <path d="M0 0 L-25 76" stroke="#252b38" stroke-width="28"/>
      <rect x="-45" y="61" width="38" height="46" rx="10" fill="#f4dfb4" stroke="#171b25" stroke-width="8"/>
    </g>
    <g transform="translate(77 -60) rotate(${rightArm})">
      <path d="M0 0 L25 76" stroke="#252b38" stroke-width="28"/>
      <rect x="8" y="61" width="38" height="46" rx="10" fill="#f4dfb4" stroke="#171b25" stroke-width="8"/>
    </g>
    <g transform="translate(-38 30) rotate(${leftLeg})">
      <path d="M0 0 L-8 94" stroke="#252b38" stroke-width="34"/>
      <circle cx="-8" cy="62" r="19" fill="#ff7a0b" stroke="#171b25" stroke-width="8"/>
      <path d="M-8 92 L-21 142" stroke="#f4dfb4" stroke-width="36"/>
      <path d="M-37 147 H8" stroke="#171b25" stroke-width="18"/>
    </g>
    <g transform="translate(38 30) rotate(${rightLeg})">
      <path d="M0 0 L8 94" stroke="#252b38" stroke-width="34"/>
      <circle cx="8" cy="62" r="19" fill="#ff7a0b" stroke="#171b25" stroke-width="8"/>
      <path d="M8 92 L21 142" stroke="#f4dfb4" stroke-width="36"/>
      <path d="M-8 147 H37" stroke="#171b25" stroke-width="18"/>
    </g>
  </g>
</svg>`;
}

const actions = [
  { id: "idle", label: "Idle", fps: 6, loop: true },
  { id: "walk", label: "Walk", fps: 8, loop: true },
  { id: "run", label: "Run", fps: 12, loop: true },
  { id: "attack", label: "Attack", fps: 10, loop: false },
];
const files = [];
for (const action of actions) {
  action.frames = [];
  for (let phase = 0; phase < 4; phase += 1) {
    const relative = `frames/${action.id}-${phase}.svg`;
    const target = path.join(sceneRoot, relative);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, robotSvg(action.id, phase));
    action.frames.push(relative);
    files.push(relative);
  }
}

writeJson(path.join(sceneRoot, "manifest.json"), {
  scene,
  name: "Scout Runtime Dogfood",
  description: "Four-action deterministic character runtime used to exercise the interactive Dev Lab workbench.",
  framework: "sprite-sequence",
  category: "character",
  checks: [
    { id: "motion", label: "Motion reads correctly", detail: "Inspect Idle, Walk, Run and Attack before approval is available." },
    { id: "framing", label: "Framing remains stable", detail: "Check baseline, bounds, pivot and stage presentation." },
  ],
});
writeJson(path.join(sceneRoot, "motion-spec.json"), {
  framework: "sprite-sequence",
  category: "character",
  duration_s: 0.5,
  fps: 8,
  loop: true,
  context_binding: { context_sha256: "a".repeat(64) },
});
writeJson(path.join(sceneRoot, "devlab-runtime.json"), {
  schema_version: "1.0",
  mode: "sprite-sequence",
  files,
  default_animation: "idle",
  animations: actions.map(({ id, label, fps, loop, frames }) => ({ id, label, fps, loop, frames, review_required: true })),
  controls: { play: true, pause: true, restart: true, seek: true, step: true, speed: true, loop: true },
  viewport: { canvas_width: 800, canvas_height: 600, pixel_art: false, baseline_y: 500, pivot: { x: 400, y: 500 }, background: "checker" },
  review_policy: { require_all_animations: true },
});
writeJson(path.join(sceneRoot, "browser-review.json"), {
  schema_version: "1.0",
  candidate_id: candidateId,
  task_id: taskId,
  scene,
  url: "http://127.0.0.1/",
  status: "prepared",
  context_sha256: "a".repeat(64),
  source_sha256: "b".repeat(64),
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
    bundle_sha256: "c".repeat(64),
    animations: actions.map((action) => action.id),
    review_policy: { require_all_animations: true },
  },
});

const contentTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
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
  try { body = fs.readFileSync(target); }
  catch { response.writeHead(404, { "Cache-Control": "no-store" }).end("not found"); return; }
  response.writeHead(200, { "Content-Type": contentTypes.get(path.extname(target)) || "application/octet-stream", "Cache-Control": "no-store" });
  response.end(body);
});

let browser;
try {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}/?scene=${scene}&task_id=${taskId}&candidate_id=${candidateId}`;
  browser = await chromium.launch({ headless: true });

  async function open(viewport) {
    const page = await browser.newPage({ viewport });
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => window.__lab?.ready === true, null, { timeout: 10000 });
    return page;
  }

  const page = await open({ width: 1440, height: 1000 });
  const initial = await page.evaluate(() => ({
    mode: window.__lab.mode,
    actions: [...document.querySelectorAll(".animation-btn")].map((node) => node.dataset.animation),
    approveDisabled: document.querySelector("#confirm").disabled,
    modeBadge: document.querySelector("#mode-badge").textContent,
  }));
  if (initial.mode !== "live-runtime" || initial.modeBadge !== "LIVE RUNTIME") throw new Error(`Dogfood did not open live runtime: ${JSON.stringify(initial)}`);
  if (initial.actions.join(",") !== "idle,walk,run,attack") throw new Error(`Dogfood action discovery mismatch: ${JSON.stringify(initial.actions)}`);
  if (!initial.approveDisabled) throw new Error("Approval must remain gated before review coverage/checklist completion");

  const actionStates = {};
  for (const action of actions) {
    await page.evaluate(async (id) => { await window.__lab.selectAnimation(id); await window.__lab.seek(0.5); }, action.id);
    await page.waitForFunction(() => {
      const image = document.querySelector("#frame");
      return image && !image.hidden && image.complete && image.naturalWidth > 0;
    });
    actionStates[action.id] = await page.evaluate(() => window.__lab.getRuntimeState());
    await page.locator("#stage-shell").screenshot({ path: path.join(outRoot, `action-${action.id}.png`) });
  }

  await page.evaluate(async () => { await window.__lab.selectAnimation("walk"); await window.__lab.seek(0.1); await window.__lab.setSpeed(2); await window.__lab.setLoop(false); await window.__lab.play(); });
  await page.waitForTimeout(180);
  await page.evaluate(async () => window.__lab.pause());
  const played = await page.evaluate(() => window.__lab.getRuntimeState());
  if (!(played.progress > 0.1) || played.playing || played.speed !== 2 || played.loop !== false) throw new Error(`Play/pause/speed/loop dogfood failed: ${JSON.stringify(played)}`);
  const pausedProgress = played.progress;
  await page.waitForTimeout(120);
  const stillPaused = await page.evaluate(() => window.__lab.getRuntimeState());
  if (Math.abs(stillPaused.progress - pausedProgress) > 0.001) throw new Error("Paused runtime continued advancing");

  await page.evaluate(async () => window.__lab.restart());
  const restarted = await page.evaluate(() => window.__lab.getRuntimeState());
  if (restarted.progress > 0.001) throw new Error(`Restart did not return to frame zero: ${JSON.stringify(restarted)}`);
  await page.evaluate(async () => window.__lab.stepFrames(1));
  const stepped = await page.evaluate(() => window.__lab.getRuntimeState());
  if (!(stepped.frame >= 1)) throw new Error(`Frame step did not advance: ${JSON.stringify(stepped)}`);

  await page.selectOption("#background", "light");
  for (const id of ["grid", "bounds", "baseline", "pivot"]) await page.click(`#${id}`);
  await page.click("#zoom-in");
  const tools = await page.evaluate(() => ({
    light: document.querySelector("#stage").classList.contains("bg-light"),
    grid: document.querySelector("#overlay-grid").classList.contains("on"),
    bounds: document.querySelector("#overlay-bounds").classList.contains("on"),
    baseline: document.querySelector("#overlay-baseline").classList.contains("on"),
    pivot: document.querySelector("#overlay-pivot").classList.contains("on"),
    zoom: document.querySelector("#zoom-label").textContent,
    fullscreenAvailable: !document.querySelector("#fullscreen").disabled,
  }));
  if (!tools.light || !tools.grid || !tools.bounds || !tools.baseline || !tools.pivot || tools.zoom === "100%" || !tools.fullscreenAvailable) throw new Error(`Stage tools dogfood failed: ${JSON.stringify(tools)}`);
  await page.locator("body").screenshot({ path: path.join(outRoot, "workbench-desktop.png"), fullPage: true });
  await page.click("#zoom-reset");

  const coverage = await page.evaluate(() => ({
    visited: [...document.querySelectorAll(".animation-btn.visited")].map((node) => node.dataset.animation),
    text: document.querySelector("#review-progress").textContent,
    approveDisabled: document.querySelector("#confirm").disabled,
  }));
  if (coverage.visited.length !== 4 || !coverage.text.includes("4/4") || !coverage.approveDisabled) throw new Error(`Review coverage gate failed: ${JSON.stringify(coverage)}`);

  const checkboxes = page.locator("#checks input[type=checkbox]");
  const checkboxCount = await checkboxes.count();
  for (let index = 0; index < checkboxCount; index += 1) await checkboxes.nth(index).check();
  const approvalReady = await page.evaluate(() => ({ disabled: document.querySelector("#confirm").disabled, review: window.__lab.getReview() }));
  if (approvalReady.disabled) throw new Error("Approval did not become available after all required user-review gates were satisfied");
  if (approvalReady.review?.decision === "approved") throw new Error("Dogfood must not mint or click user approval");
  await page.close();

  const mobile = await open({ width: 390, height: 844 });
  await mobile.evaluate(async () => { await window.__lab.selectAnimation("attack"); await window.__lab.seek(0.5); });
  const mobileState = await mobile.evaluate(() => ({
    actions: document.querySelectorAll(".animation-btn").length,
    stageWidth: document.querySelector("#stage-shell").getBoundingClientRect().width,
    bodyWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
  }));
  if (mobileState.actions !== 4 || mobileState.bodyWidth > mobileState.viewportWidth + 2 || mobileState.stageWidth > mobileState.viewportWidth) throw new Error(`Mobile dogfood layout failed: ${JSON.stringify(mobileState)}`);
  await mobile.locator("body").screenshot({ path: path.join(outRoot, "workbench-mobile.png"), fullPage: true });
  await mobile.close();

  const report = {
    status: "pass",
    scene,
    runtime_mode: "sprite-sequence",
    animations: actions.map((action) => action.id),
    animation_discovery: "pass",
    play_pause_restart: "pass",
    frame_step: "pass",
    scrub: "pass",
    speed: "pass",
    loop: "pass",
    stage_tools: { background: "pass", grid: "pass", bounds: "pass", baseline: "pass", pivot: "pass", zoom: "pass", fullscreen_control: "present" },
    desktop_layout: "pass",
    mobile_layout: "pass",
    review_coverage: "4/4",
    approval: "not_granted_by_test",
    screenshots: ["action-idle.png", "action-walk.png", "action-run.png", "action-attack.png", "workbench-desktop.png", "workbench-mobile.png"],
    action_states: actionStates,
  };
  writeJson(path.join(outRoot, "dogfood-report.json"), report);
  console.log(JSON.stringify(report, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
  fs.rmSync(fixtureRoot, { recursive: true, force: true });
}
