import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @StateObject private var pdfStore = LocalPDFStore()
    @State private var isImporterPresented = false
    @State private var importError: ImportFailure?
    @State private var pageCount = 0

    var body: some View {
        NavigationSplitView {
            sidebar
                .navigationTitle("InfoDrip")
        } detail: {
            ReaderWorkspace(
                document: pdfStore.currentDocument,
                uploadState: pdfStore.uploadState,
                highlightSaveState: pdfStore.highlightSaveState,
                explanationState: pdfStore.explanationState,
                glossaryState: pdfStore.glossaryState,
                quizState: pdfStore.quizState,
                pageCount: $pageCount,
                onImport: { isImporterPresented = true },
                onSaveHighlight: { selection in
                    pdfStore.saveSelectedHighlight(
                        text: selection.text,
                        pageNumber: selection.pageNumber
                    )
                },
                onExplain: { selection in
                    pdfStore.explainSelectedHighlight(
                        text: selection.text,
                        pageNumber: selection.pageNumber
                    )
                },
                onGlossary: { selection in
                    pdfStore.createGlossaryTermsForSelection(
                        text: selection.text,
                        pageNumber: selection.pageNumber
                    )
                },
                onQuiz: { selection in
                    pdfStore.createQuizzesForSelection(
                        text: selection.text,
                        pageNumber: selection.pageNumber
                    )
                },
                onClearHighlightState: {
                    pdfStore.clearHighlightSaveState()
                    pdfStore.clearExplanationState()
                    pdfStore.clearGlossaryState()
                    pdfStore.clearQuizState()
                }
            )
        }
        .fileImporter(
            isPresented: $isImporterPresented,
            allowedContentTypes: [.pdf],
            allowsMultipleSelection: false,
            onCompletion: handleImportResult
        )
        .alert(item: $importError) { error in
            Alert(
                title: Text("Import failed"),
                message: Text(error.message),
                dismissButton: .default(Text("OK"))
            )
        }
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 24) {
            VStack(alignment: .leading, spacing: 8) {
                Text("PDF Reader")
                    .font(.title2.weight(.semibold))
                Text("Import a PDF and read it locally on this iPad.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Button {
                isImporterPresented = true
            } label: {
                Label("Import PDF", systemImage: "doc.badge.plus")
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)

            if let document = pdfStore.currentDocument {
                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("Current Document")
                        .font(.headline)
                    Text(document.title)
                        .font(.body)
                        .lineLimit(3)
                    Text("\(pageCount) pages")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                UploadStatusView(uploadState: pdfStore.uploadState)
            }

            Spacer()
        }
        .padding(24)
        .frame(minWidth: 280)
        .background(Color(.systemGroupedBackground))
    }

    private func handleImportResult(_ result: Result<[URL], Error>) {
        switch result {
        case .success(let urls):
            guard let selectedURL = urls.first else {
                importError = ImportFailure(message: "No PDF was selected.")
                return
            }

            do {
                try pdfStore.importPDF(from: selectedURL)
                pageCount = 0
            } catch {
                importError = ImportFailure(message: error.localizedDescription)
            }
        case .failure(let error):
            importError = ImportFailure(message: error.localizedDescription)
        }
    }
}

private struct ReaderWorkspace: View {
    let document: ImportedPDF?
    let uploadState: PDFUploadState
    let highlightSaveState: HighlightSaveState
    let explanationState: ExplanationState
    let glossaryState: GlossaryState
    let quizState: QuizState
    @Binding var pageCount: Int
    let onImport: () -> Void
    let onSaveHighlight: (PDFTextSelection) -> Void
    let onExplain: (PDFTextSelection) -> Void
    let onGlossary: (PDFTextSelection) -> Void
    let onQuiz: (PDFTextSelection) -> Void
    let onClearHighlightState: () -> Void
    @State private var isDocumentInfoPresented = false
    @State private var isQuizStudyPresented = false
    @State private var quizStudyQuizzes: [BackendQuiz] = []
    @State private var selection = PDFTextSelection.empty
    @State private var selectedQuickAction: QuickAction?

    var body: some View {
        Group {
            if let document {
                PDFKitView(
                    documentURL: document.url,
                    pageCount: $pageCount,
                    selection: $selection
                )
                    .ignoresSafeArea(edges: .bottom)
                    .navigationTitle(document.title)
                    .overlay(alignment: .bottom) {
                        if !selection.isEmpty {
                            QuickActionPanel(
                                selectedAction: selectedQuickAction,
                                highlightSaveState: highlightSaveState,
                                explanationState: explanationState,
                                glossaryState: glossaryState,
                                quizState: quizState,
                                highlightAvailabilityMessage: highlightAvailabilityMessage,
                                canRunQuickAction: canRunQuickAction,
                                onSelect: handleQuickAction,
                                onOpenQuizStudy: openQuizStudy
                            )
                            .padding(.horizontal, 24)
                            .padding(.bottom, 20)
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                        }
                    }
                    .animation(.easeInOut(duration: 0.2), value: selection.isEmpty)
                    .onChange(of: selection) { _ in
                        selectedQuickAction = nil
                        onClearHighlightState()
                    }
                    .onChange(of: document.id) { _ in
                        selection = .empty
                        selectedQuickAction = nil
                        onClearHighlightState()
                    }
                    .toolbar {
                        ToolbarItemGroup(placement: .navigationBarTrailing) {
                            Button {
                                isDocumentInfoPresented = true
                            } label: {
                                Label("Document Info", systemImage: "info.circle")
                            }

                            Button(action: onImport) {
                                Label("Import PDF", systemImage: "doc.badge.plus")
                            }
                        }
                    }
                    .sheet(isPresented: $isDocumentInfoPresented) {
                        DocumentInfoView(
                            document: document,
                            uploadState: uploadState,
                            pageCount: pageCount
                        )
                            .presentationDetents([.medium])
                    }
                    .sheet(
                        isPresented: $isQuizStudyPresented,
                        onDismiss: {
                            quizStudyQuizzes = []
                        }
                    ) {
                        QuizStudySheet(quizzes: quizStudyQuizzes)
                    }
            } else {
                EmptyReaderState(onImport: onImport)
            }
        }
    }

    private var canRunQuickAction: Bool {
        if case .saving = highlightSaveState {
            return false
        }

        if case .loading = explanationState {
            return false
        }

        if case .loading = glossaryState {
            return false
        }

        if case .loading = quizState {
            return false
        }

        guard case .uploaded = uploadState else {
            return false
        }

        return !selection.text.isEmpty && selection.pageNumber != nil
    }

    private var highlightAvailabilityMessage: String? {
        if case .uploaded = uploadState {
            return selection.pageNumber == nil ? "선택한 페이지를 확인할 수 없습니다." : nil
        }

        switch uploadState {
        case .idle:
            return "Backend document가 아직 없습니다."
        case .uploading:
            return "PDF 업로드가 끝난 뒤 저장할 수 있습니다."
        case .uploaded:
            return nil
        case .failed:
            return "PDF upload 실패 상태에서는 저장할 수 없습니다."
        }
    }

    private func handleQuickAction(_ action: QuickAction) {
        selectedQuickAction = action

        switch action {
        case .highlight:
            onSaveHighlight(selection)
        case .explain:
            onExplain(selection)
        case .glossary:
            onGlossary(selection)
        case .quiz:
            onQuiz(selection)
        }
    }

    private func openQuizStudy(_ quizzes: [BackendQuiz]) {
        quizStudyQuizzes = quizzes
        isQuizStudyPresented = true
    }
}

private struct EmptyReaderState: View {
    let onImport: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "doc.richtext")
                .font(.system(size: 56, weight: .light))
                .foregroundStyle(.secondary)

            VStack(spacing: 8) {
                Text("Import a PDF to start reading")
                    .font(.title.weight(.semibold))
                Text("Choose a PDF, then select a passage while reading to start a study action.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 460)
            }

            Button(action: onImport) {
                Label("Import PDF", systemImage: "doc.badge.plus")
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemBackground))
    }
}

private struct DocumentInfoView: View {
    let document: ImportedPDF
    let uploadState: PDFUploadState
    let pageCount: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Document")
                    .font(.title2.weight(.semibold))
                Text(document.title)
                    .font(.title3.weight(.semibold))
                    .fixedSize(horizontal: false, vertical: true)
                Text(pageCount == 1 ? "1 page" : "\(pageCount) pages")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Divider()

            VStack(alignment: .leading, spacing: 12) {
                Label("Stored on this iPad", systemImage: "internaldrive")
                backendDocumentLabel
                Label("Select text while reading", systemImage: "text.cursor")
                Label("Use quick study actions", systemImage: "sparkles")
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)

            Spacer()
        }
        .padding(24)
    }

    private var backendDocumentLabel: some View {
        switch uploadState {
        case .idle:
            return Label("Not uploaded to backend", systemImage: "icloud.slash")
        case .uploading:
            return Label("Uploading to backend", systemImage: "icloud.and.arrow.up")
        case .uploaded(let backendDocument):
            return Label(
                "Backend document #\(backendDocument.id) · \(backendDocument.pageCount) pages",
                systemImage: "checkmark.icloud"
            )
        case .failed:
            return Label("Backend upload failed", systemImage: "exclamationmark.icloud")
        }
    }
}

private struct UploadStatusView: View {
    let uploadState: PDFUploadState

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            statusIcon
                .frame(width: 18)

            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.caption.weight(.semibold))
                Text(detail)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
    }

    @ViewBuilder
    private var statusIcon: some View {
        switch uploadState {
        case .uploading:
            ProgressView()
                .controlSize(.small)
        case .uploaded:
            Image(systemName: "checkmark.icloud")
                .foregroundStyle(.green)
        case .failed:
            Image(systemName: "exclamationmark.icloud")
                .foregroundStyle(.red)
        case .idle:
            Image(systemName: "icloud.slash")
                .foregroundStyle(.secondary)
        }
    }

    private var title: String {
        switch uploadState {
        case .idle:
            return "Backend not linked"
        case .uploading:
            return "Uploading PDF"
        case .uploaded:
            return "Backend linked"
        case .failed:
            return "Upload failed"
        }
    }

    private var detail: String {
        switch uploadState {
        case .idle:
            return "Import a PDF to create a backend document."
        case .uploading:
            return "Creating backend document record."
        case .uploaded(let backendDocument):
            return "Document #\(backendDocument.id) is ready for highlights."
        case .failed(let message):
            return message
        }
    }
}

private struct QuickActionPanel: View {
    private let loadedResultPreviewMaxHeight: CGFloat = 220
    private let maxPreviewKeyPoints = 3

    let selectedAction: QuickAction?
    let highlightSaveState: HighlightSaveState
    let explanationState: ExplanationState
    let glossaryState: GlossaryState
    let quizState: QuizState
    let highlightAvailabilityMessage: String?
    let canRunQuickAction: Bool
    let onSelect: (QuickAction) -> Void
    let onOpenQuizStudy: ([BackendQuiz]) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("선택한 문장")
                        .font(.headline)
                    Text(selectedAction.map { "\($0.title) 선택됨" } ?? "학습 활동을 고르세요")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()
            }

            HStack(spacing: 10) {
                ForEach(QuickAction.allCases) { action in
                    Button {
                        onSelect(action)
                    } label: {
                        Label(action.title, systemImage: action.systemImage)
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.large)
                    .disabled(isDisabled(action))
                }
            }

            if let statusMessage {
                Text(statusMessage)
                    .font(.caption)
                    .foregroundStyle(statusColor)
                    .fixedSize(horizontal: false, vertical: true)
            }

            explanationContent
            glossaryContent
            quizContent
        }
        .padding(16)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
        .frame(maxWidth: 620)
    }

    private var statusMessage: String? {
        if selectedAction == .explain {
            switch explanationState {
            case .idle:
                return highlightAvailabilityMessage
            case .loading:
                return "설명을 생성하는 중..."
            case .loaded(let explanation):
                return "설명 생성됨 · #\(explanation.id)"
            case .failed(let message):
                return message
            }
        } else if selectedAction == .glossary {
            switch glossaryState {
            case .idle:
                return highlightAvailabilityMessage
            case .loading:
                return "용어를 추출하는 중..."
            case .loaded(let glossaryTerms):
                return "용어 추출됨 · \(glossaryTerms.count)개"
            case .failed(let message):
                return message
            }
        } else if selectedAction == .quiz {
            switch quizState {
            case .idle:
                return highlightAvailabilityMessage
            case .loading:
                return "퀴즈를 생성하는 중..."
            case .loaded(let quizzes):
                return "퀴즈 생성됨 · \(quizzes.count)개"
            case .failed(let message):
                return message
            }
        } else {
            switch highlightSaveState {
            case .idle:
                return highlightAvailabilityMessage
            case .saving:
                return "하이라이트 저장 중..."
            case .saved(let highlight):
                return "하이라이트 저장됨 · #\(highlight.id)"
            case .failed(let message):
                return message
            }
        }
    }

    private var statusColor: Color {
        if selectedAction == .explain {
            switch explanationState {
            case .loaded:
                return .green
            case .failed:
                return .red
            case .idle, .loading:
                return .secondary
            }
        }

        if selectedAction == .glossary {
            switch glossaryState {
            case .loaded:
                return .green
            case .failed:
                return .red
            case .idle, .loading:
                return .secondary
            }
        }

        if selectedAction == .quiz {
            switch quizState {
            case .loaded:
                return .green
            case .failed:
                return .red
            case .idle, .loading:
                return .secondary
            }
        }

        switch highlightSaveState {
        case .saved:
            return .green
        case .failed:
            return .red
        case .idle, .saving:
            return .secondary
        }
    }

    @ViewBuilder
    private var quizContent: some View {
        if selectedAction == .quiz {
            switch quizState {
            case .loading:
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("선택한 문장을 backend에서 퀴즈로 바꾸고 있습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            case .loaded(let quizzes):
                if quizzes.isEmpty {
                    Text("생성된 퀴즈가 없습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    loadedResultPreview {
                        VStack(alignment: .leading, spacing: 10) {
                            Button {
                                onOpenQuizStudy(quizzes)
                            } label: {
                                Label("공부 모드 열기", systemImage: "rectangle.stack.badge.play")
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.regular)

                            ForEach(quizzes, id: \.id) { quiz in
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(displayTitle(for: quiz.quizType))
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)

                                    Text(quiz.question)
                                        .font(.subheadline.weight(.semibold))
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                                .padding(12)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color(.systemBackground), in: RoundedRectangle(cornerRadius: 8))
                            }
                        }
                    }
                }
            case .failed, .idle:
                EmptyView()
            }
        }
    }

    @ViewBuilder
    private var explanationContent: some View {
        if selectedAction == .explain {
            switch explanationState {
            case .loading:
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("선택한 문장을 backend에서 설명으로 바꾸고 있습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            case .loaded(let explanation):
                VStack(alignment: .leading, spacing: 10) {
                    Text(explanation.summary)
                        .font(.subheadline)
                        .lineLimit(4)

                    if !explanation.keyPoints.isEmpty {
                        VStack(alignment: .leading, spacing: 6) {
                            Text("핵심 포인트")
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(.secondary)

                            ForEach(Array(explanation.keyPoints.prefix(maxPreviewKeyPoints)), id: \.self) { point in
                                HStack(alignment: .firstTextBaseline, spacing: 6) {
                                    Image(systemName: "checkmark.circle.fill")
                                        .font(.caption)
                                        .foregroundStyle(.green)
                                    Text(point)
                                        .font(.caption)
                                        .lineLimit(2)
                                }
                            }
                        }
                    }
                }
                .modifier(LoadedResultPreviewModifier(maxHeight: loadedResultPreviewMaxHeight))
            case .failed, .idle:
                EmptyView()
            }
        }
    }

    @ViewBuilder
    private var glossaryContent: some View {
        if selectedAction == .glossary {
            switch glossaryState {
            case .loading:
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("선택한 문장에서 학습 용어를 추출하고 있습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            case .loaded(let glossaryTerms):
                if glossaryTerms.isEmpty {
                    Text("추출된 용어가 없습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    loadedResultPreview {
                        VStack(alignment: .leading, spacing: 10) {
                            ForEach(glossaryTerms, id: \.id) { glossaryTerm in
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(glossaryTerm.term)
                                        .font(.subheadline.weight(.semibold))
                                    Text(glossaryTerm.definition)
                                        .font(.caption)
                                        .lineLimit(3)

                                    if let sourceText = glossaryTerm.sourceText,
                                       !sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                                        Text(sourceText)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                            .lineLimit(1)
                                    }
                                }

                                if glossaryTerm.id != glossaryTerms.last?.id {
                                    Divider()
                                }
                            }
                        }
                    }
                }
            case .failed, .idle:
                EmptyView()
            }
        }
    }

    private func isDisabled(_ action: QuickAction) -> Bool {
        switch action {
        case .highlight, .explain, .glossary, .quiz:
            return !canRunQuickAction
        }
    }

    private func displayTitle(for quizType: String) -> String {
        switch quizType {
        case "short_answer":
            return "단답형"
        case "fill_blank":
            return "빈칸"
        default:
            return quizType
        }
    }

    private func loadedResultPreview<Content: View>(
        @ViewBuilder content: () -> Content
    ) -> some View {
        content()
            .modifier(LoadedResultPreviewModifier(maxHeight: loadedResultPreviewMaxHeight))
    }
}

private struct LoadedResultPreviewModifier: ViewModifier {
    let maxHeight: CGFloat

    func body(content: Content) -> some View {
        ScrollView {
            content
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .frame(maxHeight: maxHeight, alignment: .top)
        .padding(12)
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 8))
    }
}

private struct QuizStudySheet: View {
    let quizzes: [BackendQuiz]
    @Environment(\.dismiss) private var dismiss
    @State private var answersByQuizID: [Int: String] = [:]
    @State private var revealedQuizIDs: Set<Int> = []

    var body: some View {
        NavigationStack {
            ScrollView {
                if quizzes.isEmpty {
                    VStack(spacing: 10) {
                        Image(systemName: "questionmark.square.dashed")
                            .font(.system(size: 36, weight: .light))
                            .foregroundStyle(.secondary)
                        Text("생성된 퀴즈가 없습니다.")
                            .font(.headline)
                        Text("선택한 문장에서 퀴즈를 먼저 생성한 뒤 공부 모드를 열 수 있습니다.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(40)
                } else {
                    LazyVStack(alignment: .leading, spacing: 14) {
                        ForEach(quizzes, id: \.id) { quiz in
                            QuizStudyCard(
                                quiz: quiz,
                                answer: Binding(
                                    get: { answersByQuizID[quiz.id, default: ""] },
                                    set: { answersByQuizID[quiz.id] = $0 }
                                ),
                                isRevealed: Binding(
                                    get: { revealedQuizIDs.contains(quiz.id) },
                                    set: { isRevealed in
                                        if isRevealed {
                                            revealedQuizIDs.insert(quiz.id)
                                        } else {
                                            revealedQuizIDs.remove(quiz.id)
                                        }
                                    }
                                )
                            )
                        }
                    }
                    .padding(24)
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("퀴즈 공부")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("닫기") {
                        dismiss()
                    }
                }
            }
        }
    }
}

private struct QuizStudyCard: View {
    let quiz: BackendQuiz
    @Binding var answer: String
    @Binding var isRevealed: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(displayTitle(for: quiz.quizType))
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)

            Text(quiz.question)
                .font(.headline)
                .fixedSize(horizontal: false, vertical: true)

            VStack(alignment: .leading, spacing: 6) {
                Text("내 답안")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                TextEditor(text: $answer)
                    .frame(minHeight: 96)
                    .padding(8)
                    .scrollContentBackground(.hidden)
                    .background(Color(.systemBackground), in: RoundedRectangle(cornerRadius: 8))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color(.separator), lineWidth: 0.5)
                    }
            }

            Button {
                isRevealed.toggle()
            } label: {
                Label(isRevealed ? "답 숨기기" : "답 보기", systemImage: isRevealed ? "eye.slash" : "eye")
            }
            .buttonStyle(.bordered)

            if isRevealed {
                VStack(alignment: .leading, spacing: 10) {
                    answerBlock(title: "정답", text: quiz.answer)
                    answerBlock(title: "해설", text: quiz.explanation)
                    answerBlock(title: "근거", text: quiz.sourceText)
                }
                .transition(.opacity)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
        .overlay {
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
    }

    private func answerBlock(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(text)
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func displayTitle(for quizType: String) -> String {
        switch quizType {
        case "short_answer":
            return "단답형"
        case "fill_blank":
            return "빈칸"
        default:
            return quizType
        }
    }
}

private enum QuickAction: String, CaseIterable, Identifiable {
    case highlight
    case explain
    case glossary
    case quiz

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .highlight:
            return "하이라이트"
        case .explain:
            return "쉽게 설명"
        case .glossary:
            return "용어"
        case .quiz:
            return "퀴즈"
        }
    }

    var systemImage: String {
        switch self {
        case .highlight:
            return "highlighter"
        case .explain:
            return "lightbulb"
        case .glossary:
            return "text.book.closed"
        case .quiz:
            return "questionmark.circle"
        }
    }
}

private struct ImportFailure: Identifiable {
    let id = UUID()
    let message: String
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
