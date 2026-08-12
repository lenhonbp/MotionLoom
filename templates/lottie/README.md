# Lottie / dotLottie Templates

Scaffold every Lottie scene from this directory. The workflow: copy `scaffold/` into `src/output/<scene>/`, replace `assets/svg-source.svg` with the authoritative vector art, run the generation prompt against the spec, then convert the resulting `animation.json` into `animation.lottie` (see `scripts/to-dotlottie.sh`).

## Files

| File | Purpose |
|---|---|
| `scaffold/animation.json` | Minimal valid Bodymovin v5.12 document — the canonical shape every generated file must validate against |
| `scaffold/character-rig.svg` | Cutout avatar ready for `src/rig/cutout_rig.py build` |
| `player.html` | Standalone dotLottie player for quick local inspection (`open player.html`) |
| `react-component.tsx` | Production React component using `@lottiefiles/dotlottie-react` with worker offload and reduced-motion support |
| `vanilla.js` | Production vanilla-js bootstrap with `DotLottieWorker` and visibility freeze |

## Generation prompt recipe (for coding agents)

> Create a Lottie animation from the SVG path in `<source url>`. Reveal the path with an animation that follows the natural path direction. Apply a premium gradient bound to the project's primary/accent tokens. Use ease-in-out timing, a transparent background, preserve the original SVG geometry, 60 fps, total `<N>` frames. Expose the primary color as a dotLottie slot named `primary-color`.

## Validation

A generated file is accepted only if `scripts/validate-lottie.py` passes: version header, frame count vs. spec, layer count under budget, and slot names matching the brand spec.
