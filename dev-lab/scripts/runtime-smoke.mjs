#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const labRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(labRoot, "..");
const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), "motionloom-devlab-runtime-"));
const publicRoot = path.join(fixtureRoot, "public");
fs.mkdirSync(path.join(publicRoot, "scenes"), { recursive: true });
for (const file of ["index.html", "devlab.js", "runtime-bridge.js"]) {
  fs.copyFileSync(path.join(labRoot, "public", file), path.join(publicRoot, file));
}

const sourceFrames = [0, 50, 100].map((pct) => path.join(repositoryRoot, "src", "output", "browser-review-smoke", "snapshot", `frame-${String(pct).padStart(2, "0")}.png`));
if (sourceFrames.some((file) => !fs.existsSync(file))) throw new Error("browser-review-smoke snapshot fixture is missing");

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}

function commonScene(scene, candidateId) {
  const root = path.join(publicRoot, "scenes", scene);
  fs.mkdirSync(root, { recursive: true });
  writeJson(path.join(root, "manifest.json"), {
    scene, name: `Runtime smoke ${scene}`, description: "Interactive Dev Lab smoke fixture", framework: "test-runtime", category: "character",
    checks: [{ id: "visual", label: "Visual review", detail: "User-owned review decision" }]
  });
  writeJson(path.join(root, "motion-spec.json"), { framework: "test-runtime", category: "character", duration_s: 1, fps: 12, loop: true, context_binding: { context_sha256: "1".repeat(64) } });
  writeJson(path.join(root, "browser-review.json"), {
    schema_version: "1.0", candidate_id: candidateId, task_id: `${scene}-task`, scene, url: "http://127.0.0.1/", status: "prepared",
    context_sha256: "1".repeat(64), source_sha256: "2".repeat(64), runtime: "test-runtime", checkpoints: [0, 50, 100],
    review_artifact: "review.json", requires_user_approval: true, prepared_at: "2026-01-01T00:00:00Z", expires_at: "2099-01-01T00:00:00Z"
  });
  return root;
}

const spriteScene = "sprite-live-smoke";
const spriteCandidate = "a".repeat(20);
const spriteRoot = commonScene(spriteScene, spriteCandidate);
const spriteFiles = [];
for (const [action, mapping] of [["idle", [0, 50]], ["attack", [50, 100, 0]]]) {
  for (const [index, pct] of mapping.entries()) {
    const name = `frames/${action}-${index}.png`;
    const target = path.join(spriteRoot, name);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(sourceFrames[[0, 50, 100].indexOf(pct)], target);
    spriteFiles.push(name);
  }
}
const spriteDescriptor = {
  schema_version: "1.0", mode: "sprite-sequence", files: spriteFiles, default_animation: "idle",
  animations: [
    { id: "idle", label: "Idle", fps: 8, frames: ["frames/idle-0.png", "frames/idle-1.png"], loop: true, review_required: true },
    { id: "attack", label: "Attack", fps: 12, frames: ["frames/attack-0.png", "frames/attack-1.png", "frames/attack-2.png"], loop: false, review_required: true }
  ],
  controls: { play: true, pause: true, restart: true, seek: true, step: true, speed: true, loop: true },
  viewport: { canvas_width: 800, canvas_height: 600, pixel_art: true, baseline_y: 500, pivot: { x: 400, y: 500 }, background: "checker" },
  review_policy: { require_all_animations: true }
};
writeJson(path.join(spriteRoot, "devlab-runtime.json"), spriteDescriptor);
const spriteCandidatePath = path.join(spriteRoot, "browser-review.json");
const spriteCandidateDoc = JSON.parse(fs.readFileSync(spriteCandidatePath, "utf8"));
spriteCandidateDoc.runtime_review = { live: true, mode: "sprite-sequence", descriptor: "devlab-runtime.json", bundle_sha256: "3".repeat(64), animations: ["idle", "attack"], review_policy: { require_all_animations: true } };
writeJson(spriteCandidatePath, spriteCandidateDoc);

const iframeScene = "iframe-live-smoke";
const iframeCandidate = "b".repeat(20);
const iframeRoot = commonScene(iframeScene, iframeCandidate);
const iframeHtml = `<!doctype html><html><body style="margin:0;background:transparent;display:grid;place-items:center;min-height:100vh"><div id="box" style="width:80px;height:80px;background:#f5a524"></div><script src="/runtime-bridge.js"></script><script>
let animation='idle', progress=0, playing=false, speed=1, loop=true; const box=document.getElementById('box'); let raf=0,last=0;
function render(){ box.style.transform='translateX('+(progress*160-80)+'px) rotate('+(progress*30)+'deg)'; }
function tick(t){ if(!playing)return; if(!last)last=t; progress+=(t-last)/1000*speed; last=t; if(progress>=1){ if(loop)progress%=1; else {progress=1;playing=false;} } render(); if(playing)raf=requestAnimationFrame(tick); }
MotionLoomRuntimeBridge.attach({runtime:'smoke@1',framework:'custom',animations:[{id:'idle',label:'Idle',loop:true},{id:'attack',label:'Attack',loop:false}],listAnimations(){return this.animations},selectAnimation(id){animation=id;progress=0;render()},play(){playing=true;last=0;raf=requestAnimationFrame(tick)},pause(){playing=false;cancelAnimationFrame(raf)},restart(){playing=false;progress=0;render()},seek(p){progress=Math.max(0,Math.min(1,p));render()},stepFrames(d){progress=Math.max(0,Math.min(1,progress+d/12));render()},setSpeed(v){speed=v},setLoop(v){loop=v},getState(){return {animation,progress,currentTime:progress,duration:1,frame:Math.round(progress*11),totalFrames:12,playing,speed,loop}}}); render();
</script></body></html>`;
fs.writeFileSync(path.join(iframeRoot, "runtime.html"), iframeHtml);
writeJson(path.join(iframeRoot, "devlab-runtime.json"), {
  schema_version: "1.0", mode: "iframe", files: ["runtime.html"], entrypoint: "runtime.html", default_animation: "idle",
  animations: [{ id: "idle", label: "Idle", loop: true, review_required: true }, { id: "attack", label: "Attack", loop: false, review_required: true }],
  controls: { play: true, pause: true, restart: true, seek: true, step: true, speed: true, loop: true },
  viewport: { canvas_width: 800, canvas_height: 600, pixel_art: false, background: "dark" }, review_policy: { require_all_animations: true }
});
const iframeCandidatePath = path.join(iframeRoot, "browser-review.json");
const iframeCandidateDoc = JSON.parse(fs.readFileSync(iframeCandidatePath, "utf8"));
iframeCandidateDoc.runtime_review = { live: true, mode: "iframe", descriptor: "devlab-runtime.json", bundle_sha256: "4".repeat(64), animations: ["idle", "attack"], review_policy: { require_all_animations: true } };
writeJson(iframeCandidatePath, iframeCandidateDoc);

const contentTypes = new Map([[".html", "text/html; charset=utf-8"], [".js", "text/javascript; charset=utf-8"], [".json", "application/json; charset=utf-8"], [".png", "image/png"]]);
const server = http.createServer((request, response) => {
  const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
  const relative = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const target = path.resolve(publicRoot, relative);
  if (target !== publicRoot && !target.startsWith(`${publicRoot}${path.sep}`)) { response.writeHead(403).end("forbidden"); return; }
  try { response.writeHead(200, { "Content-Type": contentTypes.get(path.extname(target)) || "application/octet-stream", "Cache-Control": "no-store" }); response.end(fs.readFileSync(target)); }
  catch { response.writeHead(404).end("not found"); }
});

let browser;
try {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  browser = await chromium.launch({ headless: true });

  async function open(scene, taskId, candidateId) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const url = `http://127.0.0.1:${port}/?scene=${scene}&task_id=${taskId}&candidate_id=${candidateId}`;
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForFunction(() => window.__lab?.ready === true, null, { timeout: 10000 });
    return page;
  }

  const sprite = await open(spriteScene, `${spriteScene}-task`, spriteCandidate);
  const spriteInitial = await sprite.evaluate(() => ({ mode: window.__lab.mode, state: window.__lab.getRuntimeState(), actions: [...document.querySelectorAll('.animation-btn')].map((node) => node.dataset.animation), approveDisabled: document.querySelector('#confirm').disabled }));
  if (spriteInitial.mode !== "live-runtime" || spriteInitial.actions.join(",") !== "idle,attack" || !spriteInitial.approveDisabled) throw new Error(`sprite runtime did not initialize correctly: ${JSON.stringify(spriteInitial)}`);
  await sprite.evaluate(async () => { await window.__lab.selectAnimation('attack'); await window.__lab.seek(0.5); await window.__lab.setSpeed(2); await window.__lab.setLoop(false); await window.__lab.play(); });
  await sprite.waitForTimeout(80);
  await sprite.evaluate(async () => window.__lab.pause());
  const spriteState = await sprite.evaluate(() => ({ state: window.__lab.getRuntimeState(), review: window.__lab.getReview(), visited: [...document.querySelectorAll('.animation-btn.visited')].map((node) => node.dataset.animation) }));
  if (spriteState.state.animation !== "attack" || spriteState.state.speed !== 2 || spriteState.state.loop !== false || !spriteState.visited.includes("attack")) throw new Error(`sprite controls failed: ${JSON.stringify(spriteState)}`);
  await sprite.close();

  const iframe = await open(iframeScene, `${iframeScene}-task`, iframeCandidate);
  await iframe.evaluate(async () => { await window.__lab.selectAnimation('attack'); await window.__lab.seek(0.5); await window.__lab.setSpeed(2); await window.__lab.setLoop(false); await window.__lab.play(); });
  await iframe.waitForTimeout(80);
  await iframe.evaluate(async () => window.__lab.pause());
  const iframeState = await iframe.evaluate(() => window.__lab.getRuntimeState());
  if (iframeState.animation !== "attack" || iframeState.speed !== 2 || iframeState.loop !== false) throw new Error(`iframe controls failed: ${JSON.stringify(iframeState)}`);
  await iframe.close();

  console.log(JSON.stringify({ status: "pass", sprite_sequence: "interactive", iframe_bridge: "interactive", approval: "user_only" }, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
  fs.rmSync(fixtureRoot, { recursive: true, force: true });
}
