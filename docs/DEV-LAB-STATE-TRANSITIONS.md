# Dev Lab state/transition tester

MotionLoom Dev Lab can review more than isolated animation clips. A live candidate may also expose a state/transition contract so a reviewer can exercise flows such as `Idle -> Run -> Attack -> Hurt -> Idle` against the same candidate runtime.

The state-machine contract is optional. When used, place `devlab-state-machine.json` beside `devlab-runtime.json` and list `devlab-state-machine.json` in the runtime descriptor's `files` array. This is mandatory: the state-machine bytes must participate in the candidate runtime bundle hash. Dev Lab ignores unbound state-machine data and blocks approval if a hash-bound state-machine contract is invalid.

The schema is `schemas/devlab-state-machine.schema.json`.

## Example

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
    {
      "id": "start-run",
      "label": "Start running",
      "from": "idle",
      "to": "run",
      "trigger": "move",
      "mode": "select-animation",
      "auto_play": true,
      "review_required": true
    },
    {
      "id": "attack",
      "from": "run",
      "to": "attack",
      "trigger": "attack",
      "mode": "select-animation",
      "auto_play": true,
      "review_required": true
    },
    {
      "id": "take-hit",
      "from": "attack",
      "to": "hurt",
      "trigger": "hit",
      "mode": "select-animation",
      "auto_play": true,
      "review_required": true
    },
    {
      "id": "recover",
      "from": "hurt",
      "to": "idle",
      "trigger": "recover",
      "mode": "select-animation",
      "auto_play": true,
      "review_required": true
    }
  ],
  "sequences": [
    {
      "id": "combat-cycle",
      "label": "Combat cycle",
      "review_required": true,
      "steps": [
        { "transition": "start-run", "wait_ms": 250 },
        { "transition": "attack", "wait_ms": 450 },
        { "transition": "take-hit", "wait_ms": 300 },
        { "transition": "recover", "wait_ms": 200 }
      ]
    }
  ],
  "review_policy": {
    "require_all_transitions": true,
    "require_all_sequences": false
  }
}
```

## Transition modes

`select-animation` is the portable mode. Dev Lab changes to the target state's declared animation through the existing live runtime controller and optionally starts playback. It is appropriate for sprite-sequence candidates and simple clip-oriented runtimes. This mode does not claim that a blend tree or engine state machine was exercised.

`runtime-trigger` is for runtimes that own real state-machine behavior, such as a Rive state machine, a game-runtime adapter, or another project-specific player. The iframe adapter must expose `triggerTransition(request)` through `runtime-bridge.js` and `getState()` must expose an observable `state`/`currentState` or an animation that maps to a declared state. Dev Lab sends the exact transition request and verifies that the target state becomes observable before counting the transition as inspected. It never silently downgrades a `runtime-trigger` transition to a clip switch.

Example adapter:

```js
MotionLoomRuntimeBridge.attach({
  runtime: "game-preview@1",
  framework: "custom",
  animations: [
    { id: "idle", label: "Idle", loop: true },
    { id: "run", label: "Run", loop: true },
    { id: "attack", label: "Attack", loop: false }
  ],
  triggerTransition(request) {
    // Dispatch the real trigger/input into the runtime state machine.
    // request: { id, from, to, trigger, payload }
  },
  getState() {
    return {
      state: "idle",
      animation: "idle",
      progress: 0,
      currentTime: 0,
      duration: 1
    };
  }
});
```

## Review behavior

The State Machine panel follows the runtime's current state, shows only transitions that are legal from that state (plus wildcard transitions), and records successful transition observations. Review sequences execute declared transitions in order; each wait is explicit and bounded.

If `review_policy.require_all_transitions` is true, every transition with `review_required != false` must be exercised before Dev Lab allows approval. `require_all_sequences` applies the same rule to review-required sequences. Search/filtering in the Action Library cannot bypass these requirements.

A transition is counted only after its command succeeds and the target state is observable. Unsupported runtime-trigger transitions remain disabled. A reviewer can always request changes without completing transition coverage.

Transition execution, state observability, sequence completion, runtime hashes, snapshots, and automated smoke tests are evidence only. None of them grant `production_approved`, runtime approval, or visual approval. The final approval remains an explicit user action.
