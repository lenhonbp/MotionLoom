# Audit research notes

## Official runtime findings

The LottieFiles runtime documentation describes dotLottie players as supporting both Lottie JSON and `.lottie`, with a shared runtime core, state machines, theming, multiple animations, and Web Worker support across distributions. Its web player comparison lists React, Vue, Svelte, JavaScript, and Web Component variants and distinguishes SSR compatibility. Source: https://docs.lottiefiles.com/en/runtimes

The Rive runtime documentation defines state machines as the logic controlling interactive animations in a Rive file. The audit implication is that a Rive template must model named state machines and inputs, not merely render a static `.riv` file. Source: https://rive.app/docs/runtimes/state-machines

## Audit implications

1. A format validator must distinguish a valid JSON payload from an actually renderable runtime artifact and should verify the runtime entrypoint rather than only header fields.
2. The project context must be an explicit input to selection, generation, theming, and validation; producing `project-context.json` alone is insufficient.
3. The Dev Lab must load the same scene output and signed spec that CI validates. A visually convincing demo that is disconnected from `src/output/<scene>/` is not an end-to-end acceptance test.
4. Fallback placeholder snapshots must never be accepted as production evidence. They are useful only for local diagnostics and must be marked or rejected by the quality gate.
5. Interactive runtime templates need a11y/reduced-motion behavior and explicit state/input contracts, not only playback controls.

The GSAP accessibility guidance recommends using `prefers-reduced-motion`, then reducing or removing motion depending on whether it is functional or decorative; it also calls out fast flashing and large swiping motion as potential triggers. Source: https://gsap.com/resources/a11y/

The dotLottie v2 specification exposes separate package sections for the file structure, manifest, animations, assets, themes, and state machines. The audit implication is that a `.lottie` validator should not assume the first JSON member is the authoritative animation; it should inspect the package manifest and resolve the declared animation entry. Source: https://dotlottie.io/spec/2.0/
