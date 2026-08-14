# AI Animation and Asset Tools — Research Notes

> Working research notes. Claims below are discovery leads from official-site search results and must be verified by opening the source pages before inclusion in the final report.

## Initial source leads

| Tool / family | Official URL | Discovery lead to verify |
|---|---|---|
| PixelLab | https://www.pixellab.ai/ | AI pixel-art game assets, animated characters, sprite sheets and environments. |
| PixelLab API | https://www.pixellab.ai/pixellab-api | API-oriented generation of characters, animations and environments for procedural/live asset creation. |
| Runway | https://runway.com/product | Text-to-video and image-to-video generation, plus image generation/editing. |
| DeepMotion | https://www.deepmotion.com/ | Browser-based AI motion capture and body tracking that produces 3D animation from video. |
| Rokoko Vision | https://www.rokoko.com/products/vision | Video-to-3D animation through an AI mocap solver. |
| Scenario | https://www.scenario.com/ | Style-consistent game asset generation and animated video positioning; workflow details require verification. |
| Leonardo AI | https://leonardo.ai/news/how-to-generate-a-full-game-asset-suite-with-leonardo-ai | Game asset ideation, iteration and refinement workflow; official article requires verification. |
| Ludo.ai | https://ludo.ai/features/sprite-generator | Sprite generation and animation workflow; official feature page requires verification. |
| GameLab Studio | https://gamelabstudio.co/ | AI sprite-sheet and transparent animation generation; official claims require verification. |

## Planned comparison dimensions

1. Input controls: text, reference image, video, pose/motion reference, style training or project memory.
2. Output model: raster frames, sprite sheet, atlas, 2D rig, 3D skeleton animation, video, vector/timeline or runtime component.
3. Temporal/identity consistency: seed, reference locking, character/style model, pose control, frame geometry and loop controls.
4. Production integration: export formats, API/CLI, engine/runtime adapters, metadata, versioning and deterministic replay.
5. Human governance: provenance, license/source records, review checkpoints, editability and approval boundaries.
6. MotionLoom relevance: which capability belongs in project memory, contracts, analyzers, runtime evidence, Dev Lab or handoff.

## Verified findings — PixelLab

Source pages opened:

- https://www.pixellab.ai/
- https://www.pixellab.ai/docs/tools/animate-with-skeletons

The official product page exposes separate workflows for one-click animation, skeleton-based animation and text-described animation. It also lists 4/8 directional rotation, reference-based style consistency, true inpainting, scenes, tilesets and UI elements. The animation copy explicitly targets walking, running, attacking and custom sprite-sheet animations. The page also positions scene animation as text-described motion for animated environments and dynamic backgrounds.

The skeleton documentation page is currently a product/tutorial-style page rather than a full API specification. It confirms the product surface includes skeleton controls, automatic character animation and reference-driven generation, but it does not yet provide enough public detail to claim deterministic skeleton export, frame hashing, atlas metadata or runtime bindings. Those remain questions for MotionLoom to verify at the artifact/export boundary instead of inferring them from visual output.

Initial design lesson: a useful AI asset tool separates **character identity/style editing**, **motion authoring**, **directional rotation**, **environment/tileset generation** and **inpainting** into distinct operations. MotionLoom should model these as explicit artifact stages and contracts, not as one generic "generate animation" action.

The official PixelLab API page exposes a more structured pipeline than the homepage alone suggests. It separates image generation, image operations, animation, rotation, inpainting/editing, map/tileset generation, character/object state management and prompt enhancement. Relevant animation operations include text animation, text animation v3 with optional start/end frames and up to 16 frames, skeleton animation, skeleton estimation, character animation and animation editing. It also exposes interpolation between images/animations and outfit transfer across frames. Character and object operations are persisted as reusable entities with later states and animations, which is a useful identity-first model.

The API page also reveals concrete limits and options such as transparent output, forced palettes, init images, inpainting, direction/view controls, maximum canvas/frame sizes and explicit frame counts. These are implementation facts for PixelLab's API surface, not evidence that every output is production-safe. MotionLoom should treat them as source metadata and then measure the returned artifacts independently.

The official style-reference guide states that users add one or more style reference images, describe the desired asset and generate multiple variations. It describes a grid/frame-output relationship based on the largest reference-image dimension and exposes a large reference-image count at small sizes. The important lesson is that style consistency is reference-conditioned and parameterized by output geometry; it is not merely a textual prompt convention. MotionLoom's identity manifest, palette/camera/scale fields and frame-geometry analyzer are the natural verification layer after such a generator.

## Verified findings — Runway and DeepMotion

Runway's official Gen-4 research page describes a reference-conditioned video workflow: visual references plus instructions are used to create images/videos while maintaining consistent characters, locations, objects, style, mood and cinematographic elements across scenes and perspectives. It emphasizes that this is achieved without fine-tuning or additional training. For MotionLoom, the transferable idea is a reusable **reference bundle** and scene-level identity rather than re-prompting a character from scratch for every shot. The non-transferable assumption is that visual consistency alone proves a game-ready frame contract; raster bounds, sockets, timing and runtime evidence still need independent checks.

DeepMotion's official homepage exposes two distinct products/workflows: SayMotion for text-to-3D animation and Animate 3D for video-to-3D animation. It also exposes an Animate 3D API surface in the site navigation. The key architectural lesson is the separation between **motion source acquisition** (text or video) and **3D animation output**. MotionLoom should model body animation as a source-bound motion artifact with rig/skeleton compatibility, retargeting metadata and runtime evidence, not as an opaque generated clip.

Rokoko Vision 3.0's official page describes a four-step workflow: upload a video, generate 3D motion, edit/view/loop the capture in Rokoko Studio, upload a character for retargeting, then export to FBX or BVH for tools such as Blender, Unity and Unreal. This is a strong reference for MotionLoom's body-rig path because it makes cleanup, looping, skeleton choice and export explicit stages after AI inference. The page also links integrations and motion-data workflows, reinforcing that the generated result is an editable motion artifact rather than only a rendered video.

Luma's official Ray3.2 page positions multi-keyframe control, Modify Video and Motion/Structure settings as first-class controls. The page exposes FAQ topics for preserving actor/performance, lip-sync/dialogue timing, source-video frame rate, footage suitability and keyframe counts. Even where the page does not expose all answers in static extraction, the architecture is clear: preserve source motion/structure while changing appearance, and use explicit keyframes to direct continuity. MotionLoom can learn the separation between source motion, structural constraints and appearance transformation, while still requiring its own runtime telemetry and artifact checks.

Scenario's official platform page describes an AI creative infrastructure spanning image, video, audio and 3D, with a custom-model workflow that trains on 5–100 reference images, supports custom LoRA models and embeds brand/style guidance. It also exposes visual multi-step workflows, batch generation, reusable templates, API and MCP integration. The page lists concrete game-oriented workflows such as splitting a character/object/scene into isolated components, pose transfer and character variation, 2D animation rigging sheets, 3D auto-rigging and concept-to-game-ready 3D. The lesson for MotionLoom is to treat an AI tool as an orchestrated graph of reusable steps and agents, not only a single model call. Any claims about Scenario's internal model quality or production readiness still require artifact-level validation.

The previously discovered Adobe Firefly Video Model blog URL returned HTTP 404 when opened, so it is excluded as evidence for this report. Adobe Firefly remains a candidate source for a later pass using a currently valid official product or help page; no unsupported claim is made from the stale search snippet.

Cascadeur's official AI-tools documentation is unusually explicit about the division of labor. It lists AutoPosing, Inbetweening, AutoInterpolation and Video Mocap as ML-based tools, while separating AutoPhysics, Ragdoll, Animation Unbaking and Fulcrum Motion Cleaning as non-ML tools. AutoPosing predicts a pose from activated manipulators and their locations; Inbetweening predicts motion between keyed poses using pose, timing, keyframe count and style; AutoInterpolation predicts interpolation/kinematics types; Video Mocap extracts actor poses and applies them to a rigged character. Cascadeur also states that its tools assist rather than replace the animator, and that users' animations are not collected for training. This is a strong model for MotionLoom's human-governed boundary: AI proposes or fills motion, deterministic tools clean/measure it, and the user remains the authority for acceptance.

The current Adobe Firefly Help URL was found through official search results but returned no extractable page content in this browser session. It is therefore not treated as fully verified evidence here. The candidate workflow is camera-motion transfer from a reference video with a start frame, but this requires a future successful page extraction before being used for a strong claim.

Kinetix's current official homepage describes video-to-animation models for 3D character animation and points to integration into Unity Muse, an in-game Emote Creator for OVERDARE, and AI-assisted animation in Adobe Mixamo. This is relevant because the output is positioned as reusable in-game 3D animation, not merely a video render, and because moderation is mentioned for the player-generated emote workflow. The official publication URL suggested by the page returned 404, so no additional technical claim is taken from it.

## Cross-tool pipeline synthesis

Across the verified sources, the strongest tools do not rely on one prompt-to-final-output step. They expose a sequence of controls and artifacts:

| Pipeline layer | Patterns observed | MotionLoom implication |
|---|---|---|
| Identity/style | Reference images, custom style models, init images, palettes, persisted characters/objects | Keep identity manifest, reference hashes, palette/camera/scale and derivation chain as first-class inputs. |
| Motion source | Text action description, skeleton/pose controls, keyed poses, video performance or camera-motion reference | Bind the source type and source hash to the motion spec; do not treat generated pixels as the only source of truth. |
| Temporal construction | Explicit frame counts, start/end frames, inbetweening, interpolation, multi-keyframes, animation-to-animation editing | Expand action-set with source keyframes, timing, loop seam and editable intermediate evidence. |
| Spatial/rig mapping | Skeleton estimation, retargeting, 2D rig sheets, 3D auto-rigging, camera/direction/projection controls | Add rig compatibility, socket map, anchor/pivot and coordinate-system metadata before runtime rendering. |
| Cleanup/measurement | Studio cleanup, looping, physics tools, inpainting, frame editing, palette/geometry limits | Separate deterministic cleanup and measurement from model generation; fail closed on contamination/drift. |
| Packaging/runtime | Sprite sheets, FBX/BVH, game-engine integration, API/MCP, reusable templates and persisted states | Make export contract, runtime adapter and Dev Lab evidence mandatory for claims of readiness. |
| Governance | Licensed training data disclosures, moderation, style ownership, human review and approval boundaries | Keep provenance and user approval separate; record source/license/model details without self-asserted authority. |

This synthesis suggests that MotionLoom's differentiator should not be another generator. It should be the **artifact compiler and review governor between generators and real runtimes**: accept outputs from multiple tools, normalize their source/identity/motion metadata, measure the artifacts, render them in the target runtime, and return a user-facing evidence bundle before any PR action.
