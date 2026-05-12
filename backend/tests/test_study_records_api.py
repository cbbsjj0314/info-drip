import json
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.main import app

DOCUMENT_KEYS = {
    "id",
    "title",
    "original_filename",
    "storage_path",
    "page_count",
    "created_at",
}
HIGHLIGHT_KEYS = {
    "id",
    "document_id",
    "page_number",
    "selected_text",
    "created_at",
}
EXPLANATION_KEYS = {
    "id",
    "document_id",
    "highlight_id",
    "summary",
    "key_points",
    "provider",
    "model",
    "created_at",
}
GLOSSARY_TERM_KEYS = {
    "id",
    "document_id",
    "highlight_id",
    "term",
    "definition",
    "source_text",
    "provider",
    "model",
    "created_at",
}
USER_QUESTION_KEYS = {
    "id",
    "document_id",
    "highlight_id",
    "question",
    "answer",
    "evidence_text",
    "provider",
    "model",
    "created_at",
}
QUIZ_KEYS = {
    "id",
    "document_id",
    "highlight_id",
    "quiz_type",
    "question",
    "answer",
    "explanation",
    "source_text",
    "provider",
    "model",
    "created_at",
}
QUIZ_ATTEMPT_KEYS = {
    "id",
    "quiz_id",
    "user_answer",
    "is_correct",
    "feedback",
    "created_at",
}
STUDY_RECORD_KEYS = {
    "document",
    "highlights",
    "explanations",
    "glossary_terms",
    "user_questions",
    "quizzes",
    "quiz_attempts",
}


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


def create_document(
    session: Session,
    *,
    title: str,
    page_count: int = 2,
) -> database.Document:
    document = database.Document(
        title=title,
        original_filename=f"{title.lower().replace(' ', '-')}.pdf",
        storage_path=f"documents/{title.lower().replace(' ', '-')}.pdf",
        page_count=page_count,
        pages=[
            database.DocumentPage(
                page_number=index,
                text=f"{title} page {index} text.",
            )
            for index in range(1, page_count + 1)
        ],
    )
    session.add(document)
    session.flush()
    return document


def add_highlight(
    session: Session,
    document: database.Document,
    *,
    page_number: int,
    selected_text: str,
) -> database.Highlight:
    highlight = database.Highlight(
        document_id=document.id,
        page_number=page_number,
        selected_text=selected_text,
    )
    session.add(highlight)
    session.flush()
    return highlight


def add_quiz(
    session: Session,
    document: database.Document,
    highlight: database.Highlight,
    *,
    question: str,
    created_at: datetime,
) -> database.Quiz:
    quiz = database.Quiz(
        document_id=document.id,
        highlight_id=highlight.id,
        quiz_type="short_answer",
        question=question,
        answer="Stored answer.",
        explanation="Stored quiz explanation.",
        source_text=highlight.selected_text,
        provider="fake-provider",
        model="fake-model",
        created_at=created_at,
    )
    session.add(quiz)
    session.flush()
    return quiz


def table_counts(session: Session) -> dict[str, int]:
    tables = [
        database.Document,
        database.DocumentPage,
        database.Highlight,
        database.LLMExplanation,
        database.GlossaryTerm,
        database.UserQuestion,
        database.Quiz,
        database.QuizAttempt,
        database.ReviewCard,
        database.LLMRequestLog,
    ]
    return {
        table.__tablename__: session.scalar(select(func.count()).select_from(table))
        or 0
        for table in tables
    }


def test_get_document_study_records_rejects_missing_document() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/documents/404/study-records")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found."}
    finally:
        app.dependency_overrides.clear()


def test_get_document_study_records_returns_empty_sections_for_empty_document() -> None:
    test_session = build_test_session()
    with test_session() as session:
        document = create_document(session, title="Empty Document", page_count=1)
        session.commit()
        document_id = document.id

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(f"/api/v1/documents/{document_id}/study-records")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == STUDY_RECORD_KEYS
        assert set(payload["document"]) == DOCUMENT_KEYS
        assert payload["document"]["id"] == document_id
        assert payload["highlights"] == []
        assert payload["explanations"] == []
        assert payload["glossary_terms"] == []
        assert payload["user_questions"] == []
        assert payload["quizzes"] == []
        assert payload["quiz_attempts"] == []
    finally:
        app.dependency_overrides.clear()


def test_get_document_study_records_returns_only_requested_document_records() -> None:
    test_session = build_test_session()
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)
    with test_session() as session:
        document = create_document(session, title="Requested Document")
        other_document = create_document(session, title="Other Document")
        highlight = add_highlight(
            session,
            document,
            page_number=1,
            selected_text="Requested selected text.",
        )
        other_highlight = add_highlight(
            session,
            other_document,
            page_number=1,
            selected_text="Other selected text.",
        )
        explanation = database.LLMExplanation(
            document_id=document.id,
            highlight_id=highlight.id,
            summary="Requested explanation.",
            key_points=json.dumps(["first point", "second point"]),
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        other_explanation = database.LLMExplanation(
            document_id=other_document.id,
            highlight_id=other_highlight.id,
            summary="Other explanation.",
            key_points=json.dumps(["other point"]),
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        glossary_term = database.GlossaryTerm(
            document_id=document.id,
            highlight_id=highlight.id,
            term="Requested term",
            definition="Requested definition.",
            source_text="Requested selected text.",
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        other_glossary_term = database.GlossaryTerm(
            document_id=other_document.id,
            highlight_id=other_highlight.id,
            term="Other term",
            definition="Other definition.",
            source_text="Other selected text.",
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        user_question = database.UserQuestion(
            document_id=document.id,
            highlight_id=highlight.id,
            question="Requested question?",
            answer="Requested answer.",
            evidence_text="Requested selected text.",
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        other_user_question = database.UserQuestion(
            document_id=other_document.id,
            highlight_id=other_highlight.id,
            question="Other question?",
            answer="Other answer.",
            evidence_text="Other selected text.",
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        session.add_all(
            [
                explanation,
                other_explanation,
                glossary_term,
                other_glossary_term,
                user_question,
                other_user_question,
            ]
        )
        session.flush()

        quiz = add_quiz(
            session,
            document,
            highlight,
            question="Requested quiz?",
            created_at=created_at,
        )
        other_quiz = add_quiz(
            session,
            other_document,
            other_highlight,
            question="Other quiz?",
            created_at=created_at,
        )
        attempt = database.QuizAttempt(
            quiz_id=quiz.id,
            user_answer="Requested attempt.",
            is_correct=False,
            feedback="Needs review.",
            created_at=created_at,
        )
        other_attempt = database.QuizAttempt(
            quiz_id=other_quiz.id,
            user_answer="Other attempt.",
            is_correct=True,
            feedback=None,
            created_at=created_at,
        )
        session.add_all([attempt, other_attempt])
        session.flush()

        review_card = database.ReviewCard(
            document_id=document.id,
            quiz_id=quiz.id,
            quiz_attempt_id=attempt.id,
            front="Excluded review card.",
            back="Excluded review answer.",
            source_text="Requested selected text.",
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        llm_log = database.LLMRequestLog(
            provider="fake-provider",
            model="fake-model",
            task_type="explanation",
            status="success",
            latency_ms=1,
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            estimated_cost=Decimal("0.000000"),
            document_id=document.id,
            highlight_id=highlight.id,
            error_message=None,
            created_at=created_at,
        )
        session.add_all([review_card, llm_log])
        session.commit()

        document_id = document.id
        highlight_id = highlight.id
        explanation_id = explanation.id
        glossary_term_id = glossary_term.id
        user_question_id = user_question.id
        quiz_id = quiz.id
        attempt_id = attempt.id

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(f"/api/v1/documents/{document_id}/study-records")

        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == STUDY_RECORD_KEYS
        assert "review_cards" not in payload
        assert "llm_request_logs" not in payload
        assert "document_pages" not in payload

        assert [item["id"] for item in payload["highlights"]] == [highlight_id]
        assert [item["id"] for item in payload["explanations"]] == [explanation_id]
        assert [item["id"] for item in payload["glossary_terms"]] == [
            glossary_term_id
        ]
        assert [item["id"] for item in payload["user_questions"]] == [
            user_question_id
        ]
        assert [item["id"] for item in payload["quizzes"]] == [quiz_id]
        assert [item["id"] for item in payload["quiz_attempts"]] == [attempt_id]

        assert set(payload["highlights"][0]) == HIGHLIGHT_KEYS
        assert set(payload["explanations"][0]) == EXPLANATION_KEYS
        assert set(payload["glossary_terms"][0]) == GLOSSARY_TERM_KEYS
        assert set(payload["user_questions"][0]) == USER_QUESTION_KEYS
        assert set(payload["quizzes"][0]) == QUIZ_KEYS
        assert set(payload["quiz_attempts"][0]) == QUIZ_ATTEMPT_KEYS

        assert payload["explanations"][0]["document_id"] == document_id
        assert payload["explanations"][0]["key_points"] == [
            "first point",
            "second point",
        ]
        assert payload["quiz_attempts"][0]["quiz_id"] == quiz_id
    finally:
        app.dependency_overrides.clear()


def test_get_document_study_records_uses_deterministic_section_order() -> None:
    test_session = build_test_session()
    older_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)
    newer_at = datetime(2026, 5, 12, 10, 31, tzinfo=UTC)
    with test_session() as session:
        document = create_document(session, title="Ordered Document")
        first_page_first = add_highlight(
            session,
            document,
            page_number=1,
            selected_text="First page first highlight.",
        )
        second_page = add_highlight(
            session,
            document,
            page_number=2,
            selected_text="Second page highlight.",
        )
        first_page_second = add_highlight(
            session,
            document,
            page_number=1,
            selected_text="First page second highlight.",
        )
        session.add_all(
            [
                database.LLMExplanation(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    summary="Older explanation.",
                    key_points=json.dumps(["older"]),
                    provider="fake-provider",
                    model="fake-model",
                    created_at=older_at,
                ),
                database.LLMExplanation(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    summary="Newer first explanation.",
                    key_points=json.dumps(["newer first"]),
                    provider="fake-provider",
                    model="fake-model",
                    created_at=newer_at,
                ),
                database.LLMExplanation(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    summary="Newer second explanation.",
                    key_points=json.dumps(["newer second"]),
                    provider="fake-provider",
                    model="fake-model",
                    created_at=newer_at,
                ),
                database.GlossaryTerm(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    term="Older term",
                    definition="Older definition.",
                    source_text=None,
                    provider="fake-provider",
                    model="fake-model",
                    created_at=older_at,
                ),
                database.GlossaryTerm(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    term="Newer first term",
                    definition="Newer first definition.",
                    source_text=None,
                    provider="fake-provider",
                    model="fake-model",
                    created_at=newer_at,
                ),
                database.GlossaryTerm(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    term="Newer second term",
                    definition="Newer second definition.",
                    source_text=None,
                    provider="fake-provider",
                    model="fake-model",
                    created_at=newer_at,
                ),
                database.UserQuestion(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    question="Older question?",
                    answer="Older answer.",
                    evidence_text=None,
                    provider="fake-provider",
                    model="fake-model",
                    created_at=older_at,
                ),
                database.UserQuestion(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    question="Newer first question?",
                    answer="Newer first answer.",
                    evidence_text=None,
                    provider="fake-provider",
                    model="fake-model",
                    created_at=newer_at,
                ),
                database.UserQuestion(
                    document_id=document.id,
                    highlight_id=first_page_first.id,
                    question="Newer second question?",
                    answer="Newer second answer.",
                    evidence_text=None,
                    provider="fake-provider",
                    model="fake-model",
                    created_at=newer_at,
                ),
            ]
        )
        session.flush()
        older_quiz = add_quiz(
            session,
            document,
            first_page_first,
            question="Older quiz?",
            created_at=older_at,
        )
        newer_first_quiz = add_quiz(
            session,
            document,
            first_page_first,
            question="Newer first quiz?",
            created_at=newer_at,
        )
        newer_second_quiz = add_quiz(
            session,
            document,
            first_page_first,
            question="Newer second quiz?",
            created_at=newer_at,
        )
        session.add_all(
            [
                database.QuizAttempt(
                    quiz_id=older_quiz.id,
                    user_answer="Older attempt.",
                    is_correct=True,
                    feedback=None,
                    created_at=older_at,
                ),
                database.QuizAttempt(
                    quiz_id=newer_first_quiz.id,
                    user_answer="Newer first attempt.",
                    is_correct=False,
                    feedback=None,
                    created_at=newer_at,
                ),
                database.QuizAttempt(
                    quiz_id=newer_second_quiz.id,
                    user_answer="Newer second attempt.",
                    is_correct=False,
                    feedback=None,
                    created_at=newer_at,
                ),
            ]
        )
        session.commit()
        document_id = document.id
        expected_highlight_texts = [
            first_page_first.selected_text,
            first_page_second.selected_text,
            second_page.selected_text,
        ]

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(f"/api/v1/documents/{document_id}/study-records")

        assert response.status_code == 200
        payload = response.json()
        assert [
            item["selected_text"] for item in payload["highlights"]
        ] == expected_highlight_texts
        assert [item["summary"] for item in payload["explanations"]] == [
            "Newer second explanation.",
            "Newer first explanation.",
            "Older explanation.",
        ]
        assert [item["term"] for item in payload["glossary_terms"]] == [
            "Newer second term",
            "Newer first term",
            "Older term",
        ]
        assert [item["question"] for item in payload["user_questions"]] == [
            "Newer second question?",
            "Newer first question?",
            "Older question?",
        ]
        assert [item["question"] for item in payload["quizzes"]] == [
            "Newer second quiz?",
            "Newer first quiz?",
            "Older quiz?",
        ]
        assert [item["user_answer"] for item in payload["quiz_attempts"]] == [
            "Newer second attempt.",
            "Newer first attempt.",
            "Older attempt.",
        ]
    finally:
        app.dependency_overrides.clear()


def test_get_document_study_records_does_not_create_or_update_rows() -> None:
    test_session = build_test_session()
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)
    with test_session() as session:
        document = create_document(session, title="Read Only Document")
        highlight = add_highlight(
            session,
            document,
            page_number=1,
            selected_text="Read only selected text.",
        )
        quiz = add_quiz(
            session,
            document,
            highlight,
            question="Read only quiz?",
            created_at=created_at,
        )
        session.add(
            database.QuizAttempt(
                quiz_id=quiz.id,
                user_answer="Read only attempt.",
                is_correct=None,
                feedback=None,
                created_at=created_at,
            )
        )
        session.commit()
        document_id = document.id
        before_counts = table_counts(session)

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(f"/api/v1/documents/{document_id}/study-records")

        assert response.status_code == 200
        with test_session() as session:
            assert table_counts(session) == before_counts
            assert session.scalars(select(database.LLMRequestLog)).all() == []
    finally:
        app.dependency_overrides.clear()
