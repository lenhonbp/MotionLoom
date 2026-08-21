# Multi-frame asset generation discipline

This contract applies whenever MotionLoom or an Agent creates two or more source frames for the same character, object, effect or other frame-based animation. It is automatic: the user should not have to ask for consistent frame geometry, isolated source frames or atlas hygiene.

## Default source policy

Generated source frames are **isolated-frame assets**, not a pose sheet.

- Generate exactly one animation source frame per image/canvas by default.
- For long actions (including actions with six or more frames), never ask an image generator for one contact sheet, sprite sheet or multi-pose canvas and then crop the poses out as production source frames.
- Do not pack an atlas or sprite sheet until every isolated source frame has passed identity and frame-geometry validation.
- Imported third-party atlases may still use the atlas contract; this rule is about Agent-generated source material.

This avoids neighboring poses leaking into a crop, shared-canvas bleed, accidental partial limbs from adjacent frames and ambiguous ownership of opaque pixels.

## Lock geometry before the second frame

Before generating frame 2, establish one canonical geometry lock from the accepted identity/reference frame and keep it unchanged for the rest of the action:

- exact canvas width and height;
- transparent alpha mode and color space;
- camera and left/right orientation;
- target apparent character scale;
- pivot point;
- baseline / footline;
- safe rectangle and transparent guard band;
- palette/style/identity reference;
- frame naming and action order.

Create or update the matching `action-set` and `frame-geometry` contracts before continuing the sequence. The first accepted frame is the geometry anchor; later poses may move limbs, but they must not silently change canvas size, camera, character scale, pivot or baseline.

For AI-generated frames, every subsequent generation request should carry the same locked identity reference and geometry requirements. When the image tool can accept an image reference, reuse the accepted identity/anchor frame rather than relying on prose alone.

## Validate incrementally

Do not generate the complete action and only inspect it at the end. After each candidate frame:

1. verify the image is an isolated source canvas rather than a shared pose sheet;
2. verify exact canvas dimensions and alpha transparency;
3. measure the real alpha bounding box from pixels;
4. compare apparent size against the anchor within the declared `bbox_drift_tolerance_px`;
5. verify pivot and footline tolerance;
6. verify the alpha bounding box remains inside `safe_rect` with the declared `bleed_margin_px` guard band;
7. reject unexpected opaque contamination;
8. only then accept the frame and continue.

Use:

```bash
python3 scripts/frame-set-preflight.py \
  --input src/output/<scene>/<action>-frame-geometry.json \
  --root src/output/<scene> --json
```

The preflight is intentionally stricter than a visual warning: shared source images, non-isolated frame rectangles, scale drift beyond the declared tolerance, guard-band violations, pivot/footline drift, hash mismatch or other deterministic frame-geometry failures block the sequence.

If one frame fails, regenerate or repair **that frame only** using the same lock. Do not silently rescale every previously accepted frame to match a bad frame, and do not weaken tolerances merely to make the set pass.

## Apparent-size consistency

Equal canvas dimensions are not enough. A 1920 × 1920 PNG can still contain a character that is 20% smaller than the previous frame. MotionLoom therefore treats measured alpha-bounds drift as a real source defect when it exceeds the declared tolerance.

Pose motion can legitimately change the bounding box, so choose a tolerance that allows expected limb extension while preventing whole-character zoom drift. For actions with large reaches, jumps or weapons, lock the body pivot/footline and define a safe rectangle large enough for those poses instead of changing the character scale between frames.

For pixel art, any intentional normalization step must preserve nearest-neighbor pixel density and the locked pivot/baseline. Large scale corrections should trigger regeneration rather than interpolation.

## Packing happens last

Only after every source frame passes preflight may the Agent build a sprite sheet or atlas. The packed result must then pass the atlas contract: no region overlap, no opaque pixels outside declared regions when required, explicit padding/extrusion, and no ambiguous neighboring-frame bleed.

Source-frame acceptance and atlas acceptance are separate gates. A clean atlas cannot repair inconsistent source-frame scale, and consistent source frames do not prove the packed atlas is clean.

## Agent decision rule

When the user asks for an animation such as idle, walk, run, attack, hurt, jump or any project-defined multi-frame action, the Agent should apply this contract automatically. Do not ask the user whether they want frame consistency checks; they are part of the default MotionLoom workflow. Only ask the user when a genuine artistic decision is required, such as choosing between materially different silhouettes or motion intent.
