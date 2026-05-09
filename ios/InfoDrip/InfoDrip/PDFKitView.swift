import PDFKit
import SwiftUI

struct PDFKitView: UIViewRepresentable {
    let documentURL: URL
    @Binding var pageCount: Int

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeUIView(context: Context) -> PDFView {
        let pdfView = PDFView()
        pdfView.autoScales = true
        pdfView.displayDirection = .vertical
        pdfView.displayMode = .singlePageContinuous
        pdfView.backgroundColor = .systemGroupedBackground
        loadDocument(in: pdfView, context: context)
        return pdfView
    }

    func updateUIView(_ pdfView: PDFView, context: Context) {
        guard context.coordinator.currentURL != documentURL else {
            return
        }
        loadDocument(in: pdfView, context: context)
    }

    private func loadDocument(in pdfView: PDFView, context: Context) {
        let document = PDFDocument(url: documentURL)
        pdfView.document = document
        pdfView.autoScales = true
        context.coordinator.currentURL = documentURL

        DispatchQueue.main.async {
            pageCount = document?.pageCount ?? 0
        }
    }

    final class Coordinator {
        var currentURL: URL?
    }
}
