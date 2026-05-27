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
                questionState: pdfStore.questionState,
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
                onQuestion: { selection, question in
                    pdfStore.createQuestionForSelection(
                        text: selection.text,
                        pageNumber: selection.pageNumber,
                        question: question
                    )
                },
                onStudyQuiz: { selection, count in
                    pdfStore.createQuizzesForSelection(
                        text: selection.text,
                        pageNumber: selection.pageNumber,
                        maxQuizzes: count
                    )
                },
                onCancelQuickActionWaiting: { action in
                    switch action {
                    case .explain:
                        pdfStore.cancelExplanationWaiting()
                    case .glossary:
                        pdfStore.cancelGlossaryWaiting()
                    case .quiz:
                        pdfStore.cancelQuizWaiting()
                    case .question:
                        pdfStore.cancelQuestionWaiting()
                    case .highlight:
                        break
                    }
                },
                onSaveQuizAttempt: { quizID, userAnswer, isCorrect in
                    try await pdfStore.createQuizAttempt(
                        quizID: quizID,
                        userAnswer: userAnswer,
                        isCorrect: isCorrect
                    )
                },
                onLoadReviewAgainAttempts: { documentID in
                    try await pdfStore.listReviewAgainQuizAttempts(documentID: documentID)
                },
                onDeleteQuizAttempt: { attemptID in
                    try await pdfStore.deleteQuizAttempt(attemptID: attemptID)
                },
                onLoadStudyRecord: { documentID in
                    try await pdfStore.loadDocumentStudyRecord(documentID: documentID)
                },
                onClearHighlightState: {
                    pdfStore.clearHighlightSaveState()
                    pdfStore.clearExplanationState()
                    pdfStore.clearGlossaryState()
                    pdfStore.clearQuizState()
                    pdfStore.clearQuestionState()
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
                title: Text("PDF를 가져오지 못했습니다."),
                message: Text(error.message),
                dismissButton: .default(Text("확인"))
            )
        }
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 24) {
            VStack(alignment: .leading, spacing: 8) {
                Text("AI PDF 리더")
                    .font(.title2.weight(.semibold))
                Text("PDF를 불러와 읽어보세요. 문장을 선택하면 AI가 이해를 도와줍니다.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Button {
                isImporterPresented = true
            } label: {
                Label("PDF 가져오기", systemImage: "doc.badge.plus")
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)

            if let document = pdfStore.currentDocument {
                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    Text("현재 문서")
                        .font(.headline)
                    Text(document.title)
                        .font(.body)
                        .lineLimit(3)
                    Text("\(pageCount)쪽")
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
                importError = ImportFailure(message: "선택한 PDF가 없습니다.")
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
            return "AI 기능 준비 전"
        case .uploading:
            return "PDF 불러오는 중"
        case .uploaded:
            return "AI 기능 준비 완료"
        case .failed:
            return "PDF를 불러오지 못했습니다."
        }
    }

    private var detail: String {
        switch uploadState {
        case .idle:
            return "PDF를 가져오면 AI가 문서를 분석할 준비를 합니다."
        case .uploading:
            return "문서를 분석하여 AI 기능을 준비하고 있습니다."
        case .uploaded(let backendDocument):
            return "분석 완료 · \(backendDocument.pageCount)쪽 · AI 사용 가능"
        case .failed(let message):
            return message
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
