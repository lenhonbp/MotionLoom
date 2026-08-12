# Animation Category Taxonomy

Every request must be classified into exactly one category before generation. The category determines the framework shortlist, the default duration/FPS/loop contract, and the rigging approach.

| Category | Key signals | Contract |
|---|---|---|
| ui-micro | button, toggle, toast, hover, focus, feedback | 0.2–0.6 s, 60 fps, no loop, ease-in-out |
| loading | spinner, skeleton, progress, shimmer | 0.8–1.5 s, loop true, dotLottie |
| hero-scene | marketing, landing, camera push/pan/tilt | 2–8 s, camera motion, optional state machine |
| character-body | avatar, mascot, idle/walk/emote | cutout rig, 30 fps, loop true, parent-first bone order |
| icon-animation | glyph reveal, state change, path draw | ≤0.8 s, path-draw or morph, theme slot bound |
| scroll-linked | parallax, pin, scroll progress | GSAP ScrollTrigger, scrub |
| data-viz | charts, counters, transitions | tweened values, accessible reduced-motion alternative |
| 3d-scene | model turntable, shader, WebGL | threejs/R3F, ≤60 fps, memory budget |

When a request spans categories (e.g., a hero with an animated character), decompose it: the character body becomes a `character-body` scene, the surrounding motion a `hero-scene`, and the Dev Lab composes both.
