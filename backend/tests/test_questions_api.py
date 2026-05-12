from collections.abc import Generator
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.llm import (
    LLMUsageMetadata,
    QuestionAnswerContent,
    QuestionAnswerRequest,
    QuestionAnswerResponse,
)
from app.main import PAGE_CONTEXT_MAX_CHARS, app, get_llm_provider

QUESTION_RESPONSE_KEYS = {
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


def create_document_with_highlight(
    test_session: sessionmaker[Session],
    page_texts: list[str],
    *,
    title: str = "Question Sample",
    page_number: int = 1,
    selected_text: str = "Sanitized selected text.",
) -> tuple[int, int]:
    with test_session() as session:
        document = database.Document(
            title=title,
            original_filename="question-sample.pdf",
            storage_path="documents/question-sample.pdf",
            page_count=len(page_texts),
            pages=[
                database.DocumentPage(page_number=index, text=text)
                for index, text in enumerate(page_texts, start=1)
            ],
            highlights=[
                database.Highlight(
                    page_number=page_number,
                    selected_text=selected_text,
                )
            ],
        )
        session.add(document)
        session.commit()
        highlight = document.highlights[0]
        return document.id, highlight.id


def user_question_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(database.UserQuestion)) or 0


def llm_log_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(database.LLMRequestLog)) or 0


def successful_question_response(
    request: QuestionAnswerRequest,
    *,
    evidence_text: str | None = "selected text",
) -> QuestionAnswerResponse:
    return QuestionAnswerResponse(
        content=QuestionAnswerContent(
            answer=f"Answer for: {request.question}",
            evidence_text=evidence_text,
            document_based=True,
            needs_more_context=False,
        ),
        usage=LLMUsageMetadata(
            provider="fake",
            model="fake-explanation-v1",
            prompt_tokens=7,
            completion_tokens=9,
            total_tokens=16,
            estimated_cost=Decimal("0.000000"),
        ),
    )


def test_create_highlight_question_stores_answer_and_success_log() -> None:
    test_session = build_test_session()
    document_id, highlight_id = create_document_with_highlight(
        test_session,
        ["Other page text.", "Same page context for selected text."],
        title="Learning Sample",
        page_number=2,
    )

    captured_requests: list[QuestionAnswerRequest] = []

    class CapturingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def answer_question(
            self,
            request: QuestionAnswerRequest,
        ) -> QuestionAnswerResponse:
            captured_requests.append(request)
            return successful_question_response(request)

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = CapturingProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/highlights/{highlight_id}/questions",
            json={"question": "  What does this mean?  "},
        )

        assert response.status_code == 201
        payload = response.json()
        assert set(payload) == QUESTION_RESPONSE_KEYS
        assert payload["document_id"] == document_id
        assert payload["highlight_id"] == highlight_id
        assert payload["question"] == "What does this mean?"
        assert payload["answer"] == "Answer for: What does this mean?"
        assert payload["evidence_text"] == "selected text"
        assert payload["provider"] == "fake"
        assert payload["model"] == "fake-explanation-v1"
        assert "created_at" in payload

        assert captured_requests == [
            QuestionAnswerRequest(
                selected_text="Sanitized selected text.",
                question="What does this mean?",
                surrounding_context="Same page context for selected text.",
                document_title="Learning Sample",
            )
        ]

        with test_session() as session:
            user_question = session.scalars(select(database.UserQuestion)).one()
            assert user_question.id == payload["id"]
            assert user_question.document_id == document_id
            assert user_question.highlight_id == highlight_id
            assert user_question.question == "What does this mean?"
            assert user_question.answer == "Answer for: What does this mean?"
            assert user_question.evidence_text == "selected text"
            assert user_question.provider == "fake"
            assert user_question.model == "fake-explanation-v1"
            assert user_question.document.id == document_id
            assert user_question.highlight.id == highlight_id

            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.document_id == document_id
            assert log.highlight_id == highlight_id
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "question_answering"
            assert log.status == "success"
            assert log.latency_ms is not None
            assert log.prompt_tokens == 7
            assert log.completion_tokens == 9
            assert log.total_tokens == 16
            assert log.estimated_cost == Decimal("0.000000")
            assert log.error_message is None
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_question_blank_question_rejects_without_log() -> None:
    test_session = build_test_session()
    _, highlight_id = create_document_with_highlight(test_session, ["Page text."])
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/highlights/{highlight_id}/questions",
            json={"question": "   "},
        )

        assert response.status_code == 422
        with test_session() as session:
            assert user_question_count(session) == 0
            assert llm_log_count(session) == 0
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_question_rejects_missing_highlight_without_log() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/highlights/404/questions",
            json={"question": "What does this mean?"},
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Highlight not found."}
        with test_session() as session:
            assert user_question_count(session) == 0
            assert llm_log_count(session) == 0
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_question_provider_failure_logs_error_only() -> None:
    test_session = build_test_session()
    document_id, highlight_id = create_document_with_highlight(
        test_session,
        ["Page text."],
    )

    class FailingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def answer_question(
            self,
            request: QuestionAnswerRequest,
        ) -> QuestionAnswerResponse:
            raise RuntimeError("private provider failure")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = FailingProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/highlights/{highlight_id}/questions",
            json={"question": "What does this mean?"},
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "Question answering failed."}
        with test_session() as session:
            assert user_question_count(session) == 0
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.document_id == document_id
            assert log.highlight_id == highlight_id
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "question_answering"
            assert log.status == "error"
            assert log.latency_ms is not None
            assert log.prompt_tokens is None
            assert log.completion_tokens is None
            assert log.total_tokens is None
            assert log.estimated_cost is None
            assert log.error_message == "Provider request failed."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_question_invalid_provider_output_logs_error_only() -> None:
    test_session = build_test_session()
    _, highlight_id = create_document_with_highlight(
        test_session,
        ["Page text."],
    )

    class InvalidOutputProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def answer_question(
            self,
            request: QuestionAnswerRequest,
        ) -> QuestionAnswerResponse:
            QuestionAnswerContent(
                answer="   ",
                evidence_text="phrase",
                document_based=True,
                needs_more_context=False,
            )
            raise AssertionError("validation should have failed")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = InvalidOutputProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/highlights/{highlight_id}/questions",
            json={"question": "What does this mean?"},
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "Question answering failed."}
        with test_session() as session:
            assert user_question_count(session) == 0
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.task_type == "question_answering"
            assert log.status == "error"
            assert log.error_message == "Provider request failed."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_question_caps_context_and_excludes_other_pages() -> None:
    test_session = build_test_session()
    long_context = "A" * (PAGE_CONTEXT_MAX_CHARS + 200)
    _, highlight_id = create_document_with_highlight(
        test_session,
        ["Other page context must not be sent.", long_context],
        title="Long Context Sample",
        page_number=2,
        selected_text="Selected text.",
    )
    captured_requests: list[QuestionAnswerRequest] = []

    class CapturingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def answer_question(
            self,
            request: QuestionAnswerRequest,
        ) -> QuestionAnswerResponse:
            captured_requests.append(request)
            return successful_question_response(request, evidence_text="Selected text")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = CapturingProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/highlights/{highlight_id}/questions",
            json={"question": "What does this mean?"},
        )

        assert response.status_code == 201
        assert captured_requests == [
            QuestionAnswerRequest(
                selected_text="Selected text.",
                question="What does this mean?",
                surrounding_context="A" * PAGE_CONTEXT_MAX_CHARS,
                document_title="Long Context Sample",
            )
        ]
        assert "Other page context" not in captured_requests[0].surrounding_context
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_question_blank_evidence_text_becomes_null() -> None:
    test_session = build_test_session()
    _, highlight_id = create_document_with_highlight(test_session, ["Page text."])

    class BlankEvidenceProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def answer_question(
            self,
            request: QuestionAnswerRequest,
        ) -> QuestionAnswerResponse:
            return successful_question_response(request, evidence_text="   ")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = BlankEvidenceProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/highlights/{highlight_id}/questions",
            json={"question": "What does this mean?"},
        )

        assert response.status_code == 201
        assert response.json()["evidence_text"] is None
        with test_session() as session:
            user_question = session.scalars(select(database.UserQuestion)).one()
            assert user_question.evidence_text is None
    finally:
        app.dependency_overrides.clear()
