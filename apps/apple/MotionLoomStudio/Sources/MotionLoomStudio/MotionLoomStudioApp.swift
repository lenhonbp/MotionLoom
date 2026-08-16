// MotionLoom Studio: macOS inspection and human-review surface.
import AppKit
import Foundation
import SwiftUI
import WebKit
#if SWIFT_PACKAGE
import MotionLoomContracts
import MotionLoomMacBridge
import MotionLoomReview
#endif

@main
struct MotionLoomStudioApp: App {
    @StateObject private var state = StudioState()

    var body: some Scene {
        WindowGroup("MotionLoom Studio") {
            StudioRootView()
                .environmentObject(state)
                .frame(minWidth: 1_120, minHeight: 720)
        }
        .commands {
            CommandGroup(after: .newItem) {
                Button("Choose MotionLoom Project…") { state.chooseProject() }
                    .keyboardShortcut("o", modifiers: [.command])
                Button("Run Doctor") { state.run(.doctor) }
                    .keyboardShortcut("r", modifiers: [.command])
                    .disabled(state.projectScope == nil)
            }
        }
    }
}

@MainActor
final class StudioState: ObservableObject {
    @Published var projectScope: ProjectAccessScope?
    @Published var activeSection: StudioSection? = .timeline
    @Published var timeline = ReviewTimeline()
    @Published var draft = ReviewDraft(decision: .requestChanges)
    @Published var annotationBody = ""
    @Published var commandStatus = "Select a MotionLoom project to run local inspection."
    @Published var showDevLab = false
    @Published var reviewExportStatus = "No review decision exported."

    let launch: ReviewLaunchDescriptor

    init() {
        let evidence = try! EvidenceDigests(
            runtimeEvidenceSHA256: "2fe4258081208faec1471294c460e7fe06e98b8bb9f793d5d43582a7deb88b52",
            candidateReportSHA256: "a85156020ff421e94d344af0ab70e6506ccb3ba49ff376c7c1d9155c7672beb3"
        )
        launch = try! ReviewLaunchDescriptor(
            taskID: "runtime-pilot-001",
            candidateID: "8cccc4ac5a7e493ffe40",
            scene: "runtime-pilot-framer",
            artifactBase: "https://animdevlab-hcxnxr9c.manus.space/scenes/runtime-pilot-framer",
            taskBase: "https://animdevlab-hcxnxr9c.manus.space/tasks/runtime-pilot-001",
            evidence: evidence,
            reviewMode: .annotate
        )
    }

    func chooseProject() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.message = "Choose the root of a MotionLoom project."
        if panel.runModal() == .OK, let url = panel.url {
            do {
                projectScope = try ProjectAccessScope(root: url)
                commandStatus = "Granted scoped access to \(url.lastPathComponent)."
            } catch {
                commandStatus = error.localizedDescription
            }
        }
    }

    func run(_ command: MotionLoomInspectionCommand) {
        guard let projectScope else { return }
        commandStatus = "Running \(command.arguments.joined(separator: " "))…"
        Task.detached { [projectScope] in
            let result: Result<CommandResult, Error> = Result {
                try SafeMotionLoomRunner(project: projectScope).run(command)
            }
            await MainActor.run {
                switch result {
                case .success(let report):
                    self.commandStatus = report.terminationStatus == 0
                        ? "PASS: \(report.standardOutput.trimmingCharacters(in: .whitespacesAndNewlines))"
                        : "CHECK FAILED: \(report.standardError.trimmingCharacters(in: .whitespacesAndNewlines))"
                case .failure(let error):
                    self.commandStatus = error.localizedDescription
                }
            }
        }
    }

    func addAnnotation() {
        do {
            try draft.addAnnotation(body: annotationBody, at: timeline.playheadMilliseconds)
            annotationBody = ""
        } catch {
            commandStatus = error.localizedDescription
        }
    }

    func exportReview() {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "review-\(launch.taskID)-\(launch.candidateID).json"
        panel.allowedContentTypes = [.json]
        panel.message = "Export a human review decision. This does not approve production or open a pull request."
        guard panel.runModal() == .OK, let destination = panel.url else { return }
        do {
            let reviewer = try HumanReviewer(displayName: NSFullUserName())
            let decision = try draft.decisionRecord(for: launch, reviewer: reviewer)
            try ReviewDecisionWriter.write(decision, to: destination)
            reviewExportStatus = "Exported \(decision.decision.rawValue) for human follow-up."
        } catch {
            reviewExportStatus = error.localizedDescription
        }
    }

    var devLabURL: URL {
        var components = URLComponents(string: "https://animdevlab-hcxnxr9c.manus.space/lab/")!
        components.queryItems = [
            URLQueryItem(name: "scene", value: launch.scene),
            URLQueryItem(name: "task_id", value: launch.taskID),
            URLQueryItem(name: "candidate_id", value: launch.candidateID),
            URLQueryItem(name: "artifact_base", value: "/scenes/\(launch.scene)"),
            URLQueryItem(name: "task_base", value: "/tasks/\(launch.taskID)"),
        ]
        return components.url!
    }
}

enum StudioSection: String, CaseIterable, Identifiable {
    case project = "Project Inspector"
    case timeline = "Timeline Desk"
    case evidence = "Evidence"
    var id: String { rawValue }
}

struct StudioRootView: View {
    @EnvironmentObject private var state: StudioState

    var body: some View {
        NavigationSplitView {
            List(StudioSection.allCases, selection: $state.activeSection) { section in
                Label(section.rawValue, systemImage: icon(for: section))
                    .tag(section)
            }
            .navigationTitle("MotionLoom")
            Divider()
            VStack(alignment: .leading, spacing: 8) {
                Text("REVIEW-FIRST")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.orange)
                Text("No production approval, push or PR is available from this app.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()
        } detail: {
            switch state.activeSection ?? .timeline {
            case .project: ProjectInspectorView()
            case .timeline: TimelineDeskView()
            case .evidence: EvidenceView()
            }
        }
        .sheet(isPresented: $state.showDevLab) { DevLabSheet(url: state.devLabURL) }
    }

    private func icon(for section: StudioSection) -> String {
        switch section {
        case .project: return "folder.badge.gearshape"
        case .timeline: return "timeline.selection"
        case .evidence: return "checkmark.seal"
        }
    }
}

struct ProjectInspectorView: View {
    @EnvironmentObject private var state: StudioState

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Project Inspector").font(.largeTitle.weight(.semibold))
                    Text("Run only explicit, local inspection commands inside a user-selected project scope.")
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Button("Choose Project…") { state.chooseProject() }
                    .buttonStyle(.borderedProminent)
            }
            GroupBox("Granted scope") {
                LabeledContent("Project root", value: state.projectScope?.root.path ?? "No folder selected")
                    .textSelection(.enabled)
                    .padding(6)
            }
            HStack(spacing: 12) {
                Button("Run Doctor") { state.run(.doctor) }.disabled(state.projectScope == nil)
                Button("Discovery Check") { state.run(.discoveryCheck) }.disabled(state.projectScope == nil)
                Button("Quality: runtime pilot") { state.run(.qualityGate(scene: "runtime-pilot-framer")) }.disabled(state.projectScope == nil)
            }
            GroupBox("Command result") {
                Text(state.commandStatus).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading).padding(6)
            }
            Spacer()
        }
        .padding(32)
    }
}

struct TimelineDeskView: View {
    @EnvironmentObject private var state: StudioState

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Timeline Desk").font(.largeTitle.weight(.semibold))
                    Text("\(state.launch.scene) · candidate \(state.launch.candidateID)")
                        .font(.subheadline.monospaced()).foregroundStyle(.secondary)
                }
                Spacer()
                Button("Open Dev Lab") { state.showDevLab = true }.buttonStyle(.borderedProminent)
            }
            ZStack {
                RoundedRectangle(cornerRadius: 18).fill(Color(nsColor: .windowBackgroundColor).shadow(.inner(color: .black.opacity(0.18), radius: 12)))
                VStack(spacing: 12) {
                    Image(systemName: "play.rectangle.on.rectangle").font(.system(size: 56)).foregroundStyle(.orange)
                    Text("Runtime evidence is inspected in Dev Lab")
                    Text("Use the embedded review surface for source-bound 0 / 50 / 100% frames.").font(.caption).foregroundStyle(.secondary)
                }
            }
            .frame(height: 250)
            VStack(alignment: .leading, spacing: 8) {
                HStack { Text("00:\(String(format: "%04d", state.timeline.playheadMilliseconds))").font(.system(.body, design: .monospaced)); Spacer(); Text("1,200 ms").foregroundStyle(.secondary) }
                Slider(value: Binding(get: { state.timeline.normalizedPlayhead }, set: { state.timeline.seek(normalized: $0) }))
                    .tint(.orange)
                HStack {
                    ForEach(state.timeline.checkpointMilliseconds, id: \.self) { checkpoint in
                        Text("\(checkpoint == 0 ? "0" : checkpoint == 600 ? "50" : "100")% · \(checkpoint)ms").font(.caption.monospaced())
                        if checkpoint != state.timeline.checkpointMilliseconds.last { Spacer() }
                    }
                }
                .foregroundStyle(.secondary)
            }
            Divider()
            HStack {
                Picker("Decision", selection: $state.draft.decision) {
                    Text("Request changes").tag(ReviewDecisionKind.requestChanges)
                    Text("Reviewed — no decision").tag(ReviewDecisionKind.reviewedNoDecision)
                    Text("Approve for next human step").tag(ReviewDecisionKind.approveForNextHumanStep)
                }.pickerStyle(.segmented)
                Button("Export Human Review") { state.exportReview() }
            }
            Text(state.reviewExportStatus).font(.caption).foregroundStyle(.secondary)
            HStack {
                TextField("Annotation at current timecode", text: $state.annotationBody)
                Button("Add") { state.addAnnotation() }.disabled(state.annotationBody.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            List(state.draft.annotations) { annotation in
                VStack(alignment: .leading) { Text("\(annotation.timecodeMilliseconds) ms").font(.caption.monospaced()).foregroundStyle(.orange); Text(annotation.body) }
            }.frame(minHeight: 90)
        }
        .padding(32)
    }
}

struct EvidenceView: View {
    @EnvironmentObject private var state: StudioState
    var body: some View {
        Form {
            Section("Candidate identity") {
                LabeledContent("Task", value: state.launch.taskID)
                LabeledContent("Candidate", value: state.launch.candidateID)
                LabeledContent("Scene", value: state.launch.scene)
            }
            Section("Hash-bound evidence") {
                LabeledContent("Runtime evidence SHA-256", value: state.launch.evidence.runtimeEvidenceSHA256)
                LabeledContent("Candidate report SHA-256", value: state.launch.evidence.candidateReportSHA256)
            }
            Section("Governance") {
                Text("This application can export a human review record only. It cannot declare production approval, enable OPEN_PR, push Git commits, publish npm packages or submit an App Store build.")
            }
        }
        .formStyle(.grouped)
        .padding(20)
        .navigationTitle("Evidence")
    }
}

struct DevLabSheet: View {
    let url: URL
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        VStack(spacing: 0) {
            HStack { Text("Dev Lab review surface").font(.headline); Spacer(); Button("Close") { dismiss() } }
                .padding()
            Divider()
            DevLabWebView(url: url)
        }
        .frame(minWidth: 1_100, minHeight: 760)
    }
}

struct DevLabWebView: NSViewRepresentable {
    let url: URL
    func makeNSView(context: Context) -> WKWebView { WKWebView() }
    func updateNSView(_ view: WKWebView, context: Context) {
        if view.url != url { view.load(URLRequest(url: url)) }
    }
}
