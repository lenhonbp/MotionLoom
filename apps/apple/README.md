# MotionLoom Apple applications

`MotionLoomStudio` is the macOS alpha. It is a native SwiftUI inspection and human-review surface around existing MotionLoom artifacts. It does not replace the cross-platform Node/Python CLI or Dev Lab, and it deliberately does not provide production approval, Git push, PR creation, npm publishing or App Store submission controls.

The package architecture separates contracts, review state and macOS-only project access:

| Package | Responsibility | Explicit boundary |
| --- | --- | --- |
| `MotionLoomContracts` | Strict decoding and identity binding for review launch and human decision records | Rejects unknown properties; no production-approval state exists. |
| `MotionLoomReview` | Timeline state, annotations and deterministic review JSON export | Emits only the three permitted human review decisions. |
| `MotionLoomMacBridge` | Security-scoped project folder access and inspection command allow-list | No arbitrary shell, push, PR or publish command. |
| `MotionLoomStudio` | macOS SwiftUI Project Inspector and Timeline Desk | Opens the existing Dev Lab review URL in a native web surface. |

## Local build

After installing Xcode and accepting its license, run:

```bash
cd apps/apple/Packages/MotionLoomContracts && swift test
cd ../MotionLoomReview && swift test
cd ../MotionLoomMacBridge && swift test
cd ../MotionLoomReviewUI && swift test
cd ../MotionLoomReviewSync && swift test
cd ../../MotionLoomStudio && swift build
swift run MotionLoomStudio
```

To cross-compile the iOS Review UI library with the installed simulator SDK, generate a machine-local SwiftPM destination rather than commit a fixed Xcode SDK path:

```bash
destination="$(mktemp)"
apps/apple/scripts/emit-ios-simulator-destination.sh "$destination"
(cd apps/apple/Packages/MotionLoomReviewUI && swift build --destination "$destination")
rm -f "$destination"
```

The first product build is intentionally local and unsigned. Distribution through TestFlight or the App Store requires an Apple Developer team, App ID, signing profile, bundle identifier and an explicit user decision to submit a build.
