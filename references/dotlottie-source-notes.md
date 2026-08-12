# dotLottie implementation notes

These notes preserve the external format facts used for the `.lottie` packager.

## Sources

- https://dotlottie.io/spec/2.0/
- https://docs.lottiefiles.com/en/format/dotlottie/structure
- https://github.com/LottieFiles/dotlottie-web/blob/main/SKILL.md

## Contract used by this repository

- A `.lottie` file is a ZIP archive using the `application/zip+dotlottie` format.
- `manifest.json` is required at the archive root.
- `a/` is required and contains at least one Lottie JSON animation.
- The v2 manifest requires `version: "2"` and `animations` with unique `id` values.
- `initial.animation`, when present, names an animation ID stored under `a/`.
- Optional directories include `i/` for images, `t/` for themes, `s/` for state machines and `f/` for fonts.
- Animation IDs should use the dotLottie filename-safe pattern: alphanumeric characters, dots, underscores, spaces and hyphens.
- Runtime rendering should use the official dotLottie runtime; synchronous frame capture uses `autoplay: false`, load completion, then `setFrame()`.
- The package/runtime reference recommends `.lottie` over raw JSON for compression, bundled assets, themes and state machines.
