/**
 * production-vanilla.js — Canonical vanilla-JS bootstrap for a dotLottie scene.
 * Uses DotLottieWorker to keep the main thread free, freezes when offscreen,
 * honors prefers-reduced-motion, and registers the uniform window.__lab handle.
 */
import { DotLottieWorker } from "@lottiefiles/dotlottie-web";

/**
 * @param {HTMLCanvasElement} canvas
 * @param {string} src
 * @param {object} [opts]
 * @param {Record<string, unknown>} [opts.theme]  brand slot overrides
 * @param {string} [opts.ariaLabel]
 */
export function mountLottieScene(canvas, src, opts = {}) {
  const dotLottie = new DotLottieWorker({
    canvas,
    src,
    autoplay: true,
    loop: true,
    renderConfig: { autoResize: true },
  });

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  dotLottie.addEventListener("load", () => {
    if (reduced) dotLottie.setLoop(false);
    if (opts.theme) {
      const rules = Object.entries(opts.theme).map(([id, value]) => ({ id, value }));
      dotLottie.setThemeData(JSON.stringify({ rules }));
    }
    // Uniform lab handle for the Dev Lab snapshot harness
    window.__lab = window.__lab || {};
    window.__lab[src] = {
      seek: (pct) => {
        dotLottie.setLoop(false);
        dotLottie.setFrame(pct * (dotLottie.totalFrames - 1));
      },
      play: () => dotLottie.play(),
      pause: () => dotLottie.pause(),
    };
  });

  // Interactive hooks: hover plays, click restarts
  canvas.addEventListener("mouseenter", () => dotLottie.play());
  canvas.addEventListener("mouseleave", () => dotLottie.pause());
  canvas.addEventListener("click", () => {
    dotLottie.setFrame(0);
    dotLottie.setLoop(false);
    dotLottie.play();
  });

  // Cleanup on removal
  const observer = new MutationObserver((records) => {
    for (const r of records) {
      for (const node of r.removedNodes) {
        if (node === canvas) {
          dotLottie.destroy();
          observer.disconnect();
          delete window.__lab?.[src];
        }
      }
    }
  });
  observer.observe(canvas.parentElement ?? document.body, { childList: true });

  return dotLottie;
}
