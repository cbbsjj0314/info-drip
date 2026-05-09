from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.llm import ExplanationRequest, FakeLLMProvider, LLMProvider


def test_fake_provider_matches_llm_provider_interface() -> None:
    provider: LLMProvider = FakeLLMProvider()
    request = ExplanationRequest(
        selected_text="selected concept",
        surrounding_context="nearby page context",
        document_title="Sample Document",
    )

    response = provider.generate_explanation(request)

    assert response.content.summary == "Fake explanation for: selected concept"
    assert response.content.key_points == [
        "This is a deterministic fake provider response.",
        "Use this response for local tests without external API calls.",
    ]
    assert response.usage.provider == "fake"
    assert response.usage.model == "fake-explanation-v1"
    assert response.usage.prompt_tokens == 7
    assert response.usage.completion_tokens == 22
    assert response.usage.total_tokens == 29
    assert response.usage.estimated_cost == Decimal("0.000000")


def test_fake_provider_is_deterministic() -> None:
    provider = FakeLLMProvider()
    request = ExplanationRequest(
        selected_text="same selected text",
        surrounding_context="same context",
        document_title="same title",
    )

    first_response = provider.generate_explanation(request)
    second_response = provider.generate_explanation(request)

    assert first_response == second_response


def test_explanation_request_trims_text_and_normalizes_empty_optional_fields() -> None:
    request = ExplanationRequest(
        selected_text="  important passage  ",
        surrounding_context="  ",
        document_title="  Document  ",
    )

    assert request.selected_text == "important passage"
    assert request.surrounding_context is None
    assert request.document_title == "Document"


def test_explanation_request_rejects_blank_selected_text() -> None:
    with pytest.raises(ValidationError):
        ExplanationRequest(selected_text="   ")
