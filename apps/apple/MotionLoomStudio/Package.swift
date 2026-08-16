// swift-tools-version: 6.0
// MotionLoom Studio: macOS inspection and human-review surface.
import PackageDescription

let package = Package(
    name: "MotionLoomStudio",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "MotionLoomStudio", targets: ["MotionLoomStudio"])],
    dependencies: [
        .package(path: "../Packages/MotionLoomContracts"),
        .package(path: "../Packages/MotionLoomReview"),
        .package(path: "../Packages/MotionLoomMacBridge"),
    ],
    targets: [
        .executableTarget(
            name: "MotionLoomStudio",
            dependencies: ["MotionLoomContracts", "MotionLoomReview", "MotionLoomMacBridge"]
        )
    ]
)
