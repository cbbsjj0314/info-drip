from collections.abc import Generator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.main import app


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


def test_list_quiz_attempts_returns_created_at_then_id_order() -> None:
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
