// MotionLoom review core: timeline evidence and human handoff, never production approval.
import Foundation
#if SWIFT_PACKAGE
import MotionLoomContracts
#endif

public struct ReviewTimeline: Hashable, Sendable {
    public let durationMilliseconds: Int
    public private(set) var playheadMilliseconds: Int

    public init(durationMilliseconds: Int = 1_200, playheadMilliseconds: Int = 0) {
        self.durationMilliseconds = max(1, durationMilliseconds)
        self.playheadMilliseconds = min(max(0, playheadMilliseconds), max(1, durationMilliseconds))
    }

    public mutating func seek(to milliseconds: Int) {
        playheadMilliseconds = min(max(0, milliseconds), durationMilliseconds)
    }

    public mutating func seek(normalized value: Double) {
        seek(to: Int((min(max(value, 0), 1) * Double(durationMilliseconds)).rounded()))
    }

    public var normalizedPlayhead: Double { Double(playheadMilliseconds) / Double(durationMilliseconds) }
    public var checkpointMilliseconds: [Int] { [0, durationMilliseconds / 2, durationMilliseconds] }
}

public struct ReviewDraft: Hashable, Sendable {
    public var decision: ReviewDecisionKind
    public var annotations: [ReviewAnnotation]

    public init(decision: ReviewDecisionKind = .reviewedNoDecision, annotations: [ReviewAnnotation] = []) {
        self.decision = decision
        self.annotations = annotations
    }

    public mutating func addAnnotation(body: String, at timecodeMilliseconds: Int, id: String = "note-\(UUID().uuidString.lowercased())") throws {
        annotations.append(try ReviewAnnotation(id: id, timecodeMilliseconds: timecodeMilliseconds, body: body))
    }

    public func decisionRecord(for launch: ReviewLaunchDescriptor, reviewer: HumanReviewer, at date: Date = .now, id: String = "review-\(UUID().uuidString.lowercased())") throws -> HumanReviewDecision {
        try HumanReviewDecision(
            decisionID: id,
            taskID: launch.taskID,
            candidateID: launch.candidateID,
            evidence: launch.evidence,
            decision: decision,
            annotations: annotations,
            createdAt: date,
            reviewer: reviewer
        )
    }
}

public enum ReviewDecisionWriter {
    public static func encode(_ review: HumanReviewDecision) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        return try encoder.encode(review)
    }

    public static func write(_ review: HumanReviewDecision, to url: URL) throws {
        try encode(review).write(to: url, options: .atomic)
    }
}
