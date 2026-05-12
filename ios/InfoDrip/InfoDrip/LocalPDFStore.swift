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

struct BackendHighlight: Equatable, Decodable {
    let id: Int
    let documentID: Int
    let pageNumber: Int
    let selectedText: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case documentID = "document_id"
        case pageNumber = "page_number"
        case selectedText = "selected_text"
        case createdAt = "created_at"
    }
}

struct BackendExplanation: Equatable, Decodable {
    let id: Int
    let highlightID: Int
    let summary: String
    let keyPoints: [String]
    let provider: String
    let model: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case highlightID = "highlight_id"
        case summary
        case keyPoints = "key_points"
        case provider
        case model
        case createdAt = "created_at"
    }
}

struct BackendGlossaryTerm: Equatable, Decodable {
    let id: Int
    let documentID: Int
    let highlightID: Int
    let term: String
    let definition: String
    let sourceText: String?
    let provider: String
    let model: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case documentID = "document_id"
        case highlightID = "highlight_id"
        case term
        case definition
        case sourceText = "source_text"
        case provider
        case model
        case createdAt = "created_at"
    }
}

struct BackendQuiz: Equatable, Decodable {
    let id: Int
    let documentID: Int
    let highlightID: Int
    let quizType: String
    let question: String
    let answer: String
    let explanation: String
    let sourceText: String
    let provider: String
    let model: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case documentID = "document_id"
        case highlightID = "highlight_id"
        case quizType = "quiz_type"
        case question
        case answer
        case explanation
        case sourceText = "source_text"
        case provider
        case model
        case createdAt = "created_at"
    }
}

struct BackendQuizAttempt: Equatable, Decodable {
    let id: Int
    let quizID: Int
    let userAnswer: String
    let isCorrect: Bool?
    let feedback: String?
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case quizID = "quiz_id"
        case userAnswer = "user_answer"
        case isCorrect = "is_correct"
        case feedback
        case createdAt = "created_at"
    }
}

struct BackendReviewAgainQuizAttempt: Equatable, Decodable {
    let attemptID: Int
    let quizID: Int
    let documentID: Int
    let highlightID: Int
    let userAnswer: String
    let isCorrect: Bool?
    let feedback: String?
    let attemptedAt: String
    let quizType: String
    let question: String
    let answer: String
    let explanation: String
    let sourceText: String
    let documentTitle: String
    let pageNumber: Int

    enum CodingKeys: String, CodingKey {
        case attemptID = "attempt_id"
        case quizID = "quiz_id"
        case documentID = "document_id"
        case highlightID = "highlight_id"
        case userAnswer = "user_answer"
        case isCorrect = "is_correct"
        case feedback
        case attemptedAt = "attempted_at"
        case quizType = "quiz_type"
        case question
        case answer
        case explanation
        case sourceText = "source_text"
        case documentTitle = "document_title"
        case pageNumber = "page_number"
    }
}

struct BackendReviewCard: Equatable, Decodable {
    let id: Int
    let documentID: Int
    let quizID: Int
    let quizAttemptID: Int
    let front: String
    let back: String
    let sourceText: String?
    let provider: String
    let model: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case documentID = "document_id"
        case quizID = "quiz_id"
        case quizAttemptID = "quiz_attempt_id"
        case front
        case back
        case sourceText = "source_text"
        case provider
        case model
        case createdAt = "created_at"
    }
}

enum PDFUploadState: Equatable {
    case idle
    case uploading
    case uploaded(BackendDocument)
    case failed(String)
}

enum HighlightSaveState: Equatable {
    case idle
    case saving
    case saved(BackendHighlight)
    case failed(String)
}

enum ExplanationState: Equatable {
    case idle
    case loading
    case loaded(BackendExplanation)
    case failed(String)
}

enum GlossaryState: Equatable {
    case idle
    case loading
    case loaded([BackendGlossaryTerm])
    case failed(String)
}

enum QuizState: Equatable {
    case idle
    case loading
    case loaded([BackendQuiz])
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

    func createHighlight(documentID: Int, pageNumber: Int, selectedText: String) async throws -> BackendHighlight {
        let endpoint = baseURL.appendingPathComponent("api/v1/highlights")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(
            HighlightCreatePayload(
                documentID: documentID,
                pageNumber: pageNumber,
                selectedText: selectedText
            )
        )

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendAPIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            let message = String(data: data, encoding: .utf8)
            throw BackendAPIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }

        return try JSONDecoder().decode(BackendHighlight.self, from: data)
    }

    func createExplanation(highlightID: Int) async throws -> BackendExplanation {
        let endpoint = baseURL
            .appendingPathComponent("api/v1/highlights")
            .appendingPathComponent(String(highlightID))
            .appendingPathComponent("explanations")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendAPIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            let message = String(data: data, encoding: .utf8)
            throw BackendAPIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }

        return try JSONDecoder().decode(BackendExplanation.self, from: data)
    }

    func createGlossaryTerms(highlightID: Int) async throws -> [BackendGlossaryTerm] {
        let endpoint = baseURL
            .appendingPathComponent("api/v1/highlights")
            .appendingPathComponent(String(highlightID))
            .appendingPathComponent("glossary-terms")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendAPIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            let message = String(data: data, encoding: .utf8)
            throw BackendAPIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }

        return try JSONDecoder().decode([BackendGlossaryTerm].self, from: data)
    }

    func createQuizzes(highlightID: Int, maxQuizzes: Int? = nil) async throws -> [BackendQuiz] {
        let endpoint = baseURL
            .appendingPathComponent("api/v1/highlights")
            .appendingPathComponent(String(highlightID))
            .appendingPathComponent("quizzes")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        if let maxQuizzes {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(
                QuizGenerationPayload(
                    quizTypes: ["short_answer", "fill_blank"],
                    maxQuizzes: maxQuizzes
                )
            )
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendAPIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            let message = String(data: data, encoding: .utf8)
            throw BackendAPIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }

        return try JSONDecoder().decode([BackendQuiz].self, from: data)
    }

    func createQuizAttempt(
        quizID: Int,
        userAnswer: String,
        isCorrect: Bool? = nil,
        feedback: String? = nil
    ) async throws -> BackendQuizAttempt {
        let normalizedAnswer = userAnswer.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedAnswer.isEmpty else {
            throw BackendAPIError.invalidRequest("Enter an answer before saving.")
        }

        let endpoint = baseURL
            .appendingPathComponent("api/v1/quizzes")
            .appendingPathComponent(String(quizID))
            .appendingPathComponent("attempts")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(
            QuizAttemptCreatePayload(
                userAnswer: normalizedAnswer,
                isCorrect: isCorrect,
                feedback: feedback
            )
        )

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendAPIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            let message = String(data: data, encoding: .utf8)
            throw BackendAPIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }

        return try JSONDecoder().decode(BackendQuizAttempt.self, from: data)
    }

    func listReviewAgainQuizAttempts(documentID: Int? = nil) async throws -> [BackendReviewAgainQuizAttempt] {
        let endpoint = baseURL
            .appendingPathComponent("api/v1/quiz-attempts/review-again")
        var components = URLComponents(url: endpoint, resolvingAgainstBaseURL: false)
        if let documentID {
            components?.queryItems = [
                URLQueryItem(name: "document_id", value: String(documentID))
            ]
        }

        guard let url = components?.url else {
            throw BackendAPIError.invalidRequest("Could not build review-again request URL.")
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendAPIError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            let message = String(data: data, encoding: .utf8)
            throw BackendAPIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }

        return try JSONDecoder().decode([BackendReviewAgainQuizAttempt].self, from: data)
    }

    func createReviewCard(attemptID: Int) async throws -> BackendReviewCard {
        let endpoint = baseURL
            .appendingPathComponent("api/v1/quiz-attempts")
            .appendingPathComponent(String(attemptID))
            .appendingPathComponent("review-cards")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw BackendAPIError.invalidResponse
        }

        guard httpResponse.statusCode == 201 else {
            let message = String(data: data, encoding: .utf8)
            throw BackendAPIError.requestFailed(statusCode: httpResponse.statusCode, message: message)
        }

        return try JSONDecoder().decode(BackendReviewCard.self, from: data)
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

    private struct HighlightCreatePayload: Encodable {
        let documentID: Int
        let pageNumber: Int
        let selectedText: String

        enum CodingKeys: String, CodingKey {
            case documentID = "document_id"
            case pageNumber = "page_number"
            case selectedText = "selected_text"
        }
    }

    private struct QuizGenerationPayload: Encodable {
        let quizTypes: [String]
        let maxQuizzes: Int

        enum CodingKeys: String, CodingKey {
            case quizTypes = "quiz_types"
            case maxQuizzes = "max_quizzes"
        }
    }

    private struct QuizAttemptCreatePayload: Encodable {
        let userAnswer: String
        let isCorrect: Bool?
        let feedback: String?

        enum CodingKeys: String, CodingKey {
            case userAnswer = "user_answer"
            case isCorrect = "is_correct"
            case feedback
        }
    }
}

enum BackendAPIError: LocalizedError {
    case invalidResponse
    case invalidRequest(String)
    case requestFailed(statusCode: Int, message: String?)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Backend returned an invalid response."
        case .invalidRequest(let message):
            return message
        case .requestFailed(let statusCode, let message):
            if let message, !message.isEmpty {
                return "Backend request failed (\(statusCode)): \(message)"
            }
            return "Backend request failed (\(statusCode))."
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
    @Published private(set) var highlightSaveState: HighlightSaveState = .idle
    @Published private(set) var explanationState: ExplanationState = .idle
    @Published private(set) var glossaryState: GlossaryState = .idle
    @Published private(set) var quizState: QuizState = .idle
    @Published private(set) var lastSavedHighlight: BackendHighlight?

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
        highlightSaveState = .idle
        explanationState = .idle
        glossaryState = .idle
        quizState = .idle
        lastSavedHighlight = nil

        Task {
            await upload(documentID: document.id, fileURL: destinationURL)
        }
    }

    func saveSelectedHighlight(text: String, pageNumber: Int?) {
        guard case .uploaded(let backendDocument) = uploadState else {
            highlightSaveState = .failed("Backend document is not ready.")
            return
        }

        guard let pageNumber else {
            highlightSaveState = .failed("Could not find the selected page.")
            return
        }

        let selectedText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !selectedText.isEmpty else {
            highlightSaveState = .failed("Select text before saving a highlight.")
            return
        }

        highlightSaveState = .saving
        lastSavedHighlight = nil

        Task {
            await createHighlight(
                documentID: backendDocument.id,
                pageNumber: pageNumber,
                selectedText: selectedText
            )
        }
    }

    func explainSelectedHighlight(text: String, pageNumber: Int?) {
        guard case .uploaded(let backendDocument) = uploadState else {
            explanationState = .failed("Backend document is not ready.")
            return
        }

        guard let pageNumber else {
            explanationState = .failed("Could not find the selected page.")
            return
        }

        let selectedText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !selectedText.isEmpty else {
            explanationState = .failed("Select text before requesting an explanation.")
            return
        }

        explanationState = .loading

        Task {
            await explainSelection(
                documentID: backendDocument.id,
                pageNumber: pageNumber,
                selectedText: selectedText
            )
        }
    }

    func createGlossaryTermsForSelection(text: String, pageNumber: Int?) {
        guard case .uploaded(let backendDocument) = uploadState else {
            glossaryState = .failed("Backend document is not ready.")
            return
        }

        guard let pageNumber else {
            glossaryState = .failed("Could not find the selected page.")
            return
        }

        let selectedText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !selectedText.isEmpty else {
            glossaryState = .failed("Select text before requesting glossary terms.")
            return
        }

        glossaryState = .loading

        Task {
            await createGlossaryTerms(
                documentID: backendDocument.id,
                pageNumber: pageNumber,
                selectedText: selectedText
            )
        }
    }

    func createQuizzesForSelection(text: String, pageNumber: Int?, maxQuizzes: Int? = nil) {
        guard case .uploaded(let backendDocument) = uploadState else {
            quizState = .failed("Backend document is not ready.")
            return
        }

        guard let pageNumber else {
            quizState = .failed("Could not find the selected page.")
            return
        }

        let selectedText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !selectedText.isEmpty else {
            quizState = .failed("Select text before requesting quizzes.")
            return
        }

        quizState = .loading

        Task {
            await createQuizzes(
                documentID: backendDocument.id,
                pageNumber: pageNumber,
                selectedText: selectedText,
                maxQuizzes: maxQuizzes
            )
        }
    }

    func clearHighlightSaveState() {
        highlightSaveState = .idle
        lastSavedHighlight = nil
    }

    func clearExplanationState() {
        explanationState = .idle
    }

    func clearGlossaryState() {
        glossaryState = .idle
    }

    func clearQuizState() {
        quizState = .idle
    }

    func createQuizAttempt(
        quizID: Int,
        userAnswer: String,
        isCorrect: Bool? = nil,
        feedback: String? = nil
    ) async throws -> BackendQuizAttempt {
        try await apiClient.createQuizAttempt(
            quizID: quizID,
            userAnswer: userAnswer,
            isCorrect: isCorrect,
            feedback: feedback
        )
    }

    func listReviewAgainQuizAttempts(documentID: Int? = nil) async throws -> [BackendReviewAgainQuizAttempt] {
        try await apiClient.listReviewAgainQuizAttempts(documentID: documentID)
    }

    func createReviewCard(attemptID: Int) async throws -> BackendReviewCard {
        try await apiClient.createReviewCard(attemptID: attemptID)
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

    private func createHighlight(documentID: Int, pageNumber: Int, selectedText: String) async {
        do {
            let highlight = try await apiClient.createHighlight(
                documentID: documentID,
                pageNumber: pageNumber,
                selectedText: selectedText
            )
            guard currentDocument?.backendDocument?.id == documentID else {
                return
            }

            lastSavedHighlight = highlight
            highlightSaveState = .saved(highlight)
        } catch {
            guard currentDocument?.backendDocument?.id == documentID else {
                return
            }

            highlightSaveState = .failed(error.localizedDescription)
        }
    }

    private func explainSelection(documentID: Int, pageNumber: Int, selectedText: String) async {
        do {
            let highlight = try await highlightForCurrentSelection(
                documentID: documentID,
                pageNumber: pageNumber,
                selectedText: selectedText
            )
            let explanation = try await apiClient.createExplanation(highlightID: highlight.id)
            guard currentDocument?.backendDocument?.id == documentID else {
                return
            }

            lastSavedHighlight = highlight
            highlightSaveState = .saved(highlight)
            explanationState = .loaded(explanation)
        } catch {
            guard currentDocument?.backendDocument?.id == documentID else {
                return
            }

            if case .saving = highlightSaveState {
                highlightSaveState = .failed(error.localizedDescription)
            }
            explanationState = .failed(error.localizedDescription)
        }
    }

    private func createGlossaryTerms(documentID: Int, pageNumber: Int, selectedText: String) async {
        do {
            let highlight = try await highlightForCurrentSelection(
                documentID: documentID,
                pageNumber: pageNumber,
                selectedText: selectedText
            )
            let glossaryTerms = try await apiClient.createGlossaryTerms(highlightID: highlight.id)
            guard currentDocument?.backendDocument?.id == documentID else {
                return
            }

            lastSavedHighlight = highlight
            highlightSaveState = .saved(highlight)
            glossaryState = .loaded(glossaryTerms)
        } catch {
            guard currentDocument?.backendDocument?.id == documentID else {
                return
            }

            if case .saving = highlightSaveState {
                highlightSaveState = .failed(error.localizedDescription)
            }
            glossaryState = .failed(error.localizedDescription)
        }
    }

    private func createQuizzes(
        documentID: Int,
        pageNumber: Int,
        selectedText: String,
        maxQuizzes: Int? = nil
    ) async {
        do {
            let highlight = try await highlightForCurrentSelection(
                documentID: documentID,
                pageNumber: pageNumber,
                selectedText: selectedText
            )
            let quizzes = try await apiClient.createQuizzes(
                highlightID: highlight.id,
                maxQuizzes: maxQuizzes
            )
            guard currentDocument?.backendDocument?.id == documentID else {
                return
            }

            lastSavedHighlight = highlight
            highlightSaveState = .saved(highlight)
            quizState = .loaded(quizzes)
        } catch {
            guard currentDocument?.backendDocument?.id == documentID else {
                return
            }

            if case .saving = highlightSaveState {
                highlightSaveState = .failed(error.localizedDescription)
            }
            quizState = .failed(error.localizedDescription)
        }
    }

    private func highlightForCurrentSelection(
        documentID: Int,
        pageNumber: Int,
        selectedText: String
    ) async throws -> BackendHighlight {
        if let lastSavedHighlight,
           lastSavedHighlight.documentID == documentID,
           lastSavedHighlight.pageNumber == pageNumber,
           lastSavedHighlight.selectedText == selectedText {
            return lastSavedHighlight
        }

        highlightSaveState = .saving
        let highlight = try await apiClient.createHighlight(
            documentID: documentID,
            pageNumber: pageNumber,
            selectedText: selectedText
        )
        lastSavedHighlight = highlight
        highlightSaveState = .saved(highlight)
        return highlight
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
