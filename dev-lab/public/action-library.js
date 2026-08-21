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
