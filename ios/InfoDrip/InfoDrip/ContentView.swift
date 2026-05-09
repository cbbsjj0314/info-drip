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
    @Binding var pageCount: Int
    let onImport: () -> Void
    @State private var isDocumentInfoPresented = false

    var body: some View {
        Group {
            if let document {
                PDFKitView(documentURL: document.url, pageCount: $pageCount)
                    .ignoresSafeArea(edges: .bottom)
                    .navigationTitle(document.title)
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
                        DocumentInfoView(document: document, pageCount: pageCount)
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
                Text("This first iPad slice keeps the document local and opens it in a PDFKit reader.")
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
                Label("Local PDF", systemImage: "internaldrive")
                Label("PDFKit reader", systemImage: "doc.text.magnifyingglass")
                Label("Backend upload deferred", systemImage: "network.slash")
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)

            Spacer()
        }
        .padding(24)
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
