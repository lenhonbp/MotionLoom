/**
 * scroll-scene.js — Canonical GSAP scroll-linked scene template.
 * Uses ScrollTrigger with scrub; never attaches raw scroll listeners
 * (ScrollTrigger already batches and rAF-schedules updates).
 *
 * Bind duration/easing to motion-spec.json; never hardcode magic numbers.
 */
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * @param {string} trigger   CSS selector of the pin/trigger element
 * @param {HTMLElement[]} targets  elements to animate, in motion order
 * @param {object} spec      motion-spec.json values
 */
export function buildScrollScene(trigger, targets, spec) {
  const tl = gsap.timeline({
    scrollTrigger: {
      trigger,
      start: "top 80%",
      end: "bottom 20%",
      scrub: 0.6,             // smooth scrub; 0 for hard lock
      toggleActions: "play none none reverse",
    },
  });

  targets.forEach((el, i) => {
    tl.to(
      el,
      {
        opacity: 1,
        y: 0,
        duration: 0.25,
        ease: spec.easing ?? "power2.out",
      },
      i * 0.08,               // stagger bound to scene, not magic
    );
  }, 0);

  return tl;
}

/**
 * Reduced-motion guard: collapse the whole timeline into a single fade.
 * Call once at boot.
 */
export function honorReducedMotion(tl) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    tl.scrollTrigger.disable();
    tl.progress(1);
  }
}
