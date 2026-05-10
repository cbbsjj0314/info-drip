import PDFKit
import SwiftUI

struct PDFTextSelection: Equatable {
    let text: String
    let pageNumber: Int?

    static let empty = PDFTextSelection(text: "", pageNumber: nil)

    var isEmpty: Bool {
        text.isEmpty
    }
}

struct PDFKitView: UIViewRepresentable {
    let documentURL: URL
    @Binding var pageCount: Int
    @Binding var selection: PDFTextSelection

    func makeCoordinator() -> Coordinator {
        Coordinator(selection: $selection)
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
        context.coordinator.selection = $selection

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
        var selection: Binding<PDFTextSelection>
        private weak var observedPDFView: PDFView?

        init(selection: Binding<PDFTextSelection>) {
            self.selection = selection
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
            updateSelection(.empty)
        }

        @objc private func selectionChanged(_ notification: Notification) {
            guard let pdfView = notification.object as? PDFView else {
                updateSelection(.empty)
                return
            }

            guard let currentSelection = pdfView.currentSelection else {
                updateSelection(.empty)
                return
            }

            let text = currentSelection.string?
                .trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            guard !text.isEmpty else {
                updateSelection(.empty)
                return
            }

            updateSelection(
                PDFTextSelection(
                    text: text,
                    pageNumber: pageNumber(for: currentSelection, in: pdfView.document)
                )
            )
        }

        private func pageNumber(for selection: PDFSelection, in document: PDFDocument?) -> Int? {
            guard
                let document,
                let page = selection.pages.first
            else {
                return nil
            }

            let pageIndex = document.index(for: page)
            guard pageIndex != NSNotFound else {
                return nil
            }

            return pageIndex + 1
        }

        private func updateSelection(_ nextSelection: PDFTextSelection) {
            DispatchQueue.main.async {
                self.selection.wrappedValue = nextSelection
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
