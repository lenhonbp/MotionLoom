# MotionLoom Studio alpha

MotionLoom Studio is a **native macOS inspection and review surface**, not a replacement for the cross-platform MotionLoom CLI, its Python validators, runtime adapters or Dev Lab. The Studio presents verified task/candidate/evidence identity and helps a human create a review handoff.

| Surface | Responsibility | Prohibited actions |
| --- | --- | --- |
| Project Inspector | User selects a scoped project folder, then launches a small allow-list of local inspections. | Arbitrary shell, `git push`, `OPEN_PR=1`, npm publish and PR creation. |
| Timeline Desk | Scrub review timecodes, open the existing Dev Lab candidate and collect annotations. | Treating a preview or heuristic as approval. |
| Evidence | Shows task/candidate identity and SHA-256 digests before review. | Loading a candidate whose identity binding is not valid. |
| Export Human Review | Writes a deterministic review JSON for an Agent or maintainer to act on later. | Writing `production_approved` or modifying a repository. |

The app uses `ProjectAccessScope` to confine read/write operations to an explicitly selected project root. It invokes the CLI through an argument vector and a closed command enum, never a shell string. macOS security-scoped bookmarks are supported for a later sandboxed/notarized build, but the alpha remains unsigned and local.

## Local verification

```bash
cd apps/apple/Packages/MotionLoomContracts && swift test
cd ../MotionLoomReview && swift test
cd ../MotionLoomMacBridge && swift test
cd ../MotionLoomReviewUI && swift test
cd ../MotionLoomReviewSync && swift test
cd ../../MotionLoomStudio && swift build
swift run MotionLoomStudio
```

To verify the companion library against the installed iOS Simulator SDK without signing an app bundle:

```bash
destination="$(mktemp)"
apps/apple/scripts/emit-ios-simulator-destination.sh "$destination"
(cd apps/apple/Packages/MotionLoomReviewUI && swift build --destination "$destination")
rm -f "$destination"
```

> A successful native build, attestation or quality gate is **not** human approval. The only review records emitted by the app are `request_changes`, `reviewed_no_decision`, and `approve_for_next_human_step`.
