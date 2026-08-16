// swift-tools-version: 6.0
// MotionLoom macOS bridge: scoped project access and non-destructive commands only.
import PackageDescription

let package = Package(
    name: "MotionLoomMacBridge",
    platforms: [.macOS(.v14)],
    products: [.library(name: "MotionLoomMacBridge", targets: ["MotionLoomMacBridge"])],
    dependencies: [.package(path: "../MotionLoomContracts")],
    targets: [
        .target(name: "MotionLoomMacBridge", dependencies: ["MotionLoomContracts"]),
        .testTarget(name: "MotionLoomMacBridgeTests", dependencies: ["MotionLoomMacBridge"]),
    ]
)
