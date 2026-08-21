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
  "groups": [
    { "id": "locomotion", "label": "Locomotion", "order": 10 },
    { "id": "combat", "label": "Combat", "order": 20 }
  ],
  "animations": [
    {
      "id": "idle",
      "label": "Idle",
      "group": "locomotion",
      "tags": ["stance", "loop"],
      "fps": 8,
      "frames": ["sprites/idle-00.png", "sprites/idle-01.png"],
      "loop": true,
      "review_required": true
    },
    {
      "id": "walk",
      "label": "Walk",
      "group": "locomotion",
      "tags": ["movement", "grounded"],
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

## Large action libraries

`animations` has no product-level fixed action vocabulary. A consumer can add `jump`, `dash`, `parry`, `skill-fireball`, `teleport-strike`, emotes, cinematic clips, state-machine entries, or any other valid action id and Dev Lab will expose it automatically.

For larger character or UI sets, use optional `groups` plus `animations[].group` and `animations[].tags`. Dev Lab turns those fields into an Action Library with search, group chips, collapsible group sections, and filters for review-required, unreviewed, looping, and one-shot actions. Group metadata changes presentation only; it does not grant runtime capability or approval.

Examples of useful project-defined groups are `locomotion`, `combat`, `skills`, `reactions`, `emotes`, or domain-specific categories. These names are not reserved by MotionLoom. Actions without a declared group remain visible under `Other` rather than being dropped.

Search matches action id, label, group label, tags, and declared events. Filtering never weakens the review gate: hidden required actions still count as unreviewed until the user actually selects them. The selected action remains visible in the `Unreviewed` filter so the reviewer does not lose the current runtime context immediately after opening it.

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
    triggerTransition(request) { /* optional: drive a real runtime state transition */ },
    getState() { return { progress: 0, currentTime: 0, duration: 1, frame: 0, totalFrames: 60, state: "idle" }; }
  };
  MotionLoomRuntimeBridge.attach(adapter);
</script>
```

The parent Dev Lab communicates by `postMessage`; the runtime never grants approval. If the live runtime cannot load or a declared control is unavailable, Dev Lab disables that control and shows an explicit live-runtime failure/fallback state. It must not relabel captured PNG evidence as live runtime.

## State and transition review

A candidate may additionally declare `devlab-state-machine.json` when the reviewer needs to test behavior across clips instead of inspecting each action in isolation. The state-machine file only participates in the candidate runtime hash when it is explicitly listed in `devlab-runtime.json.files`; undeclared state-machine bytes are not accepted as review evidence.

A minimal portable contract can use `select-animation` transitions:

```json
{
  "schema_version": "1.0",
  "initial_state": "idle",
  "states": [
    { "id": "idle", "label": "Idle", "animation": "idle" },
    { "id": "run", "label": "Run", "animation": "run" },
    { "id": "attack", "label": "Attack", "animation": "attack" },
    { "id": "hurt", "label": "Hurt", "animation": "hurt" }
  ],
  "transitions": [
    { "id": "idle-run", "from": "idle", "to": "run", "mode": "select-animation", "review_required": true },
    { "id": "run-attack", "from": "run", "to": "attack", "mode": "select-animation", "review_required": true },
    { "id": "attack-hurt", "from": "attack", "to": "hurt", "mode": "select-animation", "review_required": true },
    { "id": "hurt-idle", "from": "hurt", "to": "idle", "mode": "select-animation", "review_required": true }
  ],
  "sequences": [
    {
      "id": "combat-roundtrip",
      "label": "Combat roundtrip",
      "review_required": true,
      "steps": [
        { "transition": "idle-run", "wait_ms": 150 },
        { "transition": "run-attack", "wait_ms": 150 },
        { "transition": "attack-hurt", "wait_ms": 150 },
        { "transition": "hurt-idle", "wait_ms": 150 }
      ]
    }
  ],
  "review_policy": {
    "require_all_transitions": true,
    "require_all_sequences": true
  }
}
```

`select-animation` is the portable lane for sprite/clip runtimes: the transition selects the target state's declared animation and may auto-play it. `runtime-trigger` is stricter and is intended for a real state machine such as a Rive state machine or a project-specific runtime. For that mode the iframe adapter must implement `triggerTransition(request)`. Dev Lab sends the declared trigger/payload and only counts the transition as inspected after the runtime reports the target state through `getState()`. It never silently downgrades a failed or unsupported `runtime-trigger` transition into a clip switch.

The State/Transition Tester shows the current state, legal outgoing transitions, required transition coverage, declared review sequences and transition history. Review sequences execute their declared transition steps with bounded waits and may be stopped or reset by the reviewer. They are review helpers, not autonomous approval mechanisms.

## Review semantics

Dev Lab records which actions the reviewer actually selected. When `review_policy.require_all_animations` is true, approval is disabled until every `review_required` action has been inspected. When a state-machine contract is present, its `review_policy` can independently require all review-required transitions and review-required sequences before approval is enabled. A user may still request changes at any time.

Review evidence records action, transition and sequence coverage plus runtime/state history. Playback success, transition success, runtime readiness, hashes, snapshots, telemetry and automated checks remain evidence only; `approved` is always an explicit user review decision.

The deterministic snapshot harness continues to use `window.__lab.selectAnimation()` and `window.__lab.seek()`. For live candidates those calls drive the same runtime controller shown to the user; for legacy scenes without `devlab-runtime.json`, Dev Lab clearly enters `captured-evidence` mode and retains the older checkpoint viewer as a compatibility fallback.
