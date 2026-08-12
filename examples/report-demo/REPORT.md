# Animation Task Report — report-demo

## Status
- Overall: **created**
- Confidence: **low**
- Scene: `onboarding-wave`
- Project: `example-project`
- Context hash: ``

## Completed
| Item | Status | Evidence |
| --- | --- | --- |
| Host project context analyzed | pass | ['project-context.json'] |

## Verified
| Item | Status | Evidence |
| --- | --- | --- |
| Motion spec context binding created | pass | ['motion-spec.json'] |

## Not completed
| Item | Status | Evidence |
| --- | --- | --- |
| Runtime render has not been executed in this example | pending |  |

## Problems to fix
| ID | Severity | Problem | Status | Next action |
| --- | --- | --- | --- | --- |
| runtime-evidence | P1 | PR evidence is incomplete until runtime snapshots exist | open | Render frames 0/50/100 and attach .render-meta.json |

## Structure review
- Missing files: `project-context.json`
- Broken references: `src/output/onboarding-wave/animation.json`
- Artifact count: **3**
- Quality gate: **not-run**

## Recommended next Agent / Skill
| Agent/Skill | Action | Evidence needed |
| --- | --- | --- |
| animation-studio | Run project analysis and populate context before generation. |  |
| animation-studio |  | ['snapshot/.render-meta.json', 'review.json'] |

## Evidence files
| Path | Type | Bytes | SHA-256 |
| --- | --- | --- | --- |
| handoff.json | json | 479 | b4b14fce76fa027276ab569c1b74a2de1ebdb3f8f0e3f46d9930a1e3fb5a96ae |
| issue-register.json | json | 67 | 56667cfd1b718546956e2b0b6a08adb328fe4d7c3df6814dda81b33fb8296504 |
| task.json | json | 367 | ee315e0c3eee2f12d80d4856623520b894bfdec404f0838973026401b42c2c27 |


_Generated at 2026-08-12T13:57:24Z by `scripts/report.py`._
