// swift-tools-version: 6.0
// MotionLoom Review UI: iOS/iPadOS companion; review evidence but never production approval.
import PackageDescription

let package = Package(
    name: "MotionLoomReviewUI",
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [.library(name: "MotionLoomReviewUI", targets: ["MotionLoomReviewUI"])],
    dependencies: [
        .package(path: "../MotionLoomContracts"),
        .package(path: "../MotionLoomReview"),
    ],
    targets: [
        .target(name: "MotionLoomReviewUI", dependencies: ["MotionLoomContracts", "MotionLoomReview"]),
        .testTarget(name: "MotionLoomReviewUITests", dependencies: ["MotionLoomReviewUI", "MotionLoomContracts"]),
    ]
)
