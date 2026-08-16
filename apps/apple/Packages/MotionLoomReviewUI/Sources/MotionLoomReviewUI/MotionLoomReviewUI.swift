// MotionLoom Review UI: iOS/iPadOS companion; review evidence but never production approval.
import Foundation
import SwiftUI
#if SWIFT_PACKAGE
import MotionLoomContracts
import MotionLoomReview
#endif

@MainActor
public final class ReviewConsoleModel: ObservableObject {
    public let launch: ReviewLaunchDescriptor
    @Published public var timeline: ReviewTimeline
    @Published public var draft: ReviewDraft
    @Published public var annotationText = ""
    @Published public private(set) var status = "Review is not a production approval."

    public init(launch: ReviewLaunchDescriptor, timeline: ReviewTimeline = ReviewTimeline(), draft: ReviewDraft = ReviewDraft(decision: .requestChanges)) {
        self.launch = launch
        self.timeline = timeline
        self.draft = draft
    }

    public func addAnnotation() {
        do {
            try draft.addAnnotation(body: annotationText, at: timeline.playheadMilliseconds)
            annotationText = ""
            status = "Annotation attached to \(timeline.playheadMilliseconds) ms."
        } catch {
            status = error.localizedDescription
        }
    }

    public func encodedDecision(reviewerName: String) throws -> Data {
        let reviewer = try HumanReviewer(displayName: reviewerName)
        let decision = try draft.decisionRecord(for: launch, reviewer: reviewer)
        return try ReviewDecisionWriter.encode(decision)
    }

    public func exportDecision(reviewerName: String) throws -> Data {
        let data = try encodedDecision(reviewerName: reviewerName)
        status = "Prepared \(draft.decision.rawValue) for human follow-up."
        return data
    }
}

public struct ReviewConsoleView: View {
    @StateObject private var model: ReviewConsoleModel
    private let reviewerName: String

    public init(launch: ReviewLaunchDescriptor, reviewerName: String = "Reviewer") {
        _model = StateObject(wrappedValue: ReviewConsoleModel(launch: launch))
        self.reviewerName = reviewerName
    }

    public var body: some View {
        NavigationStack {
            List {
                Section("Candidate") {
                    LabeledContent("Scene", value: model.launch.scene)
                    LabeledContent("Task", value: model.launch.taskID)
                    LabeledContent("Candidate", value: model.launch.candidateID)
                }
                Section("Runtime review") {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("\(model.timeline.playheadMilliseconds) ms").font(.title3.monospacedDigit()).foregroundStyle(.orange)
                        Slider(value: Binding(get: { model.timeline.normalizedPlayhead }, set: { model.timeline.seek(normalized: $0) }))
                        HStack {
                            ForEach(model.timeline.checkpointMilliseconds, id: \.self) { timecode in
                                Button("\(timecode == 0 ? "0" : timecode == 600 ? "50" : "100")%") { model.timeline.seek(to: timecode) }
                                if timecode != model.timeline.checkpointMilliseconds.last { Spacer() }
                            }
                        }
                    }
                    Link("Open full evidence in Dev Lab", destination: devLabURL)
                }
                Section("Human review") {
                    #if os(iOS)
                    Picker("Decision", selection: $model.draft.decision) {
                        Text("Request changes").tag(ReviewDecisionKind.requestChanges)
                        Text("Reviewed — no decision").tag(ReviewDecisionKind.reviewedNoDecision)
                        Text("Approve for next human step").tag(ReviewDecisionKind.approveForNextHumanStep)
                    }
                    .pickerStyle(.navigationLink)
                    #else
                    Picker("Decision", selection: $model.draft.decision) {
                        Text("Request changes").tag(ReviewDecisionKind.requestChanges)
                        Text("Reviewed — no decision").tag(ReviewDecisionKind.reviewedNoDecision)
                        Text("Approve for next human step").tag(ReviewDecisionKind.approveForNextHumanStep)
                    }
                    .pickerStyle(.menu)
                    #endif
                    HStack {
                        TextField("Annotation", text: $model.annotationText)
                        Button("Add") { model.addAnnotation() }
                            .disabled(model.annotationText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                    ForEach(model.draft.annotations) { annotation in
                        VStack(alignment: .leading, spacing: 3) {
                            Text("\(annotation.timecodeMilliseconds) ms").font(.caption.monospaced()).foregroundStyle(.orange)
                            Text(annotation.body)
                        }
                    }
                    ShareLink(item: reviewJSON, preview: SharePreview("MotionLoom human review")) {
                        Label("Share review JSON", systemImage: "square.and.arrow.up")
                    }
                }
                Section("Governance") {
                    Text("This companion cannot approve production, enable OPEN_PR, push a branch or submit a build. It produces only a hash-bound human review record for the next reviewed step.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("MotionLoom Review")
        }
    }

    private var reviewJSON: Data {
        (try? model.encodedDecision(reviewerName: reviewerName)) ?? Data("{\"status\":\"review_not_ready\"}".utf8)
    }

    private var devLabURL: URL {
        var components = URLComponents(string: "https://animdevlab-hcxnxr9c.manus.space/lab/")!
        components.queryItems = [
            URLQueryItem(name: "scene", value: model.launch.scene),
            URLQueryItem(name: "task_id", value: model.launch.taskID),
            URLQueryItem(name: "candidate_id", value: model.launch.candidateID),
            URLQueryItem(name: "artifact_base", value: "/scenes/\(model.launch.scene)"),
            URLQueryItem(name: "task_base", value: "/tasks/\(model.launch.taskID)"),
        ]
        return components.url!
    }
}
