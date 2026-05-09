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
                pageCount: $pageCount,
                onImport: { isImporterPresented = true }
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
    @Binding var pageCount: Int
    let onImport: () -> Void
    @State private var isDocumentInfoPresented = false
    @State private var selectedText = ""
    @State private var selectedQuickAction: QuickAction?

    var body: some View {
        Group {
            if let document {
                PDFKitView(
                    documentURL: document.url,
                    pageCount: $pageCount,
                    selectedText: $selectedText
                )
                    .ignoresSafeArea(edges: .bottom)
                    .navigationTitle(document.title)
                    .overlay(alignment: .bottom) {
                        if !selectedText.isEmpty {
                            QuickActionPanel(
                                selectedAction: selectedQuickAction,
                                onSelect: { selectedQuickAction = $0 }
                            )
                            .padding(.horizontal, 24)
                            .padding(.bottom, 20)
                            .transition(.move(edge: .bottom).combined(with: .opacity))
                        }
                    }
                    .animation(.easeInOut(duration: 0.2), value: selectedText.isEmpty)
                    .onChange(of: selectedText) { text in
                        if text.isEmpty {
                            selectedQuickAction = nil
                        }
                    }
                    .onChange(of: document.id) { _ in
                        selectedText = ""
                        selectedQuickAction = nil
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
            } else {
                EmptyReaderState(onImport: onImport)
            }
        }
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
    let selectedAction: QuickAction?
    let onSelect: (QuickAction) -> Void

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
                }
            }
        }
        .padding(16)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
        .frame(maxWidth: 620)
    }
}

private enum QuickAction: String, CaseIterable, Identifiable {
    case explain
    case glossary
    case quiz

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
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
