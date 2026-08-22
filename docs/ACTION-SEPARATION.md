# Action-scoped isolated frame pipeline

MotionLoom keeps generated source frames isolated: one source PNG per frame, no pose sheet as production input, no shared-canvas crop and no post-generation resize. Isolation prevents pixel contamination, but it does not by itself prove that a frame belongs to the intended action. This document adds the action-level contract that closes that gap.

## Model

A frame belongs to an immutable `sequence_id` and `action_id`. The sequence manifest declares the expected action, explicitly forbidden competitor actions, the ordered frame set, the identity-lock hash and one envelope for every image. A verifier result is evidence only; it cannot grant approval or move a file.

The lock and manifest deliberately use two independent layers:

| Layer | Source of truth | Purpose |
|---|---|---|
| Generation lock | `frame-generation-lock.schema.json` / `frame-generation-lock.py` | Compose one isolated request per frame with shared identity, geometry and action cues |
| Action manifest | `action-sequence-manifest.schema.json` / `action-separation.py` | Bind frame order, image bytes, envelope metadata and competitor-action separation |
| Geometry preflight | `frame-set-preflight.py` | Measure actual PNG geometry and optionally require the action manifest to pass |
| Human review | Dev Lab | Inspect the live sequence and see whether action evidence is pass or quarantined |

## CLI

Validate the action manifest directly:

```bash
motionloom action-separation validate \
  --input examples/agent-consumer/asset-consistency/action-sequence/hero-walk-action-manifest.json \
  --root examples/agent-consumer/asset-consistency --json
```

Run geometry and action checks together:

```bash
motionloom frame-set-preflight \
  --input examples/agent-consumer/asset-consistency/hero-walk-frame-geometry.json \
  --root examples/agent-consumer/asset-consistency \
  --action-manifest examples/agent-consumer/asset-consistency/action-sequence/hero-walk-action-manifest.json \
  --json
```

The equivalent npm scripts are `npm run action:separation` and `npm run frame:preflight`. To create one envelope from a manifest and a real PNG, use:

```bash
motionloom action-separation envelope \
  --manifest examples/agent-consumer/asset-consistency/action-sequence/hero-walk-action-manifest.json \
  --root examples/agent-consumer/asset-consistency \
  --frame-id walk.00 --expected-action walk --top-competitor run \
  --margin 0.42 --threshold 0.20 \
  --output examples/agent-consumer/asset-consistency/action-sequence/envelopes/walk.00.json --json
```

A margin below threshold produces a `quarantined` envelope and a non-zero exit code; it is still written as evidence, but the manifest cannot pass until the frame is independently verified again.

## Frame envelope

Every manifest frame points to an envelope. The envelope binds the frame to the exact sequence, action, frame index, identity lock and image bytes. The verifier must provide an expected action, a top competitor, a numeric confidence margin and a declared threshold. A margin below threshold is quarantined; it is not silently assigned to the nearest action.

```json
{
  "sequence_id": "hero-walk-v1",
  "action_id": "walk",
  "frame_id": "walk.01",
  "frame_index": 1,
  "image": "assets/hero-frame-01.png",
  "image_sha256": "<sha256>",
  "identity_lock_sha256": "<lock-sha256>",
  "verifier": {
    "expected_action": "walk",
    "top_competitor": "run",
    "margin": 0.42,
    "threshold": 0.20,
    "status": "pass",
    "method": "independent-action-rubric-v1"
  },
  "approval": false
}
```

The validator rejects duplicate images, non-contiguous frame indexes, path escapes, mismatched envelope fields, stale image hashes, undeclared competitors, low margins and any verifier status other than `pass`. It never repairs, renames, relocates or approves an asset.

## Generation lock 0.2

`frame-generation-lock` accepts legacy schema `0.1` and enhanced schema `0.2`. A `0.2` lock requires `sequence_id`, `forbidden_action_ids` and `action_contract.positive_cues`/`negative_cues`. `compose` and `compose-all` include those cues in every provider-facing instruction while preserving the one-image-per-frame rule.

The canonical example is [`examples/agent-consumer/frame-generation-lock/hero-walk-lock.json`](../examples/agent-consumer/frame-generation-lock/hero-walk-lock.json). The action manifest and envelopes are under [`examples/agent-consumer/asset-consistency/action-sequence/`](../examples/agent-consumer/asset-consistency/action-sequence/).

## Status and approval boundary

The manifest may be `review_required` or `quarantined`; it must never claim approval. A passing verifier means that the evidence is sufficiently separated for the next gate, not that the user approved the action. Dev Lab still requires animation coverage and explicit checklist confirmation before enabling Approve.

For live runtime fixtures, the optional `action_separation` summary in `devlab-runtime.json` is displayed in Dev Lab. A quarantined summary disables approval and instructs the reviewer to regenerate or independently verify the ambiguous frame. Contact sheets remain review projections only; production packing must use the manifest-approved isolated images.

## Adversarial coverage

The regression suite covers a valid four-frame sequence and rejects a cross-action envelope, a low-confidence action margin and a reused image. The canonical fixture also runs through geometry preflight, so a sequence can only pass when both the measured PNG contract and the action-scoped evidence pass.
