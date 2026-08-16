// swift-tools-version: 6.0
// Xcode integration package: one local package graph for the MotionLoom Apple app targets.
import PackageDescription

let package = Package(
    name: "MotionLoomAppleSources",
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [
        .library(name: "MotionLoomContracts", targets: ["MotionLoomContracts"]),
        .library(name: "MotionLoomReview", targets: ["MotionLoomReview"]),
        .library(name: "MotionLoomMacBridge", targets: ["MotionLoomMacBridge"]),
        .library(name: "MotionLoomReviewUI", targets: ["MotionLoomReviewUI"]),
        .library(name: "MotionLoomReviewSync", targets: ["MotionLoomReviewSync"]),
    ],
    targets: [
        .target(name: "MotionLoomContracts", path: "Packages/MotionLoomContracts/Sources/MotionLoomContracts"),
        .target(name: "MotionLoomReview", dependencies: ["MotionLoomContracts"], path: "Packages/MotionLoomReview/Sources/MotionLoomReview"),
        .target(name: "MotionLoomMacBridge", dependencies: ["MotionLoomContracts"], path: "Packages/MotionLoomMacBridge/Sources/MotionLoomMacBridge"),
        .target(name: "MotionLoomReviewUI", dependencies: ["MotionLoomContracts", "MotionLoomReview"], path: "Packages/MotionLoomReviewUI/Sources/MotionLoomReviewUI"),
        .target(name: "MotionLoomReviewSync", dependencies: ["MotionLoomContracts"], path: "Packages/MotionLoomReviewSync/Sources/MotionLoomReviewSync"),
    ]
)
