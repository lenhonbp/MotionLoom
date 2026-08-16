// MotionLoom Review Sync: local-first review metadata only; never source assets or approval authority.
import CloudKit
import CryptoKit
import Foundation
import MotionLoomContracts

public struct ReviewSyncMetadata: Codable, Hashable, Sendable {
    public let schemaVersion: String
    public let reviewID: String
    public let taskID: String
    public let candidateID: String
    public let decision: ReviewDecisionKind
    public let createdAt: Date
    public let reviewerDisplayName: String
    public let annotationCount: Int
    public let runtimeEvidenceSHA256: String
    public let candidateReportSHA256: String
    public let reviewJSONSHA256: String

    public init(decision: HumanReviewDecision) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        let body = try encoder.encode(decision)
        schemaVersion = "1.0"
        reviewID = decision.decisionID
        taskID = decision.taskID
        candidateID = decision.candidateID
        self.decision = decision.decision
        createdAt = decision.createdAt
        reviewerDisplayName = decision.reviewer.displayName
        annotationCount = decision.annotations.count
        runtimeEvidenceSHA256 = decision.evidence.runtimeEvidenceSHA256
        candidateReportSHA256 = decision.evidence.candidateReportSHA256
        reviewJSONSHA256 = SHA256.hash(data: body).map { String(format: "%02x", $0) }.joined()
    }
}

public enum ReviewSyncError: Error, LocalizedError, Equatable, Sendable {
    case identityBindingFailed
    case invalidRecordIdentifier
    case outboxDoesNotExist

    public var errorDescription: String? {
        switch self {
        case .identityBindingFailed: return "Review metadata cannot sync because its task, candidate or evidence identity does not match the launch descriptor."
        case .invalidRecordIdentifier: return "Review record identifiers must be non-empty."
        case .outboxDoesNotExist: return "The review outbox does not exist."
        }
    }
}

public enum ReviewSyncFactory {
    public static func makeMetadata(decision: HumanReviewDecision, launch: ReviewLaunchDescriptor) throws -> ReviewSyncMetadata {
        do {
            try MotionLoomContractDecoder.verify(decision, matches: launch)
        } catch {
            throw ReviewSyncError.identityBindingFailed
        }
        return try ReviewSyncMetadata(decision: decision)
    }
}

public final class CloudKitReviewMetadataSync {
    private let database: CKDatabase

    public init(containerIdentifier: String? = nil) {
        let container = containerIdentifier.map(CKContainer.init(identifier:)) ?? CKContainer.default()
        database = container.privateCloudDatabase
    }

    public func upload(decision: HumanReviewDecision, verifiedAgainst launch: ReviewLaunchDescriptor) async throws -> ReviewSyncMetadata {
        let metadata = try ReviewSyncFactory.makeMetadata(decision: decision, launch: launch)
        guard !metadata.reviewID.isEmpty else { throw ReviewSyncError.invalidRecordIdentifier }
        let record = CKRecord(recordType: "MotionLoomReviewMetadata", recordID: CKRecord.ID(recordName: metadata.reviewID))
        record["schema_version"] = metadata.schemaVersion as CKRecordValue
        record["task_id"] = metadata.taskID as CKRecordValue
        record["candidate_id"] = metadata.candidateID as CKRecordValue
        record["decision"] = metadata.decision.rawValue as CKRecordValue
        record["created_at"] = metadata.createdAt as CKRecordValue
        record["reviewer_display_name"] = metadata.reviewerDisplayName as CKRecordValue
        record["annotation_count"] = metadata.annotationCount as CKRecordValue
        record["runtime_evidence_sha256"] = metadata.runtimeEvidenceSHA256 as CKRecordValue
        record["candidate_report_sha256"] = metadata.candidateReportSHA256 as CKRecordValue
        record["review_json_sha256"] = metadata.reviewJSONSHA256 as CKRecordValue
        _ = try await database.save(record)
        return metadata
    }
}

public actor ReviewOutbox {
    private let directory: URL

    public init(directory: URL) throws {
        self.directory = directory
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    }

    public func enqueue(_ decision: HumanReviewDecision) throws -> URL {
        guard !decision.decisionID.isEmpty else { throw ReviewSyncError.invalidRecordIdentifier }
        let destination = directory.appendingPathComponent("\(decision.decisionID).json")
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        encoder.dateEncodingStrategy = .iso8601
        try encoder.encode(decision).write(to: destination, options: .atomic)
        return destination
    }

    public func pendingURLs() throws -> [URL] {
        try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
            .filter { $0.pathExtension == "json" }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }
    }

    public func remove(_ url: URL) throws {
        guard url.deletingLastPathComponent().standardizedFileURL == directory.standardizedFileURL else {
            throw ReviewSyncError.outboxDoesNotExist
        }
        try FileManager.default.removeItem(at: url)
    }
}
