// MotionLoom macOS bridge: scoped project access and non-destructive commands only.
import Foundation

public enum MacBridgeError: Error, LocalizedError, Equatable, Sendable {
    case rootIsNotDirectory
    case pathEscapesProject
    case unsupportedCommand
    case invalidScene
    case processCouldNotStart(String)

    public var errorDescription: String? {
        switch self {
        case .rootIsNotDirectory: return "The selected MotionLoom project root is not a directory."
        case .pathEscapesProject: return "The selected path is outside the granted project root."
        case .unsupportedCommand: return "The app permits only allow-listed non-destructive MotionLoom commands."
        case .invalidScene: return "The scene identifier is invalid."
        case .processCouldNotStart(let reason): return "Could not start the MotionLoom command: \(reason)"
        }
    }
}

public struct ProjectAccessScope: Hashable, Sendable {
    public let root: URL

    public init(root: URL) throws {
        let normalized = root.standardizedFileURL.resolvingSymlinksInPath()
        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: normalized.path, isDirectory: &isDirectory), isDirectory.boolValue else {
            throw MacBridgeError.rootIsNotDirectory
        }
        self.root = normalized
    }

    public func file(relativePath: String) throws -> URL {
        guard !relativePath.isEmpty, !relativePath.hasPrefix("/"), !relativePath.split(separator: "/").contains("..") else {
            throw MacBridgeError.pathEscapesProject
        }
        let candidate = root.appendingPathComponent(relativePath).standardizedFileURL.resolvingSymlinksInPath()
        let prefix = root.path.hasSuffix("/") ? root.path : root.path + "/"
        guard candidate.path.hasPrefix(prefix) || candidate == root else { throw MacBridgeError.pathEscapesProject }
        return candidate
    }

    #if os(macOS)
    public func securityScopedBookmark() throws -> Data {
        try root.bookmarkData(options: .withSecurityScope, includingResourceValuesForKeys: nil, relativeTo: nil)
    }

    public static func restoreSecurityScopedBookmark(_ data: Data) throws -> (scope: ProjectAccessScope, requiresStopAccessing: Bool) {
        var stale = false
        let url = try URL(resolvingBookmarkData: data, options: [.withSecurityScope, .withoutUI], relativeTo: nil, bookmarkDataIsStale: &stale)
        let accessed = url.startAccessingSecurityScopedResource()
        return (try ProjectAccessScope(root: url), accessed)
    }
    #endif
}

public enum MotionLoomInspectionCommand: Hashable, Sendable {
    case doctor
    case discoveryCheck
    case qualityGate(scene: String)

    public var arguments: [String] {
        switch self {
        case .doctor: return ["motionloom", "doctor", "--json"]
        case .discoveryCheck: return ["motionloom", "discovery", "check"]
        case .qualityGate(let scene): return ["motionloom", "quality", "--scene", scene]
        }
    }

    public func validate() throws {
        if case .qualityGate(let scene) = self {
            let expression = try! NSRegularExpression(pattern: "^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
            guard expression.firstMatch(in: scene, range: NSRange(scene.startIndex..., in: scene)) != nil else { throw MacBridgeError.invalidScene }
        }
    }
}

public struct CommandResult: Hashable, Sendable {
    public let arguments: [String]
    public let terminationStatus: Int32
    public let standardOutput: String
    public let standardError: String
}

public struct SafeMotionLoomRunner: Sendable {
    public let project: ProjectAccessScope
    public let executableURL: URL

    public init(project: ProjectAccessScope, executableURL: URL = URL(fileURLWithPath: "/usr/bin/env")) {
        self.project = project
        self.executableURL = executableURL
    }

    public func run(_ command: MotionLoomInspectionCommand) throws -> CommandResult {
        try command.validate()
        let process = Process()
        process.executableURL = executableURL
        process.arguments = command.arguments
        process.currentDirectoryURL = project.root
        let output = Pipe()
        let error = Pipe()
        process.standardOutput = output
        process.standardError = error
        do {
            try process.run()
        } catch {
            throw MacBridgeError.processCouldNotStart(error.localizedDescription)
        }
        process.waitUntilExit()
        return CommandResult(
            arguments: command.arguments,
            terminationStatus: process.terminationStatus,
            standardOutput: String(decoding: output.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self),
            standardError: String(decoding: error.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
        )
    }
}
