import PDFKit
import SwiftUI

struct PDFKitView: UIViewRepresentable {
    let documentURL: URL
    @Binding var pageCount: Int
    @Binding var selectedText: String

    func makeCoordinator() -> Coordinator {
        Coordinator(selectedText: $selectedText)
    }

    func makeUIView(context: Context) -> PDFView {
        let pdfView = PDFView()
        pdfView.autoScales = true
        pdfView.displayDirection = .vertical
        pdfView.displayMode = .singlePageContinuous
        pdfView.backgroundColor = .systemGroupedBackground
        context.coordinator.attach(to: pdfView)
        loadDocument(in: pdfView, context: context)
        return pdfView
    }

    func updateUIView(_ pdfView: PDFView, context: Context) {
        context.coordinator.selectedText = $selectedText

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
        context.coordinator.clearSelection()

        DispatchQueue.main.async {
            pageCount = document?.pageCount ?? 0
        }
    }

    final class Coordinator: NSObject {
        var currentURL: URL?
        var selectedText: Binding<String>
        private weak var observedPDFView: PDFView?

        init(selectedText: Binding<String>) {
            self.selectedText = selectedText
        }

        func attach(to pdfView: PDFView) {
            if observedPDFView === pdfView {
                return
            }

            if let observedPDFView {
                NotificationCenter.default.removeObserver(
                    self,
                    name: .PDFViewSelectionChanged,
                    object: observedPDFView
                )
            }

            observedPDFView = pdfView
            NotificationCenter.default.addObserver(
                self,
                selector: #selector(selectionChanged(_:)),
                name: .PDFViewSelectionChanged,
                object: pdfView
            )
        }

        func clearSelection() {
            observedPDFView?.clearSelection()
            updateSelectedText("")
        }

        @objc private func selectionChanged(_ notification: Notification) {
            guard let pdfView = notification.object as? PDFView else {
                updateSelectedText("")
                return
            }

            let text = pdfView.currentSelection?.string?
                .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            updateSelectedText(text)
        }

        private func updateSelectedText(_ text: String) {
            DispatchQueue.main.async {
                self.selectedText.wrappedValue = text
            }
        }

        deinit {
            if let observedPDFView {
                NotificationCenter.default.removeObserver(
                    self,
                    name: .PDFViewSelectionChanged,
                    object: observedPDFView
                )
            }
        }
    }
}
