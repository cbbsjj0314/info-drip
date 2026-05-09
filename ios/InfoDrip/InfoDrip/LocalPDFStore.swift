import Combine
import Foundation

struct ImportedPDF: Identifiable, Equatable {
    let id: UUID
    let title: String
    let url: URL
    let importedAt: Date

    init(title: String, url: URL, importedAt: Date = Date()) {
        self.id = UUID()
        self.title = title
        self.url = url
        self.importedAt = importedAt
    }
}

final class LocalPDFStore: ObservableObject {
    @Published private(set) var currentDocument: ImportedPDF?

    func importPDF(from sourceURL: URL) throws {
        let destinationURL = try copyIntoAppDocuments(sourceURL)
        currentDocument = ImportedPDF(
            title: destinationURL.deletingPathExtension().lastPathComponent,
            url: destinationURL
        )
    }

    private func copyIntoAppDocuments(_ sourceURL: URL) throws -> URL {
        let fileManager = FileManager.default
        let importDirectory = try importedPDFDirectory(fileManager: fileManager)
        let destinationURL = importDirectory.appendingPathComponent(sourceURL.lastPathComponent)

        let canAccess = sourceURL.startAccessingSecurityScopedResource()
        defer {
            if canAccess {
                sourceURL.stopAccessingSecurityScopedResource()
            }
        }

        if fileManager.fileExists(atPath: destinationURL.path) {
            try fileManager.removeItem(at: destinationURL)
        }

        try fileManager.copyItem(at: sourceURL, to: destinationURL)
        return destinationURL
    }

    private func importedPDFDirectory(fileManager: FileManager) throws -> URL {
        let documentsDirectory = try fileManager.url(
            for: .documentDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let importDirectory = documentsDirectory.appendingPathComponent("ImportedPDFs", isDirectory: true)

        if !fileManager.fileExists(atPath: importDirectory.path) {
            try fileManager.createDirectory(at: importDirectory, withIntermediateDirectories: true)
        }

        return importDirectory
    }
}
