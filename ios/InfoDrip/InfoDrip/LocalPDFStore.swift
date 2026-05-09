import Combine
import Foundation

struct ImportedPDF: Identifiable, Equatable {
    let id: UUID
    let title: String
    let url: URL
    let importedAt: Date
    var backendDocument: BackendDocument?

    init(title: String, url: URL, importedAt: Date = Date(), backendDocument: BackendDocument? = nil) {
        self.id = UUID()
        self.title = title
        self.url = url
        self.importedAt = importedAt
        self.backendDocument = backendDocument
    }
}

struct BackendDocument: Equatable, Decodable {
    let id: Int
    let title: String
    let originalFilename: String
    let storagePath: String
    let pageCount: Int
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case originalFilename = "original_filename"
        case storagePath = "storage_path"
        case pageCount = "page_count"
        case createdAt = "created_at"
    }
}

enum PDFUploadState: Equatable {
    case idle
    case uploading
    case uploaded(BackendDocument)
    case failed(String)
}

struct BackendAPIClient {
    // Simulator development default. Change this one value for a physical iPad backend host.
    static let development = BackendAPIClient(baseURL: URL(string: "http://127.0.0.1:8000")!)

    let baseURL: URL
    private let session: URLSession

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func uploadDocument(fileURL: URL) async throws -> BackendDocument {
        let endpoint = baseURL.appendingPathComponent("api/v1/documents")
        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let body = try multipartBody(
            fileURL: fileURL,
            fieldName: "file",
            boundary: boundary
        )
        let (data, response) = try await session.upload(for: request, from: body)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendAPIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            let message = String(data: data, encoding: .utf8)
            throw BackendAPIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }

        return try JSONDecoder().decode(BackendDocument.self, from: data)
    }

    private func multipartBody(fileURL: URL, fieldName: String, boundary: String) throws -> Data {
        var body = Data()
        let filename = fileURL.lastPathComponent
        let lineBreak = "\r\n"

        body.append("--\(boundary)\(lineBreak)")
        body.append("Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(filename)\"\(lineBreak)")
        body.append("Content-Type: application/pdf\(lineBreak)\(lineBreak)")
        body.append(try Data(contentsOf: fileURL))
        body.append(lineBreak)
        body.append("--\(boundary)--\(lineBreak)")

        return body
    }
}

enum BackendAPIError: LocalizedError {
    case invalidResponse
    case requestFailed(statusCode: Int, message: String?)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Backend returned an invalid response."
        case .requestFailed(let statusCode, let message):
            if let message, !message.isEmpty {
                return "Backend upload failed (\(statusCode)): \(message)"
            }
            return "Backend upload failed (\(statusCode))."
        }
    }
}

private extension Data {
    mutating func append(_ string: String) {
        append(Data(string.utf8))
    }
}

@MainActor
final class LocalPDFStore: ObservableObject {
    @Published private(set) var currentDocument: ImportedPDF?
    @Published private(set) var uploadState: PDFUploadState = .idle

    private let apiClient: BackendAPIClient

    init(apiClient: BackendAPIClient = .development) {
        self.apiClient = apiClient
    }

    func importPDF(from sourceURL: URL) throws {
        let destinationURL = try copyIntoAppDocuments(sourceURL)
        let document = ImportedPDF(
            title: destinationURL.deletingPathExtension().lastPathComponent,
            url: destinationURL
        )
        currentDocument = document
        uploadState = .uploading

        Task {
            await upload(documentID: document.id, fileURL: destinationURL)
        }
    }

    private func upload(documentID: UUID, fileURL: URL) async {
        do {
            let backendDocument = try await apiClient.uploadDocument(fileURL: fileURL)
            guard currentDocument?.id == documentID else {
                return
            }

            currentDocument?.backendDocument = backendDocument
            uploadState = .uploaded(backendDocument)
        } catch {
            guard currentDocument?.id == documentID else {
                return
            }

            uploadState = .failed(error.localizedDescription)
        }
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
