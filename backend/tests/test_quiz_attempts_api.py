from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.main import app


@dataclass(frozen=True)
class QuizContext:
    quiz_id: int
    document_id: int
    document_title: str
    highlight_id: int
    page_number: int
    quiz_type: str
    question: str
    answer: str
    explanation: str
    source_text: str


def build_test_session() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_app_db_session(
    test_session: sessionmaker[Session],
) -> None:
    def override_db_session() -> Generator[Session]:
        with test_session() as session:
            yield session

    app.dependency_overrides[database.get_db_session] = override_db_session


def create_quiz(test_session: sessionmaker[Session]) -> int:
    with test_session() as session:
        document = database.Document(
            title="Sample",
            original_filename="sample.pdf",
            storage_path="documents/sample.pdf",
            page_count=1,
            pages=[
                database.DocumentPage(
                    page_number=1,
                    text="Sanitized sample page text.",
                )
            ],
            highlights=[
                database.Highlight(
                    page_number=1,
                    selected_text="Sanitized selected text.",
                )
            ],
        )
        session.add(document)
        session.flush()

        quiz = database.Quiz(
            document=document,
            highlight=document.highlights[0],
            quiz_type="short_answer",
            question="Sanitized question?",
            answer="Sanitized answer.",
            explanation="Sanitized explanation.",
            source_text="selected text",
            provider="fake-provider",
            model="fake-model",
        )
        session.add(quiz)
        session.commit()
        session.refresh(quiz)
        return quiz.id


def create_quiz_context(
    test_session: sessionmaker[Session],
    *,
    document_title: str = "Sample",
    page_number: int = 1,
    quiz_type: str = "short_answer",
    question: str = "Sanitized question?",
    answer: str = "Sanitized answer.",
    explanation: str = "Sanitized explanation.",
    source_text: str = "selected text",
) -> QuizContext:
    with test_session() as session:
        document = database.Document(
            title=document_title,
            original_filename=f"{document_title.lower().replace(' ', '-')}.pdf",
            storage_path=f"documents/{document_title.lower().replace(' ', '-')}.pdf",
            page_count=page_number,
            pages=[
                database.DocumentPage(
                    page_number=page_number,
                    text="Sanitized sample page text.",
                )
            ],
            highlights=[
                database.Highlight(
                    page_number=page_number,
                    selected_text="Sanitized selected text.",
                )
            ],
        )
        session.add(document)
        session.flush()

        highlight = document.highlights[0]
        quiz = database.Quiz(
            document=document,
            highlight=highlight,
            quiz_type=quiz_type,
            question=question,
            answer=answer,
            explanation=explanation,
            source_text=source_text,
            provider="fake-provider",
            model="fake-model",
        )
        session.add(quiz)
        session.commit()
        session.refresh(document)
        session.refresh(highlight)
        session.refresh(quiz)

        return QuizContext(
            quiz_id=quiz.id,
            document_id=document.id,
            document_title=document.title,
            highlight_id=highlight.id,
            page_number=highlight.page_number,
            quiz_type=quiz.quiz_type,
            question=quiz.question,
            answer=quiz.answer,
            explanation=quiz.explanation,
            source_text=quiz.source_text,
        )


def test_create_quiz_attempt_stores_answer_without_llm_log() -> None:
    test_session = build_test_session()
    quiz_id = create_quiz(test_session)
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            json={
                "user_answer": "Stored user answer.",
                "is_correct": True,
                "feedback": "Marked correct by user.",
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["id"] == 1
        assert payload["quiz_id"] == quiz_id
        assert payload["user_answer"] == "Stored user answer."
        assert payload["is_correct"] is True
        assert payload["feedback"] == "Marked correct by user."
        assert "created_at" in payload

        with test_session() as session:
            attempt = session.scalars(select(database.QuizAttempt)).one()
            assert attempt.quiz_id == quiz_id
            assert attempt.user_answer == "Stored user answer."
            assert attempt.is_correct is True
            assert attempt.feedback == "Marked correct by user."
            assert session.scalars(select(database.LLMRequestLog)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_create_quiz_attempt_trims_user_answer_in_response_and_database() -> None:
    test_session = build_test_session()
    quiz_id = create_quiz(test_session)
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            json={"user_answer": "  Stored user answer.  "},
        )

        assert response.status_code == 201
        assert response.json()["user_answer"] == "Stored user answer."

        with test_session() as session:
            attempt = session.scalars(select(database.QuizAttempt)).one()
            assert attempt.user_answer == "Stored user answer."
    finally:
        app.dependency_overrides.clear()


def test_create_quiz_attempt_rejects_blank_user_answer() -> None:
    test_session = build_test_session()
    quiz_id = create_quiz(test_session)
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            json={"user_answer": "   "},
        )

        assert response.status_code == 422

        with test_session() as session:
            assert session.scalars(select(database.QuizAttempt)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_create_quiz_attempt_trims_non_blank_feedback() -> None:
    test_session = build_test_session()
    quiz_id = create_quiz(test_session)
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            json={
                "user_answer": "Stored user answer.",
                "feedback": "  Marked correct by user.  ",
            },
        )

        assert response.status_code == 201
        assert response.json()["feedback"] == "Marked correct by user."

        with test_session() as session:
            attempt = session.scalars(select(database.QuizAttempt)).one()
            assert attempt.feedback == "Marked correct by user."
    finally:
        app.dependency_overrides.clear()


def test_create_quiz_attempt_normalizes_blank_feedback_to_none() -> None:
    test_session = build_test_session()
    quiz_id = create_quiz(test_session)
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts",
            json={
                "user_answer": "Stored user answer.",
                "feedback": "   ",
            },
        )

        assert response.status_code == 201
        assert response.json()["feedback"] is None

        with test_session() as session:
            attempt = session.scalars(select(database.QuizAttempt)).one()
            assert attempt.feedback is None
    finally:
        app.dependency_overrides.clear()


def test_create_quiz_attempt_rejects_missing_quiz() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/quizzes/404/attempts",
            json={"user_answer": "Stored user answer."},
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Quiz not found."}

        with test_session() as session:
            assert session.scalars(select(database.QuizAttempt)).all() == []
            assert session.scalars(select(database.LLMRequestLog)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_delete_quiz_attempt_removes_attempt_from_history_review_again_and_study_records() -> None:
    test_session = build_test_session()
    quiz = create_quiz_context(test_session)
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        create_response = client.post(
            f"/api/v1/quizzes/{quiz.quiz_id}/attempts",
            json={
                "user_answer": "Review answer.",
                "is_correct": False,
                "feedback": "Needs review.",
            },
        )
        assert create_response.status_code == 201
        attempt_id = create_response.json()["id"]

        review_again_before_delete = client.get("/api/v1/quiz-attempts/review-again")
        assert review_again_before_delete.status_code == 200
        assert [item["attempt_id"] for item in review_again_before_delete.json()] == [
            attempt_id
        ]

        delete_response = client.delete(f"/api/v1/quiz-attempts/{attempt_id}")

        assert delete_response.status_code == 204
        assert delete_response.content == b""

        second_delete_response = client.delete(f"/api/v1/quiz-attempts/{attempt_id}")
        assert second_delete_response.status_code == 404
        assert second_delete_response.json() == {"detail": "Quiz attempt not found."}

        history_response = client.get(f"/api/v1/quizzes/{quiz.quiz_id}/attempts")
        assert history_response.status_code == 200
        assert history_response.json() == []

        review_again_after_delete = client.get("/api/v1/quiz-attempts/review-again")
        assert review_again_after_delete.status_code == 200
        assert review_again_after_delete.json() == []

        study_records_response = client.get(
            f"/api/v1/documents/{quiz.document_id}/study-records"
        )
        assert study_records_response.status_code == 200
        assert study_records_response.json()["quiz_attempts"] == []

        with test_session() as session:
            assert session.get(database.QuizAttempt, attempt_id) is None
            assert session.get(database.Quiz, quiz.quiz_id) is not None
            assert session.get(database.Highlight, quiz.highlight_id) is not None
            assert session.get(database.Document, quiz.document_id) is not None
    finally:
        app.dependency_overrides.clear()


def test_delete_quiz_attempt_rejects_missing_attempt() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.delete("/api/v1/quiz-attempts/404")

        assert response.status_code == 404
        assert response.json() == {"detail": "Quiz attempt not found."}
    finally:
        app.dependency_overrides.clear()


def test_delete_quiz_attempt_rejects_attempt_with_review_cards() -> None:
    test_session = build_test_session()
    quiz = create_quiz_context(test_session)
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)

    with test_session() as session:
        attempt = database.QuizAttempt(
            quiz_id=quiz.quiz_id,
            user_answer="Review answer.",
            is_correct=False,
            feedback="Needs review.",
            created_at=created_at,
        )
        session.add(attempt)
        session.flush()
        review_card = database.ReviewCard(
            document_id=quiz.document_id,
            quiz_id=quiz.quiz_id,
            quiz_attempt_id=attempt.id,
            front="Sanitized front?",
            back="Sanitized back.",
            source_text=None,
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        session.add(review_card)
        session.commit()
        session.refresh(attempt)
        session.refresh(review_card)
        attempt_id = attempt.id
        review_card_id = review_card.id

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.delete(f"/api/v1/quiz-attempts/{attempt_id}")

        assert response.status_code == 409
        assert response.json() == {"detail": "Quiz attempt has review cards."}

        with test_session() as session:
            assert session.get(database.QuizAttempt, attempt_id) is not None
            assert session.get(database.ReviewCard, review_card_id) is not None
    finally:
        app.dependency_overrides.clear()


def test_list_quiz_attempts_keeps_per_quiz_history_created_at_then_id_order() -> None:
    test_session = build_test_session()
    quiz_id = create_quiz(test_session)
    other_quiz_id = create_quiz(test_session)
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)

    with test_session() as session:
        session.add_all(
            [
                database.QuizAttempt(
                    quiz_id=quiz_id,
                    user_answer="First answer.",
                    is_correct=None,
                    feedback=None,
                    created_at=created_at,
                ),
                database.QuizAttempt(
                    quiz_id=quiz_id,
                    user_answer="Second answer.",
                    is_correct=False,
                    feedback="Needs review.",
                    created_at=created_at,
                ),
                database.QuizAttempt(
                    quiz_id=other_quiz_id,
                    user_answer="Other answer.",
                    is_correct=True,
                    feedback=None,
                    created_at=created_at,
                ),
            ]
        )
        session.commit()

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(f"/api/v1/quizzes/{quiz_id}/attempts")

        assert response.status_code == 200
        payload = response.json()
        assert [item["user_answer"] for item in payload] == [
            "First answer.",
            "Second answer.",
        ]
        assert [item["id"] for item in payload] == sorted(item["id"] for item in payload)
        assert {item["quiz_id"] for item in payload} == {quiz_id}
    finally:
        app.dependency_overrides.clear()


def test_list_review_again_quiz_attempts_returns_only_false_attempts() -> None:
    test_session = build_test_session()
    quiz = create_quiz_context(test_session)
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)

    with test_session() as session:
        session.add_all(
            [
                database.QuizAttempt(
                    quiz_id=quiz.quiz_id,
                    user_answer="Correct answer.",
                    is_correct=True,
                    feedback=None,
                    created_at=created_at,
                ),
                database.QuizAttempt(
                    quiz_id=quiz.quiz_id,
                    user_answer="Unscored answer.",
                    is_correct=None,
                    feedback=None,
                    created_at=created_at,
                ),
                database.QuizAttempt(
                    quiz_id=quiz.quiz_id,
                    user_answer="Review again answer.",
                    is_correct=False,
                    feedback="Needs review.",
                    created_at=created_at,
                ),
            ]
        )
        session.commit()

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/quiz-attempts/review-again")

        assert response.status_code == 200
        payload = response.json()
        assert [item["user_answer"] for item in payload] == ["Review again answer."]
        assert [item["is_correct"] for item in payload] == [False]
    finally:
        app.dependency_overrides.clear()


def test_list_review_again_quiz_attempts_includes_flat_quiz_context_fields() -> None:
    test_session = build_test_session()
    quiz = create_quiz_context(
        test_session,
        document_title="Review Document",
        page_number=3,
        quiz_type="fill_blank",
        question="Fill the sanitized blank.",
        answer="Sanitized answer.",
        explanation="Sanitized explanation.",
        source_text="Sanitized source text.",
    )
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)

    with test_session() as session:
        attempt = database.QuizAttempt(
            quiz_id=quiz.quiz_id,
            user_answer="Review answer.",
            is_correct=False,
            feedback="Needs review.",
            created_at=created_at,
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        attempt_id = attempt.id

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/quiz-attempts/review-again")

        assert response.status_code == 200
        payload = response.json()
        assert payload == [
            {
                "attempt_id": attempt_id,
                "quiz_id": quiz.quiz_id,
                "document_id": quiz.document_id,
                "highlight_id": quiz.highlight_id,
                "user_answer": "Review answer.",
                "is_correct": False,
                "feedback": "Needs review.",
                "attempted_at": payload[0]["attempted_at"],
                "quiz_type": quiz.quiz_type,
                "question": quiz.question,
                "answer": quiz.answer,
                "explanation": quiz.explanation,
                "source_text": quiz.source_text,
                "document_title": quiz.document_title,
                "page_number": quiz.page_number,
            }
        ]
        assert "attempted_at" in payload[0]
    finally:
        app.dependency_overrides.clear()


def test_list_review_again_quiz_attempts_returns_newest_first_by_created_at_then_id() -> None:
    test_session = build_test_session()
    quiz = create_quiz_context(test_session)
    older_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)
    newer_at = datetime(2026, 5, 12, 10, 31, tzinfo=UTC)

    with test_session() as session:
        older = database.QuizAttempt(
            quiz_id=quiz.quiz_id,
            user_answer="Older review answer.",
            is_correct=False,
            feedback=None,
            created_at=older_at,
        )
        newer_first_inserted = database.QuizAttempt(
            quiz_id=quiz.quiz_id,
            user_answer="Newer first inserted review answer.",
            is_correct=False,
            feedback=None,
            created_at=newer_at,
        )
        newer_second_inserted = database.QuizAttempt(
            quiz_id=quiz.quiz_id,
            user_answer="Newer second inserted review answer.",
            is_correct=False,
            feedback=None,
            created_at=newer_at,
        )
        session.add_all([older, newer_first_inserted, newer_second_inserted])
        session.commit()
        session.refresh(older)
        session.refresh(newer_first_inserted)
        session.refresh(newer_second_inserted)
        expected_ids = [
            newer_second_inserted.id,
            newer_first_inserted.id,
            older.id,
        ]

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/quiz-attempts/review-again")

        assert response.status_code == 200
        payload = response.json()
        assert [item["attempt_id"] for item in payload] == expected_ids
        assert [item["user_answer"] for item in payload] == [
            "Newer second inserted review answer.",
            "Newer first inserted review answer.",
            "Older review answer.",
        ]
    finally:
        app.dependency_overrides.clear()


def test_list_review_again_quiz_attempts_filters_by_document_id() -> None:
    test_session = build_test_session()
    first_quiz = create_quiz_context(test_session, document_title="First Document")
    second_quiz = create_quiz_context(test_session, document_title="Second Document")
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)

    with test_session() as session:
        session.add_all(
            [
                database.QuizAttempt(
                    quiz_id=first_quiz.quiz_id,
                    user_answer="First document answer.",
                    is_correct=False,
                    feedback=None,
                    created_at=created_at,
                ),
                database.QuizAttempt(
                    quiz_id=second_quiz.quiz_id,
                    user_answer="Second document answer.",
                    is_correct=False,
                    feedback=None,
                    created_at=created_at,
                ),
            ]
        )
        session.commit()

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(
            f"/api/v1/quiz-attempts/review-again?document_id={second_quiz.document_id}"
        )

        assert response.status_code == 200
        payload = response.json()
        assert [item["user_answer"] for item in payload] == [
            "Second document answer."
        ]
        assert {item["document_id"] for item in payload} == {second_quiz.document_id}
    finally:
        app.dependency_overrides.clear()


def test_list_review_again_quiz_attempts_rejects_missing_document_filter() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/quiz-attempts/review-again?document_id=404")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found."}
    finally:
        app.dependency_overrides.clear()


def test_list_review_again_quiz_attempts_does_not_create_llm_request_logs() -> None:
    test_session = build_test_session()
    quiz = create_quiz_context(test_session)
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)

    with test_session() as session:
        session.add(
            database.QuizAttempt(
                quiz_id=quiz.quiz_id,
                user_answer="Review answer.",
                is_correct=False,
                feedback=None,
                created_at=created_at,
            )
        )
        session.commit()

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/quiz-attempts/review-again")

        assert response.status_code == 200
        with test_session() as session:
            assert session.scalars(select(database.LLMRequestLog)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_list_review_again_quiz_attempts_returns_multiple_attempts_for_same_quiz() -> None:
    test_session = build_test_session()
    quiz = create_quiz_context(test_session)
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)

    with test_session() as session:
        session.add_all(
            [
                database.QuizAttempt(
                    quiz_id=quiz.quiz_id,
                    user_answer="First review answer.",
                    is_correct=False,
                    feedback=None,
                    created_at=created_at,
                ),
                database.QuizAttempt(
                    quiz_id=quiz.quiz_id,
                    user_answer="Second review answer.",
                    is_correct=False,
                    feedback=None,
                    created_at=created_at,
                ),
            ]
        )
        session.commit()

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/quiz-attempts/review-again")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 2
        assert {item["quiz_id"] for item in payload} == {quiz.quiz_id}
        assert {item["user_answer"] for item in payload} == {
            "First review answer.",
            "Second review answer.",
        }
    finally:
        app.dependency_overrides.clear()


def test_list_quiz_attempts_rejects_missing_quiz() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/quizzes/404/attempts")

        assert response.status_code == 404
        assert response.json() == {"detail": "Quiz not found."}
    finally:
        app.dependency_overrides.clear()
