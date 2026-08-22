const params = new URLSearchParams(location.search);
const scene = params.get("scene");
const taskId = params.get("task_id") || "unbound";
const candidateId = params.get("candidate_id");
const allowedStatuses = new Set(["prepared", "opened"]);
const $ = (id) => document.getElementById(id);

let manifest;
let spec;
let candidate;
let runtimeDescriptor = null;
let actionSeparation = null;
let review;
let driver;
let currentAnimationId = null;
let zoom = 1;
let pollTimer = null;
const inspectedAnimations = new Set();
const runtimeUi = { playing: false, loop: false, speed: 1, progress: 0, state: {} };

function safeSceneBase() {
  if (!scene || !/^[A-Za-z0-9._-]+$/.test(scene)) throw new Error("Scene name is missing or unsafe");
  const expectedPath = `/scenes/${encodeURIComponent(scene)}`;
  const raw = params.get("artifact_base");
  if (!raw) return expectedPath;
  const url = new URL(raw, location.href);
  if (url.origin !== location.origin) throw new Error("Cross-origin artifact_base is not allowed");
  if (url.search || url.hash) throw new Error("artifact_base must not include query or fragment");
  const decoded = decodeURIComponent(url.pathname).replace(/\/+$/, "");
  if (decoded !== `/scenes/${scene}`) throw new Error("artifact_base does not match the selected scene");
  return url.pathname.replace(/\/+$/, "");
}

const base = safeSceneBase();

function safeRelativePath(value, label = "path") {
  if (typeof value !== "string" || !value || value.startsWith("/") || value.includes("\\")) {
    throw new Error(`${label} must be a scene-relative path`);
  }
  const parts = value.split("/");
  if (parts.some((part) => part === "" || part === "." || part === "..")) {
    throw new Error(`${label} contains unsafe path segments`);
  }
  return value;
}

function sceneUrl(relative) {
  return `${base}/${safeRelativePath(relative)}`;
}

function clamp(value, min = 0, max = 1) {
  return Math.max(min, Math.min(max, Number(value) || 0));
}

function formatTime(seconds) {
  const value = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(value / 60);
  const secs = Math.floor(value % 60);
  const millis = Math.floor((value - Math.floor(value)) * 1000);
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}.${String(millis).padStart(3, "0")}`;
}

async function fetchJson(url, { optional = false } = {}) {
  const response = await fetch(url, { cache: "no-store" });
  if (optional && response.status === 404) return null;
  if (!response.ok) throw new Error(`Could not load ${url} (${response.status})`);
  return response.json();
}

function validateCandidate() {
  if (candidate.candidate_id !== candidateId) throw new Error("Candidate identity mismatch; refusing to review a different candidate");
  if (candidate.task_id !== taskId) throw new Error("Task identity mismatch; refusing unbound review");
  if (candidate.scene !== scene) throw new Error("Scene identity mismatch; refusing mixed evidence");
  if (!allowedStatuses.has(candidate.status)) throw new Error(`Candidate status is not reviewable: ${candidate.status || "missing"}`);
  const expiresAt = Date.parse(candidate.expires_at);
  if (!Number.isFinite(expiresAt)) throw new Error("Candidate expiry is missing or invalid");
  if (Date.now() > expiresAt) throw new Error("Candidate has expired; prepare a new browser-review URL");
}

function validateRuntimeDescriptor(value) {
  if (!value) return null;
  if (candidate.runtime_review?.live !== true) throw new Error("Live runtime descriptor is not bound to this browser-review candidate");
  if (value.schema_version !== "1.0") throw new Error("Unsupported devlab-runtime schema version");
  if (!new Set(["sprite-sequence", "iframe"]).has(value.mode)) throw new Error("Unsupported Dev Lab runtime mode");
  if (!Array.isArray(value.files) || value.files.length === 0) throw new Error("Live runtime descriptor requires declared files");
  const files = new Set(value.files.map((item) => safeRelativePath(item, "runtime file")));
  if (files.size !== value.files.length) throw new Error("Live runtime descriptor contains duplicate files");
  if (!Array.isArray(value.animations) || value.animations.length === 0) throw new Error("Live runtime descriptor requires at least one animation");
  const animationIds = new Set();
  for (const animation of value.animations) {
    const id = animation?.id;
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(id || "")) throw new Error("Live runtime animation id is invalid");
    if (animationIds.has(id)) throw new Error(`Duplicate live runtime animation id: ${id}`);
    animationIds.add(id);
    if (value.mode === "sprite-sequence") {
      if (!Array.isArray(animation.frames) || animation.frames.length === 0) throw new Error(`Sprite animation ${id} has no frames`);
      if (!(Number(animation.fps) > 0)) throw new Error(`Sprite animation ${id} requires a positive fps`);
      for (const frame of animation.frames) {
        const path = safeRelativePath(frame, `frame for ${id}`);
        if (!files.has(path)) throw new Error(`Frame ${path} is not declared in runtime files`);
      }
    }
  }
  if (!animationIds.has(value.default_animation)) throw new Error("default_animation does not exist in live runtime animations");
  if (value.mode === "iframe") {
    const entrypoint = safeRelativePath(value.entrypoint, "runtime entrypoint");
    if (!files.has(entrypoint)) throw new Error("Iframe entrypoint is not declared in runtime files");
  }
  const candidateRuntime = candidate.runtime_review;
  if (candidateRuntime?.live === true) {
    if (candidateRuntime.descriptor !== "devlab-runtime.json") throw new Error("Candidate runtime descriptor binding is unexpected");
    if (candidateRuntime.mode && candidateRuntime.mode !== value.mode) throw new Error("Candidate runtime mode does not match descriptor");
    const boundIds = Array.isArray(candidateRuntime.animations) ? candidateRuntime.animations : [];
    if (boundIds.length && boundIds.join("\0") !== value.animations.map((item) => item.id).join("\0")) {
      throw new Error("Candidate runtime animation set does not match descriptor");
    }
  }
  return value;
}

function validateActionSeparation(value) {
  if (!value) return null;
  if (typeof value !== "object") throw new Error("Action-separation evidence must be an object");
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/.test(value.action_id || "")) throw new Error("Action-separation evidence requires a safe action_id");
  if (!new Set(["pass", "quarantined"]).has(value.status)) throw new Error("Action-separation evidence has an invalid status");
  if (!Number.isInteger(value.frame_count) || value.frame_count < 1) throw new Error("Action-separation evidence requires a positive frame_count");
  if (!Number.isInteger(value.passing_frame_count) || value.passing_frame_count < 0 || value.passing_frame_count > value.frame_count) throw new Error("Action-separation passing_frame_count is invalid");
  if (!Array.isArray(value.forbidden_action_ids)) throw new Error("Action-separation evidence requires forbidden_action_ids");
  return value;
}

function controlEnabled(name, capability = true) {
  if (!runtimeDescriptor) return false;
  return runtimeDescriptor.controls?.[name] !== false && capability !== false;
}

class SnapshotDriver {
  constructor() {
    this.mode = "captured-evidence";
    this.frames = Array.isArray(candidate.checkpoints) && candidate.checkpoints.length ? candidate.checkpoints : [0, 50, 100];
    this.currentProgress = 0;
    this.animation = { id: "captured-evidence", label: "Captured evidence", fps: Number(spec.fps || 0), loop: false, review_required: true };
  }
  listAnimations() { return [this.animation]; }
  async selectAnimation() { currentAnimationId = this.animation.id; return this.getState(); }
  nearest(percent) { return this.frames.reduce((best, frame) => Math.abs(frame - percent) < Math.abs(best - percent) ? frame : best, this.frames[0]); }
  async seek(progress) {
    this.currentProgress = clamp(progress);
    const checkpoint = this.nearest(this.currentProgress * 100);
    $("frame").src = `${base}/snapshot/frame-${String(checkpoint).padStart(2, "0")}.png`;
    $("frame").hidden = false;
    $("runtime-frame").hidden = true;
    $("empty").hidden = true;
    return this.getState();
  }
  async pause() { return this.getState(); }
  getState() {
    const duration = Number(spec.duration_s || 0);
    const totalFrames = Number(spec.total_frames || Math.round(duration * Number(spec.fps || 0))) || 0;
    return {
      mode: this.mode,
      playing: false,
      progress: this.currentProgress,
      currentTime: duration * this.currentProgress,
      duration,
      frame: totalFrames ? Math.round((totalFrames - 1) * this.currentProgress) : null,
      totalFrames: totalFrames || null,
      animation: this.animation.id,
      evidenceOnly: true
    };
  }
}

class SpriteSequenceDriver {
  constructor(descriptor, onUpdate) {
    this.mode = "live-runtime";
    this.descriptor = descriptor;
    this.animations = descriptor.animations;
    this.onUpdate = onUpdate;
    this.animation = this.animations.find((item) => item.id === descriptor.default_animation) || this.animations[0];
    this.frameIndex = 0;
    this.playing = false;
    this.speed = 1;
    this.loop = Boolean(this.animation.loop);
    this.raf = null;
    this.lastTimestamp = null;
    $("frame").classList.toggle("pixelated", descriptor.viewport?.pixel_art === true);
  }
  listAnimations() { return this.animations; }
  async selectAnimation(id) {
    const next = this.animations.find((item) => item.id === id);
    if (!next) throw new Error(`Unknown animation: ${id}`);
    this.pause();
    this.animation = next;
    this.frameIndex = 0;
    this.loop = Boolean(next.loop);
    this.render();
    return this.getState();
  }
  duration() { return Number(this.animation.duration_s) || this.animation.frames.length / Number(this.animation.fps); }
  render() {
    const frames = this.animation.frames;
    this.frameIndex = Math.max(0, Math.min(frames.length - 1, this.frameIndex));
    const displayIndex = Math.max(0, Math.min(frames.length - 1, Math.floor(this.frameIndex)));
    $("frame").src = sceneUrl(frames[displayIndex]);
    $("frame").hidden = false;
    $("runtime-frame").hidden = true;
    $("empty").hidden = true;
    this.onUpdate?.(this.getState());
  }
  async seek(progress) {
    const p = clamp(progress);
    this.frameIndex = Math.round(p * Math.max(0, this.animation.frames.length - 1));
    this.render();
    return this.getState();
  }
  async play() {
    if (this.playing) return this.getState();
    this.playing = true;
    this.lastTimestamp = null;
    const tick = (timestamp) => {
      if (!this.playing) return;
      if (this.lastTimestamp == null) this.lastTimestamp = timestamp;
      const elapsed = Math.max(0, timestamp - this.lastTimestamp) / 1000;
      this.lastTimestamp = timestamp;
      const frameAdvance = elapsed * Number(this.animation.fps) * this.speed;
      this.frameIndex += frameAdvance;
      const count = this.animation.frames.length;
      if (this.frameIndex >= count) {
        if (this.loop) this.frameIndex %= count;
        else { this.frameIndex = count - 1; this.playing = false; }
      }
      this.render();
      if (this.playing) this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
    this.onUpdate?.(this.getState());
    return this.getState();
  }
  async pause() {
    this.playing = false;
    this.lastTimestamp = null;
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = null;
    this.onUpdate?.(this.getState());
    return this.getState();
  }
  async restart() { await this.pause(); this.frameIndex = 0; this.render(); return this.getState(); }
  async stepFrames(delta) { await this.pause(); this.frameIndex += Number(delta || 0); this.render(); return this.getState(); }
  async setSpeed(rate) { this.speed = Math.max(0.05, Number(rate) || 1); this.onUpdate?.(this.getState()); return this.getState(); }
  async setLoop(enabled) { this.loop = Boolean(enabled); this.onUpdate?.(this.getState()); return this.getState(); }
  getState() {
    const frames = this.animation.frames.length;
    const duration = this.duration();
    const frame = Math.max(0, Math.min(frames - 1, Math.floor(this.frameIndex)));
    const progress = frames <= 1 ? 0 : frame / (frames - 1);
    return {
      mode: this.mode,
      runtime: "sprite-sequence",
      animation: this.animation.id,
      playing: this.playing,
      progress,
      frame,
      totalFrames: frames,
      currentTime: frame / Number(this.animation.fps),
      duration,
      fps: Number(this.animation.fps),
      speed: this.speed,
      loop: this.loop
    };
  }
  dispose() { this.pause(); }
}

class IframeDriver {
  constructor(descriptor, onUpdate) {
    this.mode = "live-runtime";
    this.descriptor = descriptor;
    this.onUpdate = onUpdate;
    this.pending = new Map();
    this.counter = 0;
    this.capabilities = {};
    this.animations = descriptor.animations;
    this.animation = descriptor.default_animation;
    this.state = {};
    this.listener = (event) => this.onMessage(event);
    window.addEventListener("message", this.listener);
  }
  onMessage(event) {
    if (event.source !== $("runtime-frame").contentWindow) return;
    const data = event.data;
    if (!data || data.source !== "motionloom-runtime") return;
    if (data.event === "attached") return;
    const pending = this.pending.get(data.id);
    if (!pending) return;
    this.pending.delete(data.id);
    clearTimeout(pending.timer);
    if (data.ok) pending.resolve(data.result);
    else pending.reject(new Error(data.error || "Runtime bridge command failed"));
  }
  rpc(command, payload = {}, timeout = 3500) {
    const frameWindow = $("runtime-frame").contentWindow;
    if (!frameWindow) return Promise.reject(new Error("Runtime iframe is not available"));
    const id = `ml-${Date.now()}-${++this.counter}`;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error(`Runtime command timed out: ${command}`)); }, timeout);
      this.pending.set(id, { resolve, reject, timer });
      frameWindow.postMessage({ source: "motionloom-devlab", id, command, payload }, "*");
    });
  }
  async mount() {
    const frame = $("runtime-frame");
    frame.hidden = false;
    $("frame").hidden = true;
    $("empty").hidden = true;
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("Live runtime entrypoint did not load")), 6000);
      frame.addEventListener("load", () => { clearTimeout(timer); resolve(); }, { once: true });
      frame.src = sceneUrl(this.descriptor.entrypoint);
    });
    let handshake;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      try { handshake = await this.rpc("handshake", {}, 800); break; }
      catch { await new Promise((resolve) => setTimeout(resolve, 100)); }
    }
    if (!handshake?.ready) throw new Error("Live runtime bridge did not become ready");
    this.capabilities = handshake.capabilities || {};
    if (Array.isArray(handshake.animations) && handshake.animations.length) {
      const allowed = new Set(this.descriptor.animations.map((item) => item.id));
      const runtimeIds = handshake.animations.map((item) => item.id).filter((id) => allowed.has(id));
      if (runtimeIds.length) this.animations = this.descriptor.animations.filter((item) => runtimeIds.includes(item.id));
    }
    this.state = handshake.state || {};
    await this.selectAnimation(this.descriptor.default_animation);
    this.onUpdate?.(this.getState());
    return this.getState();
  }
  listAnimations() { return this.animations; }
  async selectAnimation(id) {
    if (!this.animations.find((item) => item.id === id)) throw new Error(`Unknown animation: ${id}`);
    if (this.capabilities.selectAnimation) await this.rpc("selectAnimation", { id });
    this.animation = id;
    await this.refresh();
    return this.getState();
  }
  async play() { if (!this.capabilities.play) throw new Error("Runtime does not support play"); await this.rpc("play"); return this.refresh(); }
  async pause() { if (!this.capabilities.pause) throw new Error("Runtime does not support pause"); await this.rpc("pause"); return this.refresh(); }
  async restart() { if (!this.capabilities.restart) throw new Error("Runtime does not support restart"); await this.rpc("restart"); return this.refresh(); }
  async seek(progress) { if (!this.capabilities.seek) throw new Error("Runtime does not support seek"); await this.rpc("seek", { progress: clamp(progress) }); return this.refresh(); }
  async stepFrames(delta) { if (!this.capabilities.step) throw new Error("Runtime does not support frame stepping"); await this.rpc("stepFrames", { delta }); return this.refresh(); }
  async setSpeed(rate) { if (!this.capabilities.speed) throw new Error("Runtime does not support speed control"); await this.rpc("setSpeed", { rate }); return this.refresh(); }
  async setLoop(enabled) { if (!this.capabilities.loop) throw new Error("Runtime does not support loop control"); await this.rpc("setLoop", { enabled }); return this.refresh(); }
  async refresh() {
    if (this.capabilities.state) {
      try { this.state = await this.rpc("getState", {}, 1200) || {}; } catch { /* keep last known state */ }
    }
    this.onUpdate?.(this.getState());
    return this.getState();
  }
  getState() { return { mode: this.mode, runtime: "iframe", animation: this.animation, ...this.state }; }
  dispose() {
    window.removeEventListener("message", this.listener);
    for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(new Error("Runtime driver disposed")); }
    this.pending.clear();
  }
}

function currentChecks() {
  return [...document.querySelectorAll("[data-check]")].map((element) => ({ id: element.dataset.check, pass: element.checked }));
}

function requiredAnimationIds() {
  if (!runtimeDescriptor) return [];
  return runtimeDescriptor.animations.filter((item) => item.review_required !== false).map((item) => item.id);
}

function reviewCoverageComplete() {
  const required = requiredAnimationIds();
  if (!runtimeDescriptor?.review_policy?.require_all_animations) return true;
  return required.every((id) => inspectedAnimations.has(id));
}

function currentReview(decision) {
  const state = driver?.getState?.() || runtimeUi.state || {};
  return {
    review_version: "1.1",
    task_id: taskId,
    candidate_id: candidate.candidate_id,
    scene,
    decision,
    reviewer: "user",
    reviewed_at: new Date().toISOString(),
    checks: currentChecks(),
    notes: $("notes").value,
    frames_inspected: Array.isArray(candidate.checkpoints) ? candidate.checkpoints : [0, 50, 100],
    animations_inspected: [...inspectedAnimations],
    runtime_review: {
      mode: runtimeDescriptor ? "live-runtime" : "captured-evidence",
      descriptor_sha256: candidate.runtime_review?.bundle_sha256 || null,
      selected_animation: currentAnimationId,
      state,
      action_separation: actionSeparation
    },
    spec: { framework: spec.framework, category: spec.category, context_binding: spec.context_binding },
    candidate: { source_sha256: candidate.source_sha256, context_sha256: candidate.context_sha256 }
  };
}

function saveLocal(payload) {
  localStorage.setItem(`devlab:${taskId}:${candidate.candidate_id}`, JSON.stringify(payload));
}

function expose(payload) {
  window.__lab.lastReview = payload;
  window.__lab.getReview = () => window.__lab.lastReview;
  window.__lab.exportReview = () => JSON.stringify(window.__lab.lastReview, null, 2);
}

function setStatus(kind, text) {
  $("status").className = kind;
  $("status").textContent = text;
}

function renderMetadata() {
  const values = [
    ["TASK", taskId], ["CANDIDATE", candidateId], ["FRAMEWORK", spec.framework],
    ["CATEGORY", spec.category], ["DURATION", `${spec.duration_s ?? "—"}s`], ["FPS", spec.fps ?? "—"],
    ["RUNTIME", runtimeDescriptor ? runtimeDescriptor.mode : "captured evidence"], ["SOURCE", String(candidate.source_sha256 || "").slice(0, 12) || "—"]
  ];
  $("meta").replaceChildren(...values.map(([key, value]) => {
    const pill = document.createElement("div"); pill.className = "pill";
    const label = document.createElement("b"); label.textContent = key;
    const text = document.createElement("span"); text.textContent = value ?? "—";
    pill.append(label, text); return pill;
  }));
}

function renderActionSeparation() {
  const node = $("action-separation");
  if (!node) return;
  if (!actionSeparation) {
    node.className = "progress-note";
    node.textContent = "No action-separation evidence bound; legacy review compatibility mode.";
    return;
  }
  const pass = actionSeparation.status === "pass";
  node.className = `progress-note ${pass ? "pass" : "quarantine"}`;
  const forbidden = actionSeparation.forbidden_action_ids.join(", ") || "none";
  node.textContent = `${pass ? "PASS" : "QUARANTINED"} · expected ${actionSeparation.action_id} · ${actionSeparation.passing_frame_count}/${actionSeparation.frame_count} frames separated · competitors: ${forbidden}`;
}

function renderChecks() {
  const nodes = (manifest.checks || []).map((check) => {
    const label = document.createElement("label"); label.className = "check";
    const input = document.createElement("input"); input.type = "checkbox"; input.dataset.check = String(check.id || "");
    input.checked = Boolean(review.checks?.find((item) => item.id === check.id)?.pass);
    input.addEventListener("change", updateReviewGate);
    const copy = document.createElement("span");
    const title = document.createElement("b"); title.textContent = check.label || check.id || "Unnamed check";
    const detail = document.createElement("small"); detail.textContent = check.detail || "";
    copy.append(title, detail); label.append(input, copy); return label;
  });
  $("checks").replaceChildren(...nodes);
}

function renderAnimations() {
  const animations = driver.listAnimations();
  if (!animations.length) { $("animations").textContent = "No runtime actions declared."; return; }
  const nodes = animations.map((animation) => {
    const button = document.createElement("button"); button.type = "button"; button.className = "animation-btn";
    button.dataset.animation = animation.id;
    const dot = document.createElement("span"); dot.className = "animation-dot";
    const name = document.createElement("span"); name.className = "animation-name"; name.textContent = animation.label || animation.id;
    const meta = document.createElement("span"); meta.className = "animation-meta";
    if (animation.fps && animation.frames) meta.textContent = `${animation.frames.length}f · ${animation.fps}fps`;
    else meta.textContent = animation.loop ? "loop" : "clip";
    button.append(dot, name, meta);
    button.addEventListener("click", () => selectAnimation(animation.id));
    return button;
  });
  $("animations").replaceChildren(...nodes);
  updateAnimationSelection();
}

function updateAnimationSelection() {
  for (const button of document.querySelectorAll(".animation-btn")) {
    button.classList.toggle("selected", button.dataset.animation === currentAnimationId);
    button.classList.toggle("visited", inspectedAnimations.has(button.dataset.animation));
  }
  const required = requiredAnimationIds();
  if (runtimeDescriptor && required.length) {
    const inspected = required.filter((id) => inspectedAnimations.has(id)).length;
    $("review-progress").textContent = `Review coverage ${inspected}/${required.length}`;
  } else {
    $("review-progress").textContent = runtimeDescriptor ? "No mandatory action coverage." : "Legacy snapshot compatibility mode.";
  }
  updateReviewGate();
}

function updateReviewGate() {
  const checks = currentChecks();
  const checksPass = checks.length > 0 && checks.every((item) => item.pass);
  const coverage = reviewCoverageComplete();
  const actionGate = !actionSeparation || actionSeparation.status === "pass";
  const liveRuntimeBlocked = candidate?.runtime_review?.live === true && driver instanceof SnapshotDriver;
  $("confirm").disabled = !(checksPass && coverage && actionGate && !liveRuntimeBlocked);
  if (liveRuntimeBlocked) {
    setStatus("warn", "LIVE RUNTIME UNAVAILABLE · approval is blocked; captured evidence remains inspectable and changes may still be requested.");
    return;
  }
  if (!actionGate) {
    setStatus("warn", "ACTION SEPARATION QUARANTINED · regenerate or independently verify the ambiguous frame before approval.");
    return;
  }
  const missing = requiredAnimationIds().filter((id) => !inspectedAnimations.has(id));
  if (!coverage && missing.length) setStatus("info", `Inspect required animations before approval: ${missing.join(", ")}`);
}

function applyViewportOverlays() {
  const viewport = runtimeDescriptor?.viewport || {};
  if (viewport.background && ["checker", "dark", "light", "transparent", "project"].includes(viewport.background)) {
    $("background").value = viewport.background;
    setBackground(viewport.background);
  }
  const canvasHeight = Number(viewport.canvas_height);
  const baselineY = Number(viewport.baseline_y);
  if (canvasHeight > 0 && Number.isFinite(baselineY)) $("overlay-baseline").style.top = `${clamp(baselineY / canvasHeight) * 100}%`;
  const pivot = viewport.pivot;
  const canvasWidth = Number(viewport.canvas_width);
  if (pivot && canvasWidth > 0 && canvasHeight > 0) {
    $("overlay-pivot").style.left = `${clamp(Number(pivot.x) / canvasWidth) * 100}%`;
    $("overlay-pivot").style.top = `${clamp(Number(pivot.y) / canvasHeight) * 100}%`;
  }
}

function setBackground(value) {
  for (const kind of ["checker", "dark", "light", "transparent", "project"]) $("stage").classList.toggle(`bg-${kind}`, value === kind);
}

function toggleTool(id, overlayId) {
  const on = !$(overlayId).classList.contains("on");
  $(overlayId).classList.toggle("on", on); $(id).classList.toggle("active", on);
}

function setZoom(value) {
  zoom = Math.max(0.25, Math.min(4, Number(value) || 1));
  $("stage-content").style.transform = `scale(${zoom})`;
  $("zoom-label").textContent = `${Math.round(zoom * 100)}%`;
}

function updateTransportState(state = {}) {
  runtimeUi.state = state;
  const progress = clamp(state.progress ?? runtimeUi.progress ?? 0);
  runtimeUi.progress = progress;
  runtimeUi.playing = Boolean(state.playing);
  runtimeUi.loop = state.loop ?? runtimeUi.loop;
  runtimeUi.speed = Number(state.speed ?? runtimeUi.speed ?? 1);
  $("scrubber").value = Math.round(progress * 1000);
  $("progress-label").textContent = `${(progress * 100).toFixed(1)}%`;
  const currentTime = Number(state.currentTime ?? (Number(state.duration || spec.duration_s || 0) * progress));
  const duration = Number(state.duration ?? spec.duration_s ?? 0);
  $("timecode").textContent = `${formatTime(currentTime)} / ${formatTime(duration)}`;
  const frame = state.frame;
  const totalFrames = state.totalFrames;
  $("framecode").textContent = Number.isFinite(frame) && Number.isFinite(totalFrames) ? `Frame ${frame + 1} / ${totalFrames}` : "Frame —";
  $("play").classList.toggle("active", Boolean(state.playing));
  $("loop").classList.toggle("active", Boolean(runtimeUi.loop));
  if ([0.25, 0.5, 1, 2].includes(runtimeUi.speed)) $("speed").value = String(runtimeUi.speed);
  $("runtime-state").textContent = JSON.stringify(state, null, 2);
  window.__lab.lastProgress = progress;
  window.__lab.runtimeState = state;
}

function configureControls() {
  const caps = driver instanceof IframeDriver ? driver.capabilities : {};
  const snapshot = driver instanceof SnapshotDriver;
  $("play").disabled = snapshot || !controlEnabled("play", caps.play);
  $("pause").disabled = snapshot || !controlEnabled("pause", caps.pause);
  $("restart").disabled = snapshot || !controlEnabled("restart", caps.restart);
  $("step-back").disabled = snapshot || !controlEnabled("step", caps.step);
  $("step-forward").disabled = snapshot || !controlEnabled("step", caps.step);
  $("speed").disabled = snapshot || !controlEnabled("speed", caps.speed);
  $("loop").disabled = snapshot || !controlEnabled("loop", caps.loop);
  $("scrubber").disabled = runtimeDescriptor ? !controlEnabled("seek", caps.seek) : false;
}

async function selectAnimation(id) {
  try {
    await driver.selectAnimation(id);
    currentAnimationId = id;
    inspectedAnimations.add(id);
    if (review?.animations_inspected) for (const item of review.animations_inspected) inspectedAnimations.add(item);
    updateAnimationSelection();
    updateTransportState(driver.getState());
  } catch (error) { showRuntimeError(error); }
}

function showRuntimeError(error) {
  const message = error instanceof Error ? error.message : String(error);
  $("runtime-error").textContent = `LIVE RUNTIME ERROR · ${message}`;
  $("runtime-error").classList.add("on");
  setStatus("warn", message);
}

async function fallbackToSnapshots(error) {
  driver?.dispose?.();
  runtimeDescriptor = null;
  driver = new SnapshotDriver();
  currentAnimationId = "captured-evidence";
  inspectedAnimations.clear();
  $("mode-badge").textContent = "CAPTURED EVIDENCE";
  $("mode-badge").className = "mode-badge fallback";
  $("stage-mode").textContent = "LIVE RUNTIME UNAVAILABLE · SNAPSHOT FALLBACK";
  $("runtime-error").textContent = `LIVE RUNTIME UNAVAILABLE · ${error instanceof Error ? error.message : String(error)} · showing captured evidence only`;
  $("runtime-error").classList.add("on");
  renderAnimations(); configureControls();
  await driver.seek(0); updateTransportState(driver.getState());
}

async function callDriver(method, ...args) {
  try {
    const result = await driver?.[method]?.(...args);
    updateTransportState(result || driver?.getState?.() || {});
    return result;
  } catch (error) { showRuntimeError(error); throw error; }
}

function wireControls() {
  $("play").addEventListener("click", () => callDriver("play").catch(() => {}));
  $("pause").addEventListener("click", () => callDriver("pause").catch(() => {}));
  $("restart").addEventListener("click", () => callDriver("restart").catch(() => {}));
  $("step-back").addEventListener("click", () => callDriver("stepFrames", -1).catch(() => {}));
  $("step-forward").addEventListener("click", () => callDriver("stepFrames", 1).catch(() => {}));
  $("loop").addEventListener("click", () => callDriver("setLoop", !runtimeUi.loop).catch(() => {}));
  $("speed").addEventListener("change", (event) => callDriver("setSpeed", Number(event.target.value)).catch(() => {}));
  $("scrubber").addEventListener("input", (event) => callDriver("seek", Number(event.target.value) / 1000).catch(() => {}));
  $("background").addEventListener("change", (event) => setBackground(event.target.value));
  $("grid").addEventListener("click", () => toggleTool("grid", "overlay-grid"));
  $("bounds").addEventListener("click", () => toggleTool("bounds", "overlay-bounds"));
  $("baseline").addEventListener("click", () => toggleTool("baseline", "overlay-baseline"));
  $("pivot").addEventListener("click", () => toggleTool("pivot", "overlay-pivot"));
  $("zoom-out").addEventListener("click", () => setZoom(zoom / 1.25));
  $("zoom-in").addEventListener("click", () => setZoom(zoom * 1.25));
  $("zoom-reset").addEventListener("click", () => setZoom(1));
  $("fullscreen").addEventListener("click", async () => {
    if (document.fullscreenElement) await document.exitFullscreen(); else await $("stage-shell").requestFullscreen();
  });
  $("request-changes").addEventListener("click", () => submitReview("changes_requested"));
  $("confirm").addEventListener("click", () => submitReview("approved"));
  $("reset").addEventListener("click", () => { localStorage.removeItem(`devlab:${taskId}:${candidateId}`); location.reload(); });
  window.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return;
    if (event.code === "Space") { event.preventDefault(); callDriver(runtimeUi.playing ? "pause" : "play").catch(() => {}); }
    if (event.key === "ArrowLeft") callDriver("stepFrames", -1).catch(() => {});
    if (event.key === "ArrowRight") callDriver("stepFrames", 1).catch(() => {});
  });
}

function submitReview(decision) {
  const checks = currentChecks();
  if (decision === "approved") {
    if (!checks.length || !checks.every((item) => item.pass)) { setStatus("warn", "Approval requires every quality checklist item to be checked."); return; }
    if (!reviewCoverageComplete()) { updateReviewGate(); return; }
  }
  const payload = currentReview(decision);
  saveLocal(payload); expose(payload);
  setStatus(decision === "approved" ? "ok" : "warn", decision === "approved"
    ? "BROWSER REVIEW APPROVED · browser Agent must persist review.json before PR"
    : "CHANGES REQUESTED · browser Agent must persist notes and return to generation");
}

function startRuntimePolling() {
  if (!(driver instanceof IframeDriver)) return;
  clearInterval(pollTimer);
  pollTimer = setInterval(() => driver.refresh().catch(() => {}), 250);
}

window.__lab = {
  ready: false,
  taskId,
  candidateId,
  reviewRequired: true,
  mode: "loading",
  seek: async (progress) => callDriver("seek", progress),
  selectAnimation: async (id) => selectAnimation(id),
  play: async () => callDriver("play"),
  pause: async () => callDriver("pause"),
  restart: async () => callDriver("restart"),
  stepFrames: async (delta) => callDriver("stepFrames", delta),
  setSpeed: async (rate) => callDriver("setSpeed", rate),
  setLoop: async (enabled) => callDriver("setLoop", enabled),
  getRuntimeState: () => driver?.getState?.() || runtimeUi.state,
  getReview: () => window.__lab.lastReview,
  exportReview: () => JSON.stringify(window.__lab.lastReview || {}, null, 2)
};

async function load() {
  if (!scene || !candidateId) throw new Error("Missing scene or candidate_id; open the emitted browser-review URL");
  [manifest, spec, candidate, runtimeDescriptor] = await Promise.all([
    fetchJson(`${base}/manifest.json`), fetchJson(`${base}/motion-spec.json`), fetchJson(`${base}/browser-review.json`), fetchJson(`${base}/devlab-runtime.json`, { optional: true })
  ]);
  validateCandidate();
  runtimeDescriptor = validateRuntimeDescriptor(runtimeDescriptor);
  actionSeparation = validateActionSeparation(runtimeDescriptor?.action_separation || null);
  const expectedLiveRuntimeMissing = candidate.runtime_review?.live === true && !runtimeDescriptor;

  $("title").textContent = `${manifest.name || scene}`;
  $("description").textContent = `${manifest.description || "Evidence review for this animation scene."} Candidate ${candidateId} is bound to task ${taskId}.`;
  $("stage-label").textContent = `${scene.toUpperCase()} · ${spec.category || "animation"}`;
  $("stage-mode").textContent = `${spec.framework || "unknown"} · ${candidate.status}`;
  renderMetadata();

  const saved = JSON.parse(localStorage.getItem(`devlab:${taskId}:${candidateId}`) || "null");
  review = saved || { checks: (manifest.checks || []).map((check) => ({ id: check.id, pass: false })), notes: "", decision: "pending", animations_inspected: [] };
  for (const id of review.animations_inspected || []) inspectedAnimations.add(id);
  renderActionSeparation(); renderChecks(); $("notes").value = review.notes || ""; expose(review);
  wireControls(); applyViewportOverlays(); setZoom(1);

  if (expectedLiveRuntimeMissing) {
    await fallbackToSnapshots(new Error("Hash-bound devlab-runtime.json is missing"));
  } else if (runtimeDescriptor?.mode === "sprite-sequence") {
    driver = new SpriteSequenceDriver(runtimeDescriptor, updateTransportState);
    currentAnimationId = runtimeDescriptor.default_animation;
    $("mode-badge").textContent = "LIVE RUNTIME"; $("mode-badge").className = "mode-badge live";
    $("stage-mode").textContent = `${spec.framework || "sprite"} · LIVE SPRITE RUNTIME`;
    await driver.selectAnimation(currentAnimationId);
  } else if (runtimeDescriptor?.mode === "iframe") {
    driver = new IframeDriver(runtimeDescriptor, updateTransportState);
    currentAnimationId = runtimeDescriptor.default_animation;
    $("mode-badge").textContent = "LIVE RUNTIME"; $("mode-badge").className = "mode-badge live";
    $("stage-mode").textContent = `${spec.framework || "runtime"} · LIVE IFRAME RUNTIME`;
    try { await driver.mount(); }
    catch (error) { await fallbackToSnapshots(error); }
  } else {
    driver = new SnapshotDriver();
    currentAnimationId = "captured-evidence";
    $("mode-badge").textContent = "CAPTURED EVIDENCE"; $("mode-badge").className = "mode-badge fallback";
    $("stage-mode").textContent = `${spec.framework || "unknown"} · SNAPSHOT COMPATIBILITY`;
    await driver.seek(0);
  }

  renderAnimations(); configureControls(); applyViewportOverlays();
  await selectAnimation(currentAnimationId);
  updateTransportState(driver.getState());
  startRuntimePolling();
  window.__lab.mode = driver.mode;
  window.__lab.ready = true;
}

load().catch((error) => {
  $("mode-badge").textContent = "BLOCKED"; $("mode-badge").className = "mode-badge fallback";
  setStatus("warn", `DEV LAB ERROR: ${error.message}`);
  $("empty").textContent = "Unable to load the exact candidate evidence.";
  $("runtime-state").textContent = error.stack || error.message;
});
