// swift-tools-version: 6.0
// MotionLoom Review Sync: local-first review metadata only; never source assets or approval authority.
import PackageDescription

let package = Package(
    name: "MotionLoomReviewSync",
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [.library(name: "MotionLoomReviewSync", targets: ["MotionLoomReviewSync"])],
    dependencies: [.package(path: "../MotionLoomContracts")],
    targets: [
        .target(name: "MotionLoomReviewSync", dependencies: ["MotionLoomContracts"]),
        .testTarget(name: "MotionLoomReviewSyncTests", dependencies: ["MotionLoomReviewSync", "MotionLoomContracts"]),
    ]
)
