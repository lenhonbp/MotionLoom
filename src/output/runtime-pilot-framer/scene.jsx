import React, { useEffect, useRef } from "react";
import { motion, motionValue, useTransform } from "framer-motion";

/**
 * MotionLoom runtime-first pilot source.
 * Design: code-authored, deterministic scrub only; review remains human-gated.
 */
export const RUNTIME_PILOT_CONTRACT = Object.freeze({
  framework: "framer-motion",
  checkpoints: [0, 50, 100],
  durationSeconds: 1.2,
  loop: true,
  sourceAuthority: "code_authored",
});

export function FramerRuntimePilot({ expose }) {
  const progress = useRef(motionValue(0)).current;
  const x = useTransform(progress, [0, 0.5, 1], [0, 176, 240]);
  const y = useTransform(progress, [0, 0.5, 1], [0, -48, -36]);
  const rotate = useTransform(progress, [0, 0.5, 1], [0, -14, 28]);
  const opacity = useTransform(progress, [0, 0.15, 1], [0.28, 1, 1]);
  const scale = useTransform(progress, [0, 0.5, 1], [0.82, 1.06, 1]);

  useEffect(() => {
    const box = document.querySelector(".runtime-pilot-box");
    const adapter = {
      framework: RUNTIME_PILOT_CONTRACT.framework,
      runtime: "framer-motion@13.1.0",
      status: "ready",
      ready: true,
      setProgress(value) {
        progress.set(Math.max(0, Math.min(1, Number(value))));
      },
      getState() {
        return {
          progress: progress.get(),
          transform: box ? getComputedStyle(box).transform : "",
          opacity: box ? getComputedStyle(box).opacity : "",
          contract: RUNTIME_PILOT_CONTRACT,
        };
      },
    };
    expose(adapter);
    adapter.setProgress(0);
  }, [expose, progress]);

  return (
    <div className="stage" aria-label="MotionLoom Framer Motion runtime pilot">
      <motion.div className="motion-box runtime-pilot-box" style={{ x, y, rotate, opacity, scale }} />
    </div>
  );
}
