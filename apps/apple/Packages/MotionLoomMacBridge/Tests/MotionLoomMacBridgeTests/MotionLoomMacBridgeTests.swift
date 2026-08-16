import Foundation
import XCTest
@testable import MotionLoomMacBridge

final class MotionLoomMacBridgeTests: XCTestCase {
    func testProjectScopeRejectsRelativeTraversal() throws {
        let temporary = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: temporary, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: temporary) }
        let scope = try ProjectAccessScope(root: temporary)
        XCTAssertThrowsError(try scope.file(relativePath: "../outside.json"))
        XCTAssertThrowsError(try scope.file(relativePath: "/private/etc/passwd"))
    }

    func testQualityCommandAllowsOnlySceneIdentifier() throws {
        XCTAssertNoThrow(try MotionLoomInspectionCommand.qualityGate(scene: "runtime-pilot-framer").validate())
        XCTAssertThrowsError(try MotionLoomInspectionCommand.qualityGate(scene: "scene; rm -rf /").validate())
    }

    func testBridgeUsesArgumentVectorNotShell() throws {
        let scope = try ProjectAccessScope(root: FileManager.default.temporaryDirectory)
        let runner = SafeMotionLoomRunner(project: scope, executableURL: URL(fileURLWithPath: "/usr/bin/env"))
        let result = try runner.run(.doctor)
        XCTAssertEqual(result.arguments, ["motionloom", "doctor", "--json"])
    }
}
