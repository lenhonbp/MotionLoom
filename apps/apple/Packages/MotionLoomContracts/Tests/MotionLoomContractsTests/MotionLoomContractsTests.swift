import Foundation
import XCTest
@testable import MotionLoomContracts

final class MotionLoomContractsTests: XCTestCase {
    func testDecodesLaunchDescriptor() throws {
        let data = Data("""
        {"schema_version":"1.0","task_id":"runtime-pilot-001","candidate_id":"8cccc4ac5a7e493ffe40","scene":"runtime-pilot-framer","artifact_base":"https://example.test/scene","task_base":"https://example.test/task","review_mode":"annotate","evidence":{"runtime_evidence_sha256":"2fe4258081208faec1471294c460e7fe06e98b8bb9f793d5d43582a7deb88b52","candidate_report_sha256":"a85156020ff421e94d344af0ab70e6506ccb3ba49ff376c7c1d9155c7672beb3"}}
        """.utf8)
        let descriptor = try MotionLoomContractDecoder.launchDescriptor(from: data)
        XCTAssertEqual(descriptor.taskID, "runtime-pilot-001")
        XCTAssertEqual(descriptor.reviewMode, .annotate)
    }

    func testRejectsUnknownLaunchField() {
        let data = Data("""
        {"schema_version":"1.0","task_id":"runtime-pilot-001","candidate_id":"8cccc4ac5a7e493ffe40","scene":"runtime-pilot-framer","artifact_base":"https://example.test/scene","task_base":"https://example.test/task","review_mode":"read_only","evidence":{"runtime_evidence_sha256":"2fe4258081208faec1471294c460e7fe06e98b8bb9f793d5d43582a7deb88b52","candidate_report_sha256":"a85156020ff421e94d344af0ab70e6506ccb3ba49ff376c7c1d9155c7672beb3"},"open_pr":true}
        """.utf8)
        XCTAssertThrowsError(try MotionLoomContractDecoder.launchDescriptor(from: data))
    }

    func testRejectsMismatchedDecision() throws {
        let evidence = try EvidenceDigests(runtimeEvidenceSHA256: String(repeating: "a", count: 64), candidateReportSHA256: String(repeating: "b", count: 64))
        let launch = try ReviewLaunchDescriptor(taskID: "runtime-pilot-001", candidateID: "candidate-one", scene: "runtime-pilot-framer", artifactBase: "https://example.test/scene", taskBase: "https://example.test/task", evidence: evidence, reviewMode: .annotate)
        let decision = try HumanReviewDecision(decisionID: "decision-one", taskID: "runtime-pilot-001", candidateID: "candidate-two", evidence: evidence, decision: .requestChanges, createdAt: .now, reviewer: try HumanReviewer(displayName: "Reviewer"))
        XCTAssertThrowsError(try MotionLoomContractDecoder.verify(decision, matches: launch))
    }
}
