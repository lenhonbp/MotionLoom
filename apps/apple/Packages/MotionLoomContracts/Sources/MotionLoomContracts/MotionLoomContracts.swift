// MotionLoom Apple foundation: artifact-first, human-governed, no approval escalation.
import Foundation

public enum MotionLoomContractError: Error, LocalizedError, Equatable, Sendable {
    case invalidSchemaVersion(String)
    case invalidIdentifier(field: String)
    case invalidDigest(field: String)
    case emptyValue(field: String)
    case invalidAnnotation
    case unknownKeys(context: String, keys: [String])
    case missingKeys(context: String, keys: [String])
    case mismatchedIdentity
    case malformedJSON

    public var errorDescription: String? {
        switch self {
        case .invalidSchemaVersion(let value): return "Unsupported schema version: \(value)"
        case .invalidIdentifier(let field): return "Invalid identifier: \(field)"
        case .invalidDigest(let field): return "Invalid SHA-256 digest: \(field)"
        case .emptyValue(let field): return "Required value is empty: \(field)"
        case .invalidAnnotation: return "Review annotation is invalid"
        case .unknownKeys(let context, let keys): return "Unknown keys in \(context): \(keys.joined(separator: ", "))"
        case .missingKeys(let context, let keys): return "Missing keys in \(context): \(keys.joined(separator: ", "))"
        case .mismatchedIdentity: return "Task, candidate or evidence identity does not match"
        case .malformedJSON: return "Contract is not a JSON object"
        }
    }
}

public enum ReviewMode: String, Codable, CaseIterable, Sendable {
    case readOnly = "read_only"
    case annotate
}

public enum ReviewDecisionKind: String, Codable, CaseIterable, Sendable {
    case requestChanges = "request_changes"
    case reviewedNoDecision = "reviewed_no_decision"
    case approveForNextHumanStep = "approve_for_next_human_step"
}

public struct EvidenceDigests: Codable, Hashable, Sendable {
    public let runtimeEvidenceSHA256: String
    public let candidateReportSHA256: String
    public let attestationSHA256: String?

    public init(runtimeEvidenceSHA256: String, candidateReportSHA256: String, attestationSHA256: String? = nil) throws {
        try ContractValidation.digest(runtimeEvidenceSHA256, field: "runtime_evidence_sha256")
        try ContractValidation.digest(candidateReportSHA256, field: "candidate_report_sha256")
        if let attestationSHA256 { try ContractValidation.digest(attestationSHA256, field: "attestation_sha256") }
        self.runtimeEvidenceSHA256 = runtimeEvidenceSHA256
        self.candidateReportSHA256 = candidateReportSHA256
        self.attestationSHA256 = attestationSHA256
    }

    enum CodingKeys: String, CodingKey {
        case runtimeEvidenceSHA256 = "runtime_evidence_sha256"
        case candidateReportSHA256 = "candidate_report_sha256"
        case attestationSHA256 = "attestation_sha256"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(
            runtimeEvidenceSHA256: container.decode(String.self, forKey: .runtimeEvidenceSHA256),
            candidateReportSHA256: container.decode(String.self, forKey: .candidateReportSHA256),
            attestationSHA256: try container.decodeIfPresent(String.self, forKey: .attestationSHA256)
        )
    }
}

public struct ReviewLaunchDescriptor: Codable, Hashable, Sendable {
    public static let schemaVersion = "1.0"
    public let taskID: String
    public let candidateID: String
    public let scene: String
    public let artifactBase: String
    public let taskBase: String
    public let evidence: EvidenceDigests
    public let reviewMode: ReviewMode

    public init(taskID: String, candidateID: String, scene: String, artifactBase: String, taskBase: String, evidence: EvidenceDigests, reviewMode: ReviewMode) throws {
        try ContractValidation.identifier(taskID, field: "task_id")
        try ContractValidation.identifier(candidateID, field: "candidate_id")
        try ContractValidation.scene(scene)
        try ContractValidation.nonEmpty(artifactBase, field: "artifact_base")
        try ContractValidation.nonEmpty(taskBase, field: "task_base")
        self.taskID = taskID
        self.candidateID = candidateID
        self.scene = scene
        self.artifactBase = artifactBase
        self.taskBase = taskBase
        self.evidence = evidence
        self.reviewMode = reviewMode
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version", taskID = "task_id", candidateID = "candidate_id", scene
        case artifactBase = "artifact_base", taskBase = "task_base", evidence
        case reviewMode = "review_mode"
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let version = try container.decode(String.self, forKey: .schemaVersion)
        guard version == Self.schemaVersion else { throw MotionLoomContractError.invalidSchemaVersion(version) }
        try self.init(
            taskID: container.decode(String.self, forKey: .taskID),
            candidateID: container.decode(String.self, forKey: .candidateID),
            scene: container.decode(String.self, forKey: .scene),
            artifactBase: container.decode(String.self, forKey: .artifactBase),
            taskBase: container.decode(String.self, forKey: .taskBase),
            evidence: container.decode(EvidenceDigests.self, forKey: .evidence),
            reviewMode: container.decode(ReviewMode.self, forKey: .reviewMode)
        )
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(Self.schemaVersion, forKey: .schemaVersion)
        try container.encode(taskID, forKey: .taskID)
        try container.encode(candidateID, forKey: .candidateID)
        try container.encode(scene, forKey: .scene)
        try container.encode(artifactBase, forKey: .artifactBase)
        try container.encode(taskBase, forKey: .taskBase)
        try container.encode(evidence, forKey: .evidence)
        try container.encode(reviewMode, forKey: .reviewMode)
    }
}

public struct ReviewAnnotation: Codable, Hashable, Sendable, Identifiable {
    public let id: String
    public let timecodeMilliseconds: Int
    public let body: String

    public init(id: String, timecodeMilliseconds: Int, body: String) throws {
        try ContractValidation.nonEmpty(id, field: "annotation.id")
        guard timecodeMilliseconds >= 0, !body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, body.count <= 4000 else {
            throw MotionLoomContractError.invalidAnnotation
        }
        self.id = id
        self.timecodeMilliseconds = timecodeMilliseconds
        self.body = body
    }

    enum CodingKeys: String, CodingKey { case id, timecodeMilliseconds = "timecode_ms", body }
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(id: container.decode(String.self, forKey: .id), timecodeMilliseconds: container.decode(Int.self, forKey: .timecodeMilliseconds), body: container.decode(String.self, forKey: .body))
    }
}

public struct HumanReviewer: Codable, Hashable, Sendable {
    public let displayName: String
    public let deviceID: String?
    public let kind: String = "human"

    public init(displayName: String, deviceID: String? = nil) throws {
        try ContractValidation.nonEmpty(displayName, field: "reviewer.display_name")
        if let deviceID { try ContractValidation.nonEmpty(deviceID, field: "reviewer.device_id") }
        self.displayName = displayName
        self.deviceID = deviceID
    }

    enum CodingKeys: String, CodingKey { case kind, displayName = "display_name", deviceID = "device_id" }
    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let kind = try container.decode(String.self, forKey: .kind)
        guard kind == "human" else { throw MotionLoomContractError.emptyValue(field: "reviewer.kind must be human") }
        try self.init(displayName: container.decode(String.self, forKey: .displayName), deviceID: try container.decodeIfPresent(String.self, forKey: .deviceID))
    }
}

public struct HumanReviewDecision: Codable, Hashable, Sendable {
    public static let schemaVersion = "1.0"
    public let decisionID: String
    public let taskID: String
    public let candidateID: String
    public let evidence: EvidenceDigests
    public let decision: ReviewDecisionKind
    public let annotations: [ReviewAnnotation]
    public let createdAt: Date
    public let reviewer: HumanReviewer

    public init(decisionID: String, taskID: String, candidateID: String, evidence: EvidenceDigests, decision: ReviewDecisionKind, annotations: [ReviewAnnotation] = [], createdAt: Date, reviewer: HumanReviewer) throws {
        try ContractValidation.identifier(decisionID, field: "decision_id")
        try ContractValidation.identifier(taskID, field: "task_id")
        try ContractValidation.identifier(candidateID, field: "candidate_id")
        self.decisionID = decisionID
        self.taskID = taskID
        self.candidateID = candidateID
        self.evidence = evidence
        self.decision = decision
        self.annotations = annotations
        self.createdAt = createdAt
        self.reviewer = reviewer
    }

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version", decisionID = "decision_id", taskID = "task_id", candidateID = "candidate_id"
        case evidence, decision, annotations, createdAt = "created_at", reviewer
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let version = try container.decode(String.self, forKey: .schemaVersion)
        guard version == Self.schemaVersion else { throw MotionLoomContractError.invalidSchemaVersion(version) }
        try self.init(
            decisionID: container.decode(String.self, forKey: .decisionID),
            taskID: container.decode(String.self, forKey: .taskID),
            candidateID: container.decode(String.self, forKey: .candidateID),
            evidence: container.decode(EvidenceDigests.self, forKey: .evidence),
            decision: container.decode(ReviewDecisionKind.self, forKey: .decision),
            annotations: try container.decodeIfPresent([ReviewAnnotation].self, forKey: .annotations) ?? [],
            createdAt: container.decode(Date.self, forKey: .createdAt),
            reviewer: container.decode(HumanReviewer.self, forKey: .reviewer)
        )
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(Self.schemaVersion, forKey: .schemaVersion)
        try container.encode(decisionID, forKey: .decisionID)
        try container.encode(taskID, forKey: .taskID)
        try container.encode(candidateID, forKey: .candidateID)
        try container.encode(evidence, forKey: .evidence)
        try container.encode(decision, forKey: .decision)
        try container.encode(annotations, forKey: .annotations)
        try container.encode(createdAt, forKey: .createdAt)
        try container.encode(reviewer, forKey: .reviewer)
    }
}

public enum MotionLoomContractDecoder {
    public static func launchDescriptor(from data: Data) throws -> ReviewLaunchDescriptor {
        try StrictJSON.validateLaunch(data)
        return try JSONDecoder().decode(ReviewLaunchDescriptor.self, from: data)
    }

    public static func reviewDecision(from data: Data) throws -> HumanReviewDecision {
        try StrictJSON.validateDecision(data)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return try decoder.decode(HumanReviewDecision.self, from: data)
    }

    public static func verify(_ decision: HumanReviewDecision, matches launch: ReviewLaunchDescriptor) throws {
        guard decision.taskID == launch.taskID, decision.candidateID == launch.candidateID, decision.evidence == launch.evidence else {
            throw MotionLoomContractError.mismatchedIdentity
        }
    }
}

private enum ContractValidation {
    static func nonEmpty(_ value: String, field: String) throws {
        guard !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw MotionLoomContractError.emptyValue(field: field) }
    }

    static func identifier(_ value: String, field: String) throws {
        let expression = try! NSRegularExpression(pattern: "^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
        guard expression.firstMatch(in: value, range: NSRange(value.startIndex..., in: value)) != nil else { throw MotionLoomContractError.invalidIdentifier(field: field) }
    }

    static func scene(_ value: String) throws {
        let expression = try! NSRegularExpression(pattern: "^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
        guard expression.firstMatch(in: value, range: NSRange(value.startIndex..., in: value)) != nil else { throw MotionLoomContractError.invalidIdentifier(field: "scene") }
    }

    static func digest(_ value: String, field: String) throws {
        let expression = try! NSRegularExpression(pattern: "^[a-f0-9]{64}$")
        guard expression.firstMatch(in: value, range: NSRange(value.startIndex..., in: value)) != nil else { throw MotionLoomContractError.invalidDigest(field: field) }
    }
}

private enum StrictJSON {
    static func validateLaunch(_ data: Data) throws {
        let root = try object(data, context: "launch")
        try keys(root, allowed: ["schema_version", "task_id", "candidate_id", "scene", "artifact_base", "task_base", "evidence", "review_mode"], required: ["schema_version", "task_id", "candidate_id", "scene", "artifact_base", "task_base", "evidence", "review_mode"], context: "launch")
        try evidence(root["evidence"])
    }

    static func validateDecision(_ data: Data) throws {
        let root = try object(data, context: "decision")
        try keys(root, allowed: ["schema_version", "decision_id", "task_id", "candidate_id", "evidence", "decision", "annotations", "created_at", "reviewer"], required: ["schema_version", "decision_id", "task_id", "candidate_id", "evidence", "decision", "created_at", "reviewer"], context: "decision")
        try evidence(root["evidence"])
        let reviewer = try objectValue(root["reviewer"], context: "reviewer")
        try keys(reviewer, allowed: ["kind", "display_name", "device_id"], required: ["kind", "display_name"], context: "reviewer")
        if let annotations = root["annotations"] as? [[String: Any]] {
            for annotation in annotations {
                try keys(annotation, allowed: ["id", "timecode_ms", "body"], required: ["id", "timecode_ms", "body"], context: "annotation")
            }
        }
    }

    private static func evidence(_ value: Any?) throws {
        let evidence = try objectValue(value, context: "evidence")
        try keys(evidence, allowed: ["runtime_evidence_sha256", "candidate_report_sha256", "attestation_sha256"], required: ["runtime_evidence_sha256", "candidate_report_sha256"], context: "evidence")
    }

    private static func object(_ data: Data, context: String) throws -> [String: Any] {
        guard let value = try? JSONSerialization.jsonObject(with: data), let object = value as? [String: Any] else { throw MotionLoomContractError.malformedJSON }
        return object
    }

    private static func objectValue(_ value: Any?, context: String) throws -> [String: Any] {
        guard let object = value as? [String: Any] else { throw MotionLoomContractError.missingKeys(context: context, keys: ["object"]) }
        return object
    }

    private static func keys(_ object: [String: Any], allowed: Set<String>, required: Set<String>, context: String) throws {
        let unknown = Set(object.keys).subtracting(allowed).sorted()
        if !unknown.isEmpty { throw MotionLoomContractError.unknownKeys(context: context, keys: unknown) }
        let missing = required.subtracting(object.keys).sorted()
        if !missing.isEmpty { throw MotionLoomContractError.missingKeys(context: context, keys: missing) }
    }
}
