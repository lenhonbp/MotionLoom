import Foundation
import XCTest
@testable import MotionLoomContracts
@testable import MotionLoomReview

final class MotionLoomReviewTests: XCTestCase {
    func testTimelineClampsAndExposesRuntimeCheckpoints() {
        var timeline = ReviewTimeline(durationMilliseconds: 1_200, playheadMilliseconds: -1)
        XCTAssertEqual(timeline.playheadMilliseconds, 0)
        timeline.seek(to: 2_000)
        XCTAssertEqual(timeline.playheadMilliseconds, 1_200)
        XCTAssertEqual(timeline.checkpointMilliseconds, [0, 600, 1_200])
    }

    func testDecisionExportIsHumanBoundAndIdentityBound() throws {
        let evidence = try EvidenceDigests(runtimeEvidenceSHA256: String(repeating: "a", count: 64), candidateReportSHA256: String(repeating: "b", count: 64))
        let launch = try ReviewLaunchDescriptor(taskID: "runtime-pilot-001", candidateID: "candidate-one", scene: "runtime-pilot-framer", artifactBase: "https://example.test/scene", taskBase: "https://example.test/task", evidence: evidence, reviewMode: .annotate)
        var draft = ReviewDraft(decision: .requestChanges)
        try draft.addAnnotation(body: "Midpoint needs review.", at: 600, id: "note-midpoint")
        let review = try draft.decisionRecord(for: launch, reviewer: try HumanReviewer(displayName: "Reviewer"), at: Date(timeIntervalSince1970: 0), id: "review-one")
        let decoded = try MotionLoomContractDecoder.reviewDecision(from: ReviewDecisionWriter.encode(review))
        XCTAssertEqual(decoded.decision, .requestChanges)
        XCTAssertEqual(decoded.taskID, launch.taskID)
        XCTAssertEqual(decoded.annotations.first?.timecodeMilliseconds, 600)
        XCTAssertNoThrow(try MotionLoomContractDecoder.verify(decoded, matches: launch))
    }
}
