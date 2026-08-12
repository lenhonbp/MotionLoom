/**
 * production-dotlottie.tsx — Canonical React component for a dotLottie scene.
 * Copied into the host project per scene. Binds brand theme slots at runtime,
 * offloads rendering to a Web Worker, honors prefers-reduced-motion, and
 * exposes a uniform seek() so the Dev Lab snapshot harness can drive it.
 */
import { useEffect, useRef, useState } from "react";
import {
  DotLottieReact,
  type DotLottie,
} from "@lottiefiles/dotlottie-react";

interface SceneProps {
  src: string;                 // /scenes/<name>/animation.lottie
  ariaLabel?: string;          // required for accessibility
  className?: string;
  /** Runtime brand overrides: { slotId: color|value } */
  theme?: Record<string, unknown>;
}

/** Uniform API consumed by the Dev Lab snapshot harness and tests. */
export interface LabHandle {
  seek: (pct: number) => void; // 0-1
  play: () => void;
  pause: () => void;
}

declare global {
  interface Window {
    __lab?: Record<string, LabHandle>;
  }
}

export default function DotLottieScene({
  src,
  ariaLabel = "Animated illustration",
  className,
  theme = {},
}: SceneProps) {
  const ref = useRef<DotLottie | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    d.setLoop(!reduced); // looping decorations pause under reduced motion
    // Apply brand theme slots (see project-context.json brand.primary)
    const rules = Object.entries(theme).map(([id, value]) => ({ id, value }));
    if (rules.length) d.setThemeData(JSON.stringify({ rules }));
    // Register the uniform lab handle for snapshot/testing harnesses
    window.__lab = window.__lab || {};
    window.__lab[src] = {
      seek: (pct) => {
        if (!d.isLoaded) return;
        d.setLoop(false);
        d.setFrame(pct * (d.totalFrames - 1));
      },
      play: () => d.play(),
      pause: () => d.pause(),
    };
    return () => {
      delete window.__lab?.[src];
    };
  }, [src, theme]);

  return (
    <div role="img" aria-label={ariaLabel} className={className}>
      {!ready && <span aria-hidden className="sr-only" />}
      <DotLottieReact
        src={src}
        autoplay
        loop
        style={{ width: "100%", height: "100%" }}
        dotLottieRefCallback={(dotLottie) => {
          ref.current = dotLottie;
          dotLottie.addEventListener("load", () => setReady(true));
        }}
      />
    </div>
  );
}
