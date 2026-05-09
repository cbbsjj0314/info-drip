import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.llm import (
    EXPLANATION_RESPONSE_SCHEMA,
    ExplanationRequest,
    FakeLLMProvider,
    LLMProvider,
    LLMProviderConfigError,
    OpenAICompatibleLLMProvider,
    build_llm_provider_from_env,
)


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


def test_openai_compatible_provider_generates_normalized_explanation() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "summary": "Normalized explanation.",
            "key_points": ["First point.", "Second point."],
        },
        usage=SimpleNamespace(
            prompt_tokens=11,
            completion_tokens=7,
            total_tokens=18,
        ),
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=chat_completions),
    )
    provider = OpenAICompatibleLLMProvider(
        api_key="test-api-key",
        model="test-model",
        base_url="https://llm.example.test/v1",
        client=client,
    )

    response = provider.generate_explanation(
        ExplanationRequest(
            selected_text="selected concept",
            surrounding_context="nearby context",
            document_title="Sample Document",
        )
    )

    assert response.content.summary == "Normalized explanation."
    assert response.content.key_points == ["First point.", "Second point."]
    assert response.usage.provider == "openai-compatible"
    assert response.usage.model == "provider-model"
    assert response.usage.prompt_tokens == 11
    assert response.usage.completion_tokens == 7
    assert response.usage.total_tokens == 18
    assert response.usage.estimated_cost == Decimal("0.000000")

    assert len(chat_completions.calls) == 1
    call = chat_completions.calls[0]
    assert call["model"] == "test-model"
    assert call["temperature"] == 0
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "infodrip_explanation",
            "strict": True,
            "schema": EXPLANATION_RESPONSE_SCHEMA,
        },
    }
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1]["role"] == "user"
    assert "Selected text:\nselected concept" in call["messages"][1]["content"]
    assert "Surrounding context:\nnearby context" in call["messages"][1]["content"]
    assert "Document title:\nSample Document" in call["messages"][1]["content"]
    assert "test-api-key" not in json.dumps(call)


def test_openai_compatible_provider_validates_response_shape() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={"summary": "Missing key points."},
        usage=SimpleNamespace(
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
        ),
    )
    provider = OpenAICompatibleLLMProvider(
        api_key="test-api-key",
        model="test-model",
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=chat_completions),
        ),
    )

    with pytest.raises(ValidationError):
        provider.generate_explanation(ExplanationRequest(selected_text="concept"))


def test_openai_compatible_provider_falls_back_to_summed_total_tokens() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "summary": "Normalized explanation.",
            "key_points": ["Point."],
        },
        usage=SimpleNamespace(
            prompt_tokens=4,
            completion_tokens=6,
            total_tokens=None,
        ),
    )
    provider = OpenAICompatibleLLMProvider(
        api_key="test-api-key",
        model="test-model",
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=chat_completions),
        ),
    )

    response = provider.generate_explanation(ExplanationRequest(selected_text="concept"))

    assert response.usage.total_tokens == 10


def test_build_llm_provider_from_env_defaults_to_fake_provider() -> None:
    provider = build_llm_provider_from_env({})

    assert isinstance(provider, FakeLLMProvider)


def test_build_llm_provider_from_env_selects_openai_compatible_provider() -> None:
    provider = build_llm_provider_from_env(
        {
            "INFODRIP_LLM_PROVIDER": "openai-compatible",
            "INFODRIP_OPENAI_API_KEY": "test-api-key",
            "INFODRIP_OPENAI_BASE_URL": "https://llm.example.test/v1",
            "INFODRIP_OPENAI_MODEL": "test-model",
        }
    )

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert provider.provider == "openai-compatible"
    assert provider.model == "test-model"


def test_build_llm_provider_from_env_requires_openai_api_key() -> None:
    with pytest.raises(LLMProviderConfigError):
        build_llm_provider_from_env(
            {
                "INFODRIP_LLM_PROVIDER": "openai-compatible",
                "INFODRIP_OPENAI_MODEL": "test-model",
            }
        )


class CapturingChatCompletions:
    def __init__(self, *, response_content: dict[str, object], usage: object) -> None:
        self.calls: list[dict[str, object]] = []
        self._response_content = response_content
        self._usage = usage

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            model="provider-model",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(self._response_content),
                    ),
                )
            ],
            usage=self._usage,
        )
