import SwiftUI

struct SheetDismissIconButton: View {
    let accessibilityLabel: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: "xmark.circle.fill")
                .font(.title3)
                .foregroundStyle(.tertiary)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(accessibilityLabel)
    }
}

struct ExplanationDetailSheet: View {
    let explanation: BackendExplanation
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    let summary = trimmed(explanation.summary)
                    if !summary.isEmpty {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("요약")
                                .font(.headline)
                            Text(summary)
                                .font(.body)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    let keyPoints = nonBlankKeyPoints(for: explanation)
                    if !keyPoints.isEmpty {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("핵심 포인트")
                                .font(.headline)

                            ForEach(keyPoints, id: \.self) { point in
                                HStack(alignment: .firstTextBaseline, spacing: 8) {
                                    Image(systemName: "checkmark.circle.fill")
                                        .font(.caption)
                                        .foregroundStyle(.green)
                                    Text(point)
                                        .font(.body)
                                        .fixedSize(horizontal: false, vertical: true)
                                }
                            }
                        }
                    }

                }
                .padding(24)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("쉽게 설명")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    SheetDismissIconButton(accessibilityLabel: "설명 닫기") {
                        dismiss()
                    }
                }
            }
        }
    }

    private func nonBlankKeyPoints(for explanation: BackendExplanation) -> [String] {
        explanation.keyPoints
            .map(trimmed)
            .filter { !$0.isEmpty }
    }

    private func trimmed(_ text: String) -> String {
        text.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

struct GlossaryDetailSheet: View {
    let glossaryTerms: [BackendGlossaryTerm]
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                if glossaryTerms.isEmpty {
                    emptyState
                } else {
                    LazyVStack(alignment: .leading, spacing: 14) {
                        ForEach(glossaryTerms, id: \.id) { glossaryTerm in
                            VStack(alignment: .leading, spacing: 10) {
                                Text(glossaryTerm.term)
                                    .font(.headline)
                                    .fixedSize(horizontal: false, vertical: true)

                                Text(glossaryTerm.definition)
                                    .font(.body)
                                    .fixedSize(horizontal: false, vertical: true)

                                if let sourceText = trimmedSourceText(for: glossaryTerm) {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("원문")
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.secondary)
                                        Text(sourceText)
                                            .font(.subheadline)
                                            .foregroundStyle(.secondary)
                                            .fixedSize(horizontal: false, vertical: true)
                                    }
                                }

                            }
                            .padding(14)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
                            .overlay {
                                RoundedRectangle(cornerRadius: 8)
                                    .strokeBorder(Color(.separator), lineWidth: 0.5)
                            }
                        }
                    }
                    .padding(24)
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("용어")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    SheetDismissIconButton(accessibilityLabel: "용어 닫기") {
                        dismiss()
                    }
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "text.book.closed")
                .font(.system(size: 36, weight: .light))
                .foregroundStyle(.secondary)
            Text("표시할 용어가 없습니다.")
                .font(.headline)
            Text("용어를 다시 추출한 뒤 자세히 보기를 열어 주세요.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(40)
    }

    private func trimmedSourceText(for glossaryTerm: BackendGlossaryTerm) -> String? {
        guard let sourceText = glossaryTerm.sourceText else {
            return nil
        }

        let trimmedSourceText = sourceText.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmedSourceText.isEmpty ? nil : trimmedSourceText
    }
}

struct DocumentGlossaryCollectionSheet: View {
    let documentID: Int
    let documentTitle: String
    let onLoad: (Int) async throws -> BackendDocumentStudyRecord
    @Environment(\.dismiss) private var dismiss
    @State private var state: GlossaryCollectionLoadState = .idle

    var body: some View {
        NavigationStack {
            content
                .background(Color(.systemGroupedBackground))
                .navigationTitle("용어 모음")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        SheetDismissIconButton(accessibilityLabel: "용어 모음 닫기") {
                            dismiss()
                        }
                    }
                }
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
            Text("용어 모음을 불러오는 중입니다.")
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
            Text("용어 모음을 불러오지 못했습니다.")
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
                documentHeader(record.document)
                Text("용어 \(record.glossaryTerms.count)개")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                if record.glossaryTerms.isEmpty {
                    emptyState
                } else {
                    let items = glossaryItems(from: record)
                    LazyVStack(alignment: .leading, spacing: 14) {
                        ForEach(items) { item in
                            GlossaryCollectionTermCard(item: item)
                        }
                    }
                }
            }
            .padding(24)
        }
    }

    private func documentHeader(_ document: BackendDocument) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(nonBlank(document.originalFilename) ?? documentTitle)
                .font(.headline)
                .fixedSize(horizontal: false, vertical: true)

            Text("\(document.pageCount)쪽")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    @ViewBuilder
    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "text.book.closed")
                .font(.system(size: 36, weight: .light))
                .foregroundStyle(.secondary)
            Text("아직 정리된 용어가 없습니다.")
                .font(.headline)
            Text("PDF에서 궁금한 부분을 선택한 뒤 용어를 정리하면 여기에 표시됩니다.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 36)
    }

    private func glossaryItems(from record: BackendDocumentStudyRecord) -> [GlossaryCollectionItem] {
        let highlightsByID = record.highlights.reduce(into: [Int: BackendHighlight]()) { result, highlight in
            if result[highlight.id] == nil {
                result[highlight.id] = highlight
            }
        }

        return record.glossaryTerms.map { glossaryTerm in
            let highlight = highlightsByID[glossaryTerm.highlightID]
            return GlossaryCollectionItem(
                glossaryTerm: glossaryTerm,
                pageNumber: highlight?.pageNumber,
                sourceText: nonBlank(glossaryTerm.sourceText) ?? nonBlank(highlight?.selectedText)
            )
        }
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
}

private enum GlossaryCollectionLoadState: Equatable {
    case idle
    case loading
    case loaded(BackendDocumentStudyRecord)
    case failed(String)
}

private struct GlossaryCollectionItem: Identifiable {
    let glossaryTerm: BackendGlossaryTerm
    let pageNumber: Int?
    let sourceText: String?

    var id: Int {
        glossaryTerm.id
    }
}

private struct GlossaryCollectionTermCard: View {
    let item: GlossaryCollectionItem

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(item.glossaryTerm.term)
                    .font(.headline)
                    .fixedSize(horizontal: false, vertical: true)

                Spacer(minLength: 8)

                if let pageNumber = item.pageNumber {
                    Text("\(pageNumber)쪽")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }

            Text(item.glossaryTerm.definition)
                .font(.body)
                .fixedSize(horizontal: false, vertical: true)

            if let sourceText = item.sourceText {
                VStack(alignment: .leading, spacing: 4) {
                    Text("원문")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Text(sourceText)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(4)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
        .overlay {
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
    }
}

struct QuestionDetailSheet: View {
    let userQuestion: BackendUserQuestion
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("질문")
                            .font(.headline)
                        Text(userQuestion.question)
                            .font(.body)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("답변")
                            .font(.headline)
                        Text(userQuestion.answer)
                            .font(.body)
                            .fixedSize(horizontal: false, vertical: true)
                    }

                    if let evidenceText = trimmedEvidenceText {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("원문")
                                .font(.headline)
                            Text(evidenceText)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    Text(userQuestion.createdAt)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .padding(24)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("질문")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    SheetDismissIconButton(accessibilityLabel: "질문 닫기") {
                        dismiss()
                    }
                }
            }
        }
    }

    private var trimmedEvidenceText: String? {
        guard let evidenceText = userQuestion.evidenceText else {
            return nil
        }

        let normalizedEvidenceText = evidenceText.trimmingCharacters(in: .whitespacesAndNewlines)
        return normalizedEvidenceText.isEmpty ? nil : normalizedEvidenceText
    }
}

struct StudyRecordSection<Content: View>: View {
    let title: String
    let count: Int
    let content: Content

    init(title: String, count: Int, @ViewBuilder content: () -> Content) {
        self.title = title
        self.count = count
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text(title)
                    .font(.headline)
                Text("\(count)")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
            }

            LazyVStack(alignment: .leading, spacing: 10) {
                content
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct StudyRecordGlossaryTermCard: View {
    let glossaryTerm: BackendGlossaryTerm

    var body: some View {
        StudyRecordCard {
            metadataRow(left: glossaryTerm.term, right: glossaryTerm.createdAt)
            bodySection(title: "정의", text: glossaryTerm.definition)

            if let sourceText = nonBlank(glossaryTerm.sourceText) {
                bodySection(title: "원문", text: sourceText, lineLimit: 4)
            }

        }
    }
}

struct StudyRecordUserQuestionCard: View {
    let userQuestion: BackendUserQuestion

    var body: some View {
        StudyRecordCard {
            metadataRow(left: "질문 기록", right: userQuestion.createdAt)
            bodySection(title: "내 질문", text: userQuestion.question)
            bodySection(title: "답변", text: userQuestion.answer, lineLimit: 4)

            if let evidenceText = nonBlank(userQuestion.evidenceText) {
                bodySection(title: "원문", text: evidenceText, lineLimit: 4)
            }

        }
    }
}

struct StudyRecordCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            content
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
        .overlay {
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
    }
}

func metadataRow(left: String, right: String) -> some View {
    HStack(alignment: .firstTextBaseline, spacing: 8) {
        Text(left)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.secondary)
            .fixedSize(horizontal: false, vertical: true)

        Spacer(minLength: 8)

        Text(right)
            .font(.caption2)
            .foregroundStyle(.tertiary)
            .lineLimit(1)
    }
}

func bodySection(title: String, text: String, lineLimit: Int? = nil) -> some View {
    VStack(alignment: .leading, spacing: 4) {
        Text(title)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.secondary)
        Text(text)
            .font(.subheadline)
            .lineLimit(lineLimit)
            .fixedSize(horizontal: false, vertical: true)
    }
}

private func nonBlank(_ text: String?) -> String? {
    guard let text else {
        return nil
    }

    let normalizedText = trimmed(text)
    return normalizedText.isEmpty ? nil : normalizedText
}

private func trimmed(_ text: String) -> String {
    text.trimmingCharacters(in: .whitespacesAndNewlines)
}

struct QuizStudySheet: View {
    let quizzes: [BackendQuiz]
    let onSaveAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    @Environment(\.dismiss) private var dismiss
    @State private var answersByQuizID: [Int: String] = [:]
    @State private var revealedQuizIDs: Set<Int> = []
    @State private var saveStatesByQuizID: [Int: QuizAttemptSaveState] = [:]
    @State private var failedSaveKindsByQuizID: [Int: QuizAttemptSaveKind] = [:]
    @State private var savedSelfCheckKindsByQuizID: [Int: Set<QuizAttemptSaveKind>] = [:]

    var body: some View {
        NavigationStack {
            ScrollView {
                if quizzes.isEmpty {
                    VStack(spacing: 10) {
                        Image(systemName: "questionmark.square.dashed")
                            .font(.system(size: 36, weight: .light))
                            .foregroundStyle(.secondary)
                        Text("생성된 퀴즈가 없습니다.")
                            .font(.headline)
                        Text("선택한 문장에서 퀴즈를 먼저 생성한 뒤 공부 모드를 열 수 있습니다.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(40)
                } else {
                    LazyVStack(alignment: .leading, spacing: 14) {
                        ForEach(quizzes, id: \.id) { quiz in
                            QuizStudyCard(
                                quiz: quiz,
                                answer: answerBinding(for: quiz),
                                isRevealed: Binding(
                                    get: { revealedQuizIDs.contains(quiz.id) },
                                    set: { isRevealed in
                                        if isRevealed {
                                            revealedQuizIDs.insert(quiz.id)
                                        } else {
                                            revealedQuizIDs.remove(quiz.id)
                                        }
                                    }
                                ),
                                saveState: saveStatesByQuizID[quiz.id, default: .idle],
                                failedSaveKind: failedSaveKindsByQuizID[quiz.id],
                                savedSelfCheckKinds: savedSelfCheckKindsByQuizID[quiz.id, default: []],
                                onSave: {
                                    saveAttempt(for: quiz, isCorrect: nil, kind: .answerOnly)
                                },
                                onSaveSelfCheck: { isCorrect, kind in
                                    saveAttempt(for: quiz, isCorrect: isCorrect, kind: kind)
                                }
                            )
                        }
                    }
                    .padding(24)
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("퀴즈 공부")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    SheetDismissIconButton(accessibilityLabel: "퀴즈 공부 닫기") {
                        dismiss()
                    }
                }
            }
        }
    }

    private func answerBinding(for quiz: BackendQuiz) -> Binding<String> {
        Binding(
            get: { answersByQuizID[quiz.id, default: ""] },
            set: { newValue in
                answersByQuizID[quiz.id] = newValue

                switch saveStatesByQuizID[quiz.id, default: .idle] {
                case .saved, .failed:
                    saveStatesByQuizID[quiz.id] = .idle
                    failedSaveKindsByQuizID[quiz.id] = nil
                    savedSelfCheckKindsByQuizID[quiz.id] = []
                case .idle, .saving:
                    break
                }
            }
        )
    }

    private func saveAttempt(for quiz: BackendQuiz, isCorrect: Bool?, kind: QuizAttemptSaveKind) {
        let normalizedAnswer = answersByQuizID[quiz.id, default: ""]
            .trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedAnswer.isEmpty else {
            saveStatesByQuizID[quiz.id] = .failed("답안을 입력한 뒤 저장할 수 있습니다.")
            failedSaveKindsByQuizID[quiz.id] = kind
            return
        }

        saveStatesByQuizID[quiz.id] = .saving

        Task { @MainActor in
            do {
                let attempt = try await onSaveAttempt(quiz.id, normalizedAnswer, isCorrect)
                saveStatesByQuizID[quiz.id] = .saved(attempt, kind)
                failedSaveKindsByQuizID[quiz.id] = nil
                if kind == .correct || kind == .reviewAgain {
                    savedSelfCheckKindsByQuizID[quiz.id, default: []].insert(kind)
                }
            } catch {
                saveStatesByQuizID[quiz.id] = .failed(error.localizedDescription)
                failedSaveKindsByQuizID[quiz.id] = kind
            }
        }
    }
}

struct ReviewAgainQuizAttemptsSheet: View {
    let documentID: Int
    let documentTitle: String
    let onLoad: (Int) async throws -> [BackendReviewAgainQuizAttempt]
    let onDeleteAttempt: (Int) async throws -> Void
    let onSaveAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    @Environment(\.dismiss) private var dismiss
    @State private var state: ReviewAgainLoadState = .idle
    @State private var activeReplaySheet: ReviewAgainReplaySnapshot?
    @State private var deletingAttemptIDs: Set<Int> = []
    @State private var removalErrorsByAttemptID: [Int: String] = [:]
    @State private var removalNotice: String?

    var body: some View {
        NavigationStack {
            content
                .background(Color(.systemGroupedBackground))
                .navigationTitle("다시 보기 목록")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        SheetDismissIconButton(accessibilityLabel: "다시 보기 목록 닫기") {
                            dismiss()
                        }
                    }
                }
        }
        .sheet(item: $activeReplaySheet) { snapshot in
            ReviewAgainReplaySheet(
                item: snapshot.item,
                onSaveAttempt: onSaveAttempt
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
        case .loaded(let attempts):
            if attempts.isEmpty {
                emptyState
            } else {
                attemptsList(attempts)
            }
        case .failed(let message):
            failedState(message: message)
        }
    }

    private var loadingState: some View {
        VStack(spacing: 12) {
            ProgressView()
            Text("다시 볼 퀴즈를 불러오는 중입니다.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "arrow.counterclockwise.circle")
                .font(.system(size: 36, weight: .light))
                .foregroundStyle(.secondary)
            Text("다시 볼 퀴즈가 없습니다.")
                .font(.headline)
            Text("공부 모드에서 답을 확인한 뒤 다시 보기를 누르면 여기에 표시됩니다.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 360)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }

    private func failedState(message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 36, weight: .light))
                .foregroundStyle(.orange)
            Text("다시 보기 목록을 불러오지 못했습니다.")
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

    private func attemptsList(_ attempts: [BackendReviewAgainQuizAttempt]) -> some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 14) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(documentTitle)
                        .font(.headline)
                        .fixedSize(horizontal: false, vertical: true)
                    Text("\(attempts.count)개 다시 보기")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 4)

                if let removalNotice {
                    Label(removalNotice, systemImage: "checkmark.circle.fill")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }

                ForEach(attempts, id: \.attemptID) { attempt in
                    ReviewAgainQuizAttemptCard(
                        attempt: attempt,
                        isDeleting: deletingAttemptIDs.contains(attempt.attemptID),
                        removalError: removalErrorsByAttemptID[attempt.attemptID],
                        onReplay: {
                            activeReplaySheet = ReviewAgainReplaySnapshot(
                                item: ReviewAgainReplayItem(attempt: attempt)
                            )
                        },
                        onDelete: {
                            deleteAttempt(attempt)
                        }
                    )
                }
            }
            .padding(24)
        }
    }

    private func deleteAttempt(_ attempt: BackendReviewAgainQuizAttempt) {
        let attemptID = attempt.attemptID
        guard !deletingAttemptIDs.contains(attemptID) else {
            return
        }

        deletingAttemptIDs.insert(attemptID)
        removalErrorsByAttemptID[attemptID] = nil
        removalNotice = nil

        Task { @MainActor in
            defer {
                deletingAttemptIDs.remove(attemptID)
            }

            do {
                try await onDeleteAttempt(attemptID)
                removeAttemptFromLoadedState(attemptID: attemptID)
                await reloadLoadedAttemptsSilently()
            } catch BackendAPIError.quizAttemptAlreadyRemoved {
                removalNotice = "이미 다시 보기 목록에서 제거된 항목입니다."
                removeAttemptFromLoadedState(attemptID: attemptID)
                await reloadLoadedAttemptsSilently()
            } catch BackendAPIError.quizAttemptHasReviewCards {
                removalErrorsByAttemptID[attemptID] = "복습 카드가 연결되어 있어 제거할 수 없습니다."
            } catch {
                removalErrorsByAttemptID[attemptID] = "다시 보기 목록에서 제거하지 못했습니다."
            }
        }
    }

    private func removeAttemptFromLoadedState(attemptID: Int) {
        guard case .loaded(let attempts) = state else {
            return
        }

        state = .loaded(attempts.filter { $0.attemptID != attemptID })
    }

    private func reloadLoadedAttemptsSilently() async {
        do {
            let attempts = try await onLoad(documentID)
            state = .loaded(attempts)
        } catch {
            // Keep the locally updated list; the next sheet open will fetch backend truth again.
        }
    }

    private func load() async {
        state = .loading

        do {
            let attempts = try await onLoad(documentID)
            state = .loaded(attempts)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }
}

private enum ReviewAgainLoadState: Equatable {
    case idle
    case loading
    case loaded([BackendReviewAgainQuizAttempt])
    case failed(String)
}

private struct ReviewAgainReplaySnapshot: Identifiable {
    let id = UUID()
    let item: ReviewAgainReplayItem
}

struct ReviewAgainReplayItem {
    let quizID: Int
    let quizType: String
    let question: String
    let answer: String
    let explanation: String
    let sourceText: String
    let pageNumber: Int
    let previousUserAnswer: String

    init(attempt: BackendReviewAgainQuizAttempt) {
        quizID = attempt.quizID
        quizType = attempt.quizType
        question = attempt.question
        answer = attempt.answer
        explanation = attempt.explanation
        sourceText = attempt.sourceText
        pageNumber = attempt.pageNumber
        previousUserAnswer = attempt.userAnswer
    }

    init(attempt: BackendQuizAttempt, quiz: BackendQuiz, pageNumber: Int) {
        quizID = attempt.quizID
        quizType = quiz.quizType
        question = quiz.question
        answer = quiz.answer
        explanation = quiz.explanation
        sourceText = quiz.sourceText
        self.pageNumber = pageNumber
        previousUserAnswer = attempt.userAnswer
    }
}

private struct ReviewAgainQuizAttemptCard: View {
    let attempt: BackendReviewAgainQuizAttempt
    let isDeleting: Bool
    let removalError: String?
    let onReplay: () -> Void
    let onDelete: () -> Void
    @State private var isConfirmingRemoval = false

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            titleBlock

            bodySection(title: "내 답안", text: attempt.userAnswer)
            bodySection(title: "정답", text: attempt.answer)
            bodySection(title: "해설", text: attempt.explanation)

            if let sourceText = trimmedSourceText {
                sourceSection(text: sourceText)
            }

            actionStack
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.tertiarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 10))
        .overlay {
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
        .confirmationDialog(
            "이 풀이 기록을 다시 보기 목록에서 제거할까요?",
            isPresented: $isConfirmingRemoval,
            titleVisibility: .visible
        ) {
            Button("다시 보기에서 제거", role: .destructive, action: onDelete)
            Button("취소", role: .cancel) {}
        } message: {
            Text("제거하면 이 항목은 다시 보기 목록과 퀴즈 풀이 기록에서 빠집니다.")
        }
    }

    private var actionStack: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                Button(action: onReplay) {
                    Label("다시 풀기", systemImage: "pencil")
                }
                .buttonStyle(.borderedProminent)
                .disabled(isDeleting)

                Button(role: .destructive) {
                    isConfirmingRemoval = true
                } label: {
                    Image(systemName: "trash")
                }
                .buttonStyle(.bordered)
                .disabled(isDeleting)
                .accessibilityLabel("다시 보기에서 제거")

                if isDeleting {
                    ProgressView()
                        .controlSize(.small)
                }
            }

            if let removalError {
                Label(removalError, systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.red)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var titleBlock: some View {
        VStack(alignment: .leading, spacing: 10) {
            metadataRow

            Text(attempt.question)
                .font(.headline)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.systemBackground), in: RoundedRectangle(cornerRadius: 12))
    }

    private var metadataRow: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Text(displayTitle(for: attempt.quizType))
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)

            Text("p. \(attempt.pageNumber)")
                .font(.caption)
                .foregroundStyle(.secondary)

            Spacer(minLength: 8)

            Text(attempt.attemptedAt)
                .font(.caption2)
                .foregroundStyle(.tertiary)
                .lineLimit(1)
        }
    }

    private func bodySection(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(text)
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private func sourceSection(text: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("원문")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(text)
                .font(.caption)
                .foregroundStyle(.secondary)
                .lineLimit(4)
        }
    }

    private var trimmedSourceText: String? {
        let trimmedText = attempt.sourceText.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmedText.isEmpty ? nil : trimmedText
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

struct ReviewAgainReplaySheet: View {
    let item: ReviewAgainReplayItem
    let onSaveAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    @Environment(\.dismiss) private var dismiss
    @State private var answer = ""
    @State private var isRevealed = false
    @State private var saveState: QuizAttemptSaveState = .idle
    @State private var savedSelfCheckKinds: Set<QuizAttemptSaveKind> = []

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    titleBlock
                    previousAnswerBlock
                    answerInputBlock
                    actionRow

                    if isRevealed {
                        revealedAnswerBlock
                    }
                }
                .padding(24)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("다시 풀기")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    SheetDismissIconButton(accessibilityLabel: "다시 풀기 닫기") {
                        dismiss()
                    }
                }
            }
        }
        .onChange(of: answer) { _ in
            switch saveState {
            case .saved, .failed:
                saveState = .idle
                savedSelfCheckKinds = []
            case .idle, .saving:
                break
            }
        }
    }

    private var titleBlock: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(displayTitle(for: item.quizType))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                Text("p. \(item.pageNumber)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text(item.question)
                .font(.headline)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
        .overlay {
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
    }

    private var previousAnswerBlock: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("이전 답안")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(item.previousUserAnswer)
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var answerInputBlock: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("새 답안")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)

            TextEditor(text: $answer)
                .frame(minHeight: 120)
                .padding(8)
                .scrollContentBackground(.hidden)
                .background(Color(.systemBackground), in: RoundedRectangle(cornerRadius: 8))
                .overlay {
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color(.separator), lineWidth: 0.5)
                }
        }
    }

    private var actionRow: some View {
        HStack(spacing: 10) {
            Button {
                isRevealed.toggle()
            } label: {
                Label(isRevealed ? "답 숨기기" : "답 보기", systemImage: isRevealed ? "eye.slash" : "eye")
            }
            .buttonStyle(.bordered)

            if case .saving = saveState {
                ProgressView()
                    .controlSize(.small)
            }
        }
    }

    @ViewBuilder
    private var saveStatusView: some View {
        switch saveState {
        case .idle, .saving:
            EmptyView()
        case .saved(let attempt, let kind):
            Label(savedMessage(for: attempt, kind: kind), systemImage: "checkmark.circle.fill")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.green)
        case .failed(let message):
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .font(.caption)
                .foregroundStyle(.red)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var revealedAnswerBlock: some View {
        VStack(alignment: .leading, spacing: 10) {
            answerBlock(title: "정답", text: item.answer)
            answerBlock(title: "해설", text: item.explanation)

            if let sourceText = trimmedSourceText {
                answerBlock(title: "원문", text: sourceText)
            }

            HStack(spacing: 10) {
                Button {
                    saveAttempt(isCorrect: true, kind: .correct)
                } label: {
                    Label("맞음", systemImage: "checkmark.circle")
                }
                .buttonStyle(.borderedProminent)
                .disabled(isSelfCheckDisabled(.correct))

                Button {
                    saveAttempt(isCorrect: false, kind: .reviewAgain)
                } label: {
                    Label("다시 보기", systemImage: "arrow.counterclockwise")
                }
                .buttonStyle(.bordered)
                .disabled(isSelfCheckDisabled(.reviewAgain))
            }

            saveStatusView
        }
        .transition(.opacity)
    }

    private func answerBlock(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(text)
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var trimmedSourceText: String? {
        let trimmedText = item.sourceText.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmedText.isEmpty ? nil : trimmedText
    }

    private func isSelfCheckDisabled(_ kind: QuizAttemptSaveKind) -> Bool {
        if case .saving = saveState {
            return true
        }

        return savedSelfCheckKinds.contains(kind)
    }

    private func saveAttempt(isCorrect: Bool, kind: QuizAttemptSaveKind) {
        let normalizedAnswer = answer.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedAnswer.isEmpty else {
            saveState = .failed("답안을 입력한 뒤 저장할 수 있습니다.")
            return
        }

        saveState = .saving

        Task { @MainActor in
            do {
                let savedAttempt = try await onSaveAttempt(item.quizID, normalizedAnswer, isCorrect)
                saveState = .saved(savedAttempt, kind)
                savedSelfCheckKinds.insert(kind)
            } catch {
                saveState = .failed(error.localizedDescription)
            }
        }
    }

    private func savedMessage(for _: BackendQuizAttempt, kind: QuizAttemptSaveKind) -> String {
        switch kind {
        case .answerOnly:
            return "저장됨"
        case .correct:
            return "맞음으로 저장됨"
        case .reviewAgain:
            return "다시 보기로 저장됨"
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

private enum QuizAttemptSaveKind: Hashable {
    case answerOnly
    case correct
    case reviewAgain
}

private enum QuizAttemptSaveState: Equatable {
    case idle
    case saving
    case saved(BackendQuizAttempt, QuizAttemptSaveKind)
    case failed(String)
}

private struct QuizStudyCard: View {
    let quiz: BackendQuiz
    @Binding var answer: String
    @Binding var isRevealed: Bool
    let saveState: QuizAttemptSaveState
    let failedSaveKind: QuizAttemptSaveKind?
    let savedSelfCheckKinds: Set<QuizAttemptSaveKind>
    let onSave: () -> Void
    let onSaveSelfCheck: (Bool, QuizAttemptSaveKind) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(displayTitle(for: quiz.quizType))
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)

            Text(quiz.question)
                .font(.headline)
                .fixedSize(horizontal: false, vertical: true)

            VStack(alignment: .leading, spacing: 6) {
                Text("내 답안")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                TextEditor(text: $answer)
                    .frame(minHeight: 96)
                    .padding(8)
                    .scrollContentBackground(.hidden)
                    .background(Color(.systemBackground), in: RoundedRectangle(cornerRadius: 8))
                    .overlay {
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color(.separator), lineWidth: 0.5)
                    }
            }

            HStack(spacing: 10) {
                Button(action: onSave) {
                    Label("답안 저장", systemImage: "tray.and.arrow.down")
                }
                .buttonStyle(.bordered)
                .disabled(isAnswerSaveDisabled)

                Button {
                    isRevealed.toggle()
                } label: {
                    Label(isRevealed ? "답 숨기기" : "답 보기", systemImage: isRevealed ? "eye.slash" : "eye")
                }
                .buttonStyle(.bordered)

                if case .saving = saveState {
                    ProgressView()
                        .controlSize(.small)
                }
            }

            answerSaveStatusView

            if isRevealed {
                VStack(alignment: .leading, spacing: 10) {
                    answerBlock(title: "정답", text: quiz.answer)
                    answerBlock(title: "해설", text: quiz.explanation)
                    answerBlock(title: "원문", text: quiz.sourceText)

                    HStack(spacing: 10) {
                        Button {
                            onSaveSelfCheck(true, .correct)
                        } label: {
                            Label("맞음", systemImage: "checkmark.circle")
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(isSelfCheckDisabled(.correct))

                        Button {
                            onSaveSelfCheck(false, .reviewAgain)
                        } label: {
                            Label("다시 보기", systemImage: "arrow.counterclockwise")
                        }
                        .buttonStyle(.bordered)
                        .disabled(isSelfCheckDisabled(.reviewAgain))
                    }

                    selfCheckStatusView
                }
                .transition(.opacity)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
        .overlay {
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
    }

    private func answerBlock(title: String, text: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
            Text(text)
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    @ViewBuilder
    private var answerSaveStatusView: some View {
        switch saveState {
        case .idle, .saving:
            EmptyView()
        case .saved(let attempt, let kind):
            if kind == .answerOnly {
                Label(savedMessage(for: attempt, kind: kind), systemImage: "checkmark.circle.fill")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.green)
            }
        case .failed(let message):
            if failedSaveKind == .answerOnly {
                failedStatusLabel(message)
            }
        }
    }

    @ViewBuilder
    private var selfCheckStatusView: some View {
        switch saveState {
        case .idle, .saving:
            EmptyView()
        case .saved(let attempt, let kind):
            if kind == .correct || kind == .reviewAgain {
                Label(savedMessage(for: attempt, kind: kind), systemImage: "checkmark.circle.fill")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.green)
            }
        case .failed(let message):
            if failedSaveKind == .correct || failedSaveKind == .reviewAgain {
                failedStatusLabel(message)
            }
        }
    }

    private func failedStatusLabel(_ message: String) -> some View {
        Label(message, systemImage: "exclamationmark.triangle.fill")
            .font(.caption)
            .foregroundStyle(.red)
            .fixedSize(horizontal: false, vertical: true)
    }

    private var isAnswerSaveDisabled: Bool {
        if isBaseSaveDisabled {
            return true
        }

        if case .saved = saveState {
            return true
        }

        return false
    }

    private func isSelfCheckDisabled(_ kind: QuizAttemptSaveKind) -> Bool {
        if isBaseSaveDisabled {
            return true
        }

        return savedSelfCheckKinds.contains(kind)
    }

    private var isBaseSaveDisabled: Bool {
        if case .saving = saveState {
            return true
        }

        return answer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private func savedMessage(for _: BackendQuizAttempt, kind: QuizAttemptSaveKind) -> String {
        switch kind {
        case .answerOnly:
            return "저장됨"
        case .correct:
            return "맞음으로 저장됨"
        case .reviewAgain:
            return "다시 보기로 저장됨"
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
