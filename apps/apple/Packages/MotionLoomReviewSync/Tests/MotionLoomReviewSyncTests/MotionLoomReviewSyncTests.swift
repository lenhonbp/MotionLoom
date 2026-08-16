import Foundation
import XCTest
@testable import MotionLoomContracts
@testable import MotionLoomReviewSync

final class MotionLoomReviewSyncTests: XCTestCase {
    func testMetadataIsBoundToMatchingLaunchAndContainsNoSourceAsset() throws {
        let evidence = try EvidenceDigests(runtimeEvidenceSHA256: String(repeating: "a", count: 64), candidateReportSHA256: String(repeating: "b", count: 64))
        let launch = try ReviewLaunchDescriptor(taskID: "task-a", candidateID: "candidate-a", scene: "scene-a", artifactBase: "https://example.test/artifacts", taskBase: "https://example.test/tasks", evidence: evidence, reviewMode: .annotate)
        let decision = try HumanReviewDecision(decisionID: "review-a", taskID: "task-a", candidateID: "candidate-a", evidence: evidence, decision: .requestChanges, annotations: [], createdAt: Date(timeIntervalSince1970: 0), reviewer: try HumanReviewer(displayName: "Reviewer"))
        let metadata = try ReviewSyncFactory.makeMetadata(decision: decision, launch: launch)
        XCTAssertEqual(metadata.taskID, "task-a")
        XCTAssertEqual(metadata.candidateID, "candidate-a")
        XCTAssertEqual(metadata.annotationCount, 0)
        XCTAssertEqual(metadata.runtimeEvidenceSHA256.count, 64)
    }

    func testMetadataRejectsMismatchedIdentity() throws {
        let evidence = try EvidenceDigests(runtimeEvidenceSHA256: String(repeating: "a", count: 64), candidateReportSHA256: String(repeating: "b", count: 64))
        let launch = try ReviewLaunchDescriptor(taskID: "task-a", candidateID: "candidate-a", scene: "scene-a", artifactBase: "https://example.test/artifacts", taskBase: "https://example.test/tasks", evidence: evidence, reviewMode: .annotate)
        let decision = try HumanReviewDecision(decisionID: "review-a", taskID: "task-a", candidateID: "candidate-b", evidence: evidence, decision: .requestChanges, annotations: [], createdAt: Date(timeIntervalSince1970: 0), reviewer: try HumanReviewer(displayName: "Reviewer"))
        XCTAssertThrowsError(try ReviewSyncFactory.makeMetadata(decision: decision, launch: launch))
    }

    func testOutboxPersistsOnlyExplicitReviewDecision() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let evidence = try EvidenceDigests(runtimeEvidenceSHA256: String(repeating: "a", count: 64), candidateReportSHA256: String(repeating: "b", count: 64))
        let decision = try HumanReviewDecision(decisionID: "review-a", taskID: "task-a", candidateID: "candidate-a", evidence: evidence, decision: .requestChanges, annotations: [], createdAt: Date(timeIntervalSince1970: 0), reviewer: try HumanReviewer(displayName: "Reviewer"))
        let outbox = try ReviewOutbox(directory: directory)
        _ = try await outbox.enqueue(decision)
        let pending = try await outbox.pendingURLs()
        XCTAssertEqual(pending.map(\.lastPathComponent), ["review-a.json"])
    }
}
