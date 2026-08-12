/**
 * ui-micro.tsx — Canonical Framer Motion micro-interaction component.
 * Durations and easings come from motion-spec.json / the project manifest,
 * never from inline magic numbers.
 */
import { motion, type MotionProps, useReducedMotion } from "framer-motion";

export interface MicroSpec {
  duration: number;   // seconds, from motion-spec.json
  easing: string;     // canonical easing name
}

const EASE_MAP: Record<string, [number, number, number, number]> = {
  "ease-in-out": [0.42, 0, 0.58, 1],
  "ease-out": [0, 0, 0.58, 1],
  "ease-in": [0.42, 0, 1, 1],
  spring: [0.34, 1.56, 0.64, 1] as unknown as [number, number, number, number],
};

/** Shared press-scale treatment for buttons/cards (the project-wide default). */
export const pressable: MotionProps = {
  whileHover: { scale: 1.03, transition: { type: "spring", stiffness: 400, damping: 25 } },
  whileTap: { scale: 0.97 },
};

/**
 * Wrap any child with the project's entrance motion. Use on cards, rows,
 * and list items. The stagger offset is computed, not magic.
 */
export function entrance({ duration, easing }: MicroSpec, index = 0) {
  return {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    transition: {
      duration,
      ease: EASE_MAP[easing] ?? EASE_MAP["ease-in-out"],
      delay: index * duration * 0.25,
    },
  };
}

/** Reduced-motion aware variant component. */
export function MotionSafe(props: MotionProps & { as?: keyof JSX.IntrinsicElements }) {
  const reduce = useReducedMotion();
  const { as = "div", ...rest } = props;
  return motion[as]({
    ...rest,
    transition: reduce ? { duration: 0 } : rest.transition,
  });
}
