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

struct QuizStudySheet: View {
    let quizzes: [BackendQuiz]
    let onSaveAttempt: (Int, String, Bool?) async throws -> BackendQuizAttempt
    @Environment(\.dismiss) private var dismiss
    @State private var answersByQuizID: [Int: String] = [:]
    @State private var revealedQuizIDs: Set<Int> = []
    @State private var saveStatesByQuizID: [Int: QuizAttemptSaveState] = [:]

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
            return
        }

        saveStatesByQuizID[quiz.id] = .saving

        Task { @MainActor in
            do {
                let attempt = try await onSaveAttempt(quiz.id, normalizedAnswer, isCorrect)
                saveStatesByQuizID[quiz.id] = .saved(attempt, kind)
            } catch {
                saveStatesByQuizID[quiz.id] = .failed(error.localizedDescription)
            }
        }
    }
}

private enum QuizAttemptSaveKind: Equatable {
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
                .disabled(areSaveControlsDisabled)

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

            saveStatusView

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
                        .disabled(areSaveControlsDisabled)

                        Button {
                            onSaveSelfCheck(false, .reviewAgain)
                        } label: {
                            Label("다시 보기", systemImage: "arrow.counterclockwise")
                        }
                        .buttonStyle(.bordered)
                        .disabled(areSaveControlsDisabled)
                    }
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

    private var areSaveControlsDisabled: Bool {
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
