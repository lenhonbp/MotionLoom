// swift-tools-version: 6.0
// MotionLoom Apple foundation: artifact-first, human-governed, no approval escalation.
import PackageDescription

let package = Package(
    name: "MotionLoomContracts",
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [.library(name: "MotionLoomContracts", targets: ["MotionLoomContracts"])],
    targets: [
        .target(name: "MotionLoomContracts"),
        .testTarget(name: "MotionLoomContractsTests", dependencies: ["MotionLoomContracts"]),
    ]
)
