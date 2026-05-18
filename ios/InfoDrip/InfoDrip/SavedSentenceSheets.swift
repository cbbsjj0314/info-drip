import SwiftUI

struct SavedSentenceListSheet: View {
    let documentID: Int
    let documentTitle: String
    let onLoad: (Int) async throws -> BackendDocumentStudyRecord
    let onSaveQuizAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    let onDeleteQuizAttempt: (Int) async throws -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var state: SavedSentenceLoadState = .idle
    @State private var activeDetailSnapshot: SavedSentenceDetailSnapshot?

    var body: some View {
        NavigationStack {
            content
                .background(Color(.systemGroupedBackground))
                .navigationTitle("저장된 문장")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        SheetDismissIconButton(accessibilityLabel: "저장된 문장 닫기") {
                            dismiss()
                        }
                    }
                }
        }
        .sheet(item: $activeDetailSnapshot) { snapshot in
            SavedSentenceDetailSheet(
                snapshot: snapshot,
                onSaveQuizAttempt: onSaveQuizAttempt,
                onDeleteQuizAttempt: onDeleteQuizAttempt,
                onUpsertQuizAttemptInRecord: upsertQuizAttemptInLoadedRecord,
                onRemoveQuizAttemptFromRecord: removeQuizAttemptFromLoadedRecord
            )
        }
        .task {
            guard case .idle = state else {
                return
            }

            await load()
        }
    }

    @ViewBuilder
    private var content: some View {
        switch state {
        case .idle, .loading:
            loadingState
        case .loaded(let record):
            loadedState(record)
        case .failed(let message):
            failedState(message: message)
        }
    }

    private var loadingState: some View {
        VStack(spacing: 12) {
            ProgressView()
            Text("저장된 문장을 불러오는 중입니다.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func failedState(message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 36, weight: .light))
                .foregroundStyle(.orange)
            Text("저장된 문장을 불러오지 못했습니다.")
                .font(.headline)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: 420)
            Button {
                Task {
                    await load()
                }
            } label: {
                Label("다시 시도", systemImage: "arrow.clockwise")
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }

    private func loadedState(_ record: BackendDocumentStudyRecord) -> some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16) {
                SavedSentenceDocumentHeader(document: record.document)

                if record.highlights.isEmpty {
                    emptyState
                } else {
                    let statusSummary = SavedSentenceStatusSummary(record: record)
                    LazyVStack(alignment: .leading, spacing: 10) {
                        ForEach(record.highlights, id: \.id) { highlight in
                            SavedSentenceCard(
                                highlight: highlight,
                                statusLabels: statusSummary.statusLabels(for: highlight),
                                onShowDetail: {
                                    activeDetailSnapshot = SavedSentenceDetailSnapshot.make(
                                        highlight: highlight,
                                        record: record
                                    )
                                }
                            )
                        }
                    }
                }
            }
            .padding(24)
        }
    }

    @ViewBuilder
    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "text.badge.plus")
                .font(.system(size: 36, weight: .light))
                .foregroundStyle(.secondary)
            Text("저장된 문장이 없습니다.")
                .font(.headline)
            Text("PDF에서 문장을 선택한 뒤 문장 저장을 하면 여기에 표시됩니다.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 36)
    }

    private func load() async {
        state = .loading

        do {
            let record = try await onLoad(documentID)
            state = .loaded(record)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    private func removeQuizAttemptFromLoadedRecord(attemptID: Int) {
        guard case .loaded(let record) = state else {
            return
        }

        let updatedRecord = BackendDocumentStudyRecord(
            document: record.document,
            highlights: record.highlights,
            explanations: record.explanations,
            glossaryTerms: record.glossaryTerms,
            userQuestions: record.userQuestions,
            quizzes: record.quizzes,
            quizAttempts: record.quizAttempts.filter { $0.id != attemptID }
        )
        state = .loaded(updatedRecord)

        if let snapshot = activeDetailSnapshot {
            activeDetailSnapshot = snapshot.removingWrongQuizAttempt(attemptID: attemptID)
        }
    }

    private func upsertQuizAttemptInLoadedRecord(_ attempt: BackendQuizAttempt) {
        guard case .loaded(let record) = state else {
            return
        }

        let updatedAttempts = record.quizAttempts.upsertingSavedSentenceQuizAttempt(attempt)
        let updatedRecord = BackendDocumentStudyRecord(
            document: record.document,
            highlights: record.highlights,
            explanations: record.explanations,
            glossaryTerms: record.glossaryTerms,
            userQuestions: record.userQuestions,
            quizzes: record.quizzes,
            quizAttempts: updatedAttempts
        )
        state = .loaded(updatedRecord)

        if let snapshot = activeDetailSnapshot {
            activeDetailSnapshot = snapshot.upsertingWrongQuizAttempt(attempt)
        }
    }
}

private enum SavedSentenceLoadState: Equatable {
    case idle
    case loading
    case loaded(BackendDocumentStudyRecord)
    case failed(String)
}

private struct SavedSentenceRecordIndex {
    private let explanationsByHighlightID: [Int: [BackendStudyRecordExplanation]]
    private let glossaryTermsByHighlightID: [Int: [BackendGlossaryTerm]]
    private let userQuestionsByHighlightID: [Int: [BackendUserQuestion]]
    private let quizzesByHighlightID: [Int: [BackendQuiz]]
    private let wrongQuizAttemptsByHighlightID: [Int: [BackendQuizAttempt]]

    init(record: BackendDocumentStudyRecord) {
        explanationsByHighlightID = Dictionary(grouping: record.explanations, by: \.highlightID)
        glossaryTermsByHighlightID = Dictionary(grouping: record.glossaryTerms, by: \.highlightID)
        userQuestionsByHighlightID = Dictionary(grouping: record.userQuestions, by: \.highlightID)
        quizzesByHighlightID = Dictionary(grouping: record.quizzes, by: \.highlightID)

        let highlightIDByQuizID = Dictionary(
            uniqueKeysWithValues: record.quizzes.map { quiz in
                (quiz.id, quiz.highlightID)
            }
        )
        let wrongAttemptPairs = record.quizAttempts.compactMap { attempt -> (Int, BackendQuizAttempt)? in
            guard attempt.isCorrect == .some(false),
                  let highlightID = highlightIDByQuizID[attempt.quizID] else {
                return nil
            }

            return (highlightID, attempt)
        }

        wrongQuizAttemptsByHighlightID = wrongAttemptPairs.reduce(into: [:]) { result, pair in
            result[pair.0, default: []].append(pair.1)
        }
    }

    func explanations(for highlight: BackendHighlight) -> [BackendStudyRecordExplanation] {
        explanationsByHighlightID[highlight.id, default: []]
    }

    func glossaryTerms(for highlight: BackendHighlight) -> [BackendGlossaryTerm] {
        glossaryTermsByHighlightID[highlight.id, default: []]
    }

    func userQuestions(for highlight: BackendHighlight) -> [BackendUserQuestion] {
        userQuestionsByHighlightID[highlight.id, default: []]
    }

    func quizzes(for highlight: BackendHighlight) -> [BackendQuiz] {
        quizzesByHighlightID[highlight.id, default: []]
    }

    func wrongQuizAttempts(for highlight: BackendHighlight) -> [BackendQuizAttempt] {
        wrongQuizAttemptsByHighlightID[highlight.id, default: []]
    }
}

private struct SavedSentenceDetailSnapshot: Identifiable {
    let id: Int
    let highlight: BackendHighlight
    let explanations: [BackendStudyRecordExplanation]
    let glossaryTerms: [BackendGlossaryTerm]
    let userQuestions: [BackendUserQuestion]
    let quizzes: [BackendQuiz]
    let wrongQuizAttempts: [BackendQuizAttempt]

    static func make(
        highlight: BackendHighlight,
        record: BackendDocumentStudyRecord
    ) -> SavedSentenceDetailSnapshot {
        let index = SavedSentenceRecordIndex(record: record)
        return SavedSentenceDetailSnapshot(
            id: highlight.id,
            highlight: highlight,
            explanations: index.explanations(for: highlight),
            glossaryTerms: index.glossaryTerms(for: highlight),
            userQuestions: index.userQuestions(for: highlight),
            quizzes: index.quizzes(for: highlight),
            wrongQuizAttempts: index.wrongQuizAttempts(for: highlight)
        )
    }

    var hasGeneratedResults: Bool {
        !explanations.isEmpty
            || !glossaryTerms.isEmpty
            || !userQuestions.isEmpty
            || !quizzes.isEmpty
            || !wrongQuizAttempts.isEmpty
    }

    func removingWrongQuizAttempt(attemptID: Int) -> SavedSentenceDetailSnapshot {
        SavedSentenceDetailSnapshot(
            id: id,
            highlight: highlight,
            explanations: explanations,
            glossaryTerms: glossaryTerms,
            userQuestions: userQuestions,
            quizzes: quizzes,
            wrongQuizAttempts: wrongQuizAttempts.filter { $0.id != attemptID }
        )
    }

    func upsertingWrongQuizAttempt(_ attempt: BackendQuizAttempt) -> SavedSentenceDetailSnapshot {
        SavedSentenceDetailSnapshot(
            id: id,
            highlight: highlight,
            explanations: explanations,
            glossaryTerms: glossaryTerms,
            userQuestions: userQuestions,
            quizzes: quizzes,
            wrongQuizAttempts: wrongQuizAttempts.upsertingSavedSentenceWrongQuizAttempt(
                attempt,
                quizIDs: Set(quizzes.map(\.id))
            )
        )
    }
}

private struct SavedSentenceStatusSummary {
    private let index: SavedSentenceRecordIndex

    init(record: BackendDocumentStudyRecord) {
        index = SavedSentenceRecordIndex(record: record)
    }

    func statusLabels(for highlight: BackendHighlight) -> [String] {
        var labels: [String] = []

        if !index.explanations(for: highlight).isEmpty {
            labels.append("설명")
        }

        if !index.glossaryTerms(for: highlight).isEmpty {
            labels.append("용어")
        }

        if !index.userQuestions(for: highlight).isEmpty {
            labels.append("질문")
        }

        if !index.quizzes(for: highlight).isEmpty {
            labels.append("퀴즈")
        }

        if !index.wrongQuizAttempts(for: highlight).isEmpty {
            labels.append("다시 풀 퀴즈")
        }

        return labels.isEmpty ? ["저장만 됨"] : labels
    }
}

private struct SavedSentenceDocumentHeader: View {
    let document: BackendDocument

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(document.originalFilename)
                .font(.headline)
                .fixedSize(horizontal: false, vertical: true)

            Text("\(document.pageCount) pages")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct SavedSentenceCard: View {
    let highlight: BackendHighlight
    let statusLabels: [String]
    let onShowDetail: () -> Void

    var body: some View {
        StudyRecordCard {
            metadataRow(left: "p. \(highlight.pageNumber)", right: highlight.createdAt)

            Text(highlight.selectedText)
                .font(.subheadline)
                .lineLimit(5)
                .fixedSize(horizontal: false, vertical: true)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(statusLabels, id: \.self) { label in
                        SavedSentenceStatusBadge(label: label)
                    }
                }
            }

            Button(action: onShowDetail) {
                HStack(spacing: 6) {
                    Text("자세히 보기")
                    Image(systemName: "chevron.right")
                        .font(.caption2.weight(.semibold))
                }
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.accentColor)
                .frame(maxWidth: .infinity, alignment: .trailing)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
        }
    }
}

private struct SavedSentenceDetailSheet: View {
    let snapshot: SavedSentenceDetailSnapshot
    let onSaveQuizAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    let onDeleteQuizAttempt: (Int) async throws -> Void
    let onUpsertQuizAttemptInRecord: (BackendQuizAttempt) -> Void
    let onRemoveQuizAttemptFromRecord: (Int) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var activeSheet: SavedSentenceDetailActiveSheet?
    @State private var wrongQuizAttempts: [BackendQuizAttempt]
    @State private var deletingAttemptIDs: Set<Int> = []
    @State private var removalErrorsByAttemptID: [Int: String] = [:]

    init(
        snapshot: SavedSentenceDetailSnapshot,
        onSaveQuizAttempt: @escaping (Int, String, Bool?) async throws -> BackendQuizAttempt,
        onDeleteQuizAttempt: @escaping (Int) async throws -> Void,
        onUpsertQuizAttemptInRecord: @escaping (BackendQuizAttempt) -> Void,
        onRemoveQuizAttemptFromRecord: @escaping (Int) -> Void
    ) {
        self.snapshot = snapshot
        self.onSaveQuizAttempt = onSaveQuizAttempt
        self.onDeleteQuizAttempt = onDeleteQuizAttempt
        self.onUpsertQuizAttemptInRecord = onUpsertQuizAttemptInRecord
        self.onRemoveQuizAttemptFromRecord = onRemoveQuizAttemptFromRecord
        _wrongQuizAttempts = State(initialValue: snapshot.wrongQuizAttempts)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 16) {
                    sentenceBlock

                    if hasGeneratedResults {
                        generatedResultSections
                    } else {
                        emptyResultState
                    }
                }
                .padding(24)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("저장된 문장 상세")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    SheetDismissIconButton(accessibilityLabel: "저장된 문장 상세 닫기") {
                        dismiss()
                    }
                }
            }
        }
        .sheet(item: $activeSheet) { activeSheet in
            switch activeSheet {
            case .quizStudy(let studySnapshot):
                QuizStudySheet(
                    quizzes: studySnapshot.quizzes,
                    onSaveAttempt: saveQuizAttemptAndRefresh
                )
            case .replay(let replaySnapshot):
                ReviewAgainReplaySheet(
                    item: replaySnapshot.item,
                    onSaveAttempt: saveQuizAttemptAndRefresh
                )
            }
        }
    }

    private var sentenceBlock: some View {
        StudyRecordCard {
            metadataRow(left: "p. \(snapshot.highlight.pageNumber)", right: snapshot.highlight.createdAt)

            Text(snapshot.highlight.selectedText)
                .font(.body)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    @ViewBuilder
    private var generatedResultSections: some View {
        if !snapshot.explanations.isEmpty {
            StudyRecordSection(title: "설명", count: snapshot.explanations.count) {
                ForEach(snapshot.explanations, id: \.id) { explanation in
                    SavedSentenceDetailExplanationCard(explanation: explanation)
                }
            }
        }

        if !snapshot.glossaryTerms.isEmpty {
            StudyRecordSection(title: "용어", count: snapshot.glossaryTerms.count) {
                ForEach(snapshot.glossaryTerms, id: \.id) { glossaryTerm in
                    StudyRecordGlossaryTermCard(glossaryTerm: glossaryTerm)
                }
            }
        }

        if !snapshot.userQuestions.isEmpty {
            StudyRecordSection(title: "질문", count: snapshot.userQuestions.count) {
                ForEach(snapshot.userQuestions, id: \.id) { userQuestion in
                    StudyRecordUserQuestionCard(userQuestion: userQuestion)
                }
            }
        }

        if !snapshot.quizzes.isEmpty {
            StudyRecordSection(title: "퀴즈", count: snapshot.quizzes.count) {
                Button {
                    activeSheet = .quizStudy(SavedSentenceQuizStudySnapshot(quizzes: snapshot.quizzes))
                } label: {
                    Label("공부 모드 열기", systemImage: "play.circle")
                        .font(.subheadline.weight(.semibold))
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
                .accessibilityLabel("공부 모드 열기")

                ForEach(snapshot.quizzes, id: \.id) { quiz in
                    SavedSentenceDetailQuizCard(quiz: quiz)
                }
            }
        }

        if !wrongQuizAttempts.isEmpty {
            StudyRecordSection(title: "다시 풀 퀴즈", count: wrongQuizAttempts.count) {
                ForEach(wrongQuizAttempts, id: \.id) { attempt in
                    SavedSentenceDetailWrongAttemptCard(
                        attempt: attempt,
                        replayItem: replayItem(for: attempt),
                        isDeleting: deletingAttemptIDs.contains(attempt.id),
                        removalError: removalErrorsByAttemptID[attempt.id],
                        onReplay: { item in
                            activeSheet = .replay(SavedSentenceReplaySnapshot(item: item))
                        },
                        onDelete: {
                            deleteWrongAttempt(attempt)
                        }
                    )
                }
            }
        }
    }

    private var hasGeneratedResults: Bool {
        !snapshot.explanations.isEmpty
            || !snapshot.glossaryTerms.isEmpty
            || !snapshot.userQuestions.isEmpty
            || !snapshot.quizzes.isEmpty
            || !wrongQuizAttempts.isEmpty
    }

    private func replayItem(for attempt: BackendQuizAttempt) -> ReviewAgainReplayItem? {
        guard let quiz = snapshot.quizzes.first(where: { $0.id == attempt.quizID }) else {
            return nil
        }

        return ReviewAgainReplayItem(
            attempt: attempt,
            quiz: quiz,
            pageNumber: snapshot.highlight.pageNumber
        )
    }

    private func deleteWrongAttempt(_ attempt: BackendQuizAttempt) {
        let attemptID = attempt.id
        guard !deletingAttemptIDs.contains(attemptID) else {
            return
        }

        deletingAttemptIDs.insert(attemptID)
        removalErrorsByAttemptID[attemptID] = nil

        Task { @MainActor in
            defer {
                deletingAttemptIDs.remove(attemptID)
            }

            do {
                try await onDeleteQuizAttempt(attemptID)
                removeWrongAttempt(attemptID: attemptID)
            } catch BackendAPIError.quizAttemptAlreadyRemoved {
                removeWrongAttempt(attemptID: attemptID)
            } catch BackendAPIError.quizAttemptHasReviewCards {
                removalErrorsByAttemptID[attemptID] = "복습 카드가 연결되어 있어 제거할 수 없습니다."
            } catch {
                removalErrorsByAttemptID[attemptID] = "제거하지 못했습니다."
            }
        }
    }

    private func removeWrongAttempt(attemptID: Int) {
        wrongQuizAttempts.removeAll { $0.id == attemptID }
        removalErrorsByAttemptID[attemptID] = nil
        onRemoveQuizAttemptFromRecord(attemptID)
    }

    private func saveQuizAttemptAndRefresh(
        quizID: Int,
        userAnswer: String,
        isCorrect: Bool?
    ) async throws -> BackendQuizAttempt {
        let savedAttempt = try await onSaveQuizAttempt(quizID, userAnswer, isCorrect)
        wrongQuizAttempts = wrongQuizAttempts.upsertingSavedSentenceWrongQuizAttempt(
            savedAttempt,
            quizIDs: Set(snapshot.quizzes.map(\.id))
        )
        onUpsertQuizAttemptInRecord(savedAttempt)
        return savedAttempt
    }

    private var emptyResultState: some View {
        VStack(spacing: 10) {
            Image(systemName: "doc.text.magnifyingglass")
                .font(.system(size: 34, weight: .light))
                .foregroundStyle(.secondary)
            Text("아직 생성된 학습 결과가 없습니다.")
                .font(.headline)
            Text("이 화면에서는 저장된 문장에 연결된 기존 결과만 보여줍니다.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 28)
    }
}

private struct SavedSentenceQuizStudySnapshot: Identifiable {
    let id = UUID()
    let quizzes: [BackendQuiz]
}

private struct SavedSentenceReplaySnapshot: Identifiable {
    let id = UUID()
    let item: ReviewAgainReplayItem
}

private enum SavedSentenceDetailActiveSheet: Identifiable {
    case quizStudy(SavedSentenceQuizStudySnapshot)
    case replay(SavedSentenceReplaySnapshot)

    var id: UUID {
        switch self {
        case .quizStudy(let snapshot):
            return snapshot.id
        case .replay(let snapshot):
            return snapshot.id
        }
    }
}

private struct SavedSentenceDetailExplanationCard: View {
    let explanation: BackendStudyRecordExplanation

    var body: some View {
        StudyRecordCard {
            metadataRow(left: "설명", right: explanation.createdAt)

            Text(explanation.summary)
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)

            let keyPoints = explanation.keyPoints
                .map(savedSentenceTrimmed)
                .filter { !$0.isEmpty }
            if !keyPoints.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("핵심 포인트")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    ForEach(keyPoints, id: \.self) { point in
                        Text("• \(point)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }
        }
    }
}

private struct SavedSentenceDetailQuizCard: View {
    let quiz: BackendQuiz

    var body: some View {
        StudyRecordCard {
            metadataRow(left: displayTitle(for: quiz.quizType), right: quiz.createdAt)
            bodySection(title: "문제", text: quiz.question)
            bodySection(title: "정답", text: quiz.answer, lineLimit: 3)

            if let explanation = savedSentenceNonBlank(quiz.explanation) {
                bodySection(title: "해설", text: explanation, lineLimit: 4)
            }

            if let sourceText = savedSentenceNonBlank(quiz.sourceText) {
                bodySection(title: "원문", text: sourceText, lineLimit: 4)
            }
        }
    }

    private func displayTitle(for quizType: String) -> String {
        switch quizType {
        case "short_answer":
            return "단답형"
        case "fill_blank":
            return "빈칸"
        default:
            return quizType
        }
    }
}

private struct SavedSentenceDetailWrongAttemptCard: View {
    let attempt: BackendQuizAttempt
    let replayItem: ReviewAgainReplayItem?
    let isDeleting: Bool
    let removalError: String?
    let onReplay: (ReviewAgainReplayItem) -> Void
    let onDelete: () -> Void
    @State private var isConfirmingRemoval = false

    var body: some View {
        StudyRecordCard {
            metadataRow(left: "풀이 기록", right: attempt.createdAt)
            bodySection(title: "내 답안", text: attempt.userAnswer)

            if let feedback = savedSentenceNonBlank(attempt.feedback) {
                bodySection(title: "피드백", text: feedback, lineLimit: 4)
            }

            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 10) {
                    if let replayItem {
                        Button {
                            onReplay(replayItem)
                        } label: {
                            Label("다시 풀기", systemImage: "pencil")
                                .lineLimit(1)
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                        .disabled(isDeleting)
                        .accessibilityLabel("다시 풀기")
                    }

                    Button(role: .destructive) {
                        isConfirmingRemoval = true
                    } label: {
                        Image(systemName: "trash")
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .disabled(isDeleting)
                    .accessibilityLabel("다시 풀 퀴즈에서 제거")

                    if isDeleting {
                        ProgressView()
                            .controlSize(.small)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                if let removalError {
                    Label(removalError, systemImage: "exclamationmark.triangle.fill")
                        .font(.caption)
                        .foregroundStyle(.red)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .confirmationDialog(
            "이 퀴즈를 목록에서 제거할까요?",
            isPresented: $isConfirmingRemoval,
            titleVisibility: .visible
        ) {
            Button("제거", role: .destructive, action: onDelete)
            Button("취소", role: .cancel) {}
        } message: {
            Text("제거하면 다시 풀 퀴즈와 풀이 기록에서 빠집니다.")
        }
    }
}

private struct SavedSentenceStatusBadge: View {
    let label: String

    var body: some View {
        Text(label)
            .font(.caption.weight(.semibold))
            .foregroundStyle(foregroundStyle)
            .padding(.horizontal, 9)
            .padding(.vertical, 5)
            .background(backgroundStyle, in: Capsule())
    }

    private var foregroundStyle: Color {
        label == "저장만 됨" ? .secondary : .accentColor
    }

    private var backgroundStyle: Color {
        label == "저장만 됨"
            ? Color(.tertiarySystemGroupedBackground)
            : Color.accentColor.opacity(0.12)
    }
}

private func savedSentenceNonBlank(_ text: String?) -> String? {
    guard let text else {
        return nil
    }

    let normalizedText = savedSentenceTrimmed(text)
    return normalizedText.isEmpty ? nil : normalizedText
}

private func savedSentenceTrimmed(_ text: String) -> String {
    text.trimmingCharacters(in: .whitespacesAndNewlines)
}

private extension Array where Element == BackendQuizAttempt {
    func upsertingSavedSentenceQuizAttempt(_ attempt: BackendQuizAttempt) -> [BackendQuizAttempt] {
        var updatedAttempts = self
        if let existingIndex = updatedAttempts.firstIndex(where: { $0.id == attempt.id }) {
            updatedAttempts[existingIndex] = attempt
        } else {
            updatedAttempts.append(attempt)
        }

        return updatedAttempts
    }

    func upsertingSavedSentenceWrongQuizAttempt(
        _ attempt: BackendQuizAttempt,
        quizIDs: Set<Int>
    ) -> [BackendQuizAttempt] {
        var updatedAttempts = filter { $0.id != attempt.id }
        if attempt.isCorrect == .some(false), quizIDs.contains(attempt.quizID) {
            updatedAttempts.append(attempt)
        }

        return updatedAttempts
    }
}
