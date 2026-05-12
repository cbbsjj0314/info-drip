from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.llm import (
    LLMUsageMetadata,
    ReviewCardContent,
    ReviewCardGenerationRequest,
    ReviewCardGenerationResponse,
)
from app.main import app, get_llm_provider

REVIEW_CARD_RESPONSE_KEYS = {
    "id",
    "document_id",
    "quiz_id",
    "quiz_attempt_id",
    "front",
    "back",
    "source_text",
    "provider",
    "model",
    "created_at",
}


@dataclass(frozen=True)
class ReviewCardContext:
    attempt_id: int
    quiz_id: int
    document_id: int
    highlight_id: int


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


def create_review_card_context(
    test_session: sessionmaker[Session],
    *,
    is_correct: bool | None = False,
) -> ReviewCardContext:
    with test_session() as session:
        document = database.Document(
            title="Review Document",
            original_filename="review-document.pdf",
            storage_path="documents/review-document.pdf",
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
            question="What is selected?",
            answer="The selected concept.",
            explanation="The selected passage states the concept.",
            source_text="selected concept",
            provider="fake-provider",
            model="fake-model",
        )
        session.add(quiz)
        session.flush()

        attempt = database.QuizAttempt(
            quiz=quiz,
            user_answer="Wrong answer.",
            is_correct=is_correct,
            feedback="Needs review.",
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)

        return ReviewCardContext(
            attempt_id=attempt.id,
            quiz_id=quiz.id,
            document_id=document.id,
            highlight_id=highlight.id,
        )


def successful_review_card_response(
    request: ReviewCardGenerationRequest,
    *,
    source_text: str | None = "selected concept",
) -> ReviewCardGenerationResponse:
    return ReviewCardGenerationResponse(
        content=ReviewCardContent(
            front=f"Review prompt for: {request.question}",
            back=(
                f"Correct answer: {request.correct_answer}. "
                f"Explanation: {request.quiz_explanation}"
            ),
            source_text=source_text,
        ),
        usage=LLMUsageMetadata(
            provider="fake",
            model="fake-explanation-v1",
            prompt_tokens=10,
            completion_tokens=8,
            total_tokens=18,
            estimated_cost=Decimal("0.000000"),
        ),
    )


def review_card_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(database.ReviewCard)) or 0


def add_review_card(
    test_session: sessionmaker[Session],
    context: ReviewCardContext,
    *,
    front: str,
    back: str,
    created_at: datetime,
    source_text: str | None = "selected concept",
) -> int:
    with test_session() as session:
        review_card = database.ReviewCard(
            document_id=context.document_id,
            quiz_id=context.quiz_id,
            quiz_attempt_id=context.attempt_id,
            front=front,
            back=back,
            source_text=source_text,
            provider="fake-provider",
            model="fake-model",
            created_at=created_at,
        )
        session.add(review_card)
        session.commit()
        session.refresh(review_card)
        return review_card.id


def test_list_review_cards_returns_all_cards_newest_first() -> None:
    test_session = build_test_session()
    first_context = create_review_card_context(test_session)
    second_context = create_review_card_context(test_session)
    older_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)
    newer_at = datetime(2026, 5, 12, 10, 31, tzinfo=UTC)

    older_id = add_review_card(
        test_session,
        first_context,
        front="Older card",
        back="Older answer",
        created_at=older_at,
    )
    newer_first_id = add_review_card(
        test_session,
        first_context,
        front="Newer first inserted card",
        back="Newer first answer",
        created_at=newer_at,
    )
    newer_second_id = add_review_card(
        test_session,
        second_context,
        front="Newer second inserted card",
        back="Newer second answer",
        created_at=newer_at,
    )
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/review-cards")

        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload] == [
            newer_second_id,
            newer_first_id,
            older_id,
        ]
        assert [item["front"] for item in payload] == [
            "Newer second inserted card",
            "Newer first inserted card",
            "Older card",
        ]
        assert all(set(item) == REVIEW_CARD_RESPONSE_KEYS for item in payload)
    finally:
        app.dependency_overrides.clear()


def test_list_review_cards_filters_by_document_id() -> None:
    test_session = build_test_session()
    first_context = create_review_card_context(test_session)
    second_context = create_review_card_context(test_session)
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)
    add_review_card(
        test_session,
        first_context,
        front="First document card",
        back="First document answer",
        created_at=created_at,
    )
    second_card_id = add_review_card(
        test_session,
        second_context,
        front="Second document card",
        back="Second document answer",
        created_at=created_at,
    )
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(
            f"/api/v1/review-cards?document_id={second_context.document_id}"
        )

        assert response.status_code == 200
        payload = response.json()
        assert [item["id"] for item in payload] == [second_card_id]
        assert {item["document_id"] for item in payload} == {second_context.document_id}
        assert payload[0]["front"] == "Second document card"
        assert set(payload[0]) == REVIEW_CARD_RESPONSE_KEYS
    finally:
        app.dependency_overrides.clear()


def test_list_review_cards_rejects_missing_document_filter() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/review-cards?document_id=404")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found."}
    finally:
        app.dependency_overrides.clear()


def test_list_review_cards_returns_empty_list() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/review-cards")

        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_review_cards_returns_flat_response_shape_and_nullable_source_text() -> None:
    test_session = build_test_session()
    context = create_review_card_context(test_session)
    created_at = datetime(2026, 5, 12, 10, 30, tzinfo=UTC)
    review_card_id = add_review_card(
        test_session,
        context,
        front="Nullable source card",
        back="Nullable source answer",
        source_text=None,
        created_at=created_at,
    )
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/review-cards")

        assert response.status_code == 200
        payload = response.json()
        assert payload == [
            {
                "id": review_card_id,
                "document_id": context.document_id,
                "quiz_id": context.quiz_id,
                "quiz_attempt_id": context.attempt_id,
                "front": "Nullable source card",
                "back": "Nullable source answer",
                "source_text": None,
                "provider": "fake-provider",
                "model": "fake-model",
                "created_at": payload[0]["created_at"],
            }
        ]
        assert set(payload[0]) == REVIEW_CARD_RESPONSE_KEYS
    finally:
        app.dependency_overrides.clear()


def test_list_review_cards_does_not_create_llm_request_logs() -> None:
    test_session = build_test_session()
    context = create_review_card_context(test_session)
    add_review_card(
        test_session,
        context,
        front="Log-free card",
        back="Log-free answer",
        created_at=datetime(2026, 5, 12, 10, 30, tzinfo=UTC),
    )
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/review-cards")

        assert response.status_code == 200
        with test_session() as session:
            assert session.scalars(select(database.LLMRequestLog)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_create_review_card_success_stores_card_and_success_log() -> None:
    test_session = build_test_session()
    context = create_review_card_context(test_session)

    class CapturingProvider:
        provider = "fake"
        model = "fake-explanation-v1"
        requests: list[ReviewCardGenerationRequest] = []

        def generate_review_card(
            self,
            request: ReviewCardGenerationRequest,
        ) -> ReviewCardGenerationResponse:
            self.requests.append(request)
            return successful_review_card_response(request)

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = CapturingProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quiz-attempts/{context.attempt_id}/review-cards"
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["document_id"] == context.document_id
        assert payload["quiz_id"] == context.quiz_id
        assert payload["quiz_attempt_id"] == context.attempt_id
        assert payload["front"] == "Review prompt for: What is selected?"
        assert payload["back"] == (
            "Correct answer: The selected concept.. "
            "Explanation: The selected passage states the concept."
        )
        assert payload["source_text"] == "selected concept"
        assert payload["provider"] == "fake"
        assert payload["model"] == "fake-explanation-v1"
        assert "created_at" in payload

        request = CapturingProvider.requests[0]
        assert request.document_title == "Review Document"
        assert request.page_number == 1
        assert request.quiz_type == "short_answer"
        assert request.question == "What is selected?"
        assert request.correct_answer == "The selected concept."
        assert request.user_answer == "Wrong answer."
        assert request.quiz_explanation == "The selected passage states the concept."
        assert request.quiz_source_text == "selected concept"

        with test_session() as session:
            review_card = session.scalars(select(database.ReviewCard)).one()
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert review_card.id == payload["id"]
            assert review_card.document_id == context.document_id
            assert review_card.quiz_id == context.quiz_id
            assert review_card.quiz_attempt_id == context.attempt_id
            assert log.task_type == "review_card_generation"
            assert log.status == "success"
            assert log.document_id == context.document_id
            assert log.highlight_id == context.highlight_id
            assert log.prompt_tokens == 10
            assert log.completion_tokens == 8
            assert log.total_tokens == 18
            assert log.error_message is None
    finally:
        app.dependency_overrides.clear()


def test_review_again_static_route_still_resolves_before_dynamic_route() -> None:
    test_session = build_test_session()
    context = create_review_card_context(test_session)
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/quiz-attempts/review-again")

        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["attempt_id"] == context.attempt_id
        assert payload[0]["is_correct"] is False
    finally:
        app.dependency_overrides.clear()


def test_create_review_card_rejects_missing_attempt() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post("/api/v1/quiz-attempts/404/review-cards")

        assert response.status_code == 404
        assert response.json() == {"detail": "Quiz attempt not found."}
        with test_session() as session:
            assert review_card_count(session) == 0
            assert session.scalars(select(database.LLMRequestLog)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_create_review_card_rejects_attempt_not_marked_for_review_again() -> None:
    for is_correct in (True, None):
        test_session = build_test_session()
        context = create_review_card_context(test_session, is_correct=is_correct)
        override_app_db_session(test_session)

        try:
            client = TestClient(app)

            response = client.post(
                f"/api/v1/quiz-attempts/{context.attempt_id}/review-cards"
            )

            assert response.status_code == 400
            assert response.json() == {
                "detail": "Quiz attempt is not marked for review again."
            }
            with test_session() as session:
                assert review_card_count(session) == 0
                assert session.scalars(select(database.LLMRequestLog)).all() == []
        finally:
            app.dependency_overrides.clear()


def test_create_review_card_missing_related_data_has_no_llm_log() -> None:
    test_session = build_test_session()
    with test_session() as session:
        attempt = database.QuizAttempt(
            quiz_id=404,
            user_answer="Wrong answer.",
            is_correct=False,
            feedback=None,
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        attempt_id = attempt.id

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/quiz-attempts/{attempt_id}/review-cards")

        assert response.status_code == 500
        assert response.json() == {"detail": "Review card generation failed."}
        with test_session() as session:
            assert review_card_count(session) == 0
            assert session.scalars(select(database.LLMRequestLog)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_create_review_card_provider_failure_rolls_back_card_and_logs_error() -> None:
    test_session = build_test_session()
    context = create_review_card_context(test_session)

    class FailingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_review_card(
            self,
            request: ReviewCardGenerationRequest,
        ) -> ReviewCardGenerationResponse:
            raise RuntimeError("private provider failure")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = FailingProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quiz-attempts/{context.attempt_id}/review-cards"
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "Review card generation failed."}
        with test_session() as session:
            assert review_card_count(session) == 0
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "review_card_generation"
            assert log.status == "error"
            assert log.document_id == context.document_id
            assert log.highlight_id == context.highlight_id
            assert log.prompt_tokens is None
            assert log.completion_tokens is None
            assert log.total_tokens is None
            assert log.estimated_cost is None
            assert log.error_message == "Provider request failed."
            assert session.execute(select(1)).scalar_one() == 1
    finally:
        app.dependency_overrides.clear()


def test_create_review_card_invalid_output_rolls_back_card_and_logs_error() -> None:
    test_session = build_test_session()
    context = create_review_card_context(test_session)

    class InvalidOutputProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_review_card(
            self,
            request: ReviewCardGenerationRequest,
        ) -> ReviewCardGenerationResponse:
            ReviewCardContent(front="   ", back="Back.", source_text=None)
            raise AssertionError("validation should have failed")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = InvalidOutputProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quiz-attempts/{context.attempt_id}/review-cards"
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "Review card generation failed."}
        with test_session() as session:
            assert review_card_count(session) == 0
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.task_type == "review_card_generation"
            assert log.status == "error"
            assert log.error_message == "Provider request failed."
            assert session.execute(select(1)).scalar_one() == 1
    finally:
        app.dependency_overrides.clear()


def test_create_review_card_allows_duplicate_cards_for_same_attempt() -> None:
    test_session = build_test_session()
    context = create_review_card_context(test_session)

    class SuccessfulProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_review_card(
            self,
            request: ReviewCardGenerationRequest,
        ) -> ReviewCardGenerationResponse:
            return successful_review_card_response(request)

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = SuccessfulProvider

    try:
        client = TestClient(app)

        first_response = client.post(
            f"/api/v1/quiz-attempts/{context.attempt_id}/review-cards"
        )
        second_response = client.post(
            f"/api/v1/quiz-attempts/{context.attempt_id}/review-cards"
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        assert first_response.json()["id"] != second_response.json()["id"]
        with test_session() as session:
            assert review_card_count(session) == 2
            assert len(session.scalars(select(database.LLMRequestLog)).all()) == 2
    finally:
        app.dependency_overrides.clear()


def test_create_review_card_blank_source_text_becomes_response_null_and_db_null() -> None:
    test_session = build_test_session()
    context = create_review_card_context(test_session)

    class BlankSourceProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_review_card(
            self,
            request: ReviewCardGenerationRequest,
        ) -> ReviewCardGenerationResponse:
            return successful_review_card_response(request, source_text="   ")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = BlankSourceProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/quiz-attempts/{context.attempt_id}/review-cards"
        )

        assert response.status_code == 201
        assert response.json()["source_text"] is None
        with test_session() as session:
            review_card = session.scalars(select(database.ReviewCard)).one()
            assert review_card.source_text is None
    finally:
        app.dependency_overrides.clear()
