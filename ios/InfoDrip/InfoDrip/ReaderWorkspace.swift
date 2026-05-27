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
    let onCancelQuickActionWaiting: (QuickAction) -> Void
    let onSaveQuizAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    let onLoadReviewAgainAttempts: (Int) async throws -> [BackendReviewAgainQuizAttempt]
    let onDeleteQuizAttempt: (Int) async throws -> Void
    let onLoadStudyRecord: (Int) async throws -> BackendDocumentStudyRecord
    let onClearHighlightState: () -> Void
    @State private var activeReviewAgainSheet: ReviewAgainSheetSnapshot?
    @State private var activeSavedSentenceSheet: SavedSentenceSheetSnapshot?
    @State private var activeGlossaryCollectionSheet: GlossaryCollectionSheetSnapshot?
    @State private var activeQuickActionSheet: QuickActionSheet?
    @State private var selection = PDFTextSelection.empty
    @State private var selectedQuickAction: QuickAction?
    @State private var isQuickActionPanelDismissed = false

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
                        if !selection.isEmpty && !isQuickActionPanelDismissed {
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
                                onCancelWaiting: handleCancelWaiting,
                                onOpenExplanationDetail: openExplanationDetail,
                                onOpenGlossaryDetail: openGlossaryDetail,
                                onOpenQuizStudy: openQuizStudy,
                                onOpenQuestionDetail: openQuestionDetail,
                                onClose: closeQuickActionPanel
                            )
                            .padding(.horizontal, 24)
                            .padding(.bottom, 20)
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                        }
                    }
                    .animation(.easeInOut(duration: 0.2), value: selection.isEmpty)
                    .animation(.easeInOut(duration: 0.2), value: isQuickActionPanelDismissed)
                    .onChange(of: selection) { _ in
                        selectedQuickAction = nil
                        isQuickActionPanelDismissed = false
                        onClearHighlightState()
                    }
                    .onChange(of: document.id) { _ in
                        selection = .empty
                        selectedQuickAction = nil
                        isQuickActionPanelDismissed = false
                        onClearHighlightState()
                    }
                    .toolbar {
                        ToolbarItemGroup(placement: .navigationBarTrailing) {
                            Button(action: openSavedSentenceList) {
                                Label("저장된 문장", systemImage: "text.quote")
                            }
                            .disabled(!canOpenSavedSentenceList)

                            Button(action: openGlossaryCollection) {
                                Label("용어 모음", systemImage: "text.book.closed")
                            }
                            .disabled(!canOpenGlossaryCollection)

                            Button(action: openReviewAgainList) {
                                Label("다시 풀 퀴즈", systemImage: "arrow.counterclockwise")
                            }
                            .disabled(!canOpenReviewAgainList)
                        }
                    }
                    .sheet(item: $activeReviewAgainSheet) { snapshot in
                        ReviewAgainQuizAttemptsSheet(
                            documentID: snapshot.documentID,
                            documentTitle: snapshot.documentTitle,
                            onLoad: onLoadReviewAgainAttempts,
                            onDeleteAttempt: onDeleteQuizAttempt,
                            onSaveAttempt: onSaveQuizAttempt
                        )
                    }
                    .sheet(item: $activeSavedSentenceSheet) { snapshot in
                        SavedSentenceListSheet(
                            documentID: snapshot.documentID,
                            documentTitle: snapshot.documentTitle,
                            onLoad: onLoadStudyRecord,
                            onSaveQuizAttempt: onSaveQuizAttempt,
                            onDeleteQuizAttempt: onDeleteQuizAttempt
                        )
                    }
                    .sheet(item: $activeGlossaryCollectionSheet) { snapshot in
                        DocumentGlossaryCollectionSheet(
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

    private var canOpenGlossaryCollection: Bool {
        if case .uploaded = uploadState {
            return true
        }

        return false
    }

    private var canOpenSavedSentenceList: Bool {
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
            if case .saved = highlightSaveState {
                return
            }

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

    private func handleCancelWaiting() {
        guard let selectedQuickAction else {
            return
        }

        onCancelQuickActionWaiting(selectedQuickAction)
    }

    private func closeQuickActionPanel() {
        selectedQuickAction = nil
        isQuickActionPanelDismissed = true
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

    private func openGlossaryCollection() {
        guard case .uploaded(let backendDocument) = uploadState else {
            return
        }

        activeGlossaryCollectionSheet = GlossaryCollectionSheetSnapshot(
            documentID: backendDocument.id,
            documentTitle: backendDocument.title
        )
    }

    private func openSavedSentenceList() {
        guard case .uploaded(let backendDocument) = uploadState else {
            return
        }

        activeSavedSentenceSheet = SavedSentenceSheetSnapshot(
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

private struct GlossaryCollectionSheetSnapshot: Identifiable {
    let id = UUID()
    let documentID: Int
    let documentTitle: String
}

private struct SavedSentenceSheetSnapshot: Identifiable {
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
                Text("PDF를 가져와 읽기 시작하세요")
                    .font(.title.weight(.semibold))
                Text("문서를 읽으며 궁금한 부분을 선택해 보세요. AI가 설명, 용어 정리, 퀴즈 생성 등을 도와줍니다.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 460)
            }

            Button(action: onImport) {
                Label("PDF 가져오기", systemImage: "doc.badge.plus")
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(.systemBackground))
    }
}
