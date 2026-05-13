import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.llm import (
    ALLOWED_QUIZ_TYPES,
    DEFAULT_QUIZZES_PER_REQUEST,
    EXPLANATION_RESPONSE_SCHEMA,
    GLOSSARY_RESPONSE_SCHEMA,
    ExplanationRequest,
    FakeLLMProvider,
    GlossaryExtractionContent,
    GlossaryExtractionRequest,
    LLMProvider,
    LLMProviderConfigError,
    MAX_GLOSSARY_TERMS_PER_REQUEST,
    MAX_QUIZZES_PER_REQUEST,
    OPENAI_RESPONSE_FORMAT_ENV_VAR,
    OPENAI_RESPONSE_FORMAT_JSON_OBJECT,
    OPENAI_RESPONSE_FORMAT_JSON_SCHEMA,
    OpenAICompatibleLLMProvider,
    QUESTION_ANSWER_RESPONSE_SCHEMA,
    QUIZ_RESPONSE_SCHEMA,
    QuestionAnswerRequest,
    QuizGenerationContent,
    QuizGenerationRequest,
    REVIEW_CARD_RESPONSE_SCHEMA,
    ReviewCardContent,
    ReviewCardGenerationRequest,
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


def test_fake_provider_generates_glossary_terms() -> None:
    provider: LLMProvider = FakeLLMProvider()
    request = GlossaryExtractionRequest(
        selected_text="selected concept",
        surrounding_context="nearby page context",
        document_title="Sample Document",
    )

    response = provider.generate_glossary_terms(request)

    assert len(response.content.terms) == 1
    term = response.content.terms[0]
    assert term.term == "Fake glossary term"
    assert term.definition == "Fake definition for: selected concept"
    assert term.source_text == "selected concept"
    assert response.usage.provider == "fake"
    assert response.usage.model == "fake-explanation-v1"
    assert response.usage.prompt_tokens == 7
    assert response.usage.completion_tokens == 10
    assert response.usage.total_tokens == 17
    assert response.usage.estimated_cost == Decimal("0.000000")


def test_fake_provider_generates_deterministic_quizzes() -> None:
    provider: LLMProvider = FakeLLMProvider()
    request = QuizGenerationRequest(
        selected_text="selected concept",
        surrounding_context="nearby page context",
        document_title="Sample Document",
    )

    first_response = provider.generate_quizzes(request)
    second_response = provider.generate_quizzes(request)

    assert first_response == second_response
    assert [quiz.quiz_type for quiz in first_response.content.quizzes] == [
        "short_answer",
        "fill_blank",
    ]
    assert first_response.content.quizzes[0].question == (
        "Fake short_answer question 1 for: selected concept"
    )
    assert first_response.content.quizzes[0].answer == (
        "Fake answer for: selected concept"
    )
    assert first_response.content.quizzes[0].source_text == "selected concept"
    assert first_response.usage.provider == "fake"
    assert first_response.usage.model == "fake-explanation-v1"
    assert first_response.usage.prompt_tokens == 7
    assert first_response.usage.completion_tokens > 0
    assert first_response.usage.total_tokens == (
        first_response.usage.prompt_tokens
        + first_response.usage.completion_tokens
    )
    assert first_response.usage.estimated_cost == Decimal("0.000000")


def test_fake_provider_generates_requested_count_for_deterministic_tests() -> None:
    provider: LLMProvider = FakeLLMProvider()

    response = provider.generate_quizzes(
        QuizGenerationRequest(
            selected_text="selected concept",
            quiz_types=["short_answer", "fill_blank"],
            max_quizzes=6,
        )
    )

    assert len(response.content.quizzes) == 6
    assert [quiz.quiz_type for quiz in response.content.quizzes] == [
        "short_answer",
        "fill_blank",
        "short_answer",
        "fill_blank",
        "short_answer",
        "fill_blank",
    ]


def test_fake_provider_generates_deterministic_review_card() -> None:
    provider: LLMProvider = FakeLLMProvider()
    request = ReviewCardGenerationRequest(
        document_title="Sample Document",
        page_number=2,
        quiz_type="short_answer",
        question="What is selected?",
        correct_answer="The selected concept.",
        user_answer="Wrong answer.",
        quiz_explanation="The selected passage states the concept.",
        quiz_source_text="selected concept",
    )

    first_response = provider.generate_review_card(request)
    second_response = provider.generate_review_card(request)

    assert first_response == second_response
    assert first_response.content.front == (
        "Review this short_answer question: What is selected?"
    )
    assert first_response.content.back == (
        "Correct answer: The selected concept.\n"
        "Explanation: The selected passage states the concept."
    )
    assert first_response.content.source_text == "selected concept"
    assert first_response.usage.provider == "fake"
    assert first_response.usage.model == "fake-explanation-v1"
    assert first_response.usage.prompt_tokens > 0
    assert first_response.usage.total_tokens == (
        first_response.usage.prompt_tokens
        + first_response.usage.completion_tokens
    )


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


def test_glossary_request_trims_text_and_normalizes_empty_optional_fields() -> None:
    request = GlossaryExtractionRequest(
        selected_text="  selected concept  ",
        surrounding_context="  ",
        document_title="  Document  ",
    )

    assert request.selected_text == "selected concept"
    assert request.surrounding_context is None
    assert request.document_title == "Document"


def test_glossary_terms_require_non_blank_term_and_definition() -> None:
    with pytest.raises(ValidationError):
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

    with pytest.raises(ValidationError):
        GlossaryExtractionContent.model_validate(
            {
                "terms": [
                    {
                        "term": "Term",
                        "definition": "   ",
                        "source_text": "phrase",
                    }
                ]
            }
        )


def test_glossary_term_source_text_normalizes_blank_to_none() -> None:
    content = GlossaryExtractionContent.model_validate(
        {
            "terms": [
                {
                    "term": " Term ",
                    "definition": " Definition. ",
                    "source_text": "   ",
                }
            ]
        }
    )

    assert content.terms[0].term == "Term"
    assert content.terms[0].definition == "Definition."
    assert content.terms[0].source_text is None


def test_glossary_content_rejects_too_many_terms() -> None:
    with pytest.raises(ValidationError):
        GlossaryExtractionContent.model_validate(
            {
                "terms": [
                    {
                        "term": f"Term {index}",
                        "definition": "Definition.",
                        "source_text": None,
                    }
                    for index in range(MAX_GLOSSARY_TERMS_PER_REQUEST + 1)
                ]
            }
        )


def test_quiz_request_deduplicates_quiz_types_and_validates_bounds() -> None:
    default_request = QuizGenerationRequest(selected_text="default concept")
    max_request = QuizGenerationRequest(
        selected_text="max concept",
        max_quizzes=MAX_QUIZZES_PER_REQUEST,
    )
    request = QuizGenerationRequest(
        selected_text="  selected concept  ",
        surrounding_context="  ",
        document_title="  Document  ",
        quiz_types=["short_answer", "short_answer", "fill_blank"],
        max_quizzes=1,
    )

    assert default_request.max_quizzes == DEFAULT_QUIZZES_PER_REQUEST
    assert max_request.max_quizzes == MAX_QUIZZES_PER_REQUEST
    assert request.selected_text == "selected concept"
    assert request.surrounding_context is None
    assert request.document_title == "Document"
    assert request.quiz_types == ["short_answer", "fill_blank"]
    assert request.max_quizzes == 1

    with pytest.raises(ValidationError):
        QuizGenerationRequest(selected_text="concept", quiz_types=[])

    with pytest.raises(ValidationError):
        QuizGenerationRequest(selected_text="concept", quiz_types=["multiple_choice"])

    with pytest.raises(ValidationError):
        QuizGenerationRequest(
            selected_text="concept",
            max_quizzes=MAX_QUIZZES_PER_REQUEST + 1,
        )


def test_quiz_content_validates_required_fields_and_quiz_type() -> None:
    with pytest.raises(ValidationError):
        QuizGenerationContent.model_validate(
            {
                "quizzes": [
                    {
                        "quiz_type": "multiple_choice",
                        "question": "Question?",
                        "answer": "Answer.",
                        "explanation": "Explanation.",
                        "source_text": "phrase",
                    }
                ]
            }
        )

    with pytest.raises(ValidationError):
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


def test_quiz_content_rejects_too_many_quizzes() -> None:
    QuizGenerationContent.model_validate(
        {
            "quizzes": [
                {
                    "quiz_type": "short_answer",
                    "question": f"Question {index}?",
                    "answer": "Answer.",
                    "explanation": "Explanation.",
                    "source_text": "phrase",
                }
                for index in range(MAX_QUIZZES_PER_REQUEST)
            ]
        }
    )

    with pytest.raises(ValidationError):
        QuizGenerationContent.model_validate(
            {
                "quizzes": [
                    {
                        "quiz_type": "short_answer",
                        "question": f"Question {index}?",
                        "answer": "Answer.",
                        "explanation": "Explanation.",
                        "source_text": "phrase",
                    }
                    for index in range(MAX_QUIZZES_PER_REQUEST + 1)
                ]
            }
        )


def test_review_card_request_validates_context_fields() -> None:
    request = ReviewCardGenerationRequest(
        document_title="  Document  ",
        page_number=1,
        quiz_type=" short_answer ",
        question="  Question?  ",
        correct_answer="  Answer.  ",
        user_answer="  User answer.  ",
        quiz_explanation="  Explanation.  ",
        quiz_source_text="  source phrase  ",
    )

    assert request.document_title == "Document"
    assert request.quiz_type == "short_answer"
    assert request.question == "Question?"
    assert request.correct_answer == "Answer."
    assert request.user_answer == "User answer."
    assert request.quiz_explanation == "Explanation."
    assert request.quiz_source_text == "source phrase"

    blank_title_request = ReviewCardGenerationRequest(
        document_title="  ",
        page_number=1,
        quiz_type="fill_blank",
        question="Question?",
        correct_answer="Answer.",
        user_answer="User answer.",
        quiz_explanation="Explanation.",
        quiz_source_text="source phrase",
    )
    assert blank_title_request.document_title is None

    with pytest.raises(ValidationError):
        ReviewCardGenerationRequest(
            page_number=0,
            quiz_type="short_answer",
            question="Question?",
            correct_answer="Answer.",
            user_answer="User answer.",
            quiz_explanation="Explanation.",
            quiz_source_text="source phrase",
        )

    with pytest.raises(ValidationError):
        ReviewCardGenerationRequest(
            page_number=1,
            quiz_type="multiple_choice",
            question="Question?",
            correct_answer="Answer.",
            user_answer="User answer.",
            quiz_explanation="Explanation.",
            quiz_source_text="source phrase",
        )

    with pytest.raises(ValidationError):
        ReviewCardGenerationRequest(
            page_number=1,
            quiz_type="short_answer",
            question="   ",
            correct_answer="Answer.",
            user_answer="User answer.",
            quiz_explanation="Explanation.",
            quiz_source_text="source phrase",
        )


def test_review_card_content_validates_required_fields_and_normalizes_source() -> None:
    content = ReviewCardContent(
        front="  Front?  ",
        back="  Back.  ",
        source_text="   ",
    )

    assert content.front == "Front?"
    assert content.back == "Back."
    assert content.source_text is None

    with pytest.raises(ValidationError):
        ReviewCardContent(front="   ", back="Back.")

    with pytest.raises(ValidationError):
        ReviewCardContent(front="Front?", back="   ")


def test_review_card_response_schema_is_strict_and_nullable_source_text() -> None:
    assert REVIEW_CARD_RESPONSE_SCHEMA == {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "front": {"type": "string"},
            "back": {"type": "string"},
            "source_text": {"type": ["string", "null"]},
        },
        "required": ["front", "back", "source_text"],
    }


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
    system_prompt = call["messages"][0]["content"]
    assert "natural-language JSON values" in system_prompt
    assert "write Korean by default" in system_prompt
    assert "Never translate JSON field names" in system_prompt
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


def test_openai_compatible_provider_json_object_mode_uses_json_object_format() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "summary": "Normalized explanation.",
            "key_points": ["First point."],
        },
        usage=SimpleNamespace(
            prompt_tokens=5,
            completion_tokens=6,
            total_tokens=11,
        ),
    )
    provider = OpenAICompatibleLLMProvider(
        api_key="test-api-key",
        model="test-model",
        response_format="json_object",
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=chat_completions),
        ),
    )

    response = provider.generate_explanation(
        ExplanationRequest(selected_text="selected concept")
    )

    assert response.content.summary == "Normalized explanation."
    call = chat_completions.calls[0]
    assert call["response_format"] == {"type": "json_object"}
    system_prompt = call["messages"][0]["content"]
    assert "single JSON object" in system_prompt
    assert "summary" in system_prompt
    assert "key_points" in system_prompt
    assert "test-api-key" not in json.dumps(call)


def test_openai_compatible_provider_json_object_mode_still_validates_output() -> None:
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
        response_format="json_object",
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=chat_completions),
        ),
    )

    with pytest.raises(ValidationError):
        provider.generate_explanation(ExplanationRequest(selected_text="concept"))


def test_openai_compatible_provider_generates_normalized_glossary_terms() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "terms": [
                {
                    "term": " Concept ",
                    "definition": " Definition. ",
                    "source_text": " selected concept ",
                }
            ],
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

    response = provider.generate_glossary_terms(
        GlossaryExtractionRequest(
            selected_text="selected concept",
            surrounding_context="nearby context",
            document_title="Sample Document",
        )
    )

    assert len(response.content.terms) == 1
    assert response.content.terms[0].term == "Concept"
    assert response.content.terms[0].definition == "Definition."
    assert response.content.terms[0].source_text == "selected concept"
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
            "name": "infodrip_glossary_extraction",
            "strict": True,
            "schema": GLOSSARY_RESPONSE_SCHEMA,
        },
    }
    schema_terms = GLOSSARY_RESPONSE_SCHEMA["properties"]["terms"]
    assert schema_terms["maxItems"] == 10
    schema_source_text = schema_terms["items"]["properties"]["source_text"]
    assert schema_source_text == {"type": ["string", "null"]}
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1]["role"] == "user"
    user_prompt = call["messages"][1]["content"]
    assert "Selected text:\nselected concept" in user_prompt
    assert "Surrounding context:\nnearby context" in user_prompt
    assert "Document title:\nSample Document" in user_prompt
    assert "short phrase from the selected text" in user_prompt
    assert "top-level key terms" in user_prompt
    assert "term, definition, and source_text" in user_prompt
    assert "source_text is required and may be null" in user_prompt
    assert "natural-language JSON values" in user_prompt
    assert "write Korean by default" in user_prompt
    assert "Never translate JSON field names" in user_prompt
    assert "keep term in English when the source term is English" in user_prompt
    assert "write definition in Korean by default" in user_prompt
    assert "test-api-key" not in json.dumps(call)


def test_openai_compatible_provider_validates_glossary_response_shape() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={"terms": [{"term": "Missing definition."}]},
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
        provider.generate_glossary_terms(
            GlossaryExtractionRequest(selected_text="concept")
        )


def test_openai_compatible_provider_rejects_too_many_glossary_terms() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "terms": [
                {
                    "term": f"Term {index}",
                    "definition": "Definition.",
                    "source_text": None,
                }
                for index in range(MAX_GLOSSARY_TERMS_PER_REQUEST + 1)
            ]
        },
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
        provider.generate_glossary_terms(
            GlossaryExtractionRequest(selected_text="concept")
        )


def test_openai_compatible_provider_generates_normalized_quizzes() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "quizzes": [
                {
                    "quiz_type": " short_answer ",
                    "question": " What is the selected concept? ",
                    "answer": " It is a sanitized concept. ",
                    "explanation": " The selected passage states this directly. ",
                    "source_text": " selected concept ",
                }
            ],
        },
        usage=SimpleNamespace(
            prompt_tokens=11,
            completion_tokens=9,
            total_tokens=20,
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

    response = provider.generate_quizzes(
        QuizGenerationRequest(
            selected_text="selected concept",
            surrounding_context="nearby context",
            document_title="Sample Document",
            quiz_types=["short_answer", "fill_blank"],
            max_quizzes=1,
        )
    )

    assert len(response.content.quizzes) == 1
    quiz = response.content.quizzes[0]
    assert quiz.quiz_type == "short_answer"
    assert quiz.question == "What is the selected concept?"
    assert quiz.answer == "It is a sanitized concept."
    assert quiz.explanation == "The selected passage states this directly."
    assert quiz.source_text == "selected concept"
    assert response.usage.provider == "openai-compatible"
    assert response.usage.model == "provider-model"
    assert response.usage.prompt_tokens == 11
    assert response.usage.completion_tokens == 9
    assert response.usage.total_tokens == 20
    assert response.usage.estimated_cost == Decimal("0.000000")

    assert len(chat_completions.calls) == 1
    call = chat_completions.calls[0]
    assert call["model"] == "test-model"
    assert call["temperature"] == 0
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "infodrip_quiz_generation",
            "strict": True,
            "schema": QUIZ_RESPONSE_SCHEMA,
        },
    }
    assert QUIZ_RESPONSE_SCHEMA["additionalProperties"] is False
    schema_quizzes = QUIZ_RESPONSE_SCHEMA["properties"]["quizzes"]
    assert schema_quizzes["maxItems"] == MAX_QUIZZES_PER_REQUEST
    schema_quiz = schema_quizzes["items"]
    assert schema_quiz["additionalProperties"] is False
    assert schema_quiz["properties"]["quiz_type"]["enum"] == list(ALLOWED_QUIZ_TYPES)
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1]["role"] == "user"
    user_prompt = call["messages"][1]["content"]
    assert "Selected text:\nselected concept" in user_prompt
    assert "Same-page surrounding context:\nnearby context" in (
        user_prompt
    )
    assert "Document title:\nSample Document" in user_prompt
    assert "Return at most 1 quizzes." in user_prompt
    assert "return fewer quizzes" in user_prompt
    assert "Distribute quiz types as evenly as possible" in user_prompt
    assert "short phrase from the selected text" in user_prompt
    assert "top-level key quizzes" in user_prompt
    assert "quiz_type, question, answer, explanation, and source_text" in (
        user_prompt
    )
    assert "quiz_type must be short_answer or fill_blank" in user_prompt
    assert "natural-language JSON values" in user_prompt
    assert "write Korean by default" in user_prompt
    assert "Never translate JSON field names" in user_prompt
    assert "quiz_type values must remain exactly short_answer or fill_blank" in (
        user_prompt
    )
    assert "Do not translate quiz_type values to Korean labels" in user_prompt
    assert "단답형 or 빈칸" in user_prompt
    assert "test-api-key" not in json.dumps(call)


def test_openai_compatible_provider_validates_quiz_response_shape() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "quizzes": [
                {
                    "quiz_type": "multiple_choice",
                    "question": "Question?",
                    "answer": "Answer.",
                    "explanation": "Explanation.",
                    "source_text": "phrase",
                }
            ]
        },
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
        provider.generate_quizzes(QuizGenerationRequest(selected_text="concept"))


def test_openai_compatible_provider_question_answer_prompt_prefers_korean_values() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "answer": "Normalized answer.",
            "evidence_text": "selected concept",
            "document_based": True,
            "needs_more_context": False,
        },
        usage=SimpleNamespace(
            prompt_tokens=11,
            completion_tokens=9,
            total_tokens=20,
        ),
    )
    provider = OpenAICompatibleLLMProvider(
        api_key="test-api-key",
        model="test-model",
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=chat_completions),
        ),
    )

    response = provider.answer_question(
        QuestionAnswerRequest(
            selected_text="selected concept",
            question="What does this mean?",
            surrounding_context="nearby context",
            document_title="Sample Document",
        )
    )

    assert response.content.answer == "Normalized answer."
    assert response.content.evidence_text == "selected concept"
    assert response.content.document_based is True
    assert response.content.needs_more_context is False

    assert len(chat_completions.calls) == 1
    call = chat_completions.calls[0]
    assert call["model"] == "test-model"
    assert call["temperature"] == 0
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "infodrip_question_answer",
            "strict": True,
            "schema": QUESTION_ANSWER_RESPONSE_SCHEMA,
        },
    }
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1]["role"] == "user"
    user_prompt = call["messages"][1]["content"]
    assert "Selected text:\nselected concept" in user_prompt
    assert "User question:\nWhat does this mean?" in user_prompt
    assert "Same-page surrounding context:\nnearby context" in user_prompt
    assert "Document title:\nSample Document" in user_prompt
    assert "natural-language JSON values" in user_prompt
    assert "write Korean by default" in user_prompt
    assert "Never translate JSON field names" in user_prompt
    assert "Write answer as plain text" in user_prompt
    assert "Do not use markdown formatting inside JSON string values" in user_prompt
    assert "**bold**" in user_prompt
    assert "code fences" in user_prompt
    assert "test-api-key" not in json.dumps(call)


def test_openai_compatible_provider_generates_normalized_review_card() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "front": " What should you remember? ",
            "back": " Correct answer: selected concept. Explanation: it is stated. ",
            "source_text": " selected concept ",
        },
        usage=SimpleNamespace(
            prompt_tokens=13,
            completion_tokens=8,
            total_tokens=21,
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

    response = provider.generate_review_card(
        ReviewCardGenerationRequest(
            document_title="Sample Document",
            page_number=3,
            quiz_type="short_answer",
            question="What is selected?",
            correct_answer="selected concept",
            user_answer="wrong answer",
            quiz_explanation="The passage states it.",
            quiz_source_text="selected concept",
        )
    )

    assert response.content.front == "What should you remember?"
    assert response.content.back == (
        "Correct answer: selected concept. Explanation: it is stated."
    )
    assert response.content.source_text == "selected concept"
    assert response.usage.provider == "openai-compatible"
    assert response.usage.model == "provider-model"
    assert response.usage.prompt_tokens == 13
    assert response.usage.completion_tokens == 8
    assert response.usage.total_tokens == 21
    assert response.usage.estimated_cost == Decimal("0.000000")

    assert len(chat_completions.calls) == 1
    call = chat_completions.calls[0]
    assert call["model"] == "test-model"
    assert call["temperature"] == 0
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "infodrip_review_card_generation",
            "strict": True,
            "schema": REVIEW_CARD_RESPONSE_SCHEMA,
        },
    }
    assert REVIEW_CARD_RESPONSE_SCHEMA["additionalProperties"] is False
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1]["role"] == "user"
    user_content = call["messages"][1]["content"]
    assert "Document title:\nSample Document" in user_content
    assert "Page number:\n3" in user_content
    assert "Quiz type:\nshort_answer" in user_content
    assert "Question:\nWhat is selected?" in user_content
    assert "User answer:\nwrong answer" in user_content
    assert "Correct answer:\nselected concept" in user_content
    assert "Quiz explanation:\nThe passage states it." in user_content
    assert "Quiz source text:\nselected concept" in user_content
    assert "self-contained review prompt" in user_content
    assert "test-api-key" not in json.dumps(call)


def test_openai_compatible_provider_validates_review_card_response_shape() -> None:
    chat_completions = CapturingChatCompletions(
        response_content={
            "front": "   ",
            "back": "Back.",
            "source_text": None,
        },
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
        provider.generate_review_card(
            ReviewCardGenerationRequest(
                page_number=1,
                quiz_type="short_answer",
                question="Question?",
                correct_answer="Answer.",
                user_answer="User answer.",
                quiz_explanation="Explanation.",
                quiz_source_text="source phrase",
            )
        )


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
    assert provider.response_format == OPENAI_RESPONSE_FORMAT_JSON_SCHEMA


def test_build_llm_provider_from_env_selects_json_object_response_format() -> None:
    provider = build_llm_provider_from_env(
        {
            "INFODRIP_LLM_PROVIDER": "openai-compatible",
            "INFODRIP_OPENAI_API_KEY": "test-api-key",
            "INFODRIP_OPENAI_MODEL": "test-model",
            OPENAI_RESPONSE_FORMAT_ENV_VAR: "  json_object  ",
        }
    )

    assert isinstance(provider, OpenAICompatibleLLMProvider)
    assert provider.response_format == OPENAI_RESPONSE_FORMAT_JSON_OBJECT


def test_build_llm_provider_from_env_rejects_invalid_response_format() -> None:
    with pytest.raises(LLMProviderConfigError, match=OPENAI_RESPONSE_FORMAT_ENV_VAR):
        build_llm_provider_from_env(
            {
                "INFODRIP_LLM_PROVIDER": "openai-compatible",
                "INFODRIP_OPENAI_API_KEY": "test-api-key",
                "INFODRIP_OPENAI_MODEL": "test-model",
                OPENAI_RESPONSE_FORMAT_ENV_VAR: "yaml",
            }
        )


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
