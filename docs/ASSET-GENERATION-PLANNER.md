# Provider-aware asset generation planner

MotionLoom should not treat an image provider's native canvas as the game's runtime canvas. A request such as a `256x448` character frame can be valid for the game while being impossible as a native input to a provider whose animation tools accept only square canvases. The planner makes this mismatch explicit before any provider call.

## Command

```bash
motionloom asset-generation-plan plan \
  --request examples/agent-consumer/asset-planning/pixellab-hero-256x448-request.json \
  --project-root . --json
```

The command is **plan-only**. It does not invoke a provider, read or transfer a Bearer token, modify image bytes, create a generation job or grant approval. It reads the request, the local `artifact-adapter-registry.json`, and the repository contracts that are present in `--project-root`.

When the plan selects deterministic padding, execute it explicitly with `asset-adapt`; the operation is transparent, hash-bound and still requires downstream geometry/action review:

```bash
motionloom asset-adapt pad \
  --input provider-source.png \
  --output runtime-frame.png \
  --width 256 --height 448 \
  --anchor footline \
  --report asset-adaptation.json --json
```

`asset-adapt` uses integer nearest-neighbour scaling only when requested, refuses source pixels that do not fit the target, and never crops or non-uniformly stretches. It does not decide whether the source frame belongs to the requested action.

## Why PixelLab needs an adaptation plan

PixelLab's official API documentation exposes image and animation endpoints and documents Bearer-token authentication.[1] The official skeleton animation guide accepts square canvases including `256x256`, `128x128`, `64x64`, `32x32` and `16x16`.[2] The official animation-to-animation guide documents square sizes up to `128x128` and batch generation whose maximum frame count depends on canvas size.[3] The text animation guide documents `32x32`, `64x64` and `128x128` square canvases.[4]

Therefore, a game target of `256x448` is not a PixelLab-native animation canvas for these documented routes. The planner represents PixelLab as a `scaffold_only` adapter with a square source canvas and a batch-oriented frame behavior. Its recommendation is explicit transparent padding into the `256x448` target, followed by frame-geometry and action-separation validation. It never silently stretches, crops or treats a provider batch as equivalent to required isolated-frame generation.

PixelLab also documents a Resize tool, but the official page currently states that the feature is available in the Aseprite extension.[5] MotionLoom consequently does not claim provider-native API resize as verified. Deterministic nearest-neighbour scaling or a manual/provider-specific resize route must be declared and evidenced separately.

## Request contract

`schemas/asset-generation-request.schema.json` records the information that a generic prompt usually omits:

| Field | Purpose |
|---|---|
| `target.canvas` | The real runtime width and height, not the provider's preferred size. |
| `target.frame_count` and `fps` | The temporal contract the generated sequence must satisfy. |
| `target.alpha_mode` and `pixel_art` | Transparency and pixel-grid constraints for downstream geometry checks. |
| `generation_policy.frame_isolation` | Whether one source image per frame is required. |
| `allow_crop`, `allow_stretch`, `allow_silent_resize` | Hard safety boundaries; the current contract requires all three to be false. |
| `actions` | Positive and negative cues that feed the existing action-scoped manifest/verifier pipeline. |
| `references` | Identity/style/pose roles without placing secrets or prompt plaintext in the request. |

## Decision model

The planner compares the request with adapter capability metadata. It distinguishes four important situations.

| Situation | Planner behavior |
|---|---|
| Native canvas and native frame behavior are declared | Recommend the adapter, but retain the adapter's verification and human-review status. |
| Provider canvas is incompatible but safe adaptation is declared | Recommend a concrete source canvas, target canvas, anchor and deterministic operation such as transparent padding. |
| Provider emits a batch while per-frame isolation is required | Mark the route provisional or blocked according to policy; require independent envelopes after export and never promote it automatically. |
| Capability is unknown or no safe adaptation exists | Return `no_provider_meets_hard_constraints` or an explicit unknown warning; suggest manual import or a provider with a compatible contract. |

The current registry includes a manual single-frame import fallback. This is deliberate: when a provider cannot produce the exact target and no verified adapter exists, MotionLoom should give the Agent a useful next route instead of forcing it to invent a workaround or stop with an opaque error.

## Recommended 256x448 route

For a pixel-art action with eight frames and required isolation, the safe provisional route is:

1. Use a PixelLab square animation route only as a source-generation candidate, with a declared source canvas such as `256x256` and a separate action-specific request.
2. Keep the provider result provisional because the documented animation routes are batch-oriented and the adapter is not runtime-verified.
3. Place each accepted source frame on a transparent `256x448` target canvas using the declared footline/pivot anchor. Do not stretch or crop.
4. Bind source and target geometry in the export manifest and generate one independent frame envelope per output image.
5. Run `frame-set-preflight` and `action-separation validate` before atlas packing or Dev Lab review. The adaptation report is evidence of geometry transformation, not a substitute for either contract.
6. If any frame is ambiguous, quarantine that frame and regenerate or independently verify it. Do not move it to another action automatically.

If strict one-frame-per-provider-call isolation is non-negotiable, the planner's recommendation is to use a provider or manual workflow that declares single-frame output and target-canvas compatibility. PixelLab remains a useful provisional source option, not proof that the hard contract has been met.

## Adapter registry policy

The registry is not a provider launcher. It is a capability and evidence ledger. A `scaffold_only` entry may describe official limits and useful routes, but it cannot satisfy a strict selection policy that requires verified adapters. An adapter can become `verified` only after real export bytes, provider receipt metadata where available, target-runtime evidence, deterministic contract results and a human review path are present.

Credentials remain outside all request, receipt, control and manifest files. For an eventual PixelLab integration, the API token should be supplied through the project's secret/connector layer, while the receipt records only non-secret task identity and output hashes.

## References

[1]: https://api.pixellab.ai/v2/docs "PixelLab API — official API documentation"
[2]: https://www.pixellab.ai/docs/tools/animate-with-skeleton "PixelLab — Animate with skeleton"
[3]: https://www.pixellab.ai/docs/tools/animation-to-animation "PixelLab — Animation to animation"
[4]: https://www.pixellab.ai/docs/tools/text2animation "PixelLab — Create animated object/character"
[5]: https://www.pixellab.ai/docs/tools/resize "PixelLab — Resize"
