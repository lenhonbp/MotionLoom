// MotionLoom Review App: iOS/iPadOS entry-point template. Add this file to an iOS app target in Xcode.
import SwiftUI
#if SWIFT_PACKAGE
import MotionLoomContracts
import MotionLoomReviewUI
#endif

@main
struct MotionLoomReviewApp: App {
    private let launch: ReviewLaunchDescriptor = {
        let evidence = try! EvidenceDigests(
            runtimeEvidenceSHA256: "2fe4258081208faec1471294c460e7fe06e98b8bb9f793d5d43582a7deb88b52",
            candidateReportSHA256: "a85156020ff421e94d344af0ab70e6506ccb3ba49ff376c7c1d9155c7672beb3"
        )
        return try! ReviewLaunchDescriptor(
            taskID: "runtime-pilot-001", candidateID: "8cccc4ac5a7e493ffe40", scene: "runtime-pilot-framer",
            artifactBase: "https://animdevlab-hcxnxr9c.manus.space/scenes/runtime-pilot-framer",
            taskBase: "https://animdevlab-hcxnxr9c.manus.space/tasks/runtime-pilot-001",
            evidence: evidence, reviewMode: .annotate
        )
    }()

    var body: some Scene {
        WindowGroup { ReviewConsoleView(launch: launch) }
    }
}
