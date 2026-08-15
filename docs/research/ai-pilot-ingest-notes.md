# AI Pilot Ingest Notes

## 2026-08-15 — ImageGen pilot asset capture

The first generated robot master frame (`motionloom-ai-pilot-scout-idle.png`) contains an opaque dark background. It is therefore unsuitable as a frame-geometry source: treating its full canvas as subject pixels would conceal trim, padding, pivot, footline, and contamination issues.

An isolated alpha-background variation (`motionloom-ai-pilot-scout-idle-alpha.png`) was generated from that master. It remains an **AI-generated pilot**, not artist-authored material and not a production-approved asset. Its final hash, dimensions, alpha bounds, consistency result, and Artifact Intake receipt must be measured from bytes before any ingest result is reported.

Walk-cycle frames are handled independently under the same rule: no prompt claim, preview checkerboard, or intended transparency substitutes for actual PNG alpha/geometry measurement.

## 2026-08-15 — Alpha-channel forensic correction

The four files first named `*-alpha.png` were 8-bit RGB PNGs with no alpha channel. The subsequent `*-transparent.png` outputs were RGBA files, but every pixel still had alpha `255`: the dark scene background was painted into the pixels. The pilot builder now rejects both conditions rather than interpreting a filename, an RGBA color type, or a checkerboard preview as proof of isolated geometry.

`scripts/isolate-alpha-background.py` was added as a narrow deterministic recovery step for an **edge-connected, visually reviewed flat background**. It publishes an input/output hash report and leaves `human_review_required: true`. A first idle-frame run at RGB Manhattan tolerance `24` left visible background bands, so it was rejected as unsuitable. Tolerance selection and visual inspection are material evidence; the tool must not turn an imperfect isolation into an approval or an assertion of provider-native alpha.

The source-bound `build-ai-pilot.py` invocation against all four generated `*-transparent.png` files then failed before writing `controls.json`: `scout-idle.png has no transparent padding; an isolated alpha frame is required`. This is the intended boundary. There is no real pilot Artifact Intake report, consistency contract, runtime candidate, rig contract, or PR-ready result derived from these bytes. The Dev Lab card at `/lab?pilot=scout-alpha` presents that blocked evidence and disables review staging.

## 2026-08-15 — V2 residual-artifact finding

A successful edge-connected alpha-isolation report with `residual_edge_foreground_pixels: 0` is necessary but not sufficient. Visual review of the v2 isolated master exposed several detached horizontal opaque bands to the robot's right. Those pixels were not edge-connected and were therefore outside the isolator's intentionally narrow scope. The source remains unsuitable for ingest until a clean regeneration or a targeted visual edit removes the detached artifacts; a hash report alone is not a cleanliness approval.

The independently generated v3 master initially appeared to repeat the same class of failure when its alpha PNG was shown on a black renderer background. A targeted edit successfully replaced its smoky/green background with a flat dark field, and the alpha-isolator produced a valid hash-bound report with zero residual edge pixels. A subsequent composite preview on a light field confirmed that the apparent long black bars were transparent pixels rendered against black, not canvas-spanning residue. The v3 master has clean padding and no detached macro artifact, so it may proceed as a review-required pilot source. Minor pixel-edge irregularities remain visible in the source and are deliberately not treated as production approval.

## 2026-08-15 — Gemini-assisted pose generation checkpoint

The authenticated Gemini browser session reached its upload menu. No source image has yet been transferred and no Gemini output is part of the pilot. Any later result must record Gemini provider/model/task metadata as `ai_generated`, then pass the existing alpha, geometry, contamination, hash-bound Intake, and review-required gates without exception.

The Gemini upload menu can be displayed in the authenticated browser, but the initial automated menu selection did not expose a file input. This is recorded as a browser-integration state only; it did not transfer a source file or produce a generation.
