# ChatGPT corrective prompt — Scout v3 walk frames

Upload **only** `motionloom-ai-pilot-scout-v3-idle-alpha.png` as the reference image. Generate each requested pose in a separate turn and download the original PNG, not a screenshot.

> Treat the reference as a locked production-pilot sprite sheet source. Preserve the robot exactly; change only the limb pose required by the requested walk phase.

## Non-negotiable output contract

Copy this block into **every** generation request, then append one pose block below.

```text
Use the attached Scout v3 idle sprite as the exact visual and geometry reference.

Create ONE complete 2D pixel-art character sprite on a 1920 × 1920 pixel canvas. The canvas background must be truly transparent (RGBA alpha 0), with no black, checkerboard, coloured, shadow, floor, glow, particles, text, border, duplicate character, crop, or prop.

Do not redesign, restyle, zoom, crop, rotate, mirror, recolor, or change the camera. Keep the cream/orange/black/cyan robot identity, head, antenna, face, shoulder pads, torso, hands, feet, palette, pixel density, outlines, and apparent scale from the reference. Draw the entire robot at the same approximate scale as the reference, vertically standing on the same baseline.

Geometry requirements: leave at least 120 px transparent padding on all four canvas edges. Keep the opaque character approximately 800 px wide by 1450 px tall, centered near x=940, with the feet baseline near y=1626. The character must not occupy more than 55% of canvas width. Use crisp hard pixel edges only; do not add anti-aliased blur.

This is an AI-generated source asset for a review-only MotionLoom pilot. It must not imply artist authorship, production approval, runtime approval, or a licence.
```

## Pose 1 — contact right

Append this after the contract:

```text
Pose: walk cycle contact-right. The robot’s RIGHT foot is planted forward at the baseline; the LEFT leg trails slightly behind. Counter-swing the arms naturally. Keep both feet fully visible and preserve the locked body scale and centered composition.

Return only the single transparent-background PNG. Save it as: motionloom-ai-pilot-scout-v3-chatgpt-contact-right.png
```

## Pose 2 — passing

Append this after the contract:

```text
Pose: walk cycle passing phase. One leg passes beneath the body with a compact, balanced gait; the body remains upright and the foot baseline stays near y=1626. Counter-swing the arms naturally. Keep both feet fully visible and preserve the locked body scale and centered composition.

Return only the single transparent-background PNG. Save it as: motionloom-ai-pilot-scout-v3-chatgpt-passing.png
```

## Pose 3 — contact left

Append this after the contract:

```text
Pose: walk cycle contact-left. The robot’s LEFT foot is planted forward at the baseline; the RIGHT leg trails slightly behind. This must be the complementary phase to contact-right, not a mirror/redesign. Counter-swing the arms naturally. Keep both feet fully visible and preserve the locked body scale and centered composition.

Return only the single transparent-background PNG. Save it as: motionloom-ai-pilot-scout-v3-chatgpt-contact-left.png
```

## Before sending files back

Do not flatten the PNG or put it on a black background. Send the three original downloaded files to MotionLoom in the order above and retain the ChatGPT conversation/task context if available. MotionLoom will measure alpha, padding, identity geometry and file hashes independently; satisfying the prompt does not approve the candidate.
