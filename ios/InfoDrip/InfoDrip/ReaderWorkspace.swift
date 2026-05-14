import SwiftUI

struct ReaderWorkspace: View {
    let document: ImportedPDF?
    let uploadState: PDFUploadState
    let highlightSaveState: HighlightSaveState
    let explanationState: ExplanationState
    let glossaryState: GlossaryState
    let quizState: QuizState
    let questionState: QuestionState
    @Binding var pageCount: Int
    let onImport: () -> Void
    let onSaveHighlight: (PDFTextSelection) -> Void
    let onExplain: (PDFTextSelection) -> Void
    let onGlossary: (PDFTextSelection) -> Void
    let onQuiz: (PDFTextSelection) -> Void
    let onQuestion: (PDFTextSelection, String) -> Void
    let onStudyQuiz: (PDFTextSelection, Int) -> Void
    let onSaveQuizAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    let onLoadReviewAgainAttempts: (Int) async throws -> [BackendReviewAgainQuizAttempt]
    let onLoadStudyRecord: (Int) async throws -> BackendDocumentStudyRecord
    let onClearHighlightState: () -> Void
    @State private var isDocumentInfoPresented = false
    @State private var activeReviewAgainSheet: ReviewAgainSheetSnapshot?
    @State private var activeStudyRecordSheet: StudyRecordSheetSnapshot?
    @State private var activeQuickActionSheet: QuickActionSheet?
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
                                questionState: questionState,
                                highlightAvailabilityMessage: highlightAvailabilityMessage,
                                canRunQuickAction: canRunQuickAction,
                                selectedText: selection.text,
                                onSelect: handleQuickAction,
                                onRequestExplanation: handleExplanationRequest,
                                onRequestGlossary: handleGlossaryRequest,
                                onRequestQuiz: handleQuizRequest,
                                onQuestion: handleQuestion,
                                onStudyQuiz: handleStudyQuiz,
                                onOpenExplanationDetail: openExplanationDetail,
                                onOpenGlossaryDetail: openGlossaryDetail,
                                onOpenQuizStudy: openQuizStudy,
                                onOpenQuestionDetail: openQuestionDetail
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
                            Button(action: openStudyRecord) {
                                Label("학습 기록", systemImage: "list.bullet.rectangle")
                            }
                            .disabled(!canOpenStudyRecord)

                            Button(action: openReviewAgainList) {
                                Label("다시 보기 목록", systemImage: "arrow.counterclockwise")
                            }
                            .disabled(!canOpenReviewAgainList)

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
                    .sheet(item: $activeReviewAgainSheet) { snapshot in
                        ReviewAgainQuizAttemptsSheet(
                            documentID: snapshot.documentID,
                            documentTitle: snapshot.documentTitle,
                            onLoad: onLoadReviewAgainAttempts,
                            onSaveAttempt: onSaveQuizAttempt
                        )
                    }
                    .sheet(item: $activeStudyRecordSheet) { snapshot in
                        DocumentStudyRecordSheet(
                            documentID: snapshot.documentID,
                            documentTitle: snapshot.documentTitle,
                            onLoad: onLoadStudyRecord
                        )
                    }
                    .sheet(item: $activeQuickActionSheet) { sheet in
                        switch sheet {
                        case .explanation(let snapshot):
                            ExplanationDetailSheet(explanation: snapshot.explanation)
                        case .glossary(let snapshot):
                            GlossaryDetailSheet(glossaryTerms: snapshot.terms)
                        case .quiz(let snapshot):
                            QuizStudySheet(
                                quizzes: snapshot.quizzes,
                                onSaveAttempt: onSaveQuizAttempt
                            )
                        case .question(let snapshot):
                            QuestionDetailSheet(userQuestion: snapshot.userQuestion)
                        }
                    }
            } else {
                EmptyReaderState(onImport: onImport)
            }
        }
    }

    private var canOpenReviewAgainList: Bool {
        if case .uploaded = uploadState {
            return true
        }

        return false
    }

    private var canOpenStudyRecord: Bool {
        if case .uploaded = uploadState {
            return true
        }

        return false
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

        if case .loading = questionState {
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
        case .explain, .glossary, .quiz, .question:
            break
        }
    }

    private func handleExplanationRequest() {
        selectedQuickAction = .explain
        onExplain(selection)
    }

    private func handleGlossaryRequest() {
        selectedQuickAction = .glossary
        onGlossary(selection)
    }

    private func handleQuizRequest() {
        selectedQuickAction = .quiz
        onQuiz(selection)
    }

    private func handleQuestion(_ question: String) {
        selectedQuickAction = .question
        onQuestion(selection, question)
    }

    private func handleStudyQuiz(maxQuizzes: Int) {
        selectedQuickAction = .quiz
        onStudyQuiz(selection, maxQuizzes)
    }

    private func openReviewAgainList() {
        guard case .uploaded(let backendDocument) = uploadState else {
            return
        }

        activeReviewAgainSheet = ReviewAgainSheetSnapshot(
            documentID: backendDocument.id,
            documentTitle: backendDocument.title
        )
    }

    private func openStudyRecord() {
        guard case .uploaded(let backendDocument) = uploadState else {
            return
        }

        activeStudyRecordSheet = StudyRecordSheetSnapshot(
            documentID: backendDocument.id,
            documentTitle: backendDocument.title
        )
    }

    private func openExplanationDetail(_ explanation: BackendExplanation) {
        activeQuickActionSheet = .explanation(ExplanationSnapshot(explanation: explanation))
    }

    private func openGlossaryDetail(_ glossaryTerms: [BackendGlossaryTerm]) {
        activeQuickActionSheet = .glossary(GlossarySnapshot(terms: glossaryTerms))
    }

    private func openQuizStudy(_ quizzes: [BackendQuiz]) {
        activeQuickActionSheet = .quiz(QuizStudySnapshot(quizzes: quizzes))
    }

    private func openQuestionDetail(_ userQuestion: BackendUserQuestion) {
        activeQuickActionSheet = .question(QuestionSnapshot(userQuestion: userQuestion))
    }
}

private struct ReviewAgainSheetSnapshot: Identifiable {
    let id = UUID()
    let documentID: Int
    let documentTitle: String
}

private struct StudyRecordSheetSnapshot: Identifiable {
    let id = UUID()
    let documentID: Int
    let documentTitle: String
}

private enum QuickActionSheet: Identifiable {
    case explanation(ExplanationSnapshot)
    case glossary(GlossarySnapshot)
    case quiz(QuizStudySnapshot)
    case question(QuestionSnapshot)

    var id: UUID {
        switch self {
        case .explanation(let snapshot):
            return snapshot.id
        case .glossary(let snapshot):
            return snapshot.id
        case .quiz(let snapshot):
            return snapshot.id
        case .question(let snapshot):
            return snapshot.id
        }
    }
}

private struct ExplanationSnapshot {
    let id = UUID()
    let explanation: BackendExplanation
}

private struct GlossarySnapshot {
    let id = UUID()
    let terms: [BackendGlossaryTerm]
}

private struct QuizStudySnapshot {
    let id = UUID()
    let quizzes: [BackendQuiz]
}

private struct QuestionSnapshot {
    let id = UUID()
    let userQuestion: BackendUserQuestion
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
