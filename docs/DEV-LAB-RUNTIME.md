# Dev Lab live runtime contract

Dev Lab is the human review surface for the exact MotionLoom candidate. Static 0/50/100 snapshots remain deterministic evidence, but they are not an interactive runtime. A scene that can expose live playback SHOULD add `devlab-runtime.json` beside `manifest.json` and `motion-spec.json`.

The descriptor is scene-local and hash-bound by `scripts/review-hook.py`. Every path in `files`, `entrypoint`, and `animations[].frames` must be a relative path inside the scene directory. Path traversal, absolute paths, symlinked files, missing files, duplicate animation ids, or references outside `files` fail closed. The browser candidate records the resulting runtime bundle SHA-256; changing any declared runtime byte invalidates that candidate.

## Sprite sequence example

```json
{
  "schema_version": "1.0",
  "mode": "sprite-sequence",
  "files": [
    "sprites/idle-00.png",
    "sprites/idle-01.png",
    "sprites/walk-00.png",
    "sprites/walk-01.png"
  ],
  "default_animation": "idle",
  "animations": [
    {
      "id": "idle",
      "label": "Idle",
      "fps": 8,
      "frames": ["sprites/idle-00.png", "sprites/idle-01.png"],
      "loop": true,
      "review_required": true
    },
    {
      "id": "walk",
      "label": "Walk",
      "fps": 12,
      "frames": ["sprites/walk-00.png", "sprites/walk-01.png"],
      "loop": true,
      "review_required": true
    }
  ],
  "controls": {
    "play": true,
    "pause": true,
    "restart": true,
    "seek": true,
    "step": true,
    "speed": true,
    "loop": true
  },
  "viewport": {
    "canvas_width": 1920,
    "canvas_height": 1920,
    "pixel_art": true,
    "baseline_y": 1626,
    "pivot": { "x": 940, "y": 1626 },
    "background": "checker"
  },
  "review_policy": { "require_all_animations": true }
}
```

Dev Lab renders the declared frame bytes directly and drives them with a real clock. Play, pause, restart, scrub, frame-step, loop and speed therefore operate on the same candidate frames that are being reviewed. Action names such as `idle`, `walk`, `run`, `attack`, `hurt` or project-specific clips are data, not hard-coded UI.

## Iframe runtime example

Use `mode: "iframe"` when the candidate already has a browser runtime (for example Rive, Lottie, GSAP, Framer Motion, Three.js or a project-specific player). The descriptor adds an `entrypoint`, and that entrypoint exposes a controller through `runtime-bridge.js`:

```html
<script src="/runtime-bridge.js"></script>
<script type="module">
  const adapter = {
    runtime: "example-player@1",
    framework: "custom",
    animations: [{ id: "idle", label: "Idle", loop: true }],
    listAnimations() { return this.animations; },
    selectAnimation(id) { /* select exact clip */ },
    play() { /* play */ },
    pause() { /* pause */ },
    restart() { /* restart */ },
    seek(progress) { /* normalized 0..1 */ },
    stepFrames(delta) { /* optional */ },
    setSpeed(rate) { /* optional */ },
    setLoop(enabled) { /* optional */ },
    getState() { return { progress: 0, currentTime: 0, duration: 1, frame: 0, totalFrames: 60 }; }
  };
  MotionLoomRuntimeBridge.attach(adapter);
</script>
```

The parent Dev Lab communicates by `postMessage`; the runtime never grants approval. If the live runtime cannot load or a declared control is unavailable, Dev Lab disables that control and shows an explicit live-runtime failure/fallback state. It must not relabel captured PNG evidence as live runtime.

## Review semantics

Dev Lab records which actions the reviewer actually selected. When `review_policy.require_all_animations` is true, approval is disabled until every `review_required` action has been inspected. A user may still request changes at any time. Playback success, runtime readiness, hashes, snapshots, telemetry and automated checks remain evidence only; `approved` is always an explicit user review decision.

The deterministic snapshot harness continues to use `window.__lab.selectAnimation()` and `window.__lab.seek()`. For live candidates those calls drive the same runtime controller shown to the user; for legacy scenes without `devlab-runtime.json`, Dev Lab clearly enters `captured-evidence` mode and retains the older checkpoint viewer as a compatibility fallback.
