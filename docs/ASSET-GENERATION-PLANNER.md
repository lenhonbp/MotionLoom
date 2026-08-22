# Provider-aware asset generation planner

MotionLoom does not choose animation tools in isolation. It first understands the project and task, evaluates available or requested routes against those requirements, then produces an explainable recommendation and validation workflow. A provider is only an execution route; **MotionLoom remains the project-aware decision and guidance layer**.

MotionLoom also does not treat an image provider's native canvas as the game's runtime canvas. A request such as a `256x448` character frame can be valid for the game while being impossible as a native input to a provider whose animation tools accept only square canvases. The planner makes this mismatch explicit before any provider call.

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

PixelLab's official API documentation exposes image and animation endpoints and documents Bearer-token authentication.[1] The official skeleton animation guide accepts square canvases including `256x256`, `128x128`, `64x64`, `32x32` and `16x16`.[2] The official Animation to animation guide documents square sizes `128x128`, `64x64`, `32x32` and `16x16`, with maximum frame count dependent on canvas size.[3] The official Create animated object/character route creates a new object or character from text and action, supports `32x32`, `64x64`, `128x128` and `256x256`, and emits 16 frames for 32/64px tiers or 4 frames for larger documented tiers.[4] The separate Animate with text route animates an existing reference image and is not the same provider capability as create-from-text.[5]

Therefore, a game target of `256x448` is not a PixelLab-native animation canvas for these documented routes. MotionLoom may still recommend a PixelLab route when it is a good project fit, but represents it as `recommendation_status: recommended` with `execution_status: provisional` under the default policy. The recommendation is explicit transparent padding into the `256x448` target, followed by frame-geometry and action-separation validation. It never silently stretches, crops or treats a provider batch as equivalent to required isolated-frame generation.

PixelLab also documents a Resize tool, but the official page currently states that the feature is available in the Aseprite extension.[6] MotionLoom consequently does not claim provider-native API resize as verified. Deterministic nearest-neighbour scaling or a manual/provider-specific resize route must be declared and evidenced separately.

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
| `provider_preferences` | Optional preferred or excluded adapter IDs; preference is visible but cannot override hard constraints. |
| `references` | Identity/style/pose roles without placing secrets or prompt plaintext in the request. |

## Decision model

The planner compares the request with adapter capability metadata, current availability metadata, user preference and the active registry selection policy. It separates **recommendation status** from **execution status** and keeps normal planning useful even when no route is execution-eligible.

| Situation | Planner behavior |
|---|---|
| Verified adapter satisfies hard constraints | Set `execution_status: verified`, `execution_eligible: true` and usually `recommendation_status: recommended` or `acceptable`; retain human-review boundaries. |
| Provisional/scaffold adapter fits project requirements | It may receive `recommendation_status: recommended` in normal planning while `execution_status: provisional` remains visible. It is not authorized under verified-only strict execution. |
| User explicitly prefers a route | Preserve `user_preference: preferred`, add an explainable ranking signal and provide route guidance; never override hard incompatibility or approval boundaries. |
| User explicitly excludes a route | Preserve `user_preference: excluded` and do not recommend it, while evaluating other routes normally. |
| Provider canvas is incompatible but safe adaptation is declared | Recommend a concrete source canvas only when both source dimensions fit the target after the declared integer transform. |
| Provider emits a batch while per-frame isolation is required | Mark execution provisional or blocked according to policy; require independent envelopes after export and never promote it automatically. |
| Capability/availability is unknown or no safe route exists | Mark the route blocked or not recommended as appropriate, surface the reason, and suggest a manual/alternate option without fabricating availability. Strict mode returns non-zero when no execution-eligible route exists. |

The current registry includes a manual single-frame import fallback. In normal planning it remains a visible MotionLoom recommendation because it is project-compatible and explains its user-managed availability; under the default `require_verified: true` policy it remains provisional rather than execution-eligible. This is deliberate: MotionLoom gives the Agent useful choices without silently relaxing policy or forcing it to invent a workaround.

## Recommended 256x448 route

For a pixel-art action with eight frames and required isolation, the safe provisional route is:

1. Treat PixelLab as one MotionLoom recommendation, not a default provider. If selected or explicitly preferred, use a square animation route only as a source-generation candidate, with a declared source canvas such as `256x256` and a separate action-specific request.
2. Keep the provider result provisional because the documented animation routes are batch-oriented and the adapter is not runtime-verified.
3. Place each accepted source frame on a transparent `256x448` target canvas using the declared footline/pivot anchor. Do not stretch or crop.
4. Bind source and target geometry in the export manifest and generate one independent frame envelope per output image.
5. Run `frame-set-preflight` and `action-separation validate` before atlas packing or Dev Lab review. The adaptation report is evidence of geometry transformation, not a substitute for either contract.
6. If any frame is ambiguous, quarantine that frame and regenerate or independently verify it. Do not move it to another action automatically.

If strict one-frame-per-provider-call isolation is non-negotiable, the planner's recommendation is to use a provider or manual workflow that declares single-frame output and target-canvas compatibility. PixelLab remains a useful provisional source option, not proof that the hard contract has been met.

## MotionLoom Agent guidance

Every recommendation includes `agent_guidance` with `recommended_by: MotionLoom`, a summary, a route-specific sequence of steps and the MotionLoom validation route. The plan also exposes availability as `available`, `known`, `unavailable` or `unknown`; an unavailable/unknown tool may remain a recommendation, but the Agent must resolve connectivity before execution and MotionLoom must not claim it can invoke the tool.

Normal output uses the `MotionLoom Project Assessment`, `MotionLoom Recommendations` and `MotionLoom Agent Guidance` headings. JSON output includes `producer: MotionLoom`, `source`, project assessment, recommendation status, execution status, preference, availability, rationale and validation route.

## Adapter registry policy

The registry is not a provider launcher. It is a capability and evidence ledger. A `scaffold_only` entry may describe official limits and useful routes, but it cannot satisfy a strict selection policy that requires verified adapters. An adapter can become `verified` only after real export bytes, provider receipt metadata where available, target-runtime evidence, deterministic contract results and a human review path are present.

Credentials remain outside all request, receipt, control and manifest files. For an eventual PixelLab integration, the API token should be supplied through the project's secret/connector layer, while the receipt records only non-secret task identity and output hashes.

## References

[1]: https://api.pixellab.ai/v2/docs "PixelLab API — official API documentation"
[2]: https://www.pixellab.ai/docs/tools/animate-with-skeleton "PixelLab — Animate with skeleton"
[3]: https://www.pixellab.ai/docs/tools/animation-to-animation "PixelLab — Animation to animation"
[4]: https://www.pixellab.ai/docs/tools/text2animation "PixelLab — Create animated object/character"
[5]: https://www.pixellab.ai/docs/tools/animation "PixelLab — Animate with text (existing reference)"
[6]: https://www.pixellab.ai/docs/tools/resize "PixelLab — Resize"
