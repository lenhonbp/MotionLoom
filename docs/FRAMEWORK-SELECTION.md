# Framework Selection Matrix

The selection rule is deterministic: bind first to the host project's existing stack (from `project-context.json`), then to the category's optimal runtime, then fall back in the order below. The goal is zero new runtime dependencies per delivered scene unless the category demands it.

| Category | Primary | Secondary | Fallback | Notes |
|---|---|---|---|---|
| ui-micro | framer-motion | gsap | css | Use when React present; pure CSS for hover-only states |
| loading | lottie (dotLottie) | framer-motion | css | Embedded assets + theming slots; loop true |
| hero-scene | lottie (dotLottie) | gsap | threejs | dotLottie state machines for scroll+hover interactivity |
| character-body | lottie (dotLottie) | spine | — | Spine runtimes free but require a Spine license policy note |
| icon-animation | lottie | framer-motion | css | Path-draw reveals; ≤200 KB target |
| scroll-linked | gsap | framer-motion | — | ScrollTrigger; `toggleActions` over manual listeners |
| data-viz | gsap | framer-motion | threejs | Numbers: GSAP `to()` with `innerText` plugin pattern |
| 3d-scene | threejs | — | — | React Three Fiber when React present |

## License discipline

Lottie/dotLottie (MIT) and Anime.js (MIT) are safe defaults for any commercial product. GSAP's core is free but large-scale commercial deployments should verify the license tier; never bundle GSAP Club plugins without a license file in the repo. Spine runtimes integrate free of charge, but end users of your software need their own Spine license — record this in the scene manifest under `license_note`. Rive runtimes are free (Apache-2.0) with the Rive editor subject to its own terms.

## Why dotLottie over raw JSON

The dotLottie container is smaller than raw Lottie JSON, can hold multiple animations, embeds images and fonts, and adds state machines and theme slots (color/scalar/vector/gradient/text/image) — the canonical theming spec that keeps animations aligned with brand tokens extracted by the analyzer. Always generate `.lottie`; keep the JSON only as a debug artifact.

## Performance budget

Every scene must ship under these limits or it fails the Dev Lab checklist: Lottie UI assets ≤300 KB (hero ≤1500 KB), ≤80 layers, 60 fps standard (30 fps acceptable for body rigs), and durations ≤2 s for UI / ≤8 s for scenes. The snapshot renderer enforces these at PR time via CI (see `.github/workflows/quality.yml`).
