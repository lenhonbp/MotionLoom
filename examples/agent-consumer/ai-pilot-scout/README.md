# AI Scout Pilot Ingest

This example is a **real-byte, local workspace flow** for an AI-generated four-frame scout robot pilot. The repository does not version the generated PNG bytes. Run the portable builder against four user-held, alpha-isolated PNG frames; it copies the source bytes into `.motionloom/pilots/ai-pilot-scout/`, measures the alpha geometry, and produces the JSON contracts there.

The pilot uses `authority: ai_generated` and stays **review-required**. Its receipt is explicitly a post-hoc, hash-bound ingest record because a provider-native ImageGen receipt was not exported. The result may demonstrate that all bundle links and measured geometry validate. It must never be interpreted as artist-authored authority, provider provenance completeness, runtime verification, production eligibility, or human approval.

If a provider returns a fully opaque dark canvas despite a transparency request, run `scripts/isolate-alpha-background.py` first only when the background is visibly high-contrast and edge-connected. It rejects residual opaque pixels at the canvas edge by default, because those normally indicate contamination instead of a safely isolated sprite. The tool emits an alpha-isolation report, but that report is evidence of a deterministic post-process, not proof of source alpha or approval. Review the result visually before building the bundle.

```bash
python3 scripts/build-ai-pilot.py \
  --idle /absolute/path/scout-idle-transparent.png \
  --contact-right /absolute/path/scout-contact-right-transparent.png \
  --passing /absolute/path/scout-passing-transparent.png \
  --contact-left /absolute/path/scout-contact-left-transparent.png \
  --overwrite

python3 scripts/artifact-intake.py report \
  --root . \
  --registry artifact-adapter-registry.json \
  --controls .motionloom/pilots/ai-pilot-scout/controls.json \
  --receipt .motionloom/pilots/ai-pilot-scout/receipt.json \
  --export-manifest .motionloom/pilots/ai-pilot-scout/export.json \
  --output .motionloom/pilots/ai-pilot-scout/artifact-intake-report.json

python3 scripts/runtime-candidate.py report \
  --root . \
  --input .motionloom/pilots/ai-pilot-scout/candidate.json \
  --output .motionloom/pilots/ai-pilot-scout/runtime-candidate-report.json
```

Use `--frame-url ID=URL` when the four frames are hosted for Dev Lab. The builder carries those URLs only in `devlab-pilot-evidence.json`; it does not treat URL reachability as evidence of quality, runtime behavior, review, or approval.

> The builder rejects ordinary RGB files and a fully opaque image. A visible checkerboard painted into an RGB PNG is **not** transparency. This restriction makes frame geometry and contamination checks meaningful.

When any source fails preflight, the builder exits non-zero and writes only `partial-handoff.json` beside the copied source bytes. That handoff binds the original SHA-256, any measurable alpha/canvas/padding metrics, provider identity and exact refusal reasons. It deliberately does **not** emit `controls.json`, a receipt, candidate, runtime render or Dev Lab review link. Replace the source independently; do not resample, add transparent margins or edit metadata to make rejected bytes pass.

## Current pilot handoff

The checked-in [`partial-handoff.json`](partial-handoff.json) records the current real-byte pilot boundary: one v3 master was alpha-isolated, visually checked and retained outside this repository; the independent walk phases could not be generated before the image quota was exhausted. No intake bundle, runtime candidate, render evidence or Dev Lab candidate has been emitted from a repeated idle image. Resume only with three independently generated and reviewed action frames, then run the exact commands above.
