(() => {
  const REQUEST_SOURCE = "motionloom-devlab";
  const RESPONSE_SOURCE = "motionloom-runtime";
  let adapter = null;

  function asAnimations(value) {
    return Array.isArray(value) ? value.map((item) => {
      if (typeof item === "string") return { id: item, label: item };
      return item && typeof item === "object" ? item : null;
    }).filter(Boolean) : [];
  }

  async function invoke(command, payload = {}) {
    if (!adapter) throw new Error("MotionLoom runtime adapter is not attached");
    if (command === "handshake") {
      const animations = typeof adapter.listAnimations === "function"
        ? asAnimations(await adapter.listAnimations())
        : asAnimations(adapter.animations);
      return {
        ready: adapter.ready !== false,
        runtime: adapter.runtime || "unknown",
        framework: adapter.framework || "unknown",
        animations,
        capabilities: {
          selectAnimation: typeof adapter.selectAnimation === "function",
          transition: typeof adapter.triggerTransition === "function",
          play: typeof adapter.play === "function",
          pause: typeof adapter.pause === "function",
          restart: typeof adapter.restart === "function" || typeof adapter.seek === "function" || typeof adapter.setProgress === "function",
          seek: typeof adapter.seek === "function" || typeof adapter.setProgress === "function",
          step: typeof adapter.stepFrames === "function",
          speed: typeof adapter.setSpeed === "function",
          loop: typeof adapter.setLoop === "function",
          state: typeof adapter.getState === "function"
        },
        state: typeof adapter.getState === "function" ? await adapter.getState() : {}
      };
    }
    if (command === "listAnimations") {
      return typeof adapter.listAnimations === "function"
        ? asAnimations(await adapter.listAnimations())
        : asAnimations(adapter.animations);
    }
    if (command === "selectAnimation") {
      if (typeof adapter.selectAnimation !== "function") throw new Error("selectAnimation is not supported");
      return adapter.selectAnimation(payload.id);
    }
    if (command === "triggerTransition") {
      if (typeof adapter.triggerTransition !== "function") throw new Error("triggerTransition is not supported");
      return adapter.triggerTransition({
        id: payload.id,
        from: payload.from,
        to: payload.to,
        trigger: payload.trigger,
        payload: payload.payload && typeof payload.payload === "object" ? payload.payload : {}
      });
    }
    if (command === "play" || command === "pause" || command === "setSpeed" || command === "setLoop" || command === "stepFrames") {
      const method = command;
      if (typeof adapter[method] !== "function") throw new Error(`${command} is not supported`);
      if (command === "setSpeed") return adapter[method](payload.rate);
      if (command === "setLoop") return adapter[method](Boolean(payload.enabled));
      if (command === "stepFrames") return adapter[method](Number(payload.delta || 0));
      return adapter[method]();
    }
    if (command === "restart") {
      if (typeof adapter.restart === "function") return adapter.restart();
      if (typeof adapter.seek === "function") return adapter.seek(0);
      if (typeof adapter.setProgress === "function") return adapter.setProgress(0);
      throw new Error("restart is not supported");
    }
    if (command === "seek") {
      const progress = Math.max(0, Math.min(1, Number(payload.progress || 0)));
      if (typeof adapter.seek === "function") return adapter.seek(progress);
      if (typeof adapter.setProgress === "function") return adapter.setProgress(progress);
      throw new Error("seek is not supported");
    }
    if (command === "getState") {
      return typeof adapter.getState === "function" ? adapter.getState() : {};
    }
    throw new Error(`Unknown MotionLoom runtime command: ${command}`);
  }

  window.addEventListener("message", async (event) => {
    const data = event.data;
    if (!data || data.source !== REQUEST_SOURCE || !data.id || typeof data.command !== "string") return;
    try {
      const result = await invoke(data.command, data.payload || {});
      event.source?.postMessage({ source: RESPONSE_SOURCE, id: data.id, ok: true, result }, "*");
    } catch (error) {
      event.source?.postMessage({
        source: RESPONSE_SOURCE,
        id: data.id,
        ok: false,
        error: error instanceof Error ? error.message : String(error)
      }, "*");
    }
  });

  window.MotionLoomRuntimeBridge = {
    attach(nextAdapter) {
      if (!nextAdapter || typeof nextAdapter !== "object") throw new Error("A runtime adapter object is required");
      adapter = nextAdapter;
      window.parent?.postMessage({ source: RESPONSE_SOURCE, event: "attached" }, "*");
      return nextAdapter;
    },
    detach() { adapter = null; }
  };
})();
