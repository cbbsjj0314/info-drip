import SwiftUI

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

                    Text("\(explanation.provider) · \(explanation.model)")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                .padding(24)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("쉽게 설명")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("닫기") {
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
                                        Text("근거")
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.secondary)
                                        Text(sourceText)
                                            .font(.subheadline)
                                            .foregroundStyle(.secondary)
                                            .fixedSize(horizontal: false, vertical: true)
                                    }
                                }

                                Text("\(glossaryTerm.provider) · \(glossaryTerm.model)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
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
                    Button("닫기") {
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
                            Text("근거")
                                .font(.headline)
                            Text(evidenceText)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("\(userQuestion.provider) · \(userQuestion.model)")
                        Text(userQuestion.createdAt)
                    }
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
                    Button("닫기") {
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

struct DocumentStudyRecordSheet: View {
    let documentID: Int
    let documentTitle: String
    let onLoad: (Int) async throws -> BackendDocumentStudyRecord
    @Environment(\.dismiss) private var dismiss
    @State private var state: StudyRecordLoadState = .idle
    @State private var selectedFilter: StudyRecordFilter = .all

    var body: some View {
        NavigationStack {
            content
                .background(Color(.systemGroupedBackground))
                .navigationTitle("학습 기록")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("닫기") {
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
            Text("학습 기록을 불러오는 중입니다.")
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
            Text("학습 기록을 불러오지 못했습니다.")
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
                countSummary(record)
                filterControl

                if isEmpty(record) {
                    emptyState
                } else if isEmpty(record, for: selectedFilter) {
                    filteredEmptyState
                } else {
                    studyRecordSections(record, filter: selectedFilter)
                }
            }
            .padding(24)
        }
    }

    private func documentHeader(_ document: BackendDocument) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(document.title)
                .font(.headline)
                .fixedSize(horizontal: false, vertical: true)

            Text("\(document.pageCount) pages · #\(document.id)")
                .font(.caption)
                .foregroundStyle(.secondary)

            Text(document.originalFilename)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .lineLimit(2)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func countSummary(_ record: BackendDocumentStudyRecord) -> some View {
        let metrics = [
            ("하이라이트", record.highlights.count),
            ("설명", record.explanations.count),
            ("용어", record.glossaryTerms.count),
            ("질문", record.userQuestions.count),
            ("퀴즈", record.quizzes.count),
            ("풀이", record.quizAttempts.count),
        ]

        return LazyVGrid(columns: [GridItem(.adaptive(minimum: 110), spacing: 10)], spacing: 10) {
            ForEach(metrics, id: \.0) { metric in
                VStack(alignment: .leading, spacing: 4) {
                    Text(metric.0)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Text("\(metric.1)")
                        .font(.title3.weight(.semibold))
                }
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 8))
            }
        }
    }

    @ViewBuilder
    private var filterControl: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(StudyRecordFilter.allCases) { filter in
                    Button {
                        selectedFilter = filter
                    } label: {
                        Text(filter.title)
                            .font(.caption.weight(.semibold))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .foregroundStyle(selectedFilter == filter ? Color.white : Color.primary)
                            .background(
                                selectedFilter == filter
                                ? Color.accentColor
                                : Color(.secondarySystemGroupedBackground),
                                in: Capsule()
                            )
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.vertical, 2)
        }
    }

    @ViewBuilder
    private var emptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "tray")
                .font(.system(size: 36, weight: .light))
                .foregroundStyle(.secondary)
            Text("아직 저장된 학습 기록이 없습니다.")
                .font(.headline)
            Text("문장을 선택해 하이라이트, 설명, 용어, 질문, 퀴즈를 저장하면 여기에 표시됩니다.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 36)
    }

    @ViewBuilder
    private var filteredEmptyState: some View {
        VStack(spacing: 10) {
            Image(systemName: "line.3.horizontal.decrease.circle")
                .font(.system(size: 32, weight: .light))
                .foregroundStyle(.secondary)
            Text("표시할 학습 기록이 없습니다.")
                .font(.headline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 32)
    }

    @ViewBuilder
    private func studyRecordSections(_ record: BackendDocumentStudyRecord, filter: StudyRecordFilter) -> some View {
        switch filter {
        case .all:
            allStudyRecordSections(record)
        case .highlights:
            highlightSection(record.highlights)
        case .explanations:
            explanationSection(record.explanations)
        case .glossary:
            glossarySection(record.glossaryTerms)
        case .questions:
            questionSection(record.userQuestions)
        case .quizzes:
            quizSection(record.quizzes)
        case .wrongAnswers:
            quizAttemptSection(wrongQuizAttempts(in: record), title: "오답")
        }
    }

    @ViewBuilder
    private func allStudyRecordSections(_ record: BackendDocumentStudyRecord) -> some View {
        highlightSection(record.highlights)
        explanationSection(record.explanations)
        glossarySection(record.glossaryTerms)
        questionSection(record.userQuestions)
        quizSection(record.quizzes)
        quizAttemptSection(record.quizAttempts, title: "풀이 기록")
    }

    @ViewBuilder
    private func highlightSection(_ highlights: [BackendHighlight]) -> some View {
        if !highlights.isEmpty {
            StudyRecordSection(title: "하이라이트", count: highlights.count) {
                ForEach(highlights, id: \.id) { highlight in
                    StudyRecordHighlightCard(highlight: highlight)
                }
            }
        }
    }

    @ViewBuilder
    private func explanationSection(_ explanations: [BackendStudyRecordExplanation]) -> some View {
        if !explanations.isEmpty {
            StudyRecordSection(title: "설명", count: explanations.count) {
                ForEach(explanations, id: \.id) { explanation in
                    StudyRecordExplanationCard(explanation: explanation)
                }
            }
        }
    }

    @ViewBuilder
    private func glossarySection(_ glossaryTerms: [BackendGlossaryTerm]) -> some View {
        if !glossaryTerms.isEmpty {
            StudyRecordSection(title: "용어", count: glossaryTerms.count) {
                ForEach(glossaryTerms, id: \.id) { glossaryTerm in
                    StudyRecordGlossaryTermCard(glossaryTerm: glossaryTerm)
                }
            }
        }
    }

    @ViewBuilder
    private func questionSection(_ userQuestions: [BackendUserQuestion]) -> some View {
        if !userQuestions.isEmpty {
            StudyRecordSection(title: "질문", count: userQuestions.count) {
                ForEach(userQuestions, id: \.id) { userQuestion in
                    StudyRecordUserQuestionCard(userQuestion: userQuestion)
                }
            }
        }
    }

    @ViewBuilder
    private func quizSection(_ quizzes: [BackendQuiz]) -> some View {
        if !quizzes.isEmpty {
            StudyRecordSection(title: "퀴즈", count: quizzes.count) {
                ForEach(quizzes, id: \.id) { quiz in
                    StudyRecordQuizCard(quiz: quiz)
                }
            }
        }
    }

    @ViewBuilder
    private func quizAttemptSection(_ quizAttempts: [BackendQuizAttempt], title: String) -> some View {
        if !quizAttempts.isEmpty {
            StudyRecordSection(title: title, count: quizAttempts.count) {
                ForEach(quizAttempts, id: \.id) { attempt in
                    StudyRecordQuizAttemptCard(attempt: attempt)
                }
            }
        }
    }

    private func isEmpty(_ record: BackendDocumentStudyRecord) -> Bool {
        record.highlights.isEmpty
            && record.explanations.isEmpty
            && record.glossaryTerms.isEmpty
            && record.userQuestions.isEmpty
            && record.quizzes.isEmpty
            && record.quizAttempts.isEmpty
    }

    private func isEmpty(_ record: BackendDocumentStudyRecord, for filter: StudyRecordFilter) -> Bool {
        switch filter {
        case .all:
            return isEmpty(record)
        case .highlights:
            return record.highlights.isEmpty
        case .explanations:
            return record.explanations.isEmpty
        case .glossary:
            return record.glossaryTerms.isEmpty
        case .questions:
            return record.userQuestions.isEmpty
        case .quizzes:
            return record.quizzes.isEmpty
        case .wrongAnswers:
            return wrongQuizAttempts(in: record).isEmpty
        }
    }

    private func wrongQuizAttempts(in record: BackendDocumentStudyRecord) -> [BackendQuizAttempt] {
        record.quizAttempts.filter { $0.isCorrect == .some(false) }
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

private enum StudyRecordFilter: String, CaseIterable, Identifiable {
    case all
    case highlights
    case explanations
    case glossary
    case questions
    case quizzes
    case wrongAnswers

    var id: Self { self }

    var title: String {
        switch self {
        case .all:
            return "전체"
        case .highlights:
            return "하이라이트"
        case .explanations:
            return "설명"
        case .glossary:
            return "용어"
        case .questions:
            return "질문"
        case .quizzes:
            return "퀴즈"
        case .wrongAnswers:
            return "오답"
        }
    }
}

private enum StudyRecordLoadState: Equatable {
    case idle
    case loading
    case loaded(BackendDocumentStudyRecord)
    case failed(String)
}

private struct StudyRecordSection<Content: View>: View {
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

private struct StudyRecordHighlightCard: View {
    let highlight: BackendHighlight

    var body: some View {
        StudyRecordCard {
            metadataRow(left: "p. \(highlight.pageNumber)", right: highlight.createdAt)
            Text(highlight.selectedText)
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct StudyRecordExplanationCard: View {
    let explanation: BackendStudyRecordExplanation

    var body: some View {
        StudyRecordCard {
            metadataRow(left: "#\(explanation.id) · highlight #\(explanation.highlightID)", right: explanation.createdAt)

            Text(explanation.summary)
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)

            let keyPoints = explanation.keyPoints
                .map(trimmed)
                .filter { !$0.isEmpty }
            if !keyPoints.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Text("핵심 포인트")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    ForEach(keyPoints.prefix(3), id: \.self) { point in
                        Text("• \(point)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
            }

            Text("\(explanation.provider) · \(explanation.model)")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }
}

private struct StudyRecordGlossaryTermCard: View {
    let glossaryTerm: BackendGlossaryTerm

    var body: some View {
        StudyRecordCard {
            metadataRow(left: glossaryTerm.term, right: glossaryTerm.createdAt)
            bodySection(title: "정의", text: glossaryTerm.definition)

            if let sourceText = nonBlank(glossaryTerm.sourceText) {
                bodySection(title: "근거", text: sourceText, lineLimit: 4)
            }

            Text("\(glossaryTerm.provider) · \(glossaryTerm.model)")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }
}

private struct StudyRecordUserQuestionCard: View {
    let userQuestion: BackendUserQuestion

    var body: some View {
        StudyRecordCard {
            metadataRow(left: "#\(userQuestion.id) · highlight #\(userQuestion.highlightID)", right: userQuestion.createdAt)
            bodySection(title: "질문", text: userQuestion.question)
            bodySection(title: "답변", text: userQuestion.answer, lineLimit: 4)

            if let evidenceText = nonBlank(userQuestion.evidenceText) {
                bodySection(title: "근거", text: evidenceText, lineLimit: 4)
            }

            Text("\(userQuestion.provider) · \(userQuestion.model)")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }
}

private struct StudyRecordQuizCard: View {
    let quiz: BackendQuiz

    var body: some View {
        StudyRecordCard {
            metadataRow(left: displayTitle(for: quiz.quizType), right: quiz.createdAt)
            bodySection(title: "문제", text: quiz.question)
            bodySection(title: "정답", text: quiz.answer, lineLimit: 3)
            Text("\(quiz.provider) · \(quiz.model)")
                .font(.caption2)
                .foregroundStyle(.secondary)
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

private struct StudyRecordQuizAttemptCard: View {
    let attempt: BackendQuizAttempt

    var body: some View {
        StudyRecordCard {
            metadataRow(left: "quiz #\(attempt.quizID)", right: attempt.createdAt)
            bodySection(title: "내 답안", text: attempt.userAnswer)
            Text(correctnessText)
                .font(.caption.weight(.semibold))
                .foregroundStyle(correctnessColor)

            if let feedback = nonBlank(attempt.feedback) {
                bodySection(title: "피드백", text: feedback, lineLimit: 4)
            }
        }
    }

    private var correctnessText: String {
        switch attempt.isCorrect {
        case .some(true):
            return "맞음"
        case .some(false):
            return "다시 보기"
        case .none:
            return "자가 채점 없음"
        }
    }

    private var correctnessColor: Color {
        switch attempt.isCorrect {
        case .some(true):
            return .green
        case .some(false):
            return .orange
        case .none:
            return .secondary
        }
    }
}

private struct StudyRecordCard<Content: View>: View {
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

private func metadataRow(left: String, right: String) -> some View {
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

private func bodySection(title: String, text: String, lineLimit: Int? = nil) -> some View {
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
                    Button("닫기") {
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
    let onSaveAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    @Environment(\.dismiss) private var dismiss
    @State private var state: ReviewAgainLoadState = .idle
    @State private var activeReplaySheet: ReviewAgainReplaySnapshot?

    var body: some View {
        NavigationStack {
            content
                .background(Color(.systemGroupedBackground))
                .navigationTitle("다시 보기 목록")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("닫기") {
                            dismiss()
                        }
                    }
                }
        }
        .sheet(item: $activeReplaySheet) { snapshot in
            ReviewAgainReplaySheet(
                attempt: snapshot.attempt,
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

                ForEach(attempts, id: \.attemptID) { attempt in
                    ReviewAgainQuizAttemptCard(
                        attempt: attempt,
                        onReplay: {
                            activeReplaySheet = ReviewAgainReplaySnapshot(attempt: attempt)
                        }
                    )
                }
            }
            .padding(24)
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
    let attempt: BackendReviewAgainQuizAttempt
}

private struct ReviewAgainQuizAttemptCard: View {
    let attempt: BackendReviewAgainQuizAttempt
    let onReplay: () -> Void

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
    }

    private var actionStack: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button(action: onReplay) {
                Label("다시 풀기", systemImage: "pencil")
            }
            .buttonStyle(.borderedProminent)
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
            Text("근거")
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

private struct ReviewAgainReplaySheet: View {
    let attempt: BackendReviewAgainQuizAttempt
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
                    Button("닫기") {
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
                Text(displayTitle(for: attempt.quizType))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                Text("p. \(attempt.pageNumber)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text(attempt.question)
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
            Text(attempt.userAnswer)
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
            answerBlock(title: "정답", text: attempt.answer)
            answerBlock(title: "해설", text: attempt.explanation)

            if let sourceText = trimmedSourceText {
                answerBlock(title: "근거", text: sourceText)
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
        let trimmedText = attempt.sourceText.trimmingCharacters(in: .whitespacesAndNewlines)
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
                let savedAttempt = try await onSaveAttempt(attempt.quizID, normalizedAnswer, isCorrect)
                saveState = .saved(savedAttempt, kind)
                savedSelfCheckKinds.insert(kind)
            } catch {
                saveState = .failed(error.localizedDescription)
            }
        }
    }

    private func savedMessage(for attempt: BackendQuizAttempt, kind: QuizAttemptSaveKind) -> String {
        switch kind {
        case .answerOnly:
            return "저장됨 · #\(attempt.id)"
        case .correct:
            return "맞음으로 저장됨 · #\(attempt.id)"
        case .reviewAgain:
            return "다시 보기로 저장됨 · #\(attempt.id)"
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
                    answerBlock(title: "근거", text: quiz.sourceText)

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

    private func savedMessage(for attempt: BackendQuizAttempt, kind: QuizAttemptSaveKind) -> String {
        switch kind {
        case .answerOnly:
            return "저장됨 · #\(attempt.id)"
        case .correct:
            return "맞음으로 저장됨 · #\(attempt.id)"
        case .reviewAgain:
            return "다시 보기로 저장됨 · #\(attempt.id)"
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
