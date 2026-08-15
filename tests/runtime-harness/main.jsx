import React from "react";
import { createRoot } from "react-dom/client";
import { gsap } from "gsap";
import { Rive } from "@rive-app/canvas";
import { FramerRuntimePilot } from "../../src/output/runtime-pilot-framer/scene.jsx";

const params = new URLSearchParams(window.location.search);
const framework = params.get("framework") || "gsap";
const statusNode = document.getElementById("status");
const rootNode = document.getElementById("root");

function status(text) {
  if (statusNode) statusNode.textContent = text;
}

function expose(adapter) {
  window.__animationAdapter = adapter;
  status(`${adapter.framework}: ${adapter.status}`);
}

function mountGsap() {
  const stage = document.createElement("div");
  stage.className = "stage";
  const box = document.createElement("div");
  box.className = "gsap-box";
  stage.appendChild(box);
  rootNode.replaceChildren(stage);
  const timeline = gsap.timeline({ paused: true });
  timeline.fromTo(
    box,
    { x: 0, y: 0, rotation: 0, opacity: 0.25, scale: 0.82 },
    { x: 240, y: -36, rotation: 28, opacity: 1, scale: 1, duration: 1, ease: "power2.out" },
  );
  const adapter = {
    framework: "gsap",
    runtime: `gsap@${gsap.version}`,
    status: "ready",
    ready: true,
    setProgress(value) { timeline.progress(Math.max(0, Math.min(1, Number(value)))); },
    getState() { return { progress: timeline.progress(), transform: getComputedStyle(box).transform, opacity: getComputedStyle(box).opacity }; },
  };
  expose(adapter);
  adapter.setProgress(0);
}

async function mountRive() {
  const canvas = document.createElement("canvas");
  canvas.width = 420;
  canvas.height = 420;
  rootNode.replaceChildren(canvas);
  let riveInstance;
  const bytes = await fetch("/assets/library/rive/state-machine-test.riv").then((response) => {
    if (!response.ok) throw new Error(`Rive fixture HTTP ${response.status}`);
    return response.arrayBuffer();
  });
  await new Promise((resolve, reject) => {
    riveInstance = new Rive({
      buffer: bytes,
      canvas,
      stateMachines: "StateMachine",
      autoplay: true,
      autoBind: false,
      onLoad: resolve,
      onLoadError: reject,
    });
  });
  riveInstance.resizeDrawingSurfaceToCanvas();
  riveInstance.pause();
  const inputs = riveInstance.stateMachineInputs("StateMachine") || [];
  const byName = Object.fromEntries(inputs.map((input) => [input.name, input]));
  if (!byName.MyNum || !byName.MyBool || !byName.MyTrig) {
    throw new Error(`Rive StateMachine inputs missing: ${inputs.map((input) => input.name).join(", ")}`);
  }
  const adapter = {
    framework: "rive",
    runtime: "@rive-app/canvas@2.39.2",
    status: "ready",
    ready: true,
    setProgress(value) {
      const progress = Math.max(0, Math.min(1, Number(value)));
      byName.MyNum.value = progress * 12;
      byName.MyBool.value = progress >= 0.5;
      if (progress > 0) byName.MyTrig.fire();
      if (typeof riveInstance.advance === "function") riveInstance.advance(1 / 60);
    },
    getState() {
      return {
        inputs: inputs.map((input) => ({ name: input.name, type: input.type, value: input.value })),
        stateMachines: riveInstance.playingStateMachineNames,
        loaded: riveInstance.loaded,
      };
    },
    dispose() { riveInstance.cleanup(); },
  };
  expose(adapter);
  adapter.setProgress(0);
}

async function main() {
  try {
    if (framework === "gsap") mountGsap();
    else if (framework === "framer-motion") createRoot(rootNode).render(<FramerRuntimePilot expose={expose} />);
    else if (framework === "rive") await mountRive();
    else throw new Error(`Unknown framework: ${framework}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    expose({ framework, status: "error", ready: false, error: message, getState: () => ({ error: message }) });
  }
}

main();
