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
    GlossaryExtractionContent,
    GlossaryExtractionRequest,
    GlossaryExtractionResponse,
    LLMUsageMetadata,
    QuizGenerationContent,
    QuizGenerationRequest,
    QuizGenerationResponse,
)
from app.main import PAGE_CONTEXT_MAX_CHARS, app, get_llm_provider


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
    *,
    title: str = "Sample",
) -> int:
    with test_session() as session:
        document = database.Document(
            title=title,
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
    document_id = create_document_with_pages(
        test_session,
        ["First page text.", "Same page context for selected text."],
        title="Learning Sample",
    )
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=2,
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
            ExplanationRequest(
                selected_text="Sanitized selected text.",
                surrounding_context="Same page context for selected text.",
                document_title="Learning Sample",
            )
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


def test_create_highlight_explanation_caps_page_context_before_provider_call() -> None:
    test_session = build_test_session()
    long_context = "A" * (PAGE_CONTEXT_MAX_CHARS + 200)
    document_id = create_document_with_pages(
        test_session,
        ["Other page context.", long_context],
        title="Long Context Sample",
    )
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=2,
            selected_text="Selected text.",
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
                    key_points=["Point."],
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
        assert captured_requests == [
            ExplanationRequest(
                selected_text="Selected text.",
                surrounding_context="A" * PAGE_CONTEXT_MAX_CHARS,
                document_title="Long Context Sample",
            )
        ]
        assert "Other page context." not in captured_requests[0].surrounding_context
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_explanation_handles_missing_page_context() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(
        test_session,
        ["Existing page context."],
        title="Missing Page Sample",
    )
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=2,
            selected_text="Selected text.",
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
                    key_points=["Point."],
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
        assert captured_requests == [
            ExplanationRequest(
                selected_text="Selected text.",
                surrounding_context=None,
                document_title="Missing Page Sample",
            )
        ]
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
            raise RuntimeError

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
            assert log.error_message == "Provider request failed."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_glossary_terms_stores_result_and_success_log() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(
        test_session,
        ["First page text.", "Same page context for selected text."],
        title="Learning Sample",
    )
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=2,
            selected_text="Sanitized selected text.",
        )
        session.add(highlight)
        session.commit()
        session.refresh(highlight)
        highlight_id = highlight.id

    captured_requests: list[GlossaryExtractionRequest] = []

    class CapturingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_glossary_terms(
            self,
            request: GlossaryExtractionRequest,
        ) -> GlossaryExtractionResponse:
            captured_requests.append(request)
            return GlossaryExtractionResponse(
                content=GlossaryExtractionContent(
                    terms=[
                        {
                            "term": "Selected term",
                            "definition": "A stored fake definition.",
                            "source_text": "selected text",
                        },
                        {
                            "term": "Context term",
                            "definition": "Another fake definition.",
                            "source_text": None,
                        },
                    ]
                ),
                usage=LLMUsageMetadata(
                    provider=self.provider,
                    model=self.model,
                    prompt_tokens=4,
                    completion_tokens=6,
                    total_tokens=10,
                    estimated_cost=Decimal("0.000000"),
                ),
            )

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = CapturingProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/glossary-terms")

        assert response.status_code == 201
        payload = response.json()
        assert [
            (item["term"], item["definition"], item["source_text"]) for item in payload
        ] == [
            ("Selected term", "A stored fake definition.", "selected text"),
            ("Context term", "Another fake definition.", None),
        ]
        assert {item["document_id"] for item in payload} == {document_id}
        assert {item["highlight_id"] for item in payload} == {highlight_id}
        assert {item["provider"] for item in payload} == {"fake"}
        assert {item["model"] for item in payload} == {"fake-explanation-v1"}
        assert all("created_at" in item for item in payload)
        assert captured_requests == [
            GlossaryExtractionRequest(
                selected_text="Sanitized selected text.",
                surrounding_context="Same page context for selected text.",
                document_title="Learning Sample",
            )
        ]

        with test_session() as session:
            glossary_terms = session.scalars(
                select(database.GlossaryTerm).order_by(database.GlossaryTerm.id)
            ).all()
            assert len(glossary_terms) == 2
            assert glossary_terms[0].document_id == document_id
            assert glossary_terms[0].highlight_id == highlight_id
            assert glossary_terms[0].term == "Selected term"
            assert glossary_terms[0].definition == "A stored fake definition."
            assert glossary_terms[0].source_text == "selected text"
            assert glossary_terms[0].provider == "fake"
            assert glossary_terms[0].model == "fake-explanation-v1"

            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.document_id == document_id
            assert log.highlight_id == highlight_id
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "glossary_extraction"
            assert log.status == "success"
            assert log.latency_ms is not None
            assert log.prompt_tokens == 4
            assert log.completion_tokens == 6
            assert log.total_tokens == 10
            assert log.estimated_cost == Decimal("0.000000")
            assert log.error_message is None
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_glossary_terms_caps_page_context_before_provider_call() -> None:
    test_session = build_test_session()
    long_context = "A" * (PAGE_CONTEXT_MAX_CHARS + 200)
    document_id = create_document_with_pages(
        test_session,
        ["Other page context.", long_context],
        title="Long Context Sample",
    )
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=2,
            selected_text="Selected text.",
        )
        session.add(highlight)
        session.commit()
        session.refresh(highlight)
        highlight_id = highlight.id

    captured_requests: list[GlossaryExtractionRequest] = []

    class CapturingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_glossary_terms(
            self,
            request: GlossaryExtractionRequest,
        ) -> GlossaryExtractionResponse:
            captured_requests.append(request)
            return GlossaryExtractionResponse(
                content=GlossaryExtractionContent(terms=[]),
                usage=LLMUsageMetadata(
                    provider=self.provider,
                    model=self.model,
                    prompt_tokens=3,
                    completion_tokens=0,
                    total_tokens=3,
                    estimated_cost=Decimal("0.000000"),
                ),
            )

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = CapturingProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/glossary-terms")

        assert response.status_code == 201
        assert captured_requests == [
            GlossaryExtractionRequest(
                selected_text="Selected text.",
                surrounding_context="A" * PAGE_CONTEXT_MAX_CHARS,
                document_title="Long Context Sample",
            )
        ]
        assert "Other page context." not in captured_requests[0].surrounding_context
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_glossary_terms_rejects_missing_highlight() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post("/api/v1/highlights/404/glossary-terms")

        assert response.status_code == 404
        assert response.json() == {"detail": "Highlight not found."}

        with test_session() as session:
            assert session.scalars(select(database.LLMRequestLog)).all() == []
            assert session.scalars(select(database.GlossaryTerm)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_glossary_terms_logs_provider_failure() -> None:
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

        def generate_glossary_terms(
            self,
            request: GlossaryExtractionRequest,
        ) -> GlossaryExtractionResponse:
            raise RuntimeError("private provider failure")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = FailingProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/glossary-terms")

        assert response.status_code == 500
        assert response.json() == {"detail": "Glossary extraction failed."}

        with test_session() as session:
            assert session.scalars(select(database.GlossaryTerm)).all() == []
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.document_id == document_id
            assert log.highlight_id == highlight_id
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "glossary_extraction"
            assert log.status == "error"
            assert log.latency_ms is not None
            assert log.prompt_tokens is None
            assert log.completion_tokens is None
            assert log.total_tokens is None
            assert log.estimated_cost is None
            assert log.error_message == "Provider request failed."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_glossary_terms_does_not_store_invalid_provider_output() -> None:
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

    class InvalidProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_glossary_terms(
            self,
            request: GlossaryExtractionRequest,
        ) -> GlossaryExtractionResponse:
            GlossaryExtractionContent.model_validate(
                {
                    "terms": [
                        {
                            "term": "   ",
                            "definition": "Definition.",
                            "source_text": "phrase",
                        }
                    ]
                }
            )
            raise AssertionError("validation should have failed")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = InvalidProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/glossary-terms")

        assert response.status_code == 500
        assert response.json() == {"detail": "Glossary extraction failed."}

        with test_session() as session:
            assert session.scalars(select(database.GlossaryTerm)).all() == []
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.task_type == "glossary_extraction"
            assert log.status == "error"
            assert log.error_message == "Provider request failed."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_quizzes_without_body_uses_defaults_and_stores_log() -> None:
    test_session = build_test_session()
    document_id = create_document_with_pages(
        test_session,
        ["First page text.", "Same page context for selected text."],
        title="Learning Sample",
    )
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=2,
            selected_text="Sanitized selected text.",
        )
        session.add(highlight)
        session.commit()
        session.refresh(highlight)
        highlight_id = highlight.id

    captured_requests: list[QuizGenerationRequest] = []

    class CapturingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_quizzes(
            self,
            request: QuizGenerationRequest,
        ) -> QuizGenerationResponse:
            captured_requests.append(request)
            return QuizGenerationResponse(
                content=QuizGenerationContent(
                    quizzes=[
                        {
                            "quiz_type": "short_answer",
                            "question": "What is selected?",
                            "answer": "The selected text.",
                            "explanation": "The selection states it.",
                            "source_text": "selected text",
                        },
                        {
                            "quiz_type": "fill_blank",
                            "question": "Fill in: selected ____.",
                            "answer": "text",
                            "explanation": "The selected phrase contains this word.",
                            "source_text": "selected text",
                        },
                    ]
                ),
                usage=LLMUsageMetadata(
                    provider=self.provider,
                    model=self.model,
                    prompt_tokens=4,
                    completion_tokens=8,
                    total_tokens=12,
                    estimated_cost=Decimal("0.000000"),
                ),
            )

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = CapturingProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/quizzes")

        assert response.status_code == 201
        payload = response.json()
        assert [(item["quiz_type"], item["question"]) for item in payload] == [
            ("short_answer", "What is selected?"),
            ("fill_blank", "Fill in: selected ____."),
        ]
        assert {item["document_id"] for item in payload} == {document_id}
        assert {item["highlight_id"] for item in payload} == {highlight_id}
        assert {item["provider"] for item in payload} == {"fake"}
        assert {item["model"] for item in payload} == {"fake-explanation-v1"}
        assert all("created_at" in item for item in payload)
        assert captured_requests == [
            QuizGenerationRequest(
                selected_text="Sanitized selected text.",
                surrounding_context="Same page context for selected text.",
                document_title="Learning Sample",
                quiz_types=["short_answer", "fill_blank"],
                max_quizzes=2,
            )
        ]

        with test_session() as session:
            quizzes = session.scalars(
                select(database.Quiz).order_by(database.Quiz.id)
            ).all()
            assert len(quizzes) == 2
            assert quizzes[0].document_id == document_id
            assert quizzes[0].highlight_id == highlight_id
            assert quizzes[0].quiz_type == "short_answer"
            assert quizzes[0].question == "What is selected?"
            assert quizzes[0].answer == "The selected text."
            assert quizzes[0].explanation == "The selection states it."
            assert quizzes[0].source_text == "selected text"
            assert quizzes[0].provider == "fake"
            assert quizzes[0].model == "fake-explanation-v1"

            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.document_id == document_id
            assert log.highlight_id == highlight_id
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "quiz_generation"
            assert log.status == "success"
            assert log.latency_ms is not None
            assert log.prompt_tokens == 4
            assert log.completion_tokens == 8
            assert log.total_tokens == 12
            assert log.estimated_cost == Decimal("0.000000")
            assert log.error_message is None
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_quizzes_deduplicates_types_and_caps_page_context() -> None:
    test_session = build_test_session()
    long_context = "A" * (PAGE_CONTEXT_MAX_CHARS + 200)
    document_id = create_document_with_pages(
        test_session,
        ["Other page context.", long_context],
        title="Long Context Sample",
    )
    with test_session() as session:
        highlight = database.Highlight(
            document_id=document_id,
            page_number=2,
            selected_text="Selected text.",
        )
        session.add(highlight)
        session.commit()
        session.refresh(highlight)
        highlight_id = highlight.id

    captured_requests: list[QuizGenerationRequest] = []

    class CapturingProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_quizzes(
            self,
            request: QuizGenerationRequest,
        ) -> QuizGenerationResponse:
            captured_requests.append(request)
            return QuizGenerationResponse(
                content=QuizGenerationContent(
                    quizzes=[
                        {
                            "quiz_type": "short_answer",
                            "question": "Question?",
                            "answer": "Answer.",
                            "explanation": "Explanation.",
                            "source_text": "Selected text",
                        }
                    ]
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

        response = client.post(
            f"/api/v1/highlights/{highlight_id}/quizzes",
            json={
                "quiz_types": ["short_answer", "short_answer"],
                "max_quizzes": 1,
            },
        )

        assert response.status_code == 201
        assert captured_requests == [
            QuizGenerationRequest(
                selected_text="Selected text.",
                surrounding_context="A" * PAGE_CONTEXT_MAX_CHARS,
                document_title="Long Context Sample",
                quiz_types=["short_answer"],
                max_quizzes=1,
            )
        ]
        assert "Other page context." not in captured_requests[0].surrounding_context
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_quizzes_rejects_missing_highlight() -> None:
    test_session = build_test_session()
    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        response = client.post("/api/v1/highlights/404/quizzes")

        assert response.status_code == 404
        assert response.json() == {"detail": "Highlight not found."}

        with test_session() as session:
            assert session.scalars(select(database.LLMRequestLog)).all() == []
            assert session.scalars(select(database.Quiz)).all() == []
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_quizzes_logs_provider_failure() -> None:
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

        def generate_quizzes(
            self,
            request: QuizGenerationRequest,
        ) -> QuizGenerationResponse:
            raise RuntimeError("private provider failure")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = FailingProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/quizzes")

        assert response.status_code == 500
        assert response.json() == {"detail": "Quiz generation failed."}

        with test_session() as session:
            assert session.scalars(select(database.Quiz)).all() == []
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.document_id == document_id
            assert log.highlight_id == highlight_id
            assert log.provider == "fake"
            assert log.model == "fake-explanation-v1"
            assert log.task_type == "quiz_generation"
            assert log.status == "error"
            assert log.latency_ms is not None
            assert log.prompt_tokens is None
            assert log.completion_tokens is None
            assert log.total_tokens is None
            assert log.estimated_cost is None
            assert log.error_message == "Provider request failed."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_quizzes_does_not_store_invalid_provider_output() -> None:
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

    class InvalidProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_quizzes(
            self,
            request: QuizGenerationRequest,
        ) -> QuizGenerationResponse:
            QuizGenerationContent.model_validate(
                {
                    "quizzes": [
                        {
                            "quiz_type": "short_answer",
                            "question": "   ",
                            "answer": "Answer.",
                            "explanation": "Explanation.",
                            "source_text": "phrase",
                        }
                    ]
                }
            )
            raise AssertionError("validation should have failed")

    override_app_db_session(test_session)
    app.dependency_overrides[get_llm_provider] = InvalidProvider

    try:
        client = TestClient(app)

        response = client.post(f"/api/v1/highlights/{highlight_id}/quizzes")

        assert response.status_code == 500
        assert response.json() == {"detail": "Quiz generation failed."}

        with test_session() as session:
            assert session.scalars(select(database.Quiz)).all() == []
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.task_type == "quiz_generation"
            assert log.status == "error"
            assert log.error_message == "Provider request failed."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_quizzes_rejects_provider_result_over_requested_max() -> None:
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

    class TooManyQuizzesProvider:
        provider = "fake"
        model = "fake-explanation-v1"

        def generate_quizzes(
            self,
            request: QuizGenerationRequest,
        ) -> QuizGenerationResponse:
            return QuizGenerationResponse(
                content=QuizGenerationContent(
                    quizzes=[
                        {
                            "quiz_type": "short_answer",
                            "question": "Question 1?",
                            "answer": "Answer 1.",
                            "explanation": "Explanation 1.",
                            "source_text": "phrase",
                        },
                        {
                            "quiz_type": "fill_blank",
                            "question": "Question 2?",
                            "answer": "Answer 2.",
                            "explanation": "Explanation 2.",
                            "source_text": "phrase",
                        },
                    ]
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
    app.dependency_overrides[get_llm_provider] = TooManyQuizzesProvider

    try:
        client = TestClient(app)

        response = client.post(
            f"/api/v1/highlights/{highlight_id}/quizzes",
            json={"quiz_types": ["short_answer", "fill_blank"], "max_quizzes": 1},
        )

        assert response.status_code == 500
        assert response.json() == {"detail": "Quiz generation failed."}

        with test_session() as session:
            assert session.scalars(select(database.Quiz)).all() == []
            log = session.scalars(select(database.LLMRequestLog)).one()
            assert log.task_type == "quiz_generation"
            assert log.status == "error"
            assert log.error_message == "Provider request failed."
    finally:
        app.dependency_overrides.clear()


def test_create_highlight_quizzes_rejects_invalid_request_body() -> None:
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

    override_app_db_session(test_session)

    try:
        client = TestClient(app)

        unknown_type_response = client.post(
            f"/api/v1/highlights/{highlight_id}/quizzes",
            json={"quiz_types": ["multiple_choice"]},
        )
        empty_types_response = client.post(
            f"/api/v1/highlights/{highlight_id}/quizzes",
            json={"quiz_types": []},
        )
        invalid_max_response = client.post(
            f"/api/v1/highlights/{highlight_id}/quizzes",
            json={"max_quizzes": 3},
        )

        assert unknown_type_response.status_code == 422
        assert empty_types_response.status_code == 422
        assert invalid_max_response.status_code == 422

        with test_session() as session:
            assert session.scalars(select(database.Quiz)).all() == []
            assert session.scalars(select(database.LLMRequestLog)).all() == []
    finally:
        app.dependency_overrides.clear()
