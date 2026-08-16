// swift-tools-version: 6.0
// MotionLoom review core: timeline evidence and human handoff, never production approval.
import PackageDescription

let package = Package(
    name: "MotionLoomReview",
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [.library(name: "MotionLoomReview", targets: ["MotionLoomReview"])],
    dependencies: [.package(path: "../MotionLoomContracts")],
    targets: [
        .target(name: "MotionLoomReview", dependencies: ["MotionLoomContracts"]),
        .testTarget(name: "MotionLoomReviewTests", dependencies: ["MotionLoomReview", "MotionLoomContracts"]),
    ]
)
