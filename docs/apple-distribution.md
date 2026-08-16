# Apple distribution boundary

The current `MotionLoomStudio` build is an unsigned local alpha. GitHub CI builds packages and checks iOS Simulator compatibility; it does not sign, upload, submit or distribute an application.

| Channel | Required external inputs | Current state |
| --- | --- | --- |
| Local macOS alpha | Xcode and a user-selected project folder | Implemented and manually launchable. |
| iOS Simulator review UI | Xcode simulator runtime and an Xcode app target that embeds `MotionLoomReviewUI` | Library cross-compilation is verified; the signed target remains intentionally uncreated. |
| TestFlight | Apple Developer Program membership, bundle identifier, signing, App Store Connect app record and a user approval to upload | Not initiated. |
| Mac App Store / iOS App Store | The TestFlight requirements plus app metadata, privacy details and an explicit human submission decision | Not initiated. |

TestFlight distribution is handled through App Store Connect and requires the app owner to control signing and submission; MotionLoom’s CI must stay read-only until an owner explicitly decides to introduce that workflow.[1]

## Before a TestFlight decision

1. Create a final bundle identifier and an Apple-owned iCloud container; do not reuse development identifiers accidentally.
2. Create the iOS/macOS Xcode app targets and add `MotionLoomContracts`, `MotionLoomReview`, `MotionLoomReviewUI` and, on macOS, `MotionLoomMacBridge` as local packages.
3. Complete privacy labels and explain that CloudKit is limited to review metadata if sync is enabled.
4. Test review JSON handoff with a real candidate on a physical iPhone/iPad and macOS.
5. Make a separate explicit decision before uploading any build, inviting testers or submitting for review.

## References

[1]: https://developer.apple.com/testflight/ "Apple Developer — TestFlight"
