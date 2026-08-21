(() => {
  const params = new URLSearchParams(location.search);
  const scene = params.get("scene");
  if (!scene || !/^[A-Za-z0-9._-]+$/.test(scene)) return;

  const safeBase = (() => {
    const expected = `/scenes/${encodeURIComponent(scene)}`;
    const raw = params.get("artifact_base");
    if (!raw) return expected;
    try {
      const url = new URL(raw, location.href);
      if (url.origin !== location.origin || url.search || url.hash) return expected;
      const decoded = decodeURIComponent(url.pathname).replace(/\/+$/, "");
      return decoded === `/scenes/${scene}` ? url.pathname.replace(/\/+$/, "") : expected;
    } catch {
      return expected;
    }
  })();

  const state = {
    query: "",
    filter: "all",
    group: "all",
    collapsed: new Set(),
  };
  const metaById = new Map();
  const groupMeta = new Map();
  let descriptor = null;
  let observer = null;
  let refreshTimer = null;
  let pollTimer = null;
  let rebuilding = false;

  function installStyles() {
    if (document.getElementById("action-library-style")) return;
    const style = document.createElement("style");
    style.id = "action-library-style";
    style.textContent = `
      .action-library-toolbar{display:grid;gap:8px;margin:0 0 10px}
      .action-search{width:100%;min-width:0;border:1px solid var(--line2);border-radius:7px;background:#0f1117;color:var(--text);padding:8px 9px;outline:none}
      .action-search:focus{border-color:var(--amber);box-shadow:0 0 0 1px var(--amber)}
      .action-filter{width:100%;border:1px solid var(--line2);border-radius:7px;background:#242936;color:var(--text);padding:7px 8px}
      .action-group-chips{display:flex;gap:5px;overflow:auto;padding:1px 0 3px;scrollbar-width:thin}
      .action-group-chip{flex:0 0 auto;border-color:transparent;background:#202430;color:var(--muted);padding:5px 7px;font:10px ui-monospace,monospace}
      .action-group-chip.active{color:var(--text);border-color:#6b5726;background:#2b2519}
      .action-library-summary{color:var(--muted);font:10px/1.35 ui-monospace,monospace}
      .action-group{display:grid;gap:4px}
      .action-group[hidden]{display:none}
      .action-group-header{width:100%;display:flex;align-items:center;justify-content:space-between;gap:8px;border-color:transparent;background:transparent;color:var(--muted);padding:7px 6px 4px;text-align:left;font:700 10px ui-monospace,monospace;letter-spacing:.07em;text-transform:uppercase}
      .action-group-header:hover:not(:disabled){background:#1c202a;border-color:transparent}
      .action-group-header .chevron{display:inline-block;width:12px;color:#697284}
      .action-group-header .group-title{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .action-group-header .group-count{font-weight:500;letter-spacing:0;color:#697284}
      .action-group-actions{display:grid;gap:4px}
      .action-group.collapsed .action-group-actions{display:none}
      .animation-btn[hidden]{display:none}
      @media(max-width:820px){
        nav[aria-label="Animation actions"]{overflow:visible}
        .action-library-toolbar{grid-template-columns:minmax(170px,1fr) minmax(120px,.45fr);align-items:start}
        .action-group-chips,.action-library-summary{grid-column:1/-1}
        #animations{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));overflow:visible}
        .action-group{min-width:0}
        .action-group-actions{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr))}
        .animation-btn{width:100%;min-width:0}
      }
      @media(max-width:520px){.action-library-toolbar{grid-template-columns:1fr}.action-group-chips,.action-library-summary{grid-column:auto}}
    `;
    document.head.append(style);
  }

  async function fetchDescriptor() {
    try {
      const response = await fetch(`${safeBase}/devlab-runtime.json`, { cache: "no-store" });
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    }
  }

  function normalizeGroupId(value) {
    return typeof value === "string" && /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test(value) ? value : "ungrouped";
  }

  function hydrateMetadata(value) {
    descriptor = value;
    metaById.clear();
    groupMeta.clear();
    const declaredGroups = Array.isArray(value?.groups) ? value.groups : [];
    declaredGroups.forEach((group, index) => {
      if (!group || typeof group.id !== "string") return;
      const id = normalizeGroupId(group.id);
      groupMeta.set(id, {
        id,
        label: typeof group.label === "string" && group.label ? group.label : id,
        order: Number.isFinite(Number(group.order)) ? Number(group.order) : index,
      });
    });
    for (const animation of Array.isArray(value?.animations) ? value.animations : []) {
      if (!animation || typeof animation.id !== "string") continue;
      const group = normalizeGroupId(animation.group);
      metaById.set(animation.id, { ...animation, group });
      if (!groupMeta.has(group)) {
        groupMeta.set(group, {
          id: group,
          label: group === "ungrouped" ? "Other" : group.replace(/[._-]+/g, " "),
          order: 1000 + groupMeta.size,
        });
      }
    }
    if (!groupMeta.has("ungrouped")) groupMeta.set("ungrouped", { id: "ungrouped", label: "Other", order: 9999 });
  }

  function sortedGroups(buttons) {
    const present = new Set(buttons.map((button) => button.dataset.actionGroup || "ungrouped"));
    return [...groupMeta.values()]
      .filter((group) => present.has(group.id))
      .sort((a, b) => a.order - b.order || a.label.localeCompare(b.label));
  }

  function buildToolbar(nav) {
    if (document.getElementById("action-library-toolbar")) return;
    const toolbar = document.createElement("div");
    toolbar.id = "action-library-toolbar";
    toolbar.className = "action-library-toolbar";

    const search = document.createElement("input");
    search.id = "animation-search";
    search.className = "action-search";
    search.type = "search";
    search.autocomplete = "off";
    search.spellcheck = false;
    search.placeholder = "Search actions…";
    search.setAttribute("aria-label", "Search animation actions");
    search.addEventListener("input", () => { state.query = search.value.trim().toLowerCase(); applyFilters(); });

    const filter = document.createElement("select");
    filter.id = "animation-filter";
    filter.className = "action-filter";
    filter.setAttribute("aria-label", "Filter animation actions");
    for (const [value, label] of [["all", "All actions"], ["required", "Required review"], ["unreviewed", "Unreviewed"], ["looping", "Looping"], ["one-shot", "One-shot"]]) {
      const option = document.createElement("option"); option.value = value; option.textContent = label; filter.append(option);
    }
    filter.addEventListener("change", () => { state.filter = filter.value; applyFilters(); });

    const chips = document.createElement("div");
    chips.id = "animation-groups";
    chips.className = "action-group-chips";
    chips.setAttribute("aria-label", "Animation groups");

    const summary = document.createElement("div");
    summary.id = "animation-library-summary";
    summary.className = "action-library-summary";

    toolbar.append(search, filter, chips, summary);
    nav.insertBefore(toolbar, document.getElementById("animations"));

    window.addEventListener("keydown", (event) => {
      const target = event.target;
      const typing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;
      if (event.key === "/" && !typing) { event.preventDefault(); search.focus(); search.select(); }
      if (event.key === "Escape" && document.activeElement === search && search.value) {
        event.preventDefault(); search.value = ""; state.query = ""; applyFilters();
      }
    });
  }

  function renderGroupChips(buttons) {
    const chips = document.getElementById("animation-groups");
    if (!chips) return;
    const groups = sortedGroups(buttons);
    const entries = [{ id: "all", label: "All", count: buttons.length }, ...groups.map((group) => ({
      id: group.id,
      label: group.label,
      count: buttons.filter((button) => button.dataset.actionGroup === group.id).length,
    }))];
    chips.replaceChildren(...entries.map((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `action-group-chip${state.group === entry.id ? " active" : ""}`;
      button.dataset.group = entry.id;
      button.textContent = `${entry.label} ${entry.count}`;
      button.addEventListener("click", () => {
        state.group = entry.id;
        renderGroupChips([...document.querySelectorAll(".animation-btn")]);
        applyFilters();
      });
      return button;
    }));
  }

  function persistCollapsed() {
    try { sessionStorage.setItem("motionloom:action-groups:collapsed", JSON.stringify([...state.collapsed])); } catch { /* optional */ }
  }

  function restoreCollapsed() {
    try {
      const value = JSON.parse(sessionStorage.getItem("motionloom:action-groups:collapsed") || "[]");
      if (Array.isArray(value)) state.collapsed = new Set(value.filter((item) => typeof item === "string"));
    } catch { /* optional */ }
  }

  function rebuildGroups() {
    const container = document.getElementById("animations");
    if (!container || rebuilding) return;
    const buttons = [...container.querySelectorAll(".animation-btn")];
    if (!buttons.length) return;
    rebuilding = true;
    observer?.disconnect();

    for (const button of buttons) {
      const id = button.dataset.animation || "";
      const meta = metaById.get(id) || {};
      const group = normalizeGroupId(meta.group);
      button.dataset.actionGroup = group;
      const label = button.querySelector(".animation-name")?.textContent || id;
      const tags = Array.isArray(meta.tags) ? meta.tags : [];
      const events = Array.isArray(meta.events) ? meta.events : [];
      const groupLabel = groupMeta.get(group)?.label || group;
      button.dataset.actionKeywords = [id, label, group, groupLabel, ...tags, ...events].join(" ").toLowerCase();
    }

    const fragment = document.createDocumentFragment();
    const groups = sortedGroups(buttons);
    for (const group of groups) {
      const groupButtons = buttons.filter((button) => button.dataset.actionGroup === group.id);
      if (!groupButtons.length) continue;
      const section = document.createElement("section");
      section.className = "action-group";
      section.dataset.group = group.id;

      const header = document.createElement("button");
      header.type = "button";
      header.className = "action-group-header";
      header.setAttribute("aria-expanded", state.collapsed.has(group.id) ? "false" : "true");
      const chevron = document.createElement("span"); chevron.className = "chevron"; chevron.textContent = state.collapsed.has(group.id) ? "▸" : "▾";
      const title = document.createElement("span"); title.className = "group-title"; title.textContent = group.label;
      const count = document.createElement("span"); count.className = "group-count"; count.textContent = String(groupButtons.length);
      header.append(chevron, title, count);
      header.addEventListener("click", () => {
        if (state.collapsed.has(group.id)) state.collapsed.delete(group.id); else state.collapsed.add(group.id);
        persistCollapsed();
        applyFilters();
      });

      const actions = document.createElement("div"); actions.className = "action-group-actions"; actions.append(...groupButtons);
      section.append(header, actions); fragment.append(section);
    }
    container.replaceChildren(fragment);
    renderGroupChips(buttons);
    rebuilding = false;
    observer?.observe(container, { childList: true, subtree: true });
    applyFilters();
  }

  function filterMatches(button) {
    const id = button.dataset.animation || "";
    const meta = metaById.get(id) || {};
    const selected = button.classList.contains("selected");
    const visited = button.classList.contains("visited");
    if (state.query && !(button.dataset.actionKeywords || id).includes(state.query)) return false;
    if (state.group !== "all" && button.dataset.actionGroup !== state.group) return false;
    if (state.filter === "required" && meta.review_required === false) return false;
    if (state.filter === "unreviewed" && visited && !selected) return false;
    if (state.filter === "looping" && meta.loop !== true) return false;
    if (state.filter === "one-shot" && meta.loop !== false) return false;
    return true;
  }

  function applyFilters() {
    const buttons = [...document.querySelectorAll("#animations .animation-btn")];
    if (!buttons.length) return;
    let visible = 0;
    let visited = 0;
    let required = 0;
    for (const button of buttons) {
      const id = button.dataset.animation || "";
      const meta = metaById.get(id) || {};
      if (button.classList.contains("visited")) visited += 1;
      if (meta.review_required !== false) required += 1;
      const show = filterMatches(button);
      button.hidden = !show;
      if (show) visible += 1;
    }

    for (const section of document.querySelectorAll("#animations .action-group")) {
      const groupId = section.dataset.group;
      const shown = [...section.querySelectorAll(".animation-btn")].filter((button) => !button.hidden);
      const total = section.querySelectorAll(".animation-btn").length;
      section.hidden = shown.length === 0;
      const autoExpand = Boolean(state.query) || state.group !== "all";
      const collapsed = !autoExpand && state.collapsed.has(groupId);
      section.classList.toggle("collapsed", collapsed);
      const header = section.querySelector(".action-group-header");
      const chevron = section.querySelector(".chevron");
      const count = section.querySelector(".group-count");
      if (header) header.setAttribute("aria-expanded", collapsed ? "false" : "true");
      if (chevron) chevron.textContent = collapsed ? "▸" : "▾";
      if (count) count.textContent = shown.length === total ? String(total) : `${shown.length}/${total}`;
    }

    const summary = document.getElementById("animation-library-summary");
    if (summary) summary.textContent = `${visible}/${buttons.length} visible · ${visited}/${buttons.length} inspected · ${required} review-required`;
    for (const chip of document.querySelectorAll(".action-group-chip")) chip.classList.toggle("active", chip.dataset.group === state.group);
  }

  function scheduleRebuild() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(rebuildGroups, 20);
  }

  async function waitForLab() {
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      if (window.__lab?.ready === true && document.querySelector("#animations .animation-btn")) return true;
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    return false;
  }

  async function init() {
    if (!(await waitForLab())) return;
    installStyles();
    restoreCollapsed();
    hydrateMetadata(await fetchDescriptor());
    const nav = document.querySelector('nav[aria-label="Animation actions"]');
    const container = document.getElementById("animations");
    if (!nav || !container) return;
    buildToolbar(nav);
    observer = new MutationObserver(() => { if (!rebuilding) scheduleRebuild(); });
    observer.observe(container, { childList: true, subtree: true });
    rebuildGroups();
    pollTimer = setInterval(applyFilters, 250);

    window.__lab.actionLibrary = {
      ready: true,
      getState: () => ({ query: state.query, filter: state.filter, group: state.group, visible: [...document.querySelectorAll("#animations .animation-btn")].filter((button) => !button.hidden).map((button) => button.dataset.animation) }),
      setSearch: (query = "") => {
        state.query = String(query).trim().toLowerCase();
        const input = document.getElementById("animation-search"); if (input) input.value = query;
        applyFilters();
      },
      setFilter: (filter = "all") => {
        const allowed = new Set(["all", "required", "unreviewed", "looping", "one-shot"]);
        state.filter = allowed.has(filter) ? filter : "all";
        const select = document.getElementById("animation-filter"); if (select) select.value = state.filter;
        applyFilters();
      },
      setGroup: (group = "all") => {
        state.group = group === "all" || groupMeta.has(group) ? group : "all";
        renderGroupChips([...document.querySelectorAll(".animation-btn")]);
        applyFilters();
      },
      listGroups: () => sortedGroups([...document.querySelectorAll(".animation-btn")]).map((group) => ({ ...group })),
      dispose: () => { observer?.disconnect(); clearInterval(pollTimer); },
    };
  }

  init();
})();

(() => {
  const params = new URLSearchParams(location.search);
  const scene = params.get("scene");
  if (!scene || !/^[A-Za-z0-9._-]+$/.test(scene)) return;

  const safeBase = (() => {
    const expected = `/scenes/${encodeURIComponent(scene)}`;
    const raw = params.get("artifact_base");
    if (!raw) return expected;
    try {
      const url = new URL(raw, location.href);
      if (url.origin !== location.origin || url.search || url.hash) return expected;
      const decoded = decodeURIComponent(url.pathname).replace(/\/+$/, "");
      return decoded === `/scenes/${scene}` ? url.pathname.replace(/\/+$/, "") : expected;
    } catch {
      return expected;
    }
  })();

  const MACHINE_FILE = "devlab-state-machine.json";
  const ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/;
  const state = {
    descriptor: null,
    machine: null,
    states: new Map(),
    transitions: new Map(),
    sequences: new Map(),
    currentState: null,
    inspectedTransitions: new Set(),
    inspectedSequences: new Set(),
    history: [],
    runtimeCapabilities: {},
    runningSequence: null,
    blocked: null,
    pollTimer: null,
    rpcCounter: 0,
    pending: new Map(),
  };

  function installStyles() {
    if (document.getElementById("state-transition-style")) return;
    const style = document.createElement("style");
    style.id = "state-transition-style";
    style.textContent = `
      .state-machine-panel{margin-top:16px;padding-top:14px;border-top:1px solid var(--line);display:grid;gap:8px}
      .state-machine-head{display:flex;align-items:center;justify-content:space-between;gap:8px}
      .state-machine-current{display:flex;align-items:center;gap:7px;min-width:0;padding:7px 8px;border:1px solid var(--line);border-radius:7px;background:#10131a}
      .state-machine-dot{width:8px;height:8px;border-radius:50%;background:var(--good);box-shadow:0 0 0 3px #52d49b18}
      .state-machine-current strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .state-machine-current small{margin-left:auto;color:var(--muted);font:10px ui-monospace,monospace}
      .state-machine-actions{display:grid;gap:5px}
      .transition-btn{width:100%;display:grid;grid-template-columns:8px minmax(0,1fr) auto;align-items:center;gap:7px;text-align:left;padding:7px 8px;background:#1d222d}
      .transition-btn .transition-dot{width:6px;height:6px;border-radius:50%;background:#596173}
      .transition-btn.inspected .transition-dot{background:var(--good)}
      .transition-btn .transition-copy{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
      .transition-btn .transition-mode{color:var(--muted);font:9px ui-monospace,monospace}
      .transition-empty,.state-machine-coverage,.state-machine-error{color:var(--muted);font:10px/1.4 ui-monospace,monospace}
      .state-machine-error{color:var(--bad)}
      .sequence-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:5px}
      .sequence-row select{min-width:0;color:var(--text);background:#242936;border:1px solid var(--line2);border-radius:7px;padding:6px 7px}
      .sequence-row button{padding:6px 8px;font-size:11px}
      .transition-history{max-height:110px;overflow:auto;border:1px solid var(--line);border-radius:6px;background:#0f1117;padding:6px;display:grid;gap:4px}
      .transition-history-item{display:grid;grid-template-columns:auto 1fr;gap:6px;color:var(--muted);font:9px/1.35 ui-monospace,monospace}
      .transition-history-item b{color:var(--text);font-weight:600}
      #confirm.state-machine-gated{box-shadow:0 0 0 1px #6f363b inset;filter:saturate(.7)}
      @media(max-width:820px){.state-machine-panel{margin-top:12px}.state-machine-actions{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}.transition-history{max-height:90px}}
    `;
    document.head.append(style);
  }

  async function fetchJson(url, optional = false) {
    const response = await fetch(url, { cache: "no-store" });
    if (optional && response.status === 404) return null;
    if (!response.ok) throw new Error(`Could not load ${url} (${response.status})`);
    return response.json();
  }

  async function waitForLab() {
    const deadline = Date.now() + 10000;
    while (Date.now() < deadline) {
      if (window.__lab?.ready === true) return true;
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    return false;
  }

  function validateMachine(raw) {
    if (!raw || raw.schema_version !== "1.0") throw new Error("Unsupported or missing state-machine schema version");
    if (!Array.isArray(raw.states) || raw.states.length < 1 || raw.states.length > 256) throw new Error("State machine requires 1..256 states");
    if (!Array.isArray(raw.transitions) || raw.transitions.length < 1 || raw.transitions.length > 512) throw new Error("State machine requires 1..512 transitions");
    const animationIds = new Set((state.descriptor?.animations || []).map((item) => item.id));
    const states = new Map();
    for (const item of raw.states) {
      if (!ID.test(item?.id || "")) throw new Error("State id is invalid");
      if (states.has(item.id)) throw new Error(`Duplicate state id: ${item.id}`);
      if (!ID.test(item?.animation || "") || !animationIds.has(item.animation)) throw new Error(`State ${item.id} references an unknown animation`);
      states.set(item.id, { id: item.id, label: item.label || item.id, animation: item.animation, description: item.description || "" });
    }
    if (!states.has(raw.initial_state)) throw new Error("State-machine initial_state does not exist");

    const transitions = new Map();
    for (const item of raw.transitions) {
      if (!ID.test(item?.id || "")) throw new Error("Transition id is invalid");
      if (transitions.has(item.id)) throw new Error(`Duplicate transition id: ${item.id}`);
      if (item.from !== "*" && !states.has(item.from)) throw new Error(`Transition ${item.id} has an unknown source state`);
      if (!states.has(item.to)) throw new Error(`Transition ${item.id} has an unknown target state`);
      if (!new Set(["select-animation", "runtime-trigger"]).has(item.mode)) throw new Error(`Transition ${item.id} has an unsupported mode`);
      const waitMs = item.wait_ms == null ? 0 : Number(item.wait_ms);
      if (!Number.isInteger(waitMs) || waitMs < 0 || waitMs > 10000) throw new Error(`Transition ${item.id} wait_ms is out of range`);
      transitions.set(item.id, {
        id: item.id,
        label: item.label || item.trigger || item.id,
        from: item.from,
        to: item.to,
        trigger: item.trigger || item.id,
        mode: item.mode,
        auto_play: item.auto_play !== false,
        review_required: item.review_required !== false,
        wait_ms: waitMs,
        payload: item.payload && typeof item.payload === "object" ? item.payload : {},
      });
    }

    const sequences = new Map();
    for (const item of Array.isArray(raw.sequences) ? raw.sequences : []) {
      if (!ID.test(item?.id || "")) throw new Error("Sequence id is invalid");
      if (sequences.has(item.id)) throw new Error(`Duplicate sequence id: ${item.id}`);
      if (!Array.isArray(item.steps) || item.steps.length < 1 || item.steps.length > 64) throw new Error(`Sequence ${item.id} requires 1..64 steps`);
      const steps = item.steps.map((step) => {
        if (!transitions.has(step?.transition)) throw new Error(`Sequence ${item.id} references unknown transition ${step?.transition || ""}`);
        const waitMs = step.wait_ms == null ? transitions.get(step.transition).wait_ms : Number(step.wait_ms);
        if (!Number.isInteger(waitMs) || waitMs < 0 || waitMs > 10000) throw new Error(`Sequence ${item.id} wait_ms is out of range`);
        return { transition: step.transition, wait_ms: waitMs };
      });
      sequences.set(item.id, { id: item.id, label: item.label || item.id, description: item.description || "", review_required: item.review_required === true, steps });
    }

    state.states = states;
    state.transitions = transitions;
    state.sequences = sequences;
    return {
      ...raw,
      review_policy: {
        require_all_transitions: raw.review_policy?.require_all_transitions === true,
        require_all_sequences: raw.review_policy?.require_all_sequences === true,
      }
    };
  }

  function stateFromRuntime(runtime = window.__lab?.getRuntimeState?.() || {}) {
    const explicit = runtime.state || runtime.currentState || runtime.current_state;
    if (typeof explicit === "string" && state.states.has(explicit)) return explicit;
    const animation = runtime.animation;
    if (typeof animation === "string") {
      const match = [...state.states.values()].find((item) => item.animation === animation);
      if (match) return match.id;
    }
    return state.currentState && state.states.has(state.currentState) ? state.currentState : state.machine?.initial_state || null;
  }

  function requiredTransitions() {
    return [...state.transitions.values()].filter((item) => item.review_required).map((item) => item.id);
  }

  function requiredSequences() {
    return [...state.sequences.values()].filter((item) => item.review_required).map((item) => item.id);
  }

  function coverage() {
    const requiredT = requiredTransitions();
    const requiredS = requiredSequences();
    const transitionsComplete = !state.machine?.review_policy?.require_all_transitions || requiredT.every((id) => state.inspectedTransitions.has(id));
    const sequencesComplete = !state.machine?.review_policy?.require_all_sequences || requiredS.every((id) => state.inspectedSequences.has(id));
    return {
      transitions: { inspected: requiredT.filter((id) => state.inspectedTransitions.has(id)).length, required: requiredT.length, complete: transitionsComplete },
      sequences: { inspected: requiredS.filter((id) => state.inspectedSequences.has(id)).length, required: requiredS.length, complete: sequencesComplete },
      complete: !state.blocked && transitionsComplete && sequencesComplete,
    };
  }

  function localKey() {
    return `devlab:${window.__lab.taskId}:${window.__lab.candidateId}`;
  }

  function augmentReview(input = {}) {
    const runtime = window.__lab?.getRuntimeState?.() || {};
    const current = stateFromRuntime(runtime);
    const payload = {
      ...input,
      review_version: "1.2",
      transitions_inspected: [...state.inspectedTransitions],
      sequences_inspected: [...state.inspectedSequences],
      state_machine_review: {
        contract: MACHINE_FILE,
        current_state: current,
        coverage: coverage(),
        runtime_transition_capable: Boolean(state.runtimeCapabilities.transition),
        history: state.history.slice(-50),
      },
    };
    if (payload.runtime_review && typeof payload.runtime_review === "object") {
      payload.runtime_review = { ...payload.runtime_review, observed_state: current };
    }
    return payload;
  }

  function persistEvidence() {
    let base = window.__lab?.lastReview || {};
    try {
      const stored = JSON.parse(localStorage.getItem(localKey()) || "null");
      if (stored && typeof stored === "object") base = stored;
    } catch { /* optional local evidence */ }
    const payload = augmentReview(base);
    window.__lab.lastReview = payload;
    window.__lab.getReview = () => window.__lab.lastReview;
    window.__lab.exportReview = () => JSON.stringify(window.__lab.lastReview || {}, null, 2);
    try { localStorage.setItem(localKey(), JSON.stringify(payload)); } catch { /* optional local evidence */ }
    return payload;
  }

  function restoreEvidence() {
    let value = window.__lab?.lastReview || {};
    try { value = JSON.parse(localStorage.getItem(localKey()) || "null") || value; } catch { /* optional */ }
    for (const id of Array.isArray(value?.transitions_inspected) ? value.transitions_inspected : []) if (state.transitions.has(id)) state.inspectedTransitions.add(id);
    for (const id of Array.isArray(value?.sequences_inspected) ? value.sequences_inspected : []) if (state.sequences.has(id)) state.inspectedSequences.add(id);
    const history = value?.state_machine_review?.history;
    if (Array.isArray(history)) state.history = history.slice(-50).filter((item) => item && typeof item === "object");
  }

  function setMessage(kind, text) {
    const node = document.getElementById("status");
    if (!node) return;
    node.className = kind;
    node.textContent = text;
  }

  function rpc(command, payload = {}, timeout = 1800) {
    const frame = document.getElementById("runtime-frame");
    const target = frame?.contentWindow;
    if (!target) return Promise.reject(new Error("Live runtime iframe is unavailable"));
    const id = `ml-state-${Date.now()}-${++state.rpcCounter}`;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { state.pending.delete(id); reject(new Error(`Runtime command timed out: ${command}`)); }, timeout);
      state.pending.set(id, { resolve, reject, timer });
      target.postMessage({ source: "motionloom-devlab", id, command, payload }, "*");
    });
  }

  function onMessage(event) {
    const frame = document.getElementById("runtime-frame");
    if (!frame || event.source !== frame.contentWindow) return;
    const data = event.data;
    if (!data || data.source !== "motionloom-runtime" || !data.id) return;
    const pending = state.pending.get(data.id);
    if (!pending) return;
    state.pending.delete(data.id);
    clearTimeout(pending.timer);
    if (data.ok) pending.resolve(data.result);
    else pending.reject(new Error(data.error || "Runtime transition command failed"));
  }

  function transitionSupport(item) {
    if (item.mode === "select-animation") return { ok: true, reason: "clip switch" };
    if (state.descriptor?.mode !== "iframe") return { ok: false, reason: "requires iframe runtime" };
    if (!state.runtimeCapabilities.transition) return { ok: false, reason: "runtime adapter has no triggerTransition" };
    if (!state.runtimeCapabilities.state) return { ok: false, reason: "runtime state is not observable" };
    return { ok: true, reason: "runtime trigger" };
  }

  async function observeRuntimeTarget(targetState, timeout = 1200) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      let runtime = null;
      try { runtime = await rpc("getState", {}, 700); } catch { /* retry until deadline */ }
      const observed = stateFromRuntime(runtime || {});
      if (observed === targetState) return { observed, runtime };
      await new Promise((resolve) => setTimeout(resolve, 60));
    }
    throw new Error(`Runtime did not expose target state ${targetState}`);
  }

  async function executeTransition(id, options = {}) {
    const item = state.transitions.get(id);
    if (!item) throw new Error(`Unknown transition: ${id}`);
    const current = stateFromRuntime();
    state.currentState = current;
    if (item.from !== "*" && current !== item.from) throw new Error(`${item.label} requires state ${item.from}; current state is ${current || "unknown"}`);
    const support = transitionSupport(item);
    if (!support.ok) throw new Error(`${item.label} is unavailable: ${support.reason}`);

    const target = state.states.get(item.to);
    if (item.mode === "runtime-trigger") {
      await rpc("triggerTransition", { id: item.id, from: item.from, to: item.to, trigger: item.trigger, payload: item.payload });
      await observeRuntimeTarget(item.to);
    } else {
      await window.__lab.selectAnimation(target.animation);
      if (item.auto_play) await window.__lab.play();
      const observed = stateFromRuntime();
      if (observed !== item.to) throw new Error(`Target state mismatch after ${item.label}: expected ${item.to}, observed ${observed || "unknown"}`);
    }

    state.currentState = item.to;
    state.inspectedTransitions.add(item.id);
    state.history.push({ at: new Date().toISOString(), transition: item.id, from: current, to: item.to, mode: item.mode, sequence: options.sequence || null });
    if (state.history.length > 50) state.history = state.history.slice(-50);
    persistEvidence();
    render();
    window.dispatchEvent(new CustomEvent("motionloom:transition", { detail: { id: item.id, from: current, to: item.to, mode: item.mode } }));
    return getState();
  }

  async function resetState() {
    if (!state.machine) return;
    stopSequence();
    const initial = state.states.get(state.machine.initial_state);
    if (!initial) return;
    await window.__lab.selectAnimation(initial.animation);
    state.currentState = initial.id;
    render();
  }

  function stopSequence() {
    if (state.runningSequence) state.runningSequence.cancelled = true;
    state.runningSequence = null;
    render();
  }

  async function runSequence(id) {
    const sequence = state.sequences.get(id);
    if (!sequence) throw new Error(`Unknown state sequence: ${id}`);
    if (state.runningSequence) throw new Error("Another state sequence is already running");
    const token = { id, cancelled: false };
    state.runningSequence = token;
    render();
    try {
      for (const step of sequence.steps) {
        if (token.cancelled) throw new Error("State sequence stopped by reviewer");
        await executeTransition(step.transition, { sequence: id });
        if (step.wait_ms > 0) await new Promise((resolve) => setTimeout(resolve, step.wait_ms));
      }
      if (!token.cancelled) {
        state.inspectedSequences.add(id);
        persistEvidence();
        window.dispatchEvent(new CustomEvent("motionloom:sequence", { detail: { id, completed: true } }));
      }
    } finally {
      if (state.runningSequence === token) state.runningSequence = null;
      render();
    }
    return getState();
  }

  function getState() {
    state.currentState = stateFromRuntime();
    return {
      ready: Boolean(state.machine) && !state.blocked,
      blocked: state.blocked,
      currentState: state.currentState,
      initialState: state.machine?.initial_state || null,
      transitionsInspected: [...state.inspectedTransitions],
      sequencesInspected: [...state.inspectedSequences],
      runningSequence: state.runningSequence?.id || null,
      coverage: coverage(),
      history: state.history.slice(),
      runtimeCapabilities: { ...state.runtimeCapabilities },
    };
  }

  function buildPanel() {
    if (document.getElementById("state-machine-panel")) return;
    const nav = document.querySelector('nav[aria-label="Animation actions"]');
    if (!nav) return;
    const panel = document.createElement("section");
    panel.id = "state-machine-panel";
    panel.className = "state-machine-panel";
    panel.innerHTML = `
      <div class="state-machine-head"><div class="eyebrow" style="margin:0">State machine</div><button id="state-reset" type="button">Reset</button></div>
      <div class="state-machine-current"><span class="state-machine-dot"></span><strong id="state-current">—</strong><small id="state-current-animation"></small></div>
      <div id="state-transition-actions" class="state-machine-actions"></div>
      <div id="state-machine-coverage" class="state-machine-coverage"></div>
      <div id="state-sequences" class="sequence-row" hidden><select id="state-sequence-select" aria-label="State sequence"></select><button id="state-sequence-run" type="button">Run</button><button id="state-sequence-stop" type="button" disabled>Stop</button></div>
      <div id="state-machine-error" class="state-machine-error"></div>
      <div id="state-history" class="transition-history"></div>
    `;
    nav.append(panel);
    document.getElementById("state-reset")?.addEventListener("click", () => resetState().catch((error) => { setMessage("warn", error.message); }));
    document.getElementById("state-sequence-run")?.addEventListener("click", () => {
      const id = document.getElementById("state-sequence-select")?.value;
      if (id) runSequence(id).catch((error) => setMessage("warn", error.message));
    });
    document.getElementById("state-sequence-stop")?.addEventListener("click", stopSequence);
  }

  function render() {
    if (!state.machine) return;
    state.currentState = stateFromRuntime();
    const current = state.states.get(state.currentState);
    const currentNode = document.getElementById("state-current");
    const animationNode = document.getElementById("state-current-animation");
    if (currentNode) currentNode.textContent = current?.label || state.currentState || "Unknown";
    if (animationNode) animationNode.textContent = current?.animation || "—";

    const outgoing = [...state.transitions.values()].filter((item) => item.from === "*" || item.from === state.currentState);
    const actions = document.getElementById("state-transition-actions");
    if (actions) {
      if (!outgoing.length) {
        const empty = document.createElement("div"); empty.className = "transition-empty"; empty.textContent = "No declared transitions from this state."; actions.replaceChildren(empty);
      } else {
        actions.replaceChildren(...outgoing.map((item) => {
          const support = transitionSupport(item);
          const button = document.createElement("button");
          button.type = "button";
          button.className = `transition-btn${state.inspectedTransitions.has(item.id) ? " inspected" : ""}`;
          button.dataset.transition = item.id;
          button.disabled = !support.ok || Boolean(state.runningSequence);
          button.title = support.ok ? `${item.from} → ${item.to} · ${item.trigger}` : support.reason;
          const dot = document.createElement("span"); dot.className = "transition-dot";
          const copy = document.createElement("span"); copy.className = "transition-copy"; copy.textContent = `${item.label} → ${state.states.get(item.to)?.label || item.to}`;
          const mode = document.createElement("span"); mode.className = "transition-mode"; mode.textContent = item.mode === "runtime-trigger" ? "trigger" : "clip";
          button.append(dot, copy, mode);
          button.addEventListener("click", () => executeTransition(item.id).catch((error) => setMessage("warn", error.message)));
          return button;
        }));
      }
    }

    const c = coverage();
    const coverageNode = document.getElementById("state-machine-coverage");
    if (coverageNode) coverageNode.textContent = `Transition review ${c.transitions.inspected}/${c.transitions.required}${c.sequences.required ? ` · Sequences ${c.sequences.inspected}/${c.sequences.required}` : ""}`;

    const sequenceRow = document.getElementById("state-sequences");
    const sequenceSelect = document.getElementById("state-sequence-select");
    if (sequenceRow && sequenceSelect) {
      sequenceRow.hidden = state.sequences.size === 0;
      const selected = sequenceSelect.value;
      sequenceSelect.replaceChildren(...[...state.sequences.values()].map((sequence) => {
        const option = document.createElement("option"); option.value = sequence.id; option.textContent = `${state.inspectedSequences.has(sequence.id) ? "✓ " : ""}${sequence.label}`; return option;
      }));
      if (state.sequences.has(selected)) sequenceSelect.value = selected;
    }
    const run = document.getElementById("state-sequence-run");
    const stop = document.getElementById("state-sequence-stop");
    if (run) run.disabled = Boolean(state.runningSequence) || state.sequences.size === 0;
    if (stop) stop.disabled = !state.runningSequence;

    const history = document.getElementById("state-history");
    if (history) {
      const items = state.history.slice(-6).reverse();
      if (!items.length) {
        const empty = document.createElement("div"); empty.className = "transition-empty"; empty.textContent = "Transition history will appear here."; history.replaceChildren(empty);
      } else {
        history.replaceChildren(...items.map((item) => {
          const row = document.createElement("div"); row.className = "transition-history-item";
          const time = document.createElement("span"); time.textContent = new Date(item.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
          const copy = document.createElement("span"); const name = state.transitions.get(item.transition)?.label || item.transition; copy.innerHTML = `<b></b> ${item.from || "?"} → ${item.to}`; copy.querySelector("b").textContent = name;
          row.append(time, copy); return row;
        }));
      }
    }

    const error = document.getElementById("state-machine-error");
    if (error) error.textContent = state.blocked ? `STATE MACHINE BLOCKED · ${state.blocked}` : "";
    const confirm = document.getElementById("confirm");
    if (confirm) {
      confirm.classList.toggle("state-machine-gated", !c.complete);
      confirm.title = !c.complete ? "State/transition review requirements are incomplete" : "";
    }
  }

  function guardApproval(event) {
    const c = coverage();
    if (state.blocked || !c.complete) {
      event.preventDefault();
      event.stopImmediatePropagation();
      const missingTransitions = requiredTransitions().filter((id) => !state.inspectedTransitions.has(id));
      const missingSequences = requiredSequences().filter((id) => !state.inspectedSequences.has(id));
      const details = [missingTransitions.length ? `transitions: ${missingTransitions.join(", ")}` : "", missingSequences.length ? `sequences: ${missingSequences.join(", ")}` : ""].filter(Boolean).join(" · ");
      setMessage("warn", state.blocked ? `State-machine review is blocked: ${state.blocked}` : `State-machine review incomplete${details ? ` · ${details}` : ""}`);
      return;
    }
    setTimeout(persistEvidence, 0);
  }

  async function init() {
    if (!(await waitForLab())) return;
    let descriptor;
    try { descriptor = await fetchJson(`${safeBase}/devlab-runtime.json`, true); } catch { return; }
    if (!descriptor || !Array.isArray(descriptor.files) || !descriptor.files.includes(MACHINE_FILE)) return;
    state.descriptor = descriptor;
    installStyles();
    buildPanel();
    window.addEventListener("message", onMessage);

    try {
      const raw = await fetchJson(`${safeBase}/${MACHINE_FILE}`);
      state.machine = validateMachine(raw);
      if (descriptor.mode === "iframe") {
        const handshake = await rpc("handshake", {}, 1500);
        state.runtimeCapabilities = handshake?.capabilities || {};
      }
      state.currentState = stateFromRuntime();
      restoreEvidence();
      persistEvidence();
    } catch (error) {
      state.blocked = error instanceof Error ? error.message : String(error);
    }

    const confirm = document.getElementById("confirm");
    const requestChanges = document.getElementById("request-changes");
    confirm?.addEventListener("click", guardApproval, true);
    requestChanges?.addEventListener("click", () => setTimeout(persistEvidence, 0), true);
    state.pollTimer = setInterval(render, 250);
    render();

    window.__lab.stateMachine = {
      ready: !state.blocked,
      error: state.blocked,
      listStates: () => [...state.states.values()].map((item) => ({ ...item })),
      listTransitions: () => [...state.transitions.values()].map((item) => ({ ...item })),
      listSequences: () => [...state.sequences.values()].map((item) => ({ ...item, steps: item.steps.map((step) => ({ ...step })) })),
      getState,
      getCoverage: coverage,
      triggerTransition: executeTransition,
      runSequence,
      stopSequence,
      resetState,
      dispose: () => {
        clearInterval(state.pollTimer);
        stopSequence();
        window.removeEventListener("message", onMessage);
        for (const pending of state.pending.values()) { clearTimeout(pending.timer); pending.reject(new Error("State transition tester disposed")); }
        state.pending.clear();
      },
    };
  }

  init();
})();
