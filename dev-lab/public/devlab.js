const params = new URLSearchParams(location.search);
const scene = params.get("scene");
const taskId = params.get("task_id") || "unbound";
const candidateId = params.get("candidate_id");
const base = `/scenes/${encodeURIComponent(scene || "")}`;
const frames = [0, 50, 100];
const allowedStatuses = new Set(["prepared", "opened"]);
const $ = (id) => document.getElementById(id);
let manifest;
let spec;
let candidate;
let review;

function nearest(progress) {
  return frames.reduce(
    (current, frame) => Math.abs(frame - progress) < Math.abs(current - progress) ? frame : current,
    frames[0],
  );
}

function showProgress(progress) {
  const bounded = Math.max(0, Math.min(1, progress));
  const percent = bounded * 100;
  const frame = nearest(percent);
  $("scrubber").value = percent;
  $("timecode").textContent = `00:00:${(Number(spec?.duration_s || 0) * bounded).toFixed(3).padStart(6, "0")}`;
  $("frame").src = `${base}/snapshot/frame-${String(frame).padStart(2, "0")}.png`;
  $("frame").hidden = false;
  $("empty").hidden = true;
  window.__lab.lastProgress = bounded;
}

function currentChecks() {
  return [...document.querySelectorAll("[data-check]")].map((element) => ({
    id: element.dataset.check,
    pass: element.checked,
  }));
}

function currentReview(decision) {
  return {
    review_version: "1.0",
    task_id: taskId,
    candidate_id: candidate.candidate_id,
    scene,
    decision,
    reviewer: "user",
    reviewed_at: new Date().toISOString(),
    checks: currentChecks(),
    notes: $("notes").value,
    frames_inspected: frames,
    spec: {
      framework: spec.framework,
      category: spec.category,
      context_binding: spec.context_binding,
    },
    candidate: {
      source_sha256: candidate.source_sha256,
      context_sha256: candidate.context_sha256,
    },
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

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Could not load ${url} (${response.status})`);
  return response.json();
}

function validateCandidate() {
  if (candidate.candidate_id !== candidateId) {
    throw new Error("Candidate identity mismatch; refusing to review a different scene");
  }
  if (candidate.task_id !== taskId) {
    throw new Error("Task identity mismatch; refusing unbound review");
  }
  if (!allowedStatuses.has(candidate.status)) {
    throw new Error(`Candidate status is not reviewable: ${candidate.status || "missing"}`);
  }
  const expiresAt = Date.parse(candidate.expires_at);
  if (!Number.isFinite(expiresAt)) {
    throw new Error("Candidate expiry is missing or invalid");
  }
  if (Date.now() > expiresAt) {
    throw new Error("Candidate has expired; prepare a new browser-review URL");
  }
}

function renderMetadata() {
  const values = [
    ["TASK", taskId],
    ["CANDIDATE", candidateId],
    ["FRAMEWORK", spec.framework],
    ["DURATION", `${spec.duration_s}s`],
    ["FPS", spec.fps],
    ["EASING", spec.easing],
    ["PRIMARY", spec.theme?.primary || "unbound"],
  ];
  const nodes = values.map(([key, value]) => {
    const pill = document.createElement("div");
    pill.className = "pill";
    const label = document.createElement("b");
    label.textContent = key;
    pill.append(label, document.createTextNode(` ${value ?? "—"}`));
    return pill;
  });
  $("meta").replaceChildren(...nodes);
}

function renderChecks() {
  const nodes = (manifest.checks || []).map((check) => {
    const label = document.createElement("label");
    label.className = "check";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.dataset.check = String(check.id || "");
    input.checked = Boolean(review.checks.find((item) => item.id === check.id)?.pass);
    const copy = document.createElement("span");
    const title = document.createElement("b");
    const detail = document.createElement("small");
    title.textContent = check.label || check.id || "Unnamed check";
    detail.textContent = check.detail || "";
    copy.append(title, detail);
    label.append(input, copy);
    return label;
  });
  $("checks").replaceChildren(...nodes);
}

function confirmReview() {
  const checks = currentChecks();
  const approved = checks.length > 0 && checks.every((check) => check.pass);
  const payload = currentReview(approved ? "approved" : "changes_requested");
  saveLocal(payload);
  expose(payload);
  $("status").className = approved ? "ok" : "warn";
  $("status").textContent = approved
    ? "BROWSER REVIEW APPROVED · browser Agent must persist review.json before PR"
    : "CHANGES REQUESTED · browser Agent must persist notes and return to generation";
}

window.__lab = { seek: showProgress, ready: false, taskId, candidateId, reviewRequired: true };

async function load() {
  if (!scene || !candidateId) {
    throw new Error("Missing scene or candidate_id; open the emitted browser-review URL");
  }
  [manifest, spec, candidate] = await Promise.all([
    fetchJson(`${base}/manifest.json`),
    fetchJson(`${base}/motion-spec.json`),
    fetchJson(`${base}/browser-review.json`),
  ]);
  validateCandidate();

  $("title").textContent = `${manifest.name || scene} · candidate ${candidateId}`;
  $("description").textContent = `${manifest.description || "Evidence review for this animation scene."} Review candidate ${candidateId} is bound to task ${taskId}.`;
  $("stage-label").textContent = `${scene.toUpperCase()} · ${spec.category || "animation"} · CANDIDATE`;
  $("stage-mode").textContent = `${spec.framework || "unknown"} · ${candidate.status} · runtime evidence`;
  renderMetadata();

  const saved = JSON.parse(localStorage.getItem(`devlab:${taskId}:${candidateId}`) || "null");
  review = saved || {
    checks: (manifest.checks || []).map((check) => ({ id: check.id, pass: false })),
    notes: "",
    decision: "pending",
  };
  renderChecks();
  $("notes").value = review.notes || "";
  $("scrubber").addEventListener("input", (event) => showProgress(Number(event.target.value) / 100));
  $("confirm").addEventListener("click", confirmReview);
  $("reset").addEventListener("click", () => {
    localStorage.removeItem(`devlab:${taskId}:${candidateId}`);
    location.reload();
  });
  window.__lab.ready = true;
  showProgress(0);
}

load().catch((error) => {
  $("status").className = "warn";
  $("status").textContent = `DEV LAB ERROR: ${error.message}`;
  $("empty").textContent = "Unable to load the exact candidate evidence.";
});
