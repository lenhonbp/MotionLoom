# Asset Library — Authoritative Sources

This directory holds the **vetted, traceable source assets** the generator must bind to. The golden rule: when an authoritative source exists here (or in the host project), never invent geometry from memory. Placeholders created by the rig engine or templates are clearly marked and must be replaced before a scene ships.

## Contents

| Item | Purpose |
|---|---|
| `success-check.json` | Reference Lottie success state — 60 fps, 240 frames, 95 layers (use as a complexity benchmark) |
| `error-alert.json` | Reference Lottie error state — 60 fps, 300 frames, minimal layer count |
| `avatar-base.svg` | Authoritative cutout avatar base for body rigging (`src/rig/cutout_rig.py --input`) |
| `ATTRIBUTION.md` | Auto-generated provenance table: every fetched asset with source URL + license |

## Adding assets

Use `scripts/fetch-library.sh` — it downloads from official public sources, validates the Bodymovin header (version, fps, frame count, layer count), and appends a row to `ATTRIBUTION.md`. Always open the license page of each asset before shipping it in a commercial product; LottieFiles free assets carry individual license terms.

## Naming convention

`<category>-<variant>.<ext>` — e.g. `loading-dots.json`, `character-walk.svg`. Category must match a taxonomy entry in `docs/CATEGORIES.md`.
