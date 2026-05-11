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

private struct ImportFailure: Identifiable {
    let id = UUID()
    let message: String
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
