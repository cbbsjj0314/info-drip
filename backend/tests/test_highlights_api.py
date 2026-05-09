from collections.abc import Generator
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import database
from app.llm import (
    ExplanationContent,
    ExplanationRequest,
    ExplanationResponse,
    LLMUsageMetadata,
)
from app.main import app, get_llm_provider


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


def create_document_with_pages(
    test_session: sessionmaker[Session],
    page_texts: list[str],
) -> int:
    with test_session() as session:
        document = database.Document(
            title="Sample",
            original_filename="sample.pdf",
            storage_path="documents/sample.pdf",
            page_count=len(page_texts),
            pages=[
                database.DocumentPage(page_number=index, text=text)
                for index, text in enumerate(page_texts, start=1)
            ],
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        return document.id


def test_create_highlight_stores_selected_text_for_document_page() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(
        test_session,
        ["First page text.", "Second page text."],
    )
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/highlights",
            json={
                "document_id": document_id,
                "page_number": 2,
                "selected_text": "Sanitized selected text.",
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["id"] == 1
        assert payload["document_id"] == document_id
        assert payload["page_number"] == 2
        assert payload["selected_text"] == "Sanitized selected text."
        assert "created_at" in payload

        with test_session() as session:
            highlight = session.scalars(select(database.Highlight)).one()
            assert highlight.document_id == document_id
            assert highlight.page_number == 2
            assert highlight.selected_text == "Sanitized selected text."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_rejects_missing_document() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/highlights",
            json={
                "document_id": 404,
                "page_number": 1,
                "selected_text": "Sanitized selected text.",
            },
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found."}
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_rejects_missing_page_number() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(test_session, ["Only page text."])
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/highlights",
            json={
                "document_id": document_id,
                "page_number": 2,
                "selected_text": "Sanitized selected text.",
            },
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Document page not found."}
    finally:
        app.dependency_overrides.clear()


def test_list_document_highlights_returns_stable_page_order() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(
        test_session,
        ["First page text.", "Second page text."],
    )
    other_document_id = create_document_with_pages(test_session, ["Other page text."])

    with test_session() as session:
        session.add_all(
            [
                database.Highlight(
                    document_id=document_id,
                    page_number=2,
                    selected_text="Second page selection.",
                ),
                database.Highlight(
                    document_id=document_id,
                    page_number=1,
                    selected_text="First page selection.",
                ),
                database.Highlight(
                    document_id=document_id,
                    page_number=1,
                    selected_text="Second selection on first page.",
                ),
                database.Highlight(
                    document_id=other_document_id,
                    page_number=1,
                    selected_text="Other document selection.",
                ),
            ]
        )
        session.commit()

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(f"/api/v1/documents/{document_id}/highlights")

        assert response.status_code == 200
        payload = response.json()
        assert [
            (item["page_number"], item["selected_text"]) for item in payload
        ] == [
            (1, "First page selection."),
            (1, "Second selection on first page."),
            (2, "Second page selection."),
        ]
        assert {item["document_id"] for item in payload} == {document_id}
        required_keys = {
            "id",
            "document_id",
            "page_number",
            "selected_text",
            "created_at",
        }
        assert all(required_keys <= item.keys() for item in payload)
        assert [(item["page_number"], item["id"]) for item in payload] == sorted(
            (item["page_number"], item["id"]) for item in payload
        )
    finally:
        app.dependency_overrides.clear()


def test_list_document_highlights_returns_empty_list_without_highlights() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(test_session, ["Only page text."])
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get(f"/api/v1/documents/{document_id}/highlights")

        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_document_highlights_rejects_missing_document() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.get("/api/v1/documents/404/highlights")

        assert response.status_code == 404
        assert response.json() == {"detail": "Document not found."}
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_explanation_stores_result_and_success_log() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(test_session, ["Page text."])
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=1,
            selected_text="Sanitized selected text.",
        )
        session.add(highlight)
        session.commit()
        session.refresh(highlight)
        highlight_id = highlight.id

    captured_requests: list[ExplanationRequest] = []

    class CapturingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_explanation(
            self,
            request: ExplanationRequest,
        ) -> ExplanationResponse:
            captured_requests.append(request)
            return ExplanationResponse(
                content=ExplanationContent(
                    summary="Stored fake summary.",
                    key_points=["First point.", "Second point."],
                ),
                usage=LLMUsageMetadata(
                    provider=self.provider,
                    model=self.model,
                    prompt_tokens=3,
                    completion_tokens=5,
                    total_tokens=8,
                    estimated_cost=Decimal("0.000000"),
                ),
            )

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = CapturingProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/explanations")

        assert response.status_code == 201
        payload = response.json()
        assert payload["id"] == 1
        assert payload["highlight_id"] == highlight_id
        assert payload["summary"] == "Stored fake summary."
        assert payload["key_points"] == ["First point.", "Second point."]
        assert payload["provider"] == "fake"
        assert payload["model"] == "fake-explanation-v1"
        assert "created_at" in payload
        assert captured_requests == [
            ExplanationRequest(selected_text="Sanitized selected text.")
        ]

        with test_session() as session:
            explanation = session.scalars(select(database.LLMExplanation)).one()
            assert explanation.document_id == document_id
            assert explanation.highlight_id == highlight_id
            assert explanation.summary == "Stored fake summary."
            assert explanation.key_points == '["First point.", "Second point."]'
            assert explanation.provider == "fake"
            assert explanation.model == "fake-explanation-v1"

            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.document_id == document_id
            assert log.highlight_id == highlight_id
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "explanation"
            assert log.status == "success"
            assert log.latency_ms is not None
            assert log.prompt_tokens == 3
            assert log.completion_tokens == 5
            assert log.total_tokens == 8
            assert log.estimated_cost == Decimal("0.000000")
            assert log.error_message is None
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_explanation_rejects_missing_highlight() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post("/api/v1/highlights/404/explanations")

        assert response.status_code == 404
        assert response.json() == {"detail": "Highlight not found."}

        with test_session() as session:
            assert session.scalars(select(database.LLMRequestLog)).all() == []
            assert session.scalars(select(database.LLMExplanation)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_explanation_logs_provider_failure() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(test_session, ["Page text."])
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=1,
            selected_text="Sanitized selected text.",
        )
        session.add(highlight)
        session.commit()
        session.refresh(highlight)
        highlight_id = highlight.id

    class FailingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
            raise RuntimeError("sanitized provider failure")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = FailingProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/explanations")

        assert response.status_code == 500
        assert response.json() == {"detail": "Explanation generation failed."}

        with test_session() as session:
            assert session.scalars(select(database.LLMExplanation)).all() == []
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.document_id == document_id
            assert log.highlight_id == highlight_id
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "explanation"
            assert log.status == "error"
            assert log.latency_ms is not None
            assert log.prompt_tokens is None
            assert log.completion_tokens is None
            assert log.total_tokens is None
            assert log.estimated_cost is None
            assert log.error_message == "sanitized provider failure"
    finally:
        app.dependency_overrides.clear()
