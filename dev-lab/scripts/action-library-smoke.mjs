#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { chromium } from "playwright";

const labRoot = path.resolve(new URL("..", import.meta.url).pathname);
const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), "motionloom-action-library-"));
const publicRoot = path.join(fixtureRoot, "public");
const outRoot = path.resolve(process.env.MOTIONLOOM_ACTION_LIBRARY_OUT || path.join(os.tmpdir(), "motionloom-action-library-output"));
const scene = "action-library-smoke";
const taskId = "devlab-action-library-smoke";
const candidateId = "ac71011b000000000001";
const sceneRoot = path.join(publicRoot, "scenes", scene);

fs.rmSync(outRoot, { recursive: true, force: true });
fs.mkdirSync(sceneRoot, { recursive: true });
fs.mkdirSync(outRoot, { recursive: true });
for (const file of ["index.html", "devlab.js", "action-library.js"]) {
  fs.copyFileSync(path.join(labRoot, "public", file), path.join(publicRoot, file));
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}

function frameSvg(label, phase) {
  const offset = phase ? 20 : -20;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="transparent"/><g transform="translate(${400 + offset} 300)"><rect x="-90" y="-120" width="180" height="180" rx="40" fill="#f4dfb4" stroke="#171b25" stroke-width="12"/><rect x="-62" y="-88" width="124" height="70" rx="18" fill="#071b31"/><rect x="-30" y="-65" width="14" height="30" fill="#08d7ef"/><rect x="18" y="-65" width="14" height="30" fill="#08d7ef"/><rect x="-70" y="65" width="140" height="125" rx="30" fill="#f4dfb4" stroke="#171b25" stroke-width="12"/><rect x="45" y="75" width="45" height="38" rx="12" fill="#ff7a0b" stroke="#171b25" stroke-width="8"/><text x="0" y="145" text-anchor="middle" fill="#171b25" font-family="sans-serif" font-size="20">${label}</text></g></svg>`;
}

const groups = [
  { id: "locomotion", label: "Locomotion", order: 10 },
  { id: "combat", label: "Combat", order: 20 },
  { id: "skills", label: "Skills", order: 30 },
  { id: "reactions", label: "Reactions", order: 40 },
];

const actions = [
  { id: "idle", label: "Idle", group: "locomotion", tags: ["stance", "grounded"], loop: true, required: true },
  { id: "walk", label: "Walk", group: "locomotion", tags: ["movement", "grounded"], loop: true, required: true },
  { id: "run", label: "Run", group: "locomotion", tags: ["movement", "fast"], loop: true, required: true },
  { id: "jump", label: "Jump", group: "locomotion", tags: ["movement", "airborne"], loop: false, required: true },
  { id: "attack", label: "Attack", group: "combat", tags: ["melee", "light"], loop: false, required: true },
  { id: "heavy-attack", label: "Heavy Attack", group: "combat", tags: ["melee", "heavy"], loop: false, required: true },
  { id: "block", label: "Block", group: "combat", tags: ["defense"], loop: true, required: true },
  { id: "parry", label: "Parry", group: "combat", tags: ["defense", "timing"], loop: false, required: true },
  { id: "skill-fireball", label: "Fireball", group: "skills", tags: ["projectile", "magic"], loop: false, required: true },
  { id: "teleport-strike", label: "Teleport Strike", group: "skills", tags: ["mobility", "special"], loop: false, required: true },
  { id: "hurt", label: "Hurt", group: "reactions", tags: ["damage"], loop: false, required: false },
  { id: "victory", label: "Victory", tags: ["emote", "celebration"], loop: true, required: false },
];

const files = [];
for (const action of actions) {
  action.frames = [];
  for (let phase = 0; phase < 2; phase += 1) {
    const relative = `frames/${action.id}-${phase}.svg`;
    fs.mkdirSync(path.dirname(path.join(sceneRoot, relative)), { recursive: true });
    fs.writeFileSync(path.join(sceneRoot, relative), frameSvg(action.label, phase));
    action.frames.push(relative);
    files.push(relative);
  }
}

writeJson(path.join(sceneRoot, "manifest.json"), {
  scene,
  name: "Action Library Smoke",
  description: "Scalable Dev Lab action-library fixture with arbitrary project-defined animation actions.",
  framework: "sprite-sequence",
  category: "character",
  checks: [{ id: "visual", label: "Visual review", detail: "Human-owned review remains separate from action discovery." }],
});
writeJson(path.join(sceneRoot, "motion-spec.json"), {
  framework: "sprite-sequence",
  category: "character",
  duration_s: 0.25,
  fps: 8,
  loop: true,
  context_binding: { context_sha256: "a".repeat(64) },
});
writeJson(path.join(sceneRoot, "devlab-runtime.json"), {
  schema_version: "1.0",
  mode: "sprite-sequence",
  files,
  default_animation: "idle",
  groups,
  animations: actions.map(({ id, label, group, tags, loop, required, frames }) => ({
    id, label, ...(group ? { group } : {}), tags, fps: 8, frames, loop, review_required: required,
  })),
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

const contentTypes = new Map([[".html", "text/html; charset=utf-8"], [".js", "text/javascript; charset=utf-8"], [".json", "application/json; charset=utf-8"], [".svg", "image/svg+xml"]]);
const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const target = path.resolve(publicRoot, relative);
  if (target !== publicRoot && !target.startsWith(`${publicRoot}${path.sep}`)) { response.writeHead(403).end("forbidden"); return; }
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
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => window.__lab?.ready === true && window.__lab?.actionLibrary?.ready === true, null, { timeout: 10000 });

  const initial = await page.evaluate(() => ({
    groups: window.__lab.actionLibrary.listGroups().map((group) => group.id),
    actions: [...document.querySelectorAll(".animation-btn")].map((node) => node.dataset.animation),
    visible: window.__lab.actionLibrary.getState().visible,
    approveDisabled: document.querySelector("#confirm").disabled,
  }));
  if (initial.actions.length !== 12 || initial.visible.length !== 12) throw new Error(`Expected 12 discoverable actions: ${JSON.stringify(initial)}`);
  if (initial.groups.join(",") !== "locomotion,combat,skills,reactions,ungrouped") throw new Error(`Group discovery mismatch: ${JSON.stringify(initial.groups)}`);
  if (!initial.actions.includes("teleport-strike") || !initial.approveDisabled) throw new Error("Arbitrary action discovery or approval gate failed");

  await page.evaluate(() => window.__lab.actionLibrary.setSearch("airborne"));
  let visible = await page.evaluate(() => window.__lab.actionLibrary.getState().visible);
  if (visible.join(",") !== "jump") throw new Error(`Tag search failed: ${JSON.stringify(visible)}`);

  await page.evaluate(() => { window.__lab.actionLibrary.setSearch(""); window.__lab.actionLibrary.setGroup("combat"); });
  visible = await page.evaluate(() => window.__lab.actionLibrary.getState().visible);
  if (visible.join(",") !== "attack,heavy-attack,block,parry") throw new Error(`Combat group filter failed: ${JSON.stringify(visible)}`);

  await page.evaluate(() => { window.__lab.actionLibrary.setGroup("all"); window.__lab.actionLibrary.setFilter("one-shot"); });
  visible = await page.evaluate(() => window.__lab.actionLibrary.getState().visible);
  for (const id of ["jump", "attack", "heavy-attack", "parry", "skill-fireball", "teleport-strike", "hurt"]) {
    if (!visible.includes(id)) throw new Error(`One-shot filter omitted ${id}: ${JSON.stringify(visible)}`);
  }
  if (visible.includes("idle") || visible.includes("walk") || visible.includes("block")) throw new Error(`One-shot filter leaked looping actions: ${JSON.stringify(visible)}`);

  await page.evaluate(async () => { window.__lab.actionLibrary.setFilter("unreviewed"); await window.__lab.selectAnimation("teleport-strike"); });
  await page.waitForTimeout(350);
  visible = await page.evaluate(() => window.__lab.actionLibrary.getState().visible);
  if (!visible.includes("teleport-strike")) throw new Error("Selected action disappeared from unreviewed filter");

  await page.locator("body").screenshot({ path: path.join(outRoot, "action-library-desktop.png"), fullPage: true });
  const report = await page.evaluate(() => ({
    status: "pass",
    action_count: document.querySelectorAll(".animation-btn").length,
    groups: window.__lab.actionLibrary.listGroups().map((group) => group.id),
    selected: window.__lab.getRuntimeState().animation,
    library: window.__lab.actionLibrary.getState(),
    approval: document.querySelector("#confirm").disabled ? "not_granted" : "unexpectedly_available",
  }));
  writeJson(path.join(outRoot, "action-library-report.json"), report);
  console.log(JSON.stringify(report, null, 2));
  await page.close();
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
  fs.rmSync(fixtureRoot, { recursive: true, force: true });
}
