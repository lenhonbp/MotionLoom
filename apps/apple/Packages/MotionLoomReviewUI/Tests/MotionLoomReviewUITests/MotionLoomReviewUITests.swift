import Foundation
import XCTest
@testable import MotionLoomContracts
@testable import MotionLoomReviewUI

@MainActor
final class MotionLoomReviewUITests: XCTestCase {
    func testCompanionExportsHumanDecisionOnly() throws {
        let evidence = try EvidenceDigests(runtimeEvidenceSHA256: String(repeating: "a", count: 64), candidateReportSHA256: String(repeating: "b", count: 64))
        let launch = try ReviewLaunchDescriptor(taskID: "task-a", candidateID: "candidate-a", scene: "scene-a", artifactBase: "https://example.test/artifacts", taskBase: "https://example.test/tasks", evidence: evidence, reviewMode: .annotate)
        let model = ReviewConsoleModel(launch: launch)
        model.annotationText = "Inspect the midpoint."
        model.timeline.seek(to: 600)
        model.addAnnotation()
        let exported = try model.exportDecision(reviewerName: "Reviewer")
        let decision = try MotionLoomContractDecoder.reviewDecision(from: exported)
        XCTAssertEqual(decision.taskID, "task-a")
        XCTAssertEqual(decision.candidateID, "candidate-a")
        XCTAssertEqual(decision.annotations.first?.timecodeMilliseconds, 600)
        XCTAssertEqual(decision.decision, .requestChanges)
    }
}
