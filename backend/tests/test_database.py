from contextlib import suppress
from decimal import Decimal

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app import database


def test_default_database_url_is_local_sqlite(monkeypatch) -> None:
    monkeypatch.delenv(database.DATABASE_URL_ENV_VAR, raising=False)

    assert database.DEFAULT_DATABASE_URL == "sqlite:///./info_drip.db"
    assert database.get_database_url() == database.DEFAULT_DATABASE_URL


def test_database_url_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv(database.DATABASE_URL_ENV_VAR, "sqlite:///:memory:")

    assert database.get_database_url() == "sqlite:///:memory:"


def test_db_session_provider_yields_working_session() -> None:
    session_provider = database.get_db_session()
    session = next(session_provider)

    try:
        assert session.execute(text("select 1")).scalar_one() == 1
    finally:
        with suppress(StopIteration):
            next(session_provider)


def test_document_tables_can_be_created_from_metadata() -> None:
    engine = create_engine("sqlite:///:memory:")

    database.Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= {
        "documents",
        "document_pages",
        "glossary_terms",
        "highlights",
        "llm_explanations",
        "llm_request_logs",
        "quizzes",
        "quiz_attempts",
    }

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    assert document_columns == {
        "id",
        "title",
        "original_filename",
        "storage_path",
        "page_count",
        "created_at",
    }

    page_columns = {column["name"] for column in inspector.get_columns("document_pages")}
    assert page_columns == {
        "id",
        "document_id",
        "page_number",
        "text",
        "created_at",
    }

    page_foreign_keys = inspector.get_foreign_keys("document_pages")
    assert page_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["document_id"],
            "referred_schema": None,
            "referred_table": "documents",
            "referred_columns": ["id"],
            "options": {},
        }
    ]

    highlight_columns = {column["name"] for column in inspector.get_columns("highlights")}
    assert highlight_columns == {
        "id",
        "document_id",
        "page_number",
        "selected_text",
        "created_at",
    }

    highlight_foreign_keys = inspector.get_foreign_keys("highlights")
    assert highlight_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["document_id"],
            "referred_schema": None,
            "referred_table": "documents",
            "referred_columns": ["id"],
            "options": {},
        }
    ]

    llm_explanation_columns = {
        column["name"] for column in inspector.get_columns("llm_explanations")
    }
    assert llm_explanation_columns == {
        "id",
        "document_id",
        "highlight_id",
        "summary",
        "key_points",
        "provider",
        "model",
        "created_at",
    }

    llm_explanation_foreign_keys = sorted(
        inspector.get_foreign_keys("llm_explanations"),
        key=lambda foreign_key: foreign_key["constrained_columns"],
    )
    assert llm_explanation_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["document_id"],
            "referred_schema": None,
            "referred_table": "documents",
            "referred_columns": ["id"],
            "options": {},
        },
        {
            "name": None,
            "constrained_columns": ["highlight_id"],
            "referred_schema": None,
            "referred_table": "highlights",
            "referred_columns": ["id"],
            "options": {},
        },
    ]

    glossary_term_columns = {
        column["name"] for column in inspector.get_columns("glossary_terms")
    }
    assert glossary_term_columns == {
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

    glossary_term_foreign_keys = sorted(
        inspector.get_foreign_keys("glossary_terms"),
        key=lambda foreign_key: foreign_key["constrained_columns"],
    )
    assert glossary_term_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["document_id"],
            "referred_schema": None,
            "referred_table": "documents",
            "referred_columns": ["id"],
            "options": {},
        },
        {
            "name": None,
            "constrained_columns": ["highlight_id"],
            "referred_schema": None,
            "referred_table": "highlights",
            "referred_columns": ["id"],
            "options": {},
        },
    ]

    quiz_columns = {column["name"] for column in inspector.get_columns("quizzes")}
    assert quiz_columns == {
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

    quiz_foreign_keys = sorted(
        inspector.get_foreign_keys("quizzes"),
        key=lambda foreign_key: foreign_key["constrained_columns"],
    )
    assert quiz_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["document_id"],
            "referred_schema": None,
            "referred_table": "documents",
            "referred_columns": ["id"],
            "options": {},
        },
        {
            "name": None,
            "constrained_columns": ["highlight_id"],
            "referred_schema": None,
            "referred_table": "highlights",
            "referred_columns": ["id"],
            "options": {},
        },
    ]

    quiz_attempt_columns = {
        column["name"] for column in inspector.get_columns("quiz_attempts")
    }
    assert quiz_attempt_columns == {
        "id",
        "quiz_id",
        "user_answer",
        "is_correct",
        "feedback",
        "created_at",
    }

    quiz_attempt_foreign_keys = inspector.get_foreign_keys("quiz_attempts")
    assert quiz_attempt_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["quiz_id"],
            "referred_schema": None,
            "referred_table": "quizzes",
            "referred_columns": ["id"],
            "options": {},
        }
    ]

    llm_log_columns = {column["name"] for column in inspector.get_columns("llm_request_logs")}
    assert llm_log_columns == {
        "id",
        "provider",
        "model",
        "task_type",
        "status",
        "latency_ms",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "estimated_cost",
        "document_id",
        "highlight_id",
        "error_message",
        "created_at",
    }

    llm_log_foreign_keys = sorted(
        inspector.get_foreign_keys("llm_request_logs"),
        key=lambda foreign_key: foreign_key["constrained_columns"],
    )
    assert llm_log_foreign_keys == [
        {
            "name": None,
            "constrained_columns": ["document_id"],
            "referred_schema": None,
            "referred_table": "documents",
            "referred_columns": ["id"],
            "options": {},
        },
        {
            "name": None,
            "constrained_columns": ["highlight_id"],
            "referred_schema": None,
            "referred_table": "highlights",
            "referred_columns": ["id"],
            "options": {},
        },
    ]


def test_document_page_relationship_persists_pages() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
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
        )

        session.add(document)
        session.commit()
        session.refresh(document)

        assert document.id is not None
        assert len(document.pages) == 1
        assert document.pages[0].document_id == document.id
        assert document.pages[0].document is document


def test_document_highlight_relationship_persists_highlights() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
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
        session.commit()
        session.refresh(document)

        assert document.id is not None
        assert len(document.highlights) == 1
        assert document.highlights[0].document_id == document.id
        assert document.highlights[0].document is document


def test_llm_explanation_relationship_persists_structured_result() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
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

        highlight = document.highlights[0]
        explanation = database.LLMExplanation(
            document=document,
            highlight=highlight,
            summary="Sanitized explanation summary.",
            key_points='["First point.", "Second point."]',
            provider="fake-provider",
            model="fake-model",
        )

        session.add(explanation)
        session.commit()
        session.refresh(document)
        session.refresh(highlight)

        assert explanation.id is not None
        assert explanation.document_id == document.id
        assert explanation.highlight_id == highlight.id
        assert explanation.document is document
        assert explanation.highlight is highlight
        assert document.llm_explanations == [explanation]
        assert highlight.llm_explanations == [explanation]


def test_glossary_term_relationship_persists_structured_result() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
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

        highlight = document.highlights[0]
        glossary_term = database.GlossaryTerm(
            document=document,
            highlight=highlight,
            term="Sanitized term",
            definition="Sanitized definition.",
            source_text="selected text",
            provider="fake-provider",
            model="fake-model",
        )

        session.add(glossary_term)
        session.commit()
        session.refresh(document)
        session.refresh(highlight)

        assert glossary_term.id is not None
        assert glossary_term.document_id == document.id
        assert glossary_term.highlight_id == highlight.id
        assert glossary_term.document is document
        assert glossary_term.highlight is highlight
        assert document.glossary_terms == [glossary_term]
        assert highlight.glossary_terms == [glossary_term]


def test_quiz_relationship_persists_structured_result() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
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

        highlight = document.highlights[0]
        quiz = database.Quiz(
            document=document,
            highlight=highlight,
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
        session.refresh(document)
        session.refresh(highlight)

        assert quiz.id is not None
        assert quiz.document_id == document.id
        assert quiz.highlight_id == highlight.id
        assert quiz.document is document
        assert quiz.highlight is highlight
        assert document.quizzes == [quiz]
        assert highlight.quizzes == [quiz]


def test_quiz_attempt_relationship_persists_and_cascades_from_quiz() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
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

        highlight = document.highlights[0]
        quiz = database.Quiz(
            document=document,
            highlight=highlight,
            quiz_type="short_answer",
            question="Sanitized question?",
            answer="Sanitized answer.",
            explanation="Sanitized explanation.",
            source_text="selected text",
            provider="fake-provider",
            model="fake-model",
            attempts=[
                database.QuizAttempt(
                    user_answer="Sanitized user answer.",
                    is_correct=None,
                    feedback=None,
                )
            ],
        )

        session.add(quiz)
        session.commit()
        session.refresh(quiz)

        attempt = quiz.attempts[0]
        attempt_id = attempt.id
        assert attempt_id is not None
        assert attempt.quiz_id == quiz.id
        assert attempt.quiz is quiz
        assert attempt.user_answer == "Sanitized user answer."
        assert attempt.is_correct is None
        assert attempt.feedback is None

        session.delete(quiz)
        session.commit()

        assert session.get(database.QuizAttempt, attempt_id) is None


def test_llm_request_log_relationships_persist_success_and_error_logs() -> None:
    engine = create_engine("sqlite:///:memory:")
    database.Base.metadata.create_all(engine)

    with Session(engine) as session:
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

        highlight = document.highlights[0]
        success_log = database.LLMRequestLog(
            provider="fake-provider",
            model="fake-model",
            task_type="explanation",
            status="success",
            latency_ms=123,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            estimated_cost=Decimal("0.000123"),
            document=document,
            highlight=highlight,
        )
        error_log = database.LLMRequestLog(
            provider="fake-provider",
            model="fake-model",
            task_type="explanation",
            status="error",
            latency_ms=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            estimated_cost=None,
            error_message="Sanitized provider error.",
        )

        session.add_all([success_log, error_log])
        session.commit()
        session.refresh(document)
        session.refresh(highlight)

        assert success_log.id is not None
        assert success_log.document_id == document.id
        assert success_log.highlight_id == highlight.id
        assert success_log.document is document
        assert success_log.highlight is highlight
        assert document.llm_request_logs == [success_log]
        assert highlight.llm_request_logs == [success_log]

        assert error_log.id is not None
        assert error_log.document_id is None
        assert error_log.highlight_id is None
        assert error_log.error_message == "Sanitized provider error."
