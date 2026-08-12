# Cutout Body Rigging (`src/rig/`)

This module turns flat vector art into an animatable character body using the cutout rig technique: each limb is a separate layer pivoted on an explicit joint, and motion is expressed as per-bone rotation keyframes. It is the same principle used by Spine and Duik, implemented portably in pure SVG + JSON keyframes so it plays in Lottie, GSAP, Framer Motion, or CSS.

## Bone hierarchy

Bones rotate in strict parent-first order: `hip → spine → chest → head`, shoulders branch to upper-arm → forearm → hand, and hips to thigh → shin → foot. The engine (`cutout_rig.py`) enforces this order when building the SVG `<g>` tree — a child never appears before its parent.

## Conventions

Each bone group carries two markers: `data-bone="<name>"` (used by the player to target rotations) and an inline `transform="rotate(...)"` so the pose is readable directly in the file. The `DEFAULT_POSE` dictionary in `cutout_rig.py` is the T-pose baseline; every clip is additive to it.

## Building a rig

```
python3 src/rig/cutout_rig.py build \
  --input assets/library/character-flat.svg \
  --output rigged-avatar.svg \
  --pivot-x 0 --pivot-y 0
```

If no authoritative art is provided, the engine emits a default geometric avatar that the designer must replace — never ship the placeholder as final art.

## Clips and poses

```
python3 src/rig/cutout_rig.py pose rigged-avatar.svg --pose walk \
  --duration 1.5 --fps 30 --out idle-clip.json
```

Built-in clips: `idle`, `walk`, `wave`, `nod`, `bounce`. Custom clips are plain JSON maps of `bone → [start_deg, end_deg]`. Interpolation uses smoothstep ease-in-out; set `loop: true` on the player for seamless cycles (`idle`, `walk`).

## Exporting to Lottie

Feed the rigged SVG plus the clip JSON to the Lottie template in `templates/lottie/` — the template wraps the bone tree in a dotLottie with a theme slot for the body color so the brand analyzer can recolor the character at runtime without regenerating the file.
