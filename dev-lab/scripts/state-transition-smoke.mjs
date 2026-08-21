#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const labRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), "motionloom-devlab-transition-"));
const publicRoot = path.join(fixtureRoot, "public");
const outRoot = path.resolve(process.env.MOTIONLOOM_TRANSITION_OUT || path.join(os.tmpdir(), "motionloom-devlab-transition-output"));
fs.rmSync(outRoot, { recursive: true, force: true });
fs.mkdirSync(path.join(publicRoot, "scenes"), { recursive: true });
fs.mkdirSync(outRoot, { recursive: true });
for (const file of ["index.html", "devlab.js", "action-library.js", "runtime-bridge.js"]) {
  fs.copyFileSync(path.join(labRoot, "public", file), path.join(publicRoot, file));
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}

function writeCommon(root, scene, taskId, candidateId, runtimeMode, animations, requireAllAnimations) {
  writeJson(path.join(root, "manifest.json"), {
    scene,
    name: `State transition smoke · ${scene}`,
    description: "Deterministic Dev Lab state/transition review fixture.",
    framework: runtimeMode,
    category: "character",
    checks: [{ id: "flow", label: "State flow reads correctly", detail: "Human review remains explicit." }],
  });
  writeJson(path.join(root, "motion-spec.json"), {
    framework: runtimeMode,
    category: "character",
    duration_s: 0.5,
    fps: 8,
    loop: true,
    context_binding: { context_sha256: "a".repeat(64) },
  });
  writeJson(path.join(root, "browser-review.json"), {
    schema_version: "1.0",
    candidate_id: candidateId,
    task_id: taskId,
    scene,
    url: "http://127.0.0.1/",
    status: "prepared",
    context_sha256: "a".repeat(64),
    source_sha256: "b".repeat(64),
    runtime: runtimeMode,
    checkpoints: [0, 50, 100],
    review_artifact: "review.json",
    requires_user_approval: true,
    prepared_at: "2026-08-21T00:00:00Z",
    expires_at: "2099-01-01T00:00:00Z",
    runtime_review: {
      live: true,
      mode: runtimeMode,
      descriptor: "devlab-runtime.json",
      bundle_sha256: "c".repeat(64),
      animations: animations.map((item) => item.id),
      review_policy: { require_all_animations: requireAllAnimations },
    },
  });
}

function frameSvg(label, offset) {
  return `<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><rect width="800" height="600" fill="#11141b"/><g transform="translate(${400 + offset} 300)"><rect x="-70" y="-100" width="140" height="160" rx="28" fill="#f4dfb4" stroke="#171b25" stroke-width="12"/><rect x="-50" y="-72" width="100" height="50" rx="14" fill="#061a31"/><rect x="-28" y="-56" width="12" height="23" fill="#08d7ef"/><rect x="16" y="-56" width="12" height="23" fill="#08d7ef"/><rect x="-92" y="-70" width="35" height="30" rx="10" fill="#ff7a0b"/><rect x="57" y="-70" width="35" height="30" rx="10" fill="#ff7a0b"/><path d="M-35 55 L-48 135 M35 55 L48 135" stroke="#252b38" stroke-width="28"/><path d="M-70 145 H-25 M25 145 H70" stroke="#f4dfb4" stroke-width="28"/></g><text x="30" y="50" fill="#eef1f6" font-family="monospace" font-size="24">${label}</text></svg>`;
}

const spriteScene = "transition-sprite-smoke";
const spriteTask = "transition-sprite-task";
const spriteCandidate = "s".repeat(20);
const spriteRoot = path.join(publicRoot, "scenes", spriteScene);
fs.mkdirSync(spriteRoot, { recursive: true });
const spriteActions = [
  { id: "idle", label: "Idle", loop: true, offset: 0 },
  { id: "run", label: "Run", loop: true, offset: 18 },
  { id: "attack", label: "Attack", loop: false, offset: 38 },
  { id: "hurt", label: "Hurt", loop: false, offset: -20 },
];
const spriteFiles = ["devlab-state-machine.json"];
for (const action of spriteActions) {
  action.frames = [];
  for (let i = 0; i < 2; i += 1) {
    const relative = `frames/${action.id}-${i}.svg`;
    const target = path.join(spriteRoot, relative);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, frameSvg(action.label, action.offset + i * 4));
    action.frames.push(relative);
    spriteFiles.push(relative);
  }
}
writeCommon(spriteRoot, spriteScene, spriteTask, spriteCandidate, "sprite-sequence", spriteActions, true);
writeJson(path.join(spriteRoot, "devlab-runtime.json"), {
  schema_version: "1.0",
  mode: "sprite-sequence",
  files: spriteFiles,
  default_animation: "idle",
  animations: spriteActions.map(({ id, label, loop, frames }) => ({ id, label, fps: 8, loop, frames, review_required: true })),
  controls: { play: true, pause: true, restart: true, seek: true, step: true, speed: true, loop: true },
  viewport: { canvas_width: 800, canvas_height: 600, pixel_art: false, baseline_y: 470, pivot: { x: 400, y: 470 }, background: "dark" },
  review_policy: { require_all_animations: true },
});
writeJson(path.join(spriteRoot, "devlab-state-machine.json"), {
  schema_version: "1.0",
  initial_state: "idle",
  states: spriteActions.map((item) => ({ id: item.id, label: item.label, animation: item.id })),
  transitions: [
    { id: "start-run", label: "Start run", from: "idle", to: "run", trigger: "move", mode: "select-animation", auto_play: false, review_required: true },
    { id: "attack", label: "Attack", from: "run", to: "attack", trigger: "attack", mode: "select-animation", auto_play: false, review_required: true },
    { id: "take-hit", label: "Take hit", from: "attack", to: "hurt", trigger: "hit", mode: "select-animation", auto_play: false, review_required: true },
    { id: "recover", label: "Recover", from: "hurt", to: "idle", trigger: "recover", mode: "select-animation", auto_play: false, review_required: true },
    { id: "stop-run", label: "Stop run", from: "run", to: "idle", trigger: "stop", mode: "select-animation", auto_play: false, review_required: false },
  ],
  sequences: [
    { id: "combat-cycle", label: "Combat cycle", review_required: true, steps: [
      { transition: "start-run", wait_ms: 5 },
      { transition: "attack", wait_ms: 5 },
      { transition: "take-hit", wait_ms: 5 },
      { transition: "recover", wait_ms: 5 },
    ] },
  ],
  review_policy: { require_all_transitions: true, require_all_sequences: true },
});

const iframeScene = "transition-iframe-smoke";
const iframeTask = "transition-iframe-task";
const iframeCandidate = "i".repeat(20);
const iframeRoot = path.join(publicRoot, "scenes", iframeScene);
fs.mkdirSync(iframeRoot, { recursive: true });
const iframeActions = [
  { id: "idle", label: "Idle", loop: true },
  { id: "run", label: "Run", loop: true },
  { id: "attack", label: "Attack", loop: false },
];
writeCommon(iframeRoot, iframeScene, iframeTask, iframeCandidate, "iframe", iframeActions, false);
const iframeHtml = `<!doctype html><html><body style="margin:0;background:#10131a;display:grid;place-items:center;min-height:100vh"><div id="actor" style="width:90px;height:90px;border-radius:18px;background:#f5a524"></div><script src="/runtime-bridge.js"></script><script>
let state='idle',animation='idle',progress=0,playing=false; const actor=document.getElementById('actor');
function render(){actor.style.transform='translateX('+(state==='run'?90:state==='attack'?150:0)+'px) rotate('+(state==='attack'?25:0)+'deg)'}
const allowed={"start-run":["idle","run"],"attack":["run","attack"],"recover":["attack","idle"]};
MotionLoomRuntimeBridge.attach({runtime:'transition-smoke@1',framework:'custom',animations:[{id:'idle',label:'Idle',loop:true},{id:'run',label:'Run',loop:true},{id:'attack',label:'Attack',loop:false}],listAnimations(){return this.animations},selectAnimation(id){state=id;animation=id;progress=0;render()},triggerTransition(request){const edge=allowed[request.id];if(!edge||edge[0]!==state||edge[1]!==request.to)throw new Error('illegal transition '+request.id);state=request.to;animation=request.to;progress=0;render();return {state,animation}},play(){playing=true},pause(){playing=false},restart(){progress=0},seek(p){progress=p},stepFrames(d){progress=Math.max(0,Math.min(1,progress+d/12))},setSpeed(){},setLoop(){},getState(){return {state,animation,progress,currentTime:progress,duration:1,frame:Math.round(progress*11),totalFrames:12,playing}}});render();
</script></body></html>`;
fs.writeFileSync(path.join(iframeRoot, "runtime.html"), iframeHtml);
writeJson(path.join(iframeRoot, "devlab-runtime.json"), {
  schema_version: "1.0",
  mode: "iframe",
  files: ["runtime.html", "devlab-state-machine.json"],
  entrypoint: "runtime.html",
  default_animation: "idle",
  animations: iframeActions.map((item) => ({ ...item, review_required: true })),
  controls: { play: true, pause: true, restart: true, seek: true, step: true, speed: true, loop: true },
  viewport: { canvas_width: 800, canvas_height: 600, pixel_art: false, background: "dark" },
  review_policy: { require_all_animations: false },
});
writeJson(path.join(iframeRoot, "devlab-state-machine.json"), {
  schema_version: "1.0",
  initial_state: "idle",
  states: iframeActions.map((item) => ({ id: item.id, label: item.label, animation: item.id })),
  transitions: [
    { id: "start-run", label: "Start run", from: "idle", to: "run", trigger: "move", mode: "runtime-trigger", review_required: true },
    { id: "attack", label: "Attack", from: "run", to: "attack", trigger: "attack", mode: "runtime-trigger", review_required: true },
    { id: "recover", label: "Recover", from: "attack", to: "idle", trigger: "recover", mode: "runtime-trigger", review_required: true },
  ],
  review_policy: { require_all_transitions: true, require_all_sequences: false },
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
  browser = await chromium.launch({ headless: true });

  async function open(scene, taskId, candidateId) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const url = `http://127.0.0.1:${port}/?scene=${scene}&task_id=${taskId}&candidate_id=${candidateId}`;
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => window.__lab?.ready === true && window.__lab?.stateMachine?.ready === true, null, { timeout: 10000 });
    return page;
  }

  const sprite = await open(spriteScene, spriteTask, spriteCandidate);
  const initial = await sprite.evaluate(() => ({ machine: window.__lab.stateMachine.getState(), runtime: window.__lab.getRuntimeState() }));
  if (initial.machine.currentState !== "idle" || initial.machine.coverage.complete) throw new Error(`sprite state machine initial state is wrong: ${JSON.stringify(initial)}`);
  const outgoing = await sprite.locator(".transition-btn").evaluateAll((nodes) => nodes.map((node) => node.dataset.transition));
  if (outgoing.join(",") !== "start-run") throw new Error(`unexpected idle transitions: ${JSON.stringify(outgoing)}`);

  await sprite.evaluate(async () => window.__lab.stateMachine.triggerTransition("start-run"));
  const runState = await sprite.evaluate(() => window.__lab.stateMachine.getState());
  if (runState.currentState !== "run" || !runState.transitionsInspected.includes("start-run")) throw new Error(`sprite transition did not reach run: ${JSON.stringify(runState)}`);
  await sprite.evaluate(async () => window.__lab.stateMachine.resetState());
  await sprite.evaluate(async () => window.__lab.stateMachine.runSequence("combat-cycle"));
  const spriteFinal = await sprite.evaluate(() => ({ machine: window.__lab.stateMachine.getState(), review: window.__lab.getReview(), approveDisabled: document.querySelector("#confirm").disabled, gated: document.querySelector("#confirm").classList.contains("state-machine-gated") }));
  if (spriteFinal.machine.currentState !== "idle" || !spriteFinal.machine.coverage.complete) throw new Error(`sprite sequence coverage failed: ${JSON.stringify(spriteFinal)}`);
  if (!spriteFinal.review.transitions_inspected?.includes("recover") || !spriteFinal.review.sequences_inspected?.includes("combat-cycle")) throw new Error(`transition evidence was not persisted: ${JSON.stringify(spriteFinal.review)}`);
  if (spriteFinal.gated) throw new Error("state-machine gate remained active after required coverage");
  await sprite.check("[data-check='flow']");
  await sprite.waitForTimeout(30);
  const approvalReady = await sprite.evaluate(() => ({ disabled: document.querySelector("#confirm").disabled, decision: window.__lab.getReview().decision }));
  if (approvalReady.disabled || approvalReady.decision === "approved") throw new Error(`approval trust boundary failed: ${JSON.stringify(approvalReady)}`);
  await sprite.locator("#state-machine-panel").screenshot({ path: path.join(outRoot, "sprite-state-machine.png") });
  await sprite.close();

  const iframe = await open(iframeScene, iframeTask, iframeCandidate);
  const iframeCaps = await iframe.evaluate(() => window.__lab.stateMachine.getState().runtimeCapabilities);
  if (!iframeCaps.transition || !iframeCaps.state) throw new Error(`iframe transition capability missing: ${JSON.stringify(iframeCaps)}`);
  for (const transition of ["start-run", "attack", "recover"]) {
    await iframe.evaluate(async (id) => window.__lab.stateMachine.triggerTransition(id), transition);
    await iframe.waitForTimeout(320);
  }
  const iframeFinal = await iframe.evaluate(() => ({ machine: window.__lab.stateMachine.getState(), review: window.__lab.getReview() }));
  if (iframeFinal.machine.currentState !== "idle" || !iframeFinal.machine.coverage.complete) throw new Error(`iframe runtime-trigger flow failed: ${JSON.stringify(iframeFinal)}`);
  if (iframeFinal.machine.history.some((item) => item.mode !== "runtime-trigger")) throw new Error(`iframe transition was silently downgraded: ${JSON.stringify(iframeFinal.machine.history)}`);
  await iframe.locator("#state-machine-panel").screenshot({ path: path.join(outRoot, "iframe-state-machine.png") });
  await iframe.close();

  const report = {
    status: "pass",
    sprite: { mode: "select-animation", final_state: spriteFinal.machine.currentState, coverage: spriteFinal.machine.coverage },
    iframe: { mode: "runtime-trigger", final_state: iframeFinal.machine.currentState, coverage: iframeFinal.machine.coverage },
    state_machine_file: "hash-bound-by-runtime-files",
    approval: "not_granted_by_test",
  };
  writeJson(path.join(outRoot, "state-transition-report.json"), report);
  console.log(JSON.stringify(report, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
  fs.rmSync(fixtureRoot, { recursive: true, force: true });
}
