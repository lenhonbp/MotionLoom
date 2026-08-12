# Runtime capability levels

Use explicit capability levels in reports and `agent-card.json`.

| Level | Meaning | Acceptance |
|---|---|---|
| `scaffold` | Template/code exists but runtime integration is not proven | Never sufficient for production PR |
| `static-validated` | JSON/XML/schema and local references are valid | Still not runtime evidence |
| `runtime-verified` | Target runtime rendered required frames successfully | Can pass production gate if other rules pass |
| `project-integrated` | Runtime artifact works in the actual host project route/component and target policy | Preferred final level |

The current audited levels are `runtime-verified` for Lottie JSON and SVG cutout rig. Treat Rive, GSAP, Framer Motion, Spine and Three.js as `scaffold` until their adapter test matrix is implemented.

