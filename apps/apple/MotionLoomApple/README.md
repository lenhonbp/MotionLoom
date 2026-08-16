# MotionLoomApple Xcode project

This project has two unsigned local-alpha targets that consume the same packages as the CLI-adjacent source:

| Target | Runtime | Purpose | Scope boundary |
| --- | --- | --- | --- |
| `MotionLoomStudio` | macOS 14+ | Project Inspector, Timeline Desk, Dev Lab review and human-review export. | Local inspect-only bridge; no arbitrary shell, push, PR, publish or production approval. |
| `MotionLoomReview` | iOS/iPadOS 17+ | Evidence review, timecode annotation and shareable human-review JSON. | No repository/source asset access, CloudKit write or production authority in this target. |

## Build without signing

```bash
xcodebuild \
  -project MotionLoomApple.xcodeproj \
  -target MotionLoomStudio \
  -sdk macosx \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO build

xcodebuild \
  -project MotionLoomApple.xcodeproj \
  -target MotionLoomReview \
  -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -configuration Debug \
  CODE_SIGNING_ALLOWED=NO build
```

No app is signed or upload-capable in this project. Introducing an Apple Developer team, iCloud entitlement, TestFlight upload or App Store submission is a separate, explicit owner decision documented in [`docs/apple-distribution.md`](../../../docs/apple-distribution.md).
