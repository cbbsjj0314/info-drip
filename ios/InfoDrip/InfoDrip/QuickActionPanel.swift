import SwiftUI

struct QuickActionPanel: View {
    private let loadedResultPreviewMaxHeight: CGFloat = 160
    private let maxPreviewKeyPoints = 2
    private let maxPreviewGlossaryTerms = 2

    let selectedAction: QuickAction?
    let highlightSaveState: HighlightSaveState
    let explanationState: ExplanationState
    let glossaryState: GlossaryState
    let quizState: QuizState
    let questionState: QuestionState
    let highlightAvailabilityMessage: String?
    let canRunQuickAction: Bool
    let onSelect: (QuickAction) -> Void
    let onRequestExplanation: () -> Void
    let onRequestGlossary: () -> Void
    let onRequestQuiz: () -> Void
    let onQuestion: (String) -> Void
    let onStudyQuiz: (Int) -> Void
    let onOpenExplanationDetail: (BackendExplanation) -> Void
    let onOpenGlossaryDetail: ([BackendGlossaryTerm]) -> Void
    let onOpenQuizStudy: ([BackendQuiz]) -> Void
    let onOpenQuestionDetail: (BackendUserQuestion) -> Void
    @State private var questionText = ""
    @State private var submittedQuestionText = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("선택한 문장")
                        .font(.headline)
                    Text(selectedAction.map { "\($0.title) 선택됨" } ?? "학습 활동을 고르세요")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()
            }

            HStack(spacing: 10) {
                ForEach(QuickAction.allCases) { action in
                    Button {
                        onSelect(action)
                    } label: {
                        Label(action.title, systemImage: action.systemImage)
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.large)
                    .disabled(isDisabled(action))
                }
            }

            if let statusMessage {
                Text(statusMessage)
                    .font(.caption)
                    .foregroundStyle(statusColor)
                    .fixedSize(horizontal: false, vertical: true)
            }

            explanationContent
            glossaryContent
            quizContent
            questionContent
        }
        .padding(16)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .strokeBorder(Color(.separator), lineWidth: 0.5)
        }
        .frame(maxWidth: 620)
    }

    private var statusMessage: String? {
        if selectedAction == .explain {
            switch explanationState {
            case .idle:
                return highlightAvailabilityMessage
            case .loading:
                return "설명을 생성하는 중..."
            case .loaded(let explanation):
                return "설명 생성됨 · #\(explanation.id)"
            case .failed(let message):
                return message
            }
        } else if selectedAction == .glossary {
            switch glossaryState {
            case .idle:
                return highlightAvailabilityMessage
            case .loading:
                return "용어를 추출하는 중..."
            case .loaded(let glossaryTerms):
                return "용어 추출됨 · \(glossaryTerms.count)개"
            case .failed(let message):
                return message
            }
        } else if selectedAction == .quiz {
            switch quizState {
            case .idle:
                return highlightAvailabilityMessage
            case .loading:
                return "퀴즈를 생성하는 중..."
            case .loaded(let quizzes):
                return "퀴즈 생성됨 · \(quizzes.count)개"
            case .failed(let message):
                return message
            }
        } else if selectedAction == .question {
            switch questionState {
            case .idle:
                return highlightAvailabilityMessage
            case .loading:
                return "답변을 생성하는 중..."
            case .loaded(let userQuestion):
                if shouldShowQuestionResult(userQuestion) {
                    return "답변 생성됨 · #\(userQuestion.id)"
                }
                return "질문을 수정했습니다. 다시 질문하기를 눌러 새 답변을 생성하세요."
            case .failed(let message):
                return message
            }
        } else {
            switch highlightSaveState {
            case .idle:
                return highlightAvailabilityMessage
            case .saving:
                return "하이라이트 저장 중..."
            case .saved(let highlight):
                return "하이라이트 저장됨 · #\(highlight.id)"
            case .failed(let message):
                return message
            }
        }
    }

    private var statusColor: Color {
        if selectedAction == .explain {
            switch explanationState {
            case .loaded:
                return .green
            case .failed:
                return .red
            case .idle, .loading:
                return .secondary
            }
        }

        if selectedAction == .glossary {
            switch glossaryState {
            case .loaded:
                return .green
            case .failed:
                return .red
            case .idle, .loading:
                return .secondary
            }
        }

        if selectedAction == .quiz {
            switch quizState {
            case .loaded:
                return .green
            case .failed:
                return .red
            case .idle, .loading:
                return .secondary
            }
        }

        if selectedAction == .question {
            switch questionState {
            case .loaded(let userQuestion):
                return shouldShowQuestionResult(userQuestion) ? .green : .secondary
            case .failed:
                return .red
            case .idle, .loading:
                return .secondary
            }
        }

        switch highlightSaveState {
        case .saved:
            return .green
        case .failed:
            return .red
        case .idle, .saving:
            return .secondary
        }
    }

    @ViewBuilder
    private var questionContent: some View {
        if selectedAction == .question {
            VStack(alignment: .leading, spacing: 10) {
                actionPrompt("선택한 문장에 대해 직접 질문합니다.")

                HStack(spacing: 8) {
                    TextField("선택한 문장에 대해 질문하기", text: $questionText)
                        .textFieldStyle(.roundedBorder)
                        .submitLabel(.send)
                        .disabled(isQuestionLoading)
                        .onSubmit {
                            submitQuestion()
                        }

                    Button {
                        submitQuestion()
                    } label: {
                        Label("질문하기", systemImage: "paperplane")
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!canSubmitQuestion)
                }

                switch questionState {
                case .loading:
                    HStack(spacing: 8) {
                        ProgressView()
                            .controlSize(.small)
                        Text("선택한 문장과 질문을 backend에 보내 답변을 생성하고 있습니다.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                case .loaded(let userQuestion):
                    if shouldShowQuestionResult(userQuestion) {
                        VStack(alignment: .leading, spacing: 10) {
                            Button {
                                onOpenQuestionDetail(userQuestion)
                            } label: {
                                Label("자세히 보기", systemImage: "questionmark.bubble")
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.regular)

                            loadedResultPreview {
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(userQuestion.answer)
                                        .font(.subheadline)
                                        .lineLimit(4)
                                        .fixedSize(horizontal: false, vertical: true)

                                    if let evidenceText = trimmedEvidenceText(for: userQuestion) {
                                        VStack(alignment: .leading, spacing: 4) {
                                            Text("근거")
                                                .font(.caption.weight(.semibold))
                                                .foregroundStyle(.secondary)
                                            Text(evidenceText)
                                                .font(.caption)
                                                .foregroundStyle(.secondary)
                                                .lineLimit(2)
                                        }
                                    }
                                }
                            }
                        }
                    }
                case .failed, .idle:
                    EmptyView()
                }
            }
        }
    }

    @ViewBuilder
    private var quizContent: some View {
        if selectedAction == .quiz {
            VStack(alignment: .leading, spacing: 10) {
                switch quizState {
                case .loading:
                    HStack(spacing: 8) {
                        ProgressView()
                            .controlSize(.small)
                        Text("선택한 문장을 backend에서 퀴즈로 바꾸고 있습니다.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                case .loaded(let quizzes):
                    quizActionRow(quizzes: quizzes)

                    if quizzes.isEmpty {
                        Text("생성된 퀴즈가 없습니다.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    } else {
                        loadedResultPreview {
                            VStack(alignment: .leading, spacing: 10) {
                                ForEach(quizzes, id: \.id) { quiz in
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text(displayTitle(for: quiz.quizType))
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.secondary)

                                        Text(quiz.question)
                                            .font(.subheadline.weight(.semibold))
                                            .fixedSize(horizontal: false, vertical: true)
                                    }
                                    .padding(12)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(Color(.systemBackground), in: RoundedRectangle(cornerRadius: 8))
                                }
                            }
                        }
                    }
                case .failed, .idle:
                    actionPrompt("선택한 문장을 바탕으로 퀴즈를 생성합니다.")
                    quizActionRow(quizzes: [])
                }
            }
        }
    }

    @ViewBuilder
    private func quizActionRow(quizzes: [BackendQuiz]) -> some View {
        HStack(spacing: 8) {
            if !quizzes.isEmpty {
                Button {
                    onOpenQuizStudy(quizzes)
                } label: {
                    Label("퀴즈 풀기", systemImage: "rectangle.stack.badge.play")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.regular)
            } else {
                Button {
                    onRequestQuiz()
                } label: {
                    Label("퀴즈 생성", systemImage: "sparkles")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.regular)
                .disabled(!canRunQuickAction)
            }

            studyQuizMenu
        }
    }

    private var studyQuizMenu: some View {
        Menu {
            ForEach([4, 6, 10], id: \.self) { count in
                Button("\(count)문제") {
                    onStudyQuiz(count)
                }
            }
        } label: {
            Label("문제 수", systemImage: "list.number")
        }
        .buttonStyle(.bordered)
        .controlSize(.regular)
        .disabled(!canRunQuickAction)
    }

    @ViewBuilder
    private var explanationContent: some View {
        if selectedAction == .explain {
            switch explanationState {
            case .loading:
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("선택한 문장을 backend에서 설명으로 바꾸고 있습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            case .loaded(let explanation):
                if hasExplanationDetail(explanation) {
                    VStack(alignment: .leading, spacing: 10) {
                        Button {
                            onOpenExplanationDetail(explanation)
                        } label: {
                            Label("자세히 보기", systemImage: "doc.text.magnifyingglass")
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.regular)

                        loadedResultPreview {
                            VStack(alignment: .leading, spacing: 8) {
                                let trimmedSummary = trimmed(explanation.summary)
                                if !trimmedSummary.isEmpty {
                                    Text(trimmedSummary)
                                        .font(.subheadline)
                                        .lineLimit(3)
                                }

                                let previewKeyPoints = nonBlankKeyPoints(for: explanation).prefix(maxPreviewKeyPoints)
                                if !previewKeyPoints.isEmpty {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text("핵심 포인트")
                                            .font(.caption.weight(.semibold))
                                            .foregroundStyle(.secondary)

                                        ForEach(Array(previewKeyPoints), id: \.self) { point in
                                            HStack(alignment: .firstTextBaseline, spacing: 6) {
                                                Image(systemName: "checkmark.circle.fill")
                                                    .font(.caption)
                                                    .foregroundStyle(.green)
                                                Text(point)
                                                    .font(.caption)
                                                    .lineLimit(1)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                } else {
                    Text("생성된 설명이 비어 있습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            case .failed, .idle:
                VStack(alignment: .leading, spacing: 10) {
                    actionPrompt("선택한 문장을 한국어로 풀어 설명하고 핵심 포인트를 생성합니다.")

                    Button {
                        onRequestExplanation()
                    } label: {
                        Label("AI에게 설명 요청", systemImage: "sparkles")
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.regular)
                    .disabled(!canRunQuickAction)
                }
            }
        }
    }

    @ViewBuilder
    private var glossaryContent: some View {
        if selectedAction == .glossary {
            switch glossaryState {
            case .loading:
                HStack(spacing: 8) {
                    ProgressView()
                        .controlSize(.small)
                    Text("선택한 문장에서 학습 용어를 추출하고 있습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            case .loaded(let glossaryTerms):
                if glossaryTerms.isEmpty {
                    Text("추출된 용어가 없습니다.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } else {
                    VStack(alignment: .leading, spacing: 10) {
                        Button {
                            onOpenGlossaryDetail(glossaryTerms)
                        } label: {
                            Label("자세히 보기", systemImage: "text.book.closed")
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.regular)

                        loadedResultPreview {
                            VStack(alignment: .leading, spacing: 10) {
                                ForEach(Array(glossaryTerms.prefix(maxPreviewGlossaryTerms)), id: \.id) { glossaryTerm in
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(glossaryTerm.term)
                                            .font(.subheadline.weight(.semibold))
                                            .lineLimit(1)
                                        Text(glossaryTerm.definition)
                                            .font(.caption)
                                            .lineLimit(2)
                                    }

                                    if glossaryTerm.id != glossaryTerms.prefix(maxPreviewGlossaryTerms).last?.id {
                                        Divider()
                                    }
                                }
                            }
                        }
                    }
                }
            case .failed, .idle:
                VStack(alignment: .leading, spacing: 10) {
                    actionPrompt("선택한 문장에서 학습할 만한 용어와 정의를 추출합니다.")

                    Button {
                        onRequestGlossary()
                    } label: {
                        Label("AI에게 용어 추출 요청", systemImage: "sparkles")
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.regular)
                    .disabled(!canRunQuickAction)
                }
            }
        }
    }

    private func isDisabled(_ action: QuickAction) -> Bool {
        switch action {
        case .highlight, .explain, .glossary, .quiz, .question:
            return !canRunQuickAction
        }
    }

    private var canSubmitQuestion: Bool {
        canRunQuickAction && !trimmed(questionText).isEmpty
    }

    private var isQuestionLoading: Bool {
        if case .loading = questionState {
            return true
        }

        return false
    }

    private func submitQuestion() {
        let normalizedQuestion = trimmed(questionText)
        guard !normalizedQuestion.isEmpty, canRunQuickAction else {
            return
        }

        submittedQuestionText = normalizedQuestion
        onQuestion(normalizedQuestion)
    }

    private func shouldShowQuestionResult(_ userQuestion: BackendUserQuestion) -> Bool {
        trimmed(questionText) == trimmed(userQuestion.question)
            && submittedQuestionText == trimmed(userQuestion.question)
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

    private func hasExplanationDetail(_ explanation: BackendExplanation) -> Bool {
        !trimmed(explanation.summary).isEmpty || !nonBlankKeyPoints(for: explanation).isEmpty
    }

    private func nonBlankKeyPoints(for explanation: BackendExplanation) -> [String] {
        explanation.keyPoints
            .map(trimmed)
            .filter { !$0.isEmpty }
    }

    private func trimmed(_ text: String) -> String {
        text.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func trimmedEvidenceText(for userQuestion: BackendUserQuestion) -> String? {
        guard let evidenceText = userQuestion.evidenceText else {
            return nil
        }

        let normalizedEvidenceText = trimmed(evidenceText)
        return normalizedEvidenceText.isEmpty ? nil : normalizedEvidenceText
    }

    private func actionPrompt(_ message: String) -> some View {
        Text(message)
            .font(.caption)
            .foregroundStyle(.secondary)
            .fixedSize(horizontal: false, vertical: true)
    }

    private func loadedResultPreview<Content: View>(
        @ViewBuilder content: () -> Content
    ) -> some View {
        content()
            .modifier(LoadedResultPreviewModifier(maxHeight: loadedResultPreviewMaxHeight))
    }
}

private struct LoadedResultPreviewModifier: ViewModifier {
    let maxHeight: CGFloat

    func body(content: Content) -> some View {
        ScrollView {
            content
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .frame(maxHeight: maxHeight, alignment: .top)
        .padding(12)
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 8))
    }
}

enum QuickAction: String, CaseIterable, Identifiable {
    case highlight
    case explain
    case glossary
    case quiz
    case question

    var id: String {
        rawValue
    }

    var title: String {
        switch self {
        case .highlight:
            return "하이라이트"
        case .explain:
            return "설명"
        case .glossary:
            return "용어"
        case .quiz:
            return "퀴즈"
        case .question:
            return "질문"
        }
    }

    var systemImage: String {
        switch self {
        case .highlight:
            return "highlighter"
        case .explain:
            return "lightbulb"
        case .glossary:
            return "text.book.closed"
        case .quiz:
            return "questionmark.circle"
        case .question:
            return "questionmark.bubble"
        }
    }
}
