import os
from decimal import Decimal
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, Field, field_validator

LLM_PROVIDER_ENV_VAR = "INFODRIP_LLM_PROVIDER"
OPENAI_API_KEY_ENV_VAR = "INFODRIP_OPENAI_API_KEY"
OPENAI_BASE_URL_ENV_VAR = "INFODRIP_OPENAI_BASE_URL"
OPENAI_MODEL_ENV_VAR = "INFODRIP_OPENAI_MODEL"
FAKE_PROVIDER_NAME = "fake"
OPENAI_COMPATIBLE_PROVIDER_NAME = "openai-compatible"
MAX_GLOSSARY_TERMS_PER_REQUEST = 10
SHORT_ANSWER_QUIZ_TYPE = "short_answer"
FILL_BLANK_QUIZ_TYPE = "fill_blank"
ALLOWED_QUIZ_TYPES = (SHORT_ANSWER_QUIZ_TYPE, FILL_BLANK_QUIZ_TYPE)
DEFAULT_QUIZZES_PER_REQUEST = 2
MAX_QUIZZES_PER_REQUEST = 10

EXPLANATION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["summary", "key_points"],
}

GLOSSARY_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "terms": {
            "type": "array",
            "maxItems": MAX_GLOSSARY_TERMS_PER_REQUEST,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "term": {"type": "string"},
                    "definition": {"type": "string"},
                    "source_text": {"type": ["string", "null"]},
                },
                "required": ["term", "definition", "source_text"],
            },
        },
    },
    "required": ["terms"],
}

QUIZ_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "quizzes": {
            "type": "array",
            "maxItems": MAX_QUIZZES_PER_REQUEST,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "quiz_type": {
                        "type": "string",
                        "enum": list(ALLOWED_QUIZ_TYPES),
                    },
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "explanation": {"type": "string"},
                    "source_text": {"type": "string"},
                },
                "required": [
                    "quiz_type",
                    "question",
                    "answer",
                    "explanation",
                    "source_text",
                ],
            },
        },
    },
    "required": ["quizzes"],
}

REVIEW_CARD_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "front": {"type": "string"},
        "back": {"type": "string"},
        "source_text": {"type": ["string", "null"]},
    },
    "required": ["front", "back", "source_text"],
}


class ExplanationRequest(BaseModel):
    selected_text: str = Field(min_length=1)
    surrounding_context: str | None = None
    document_title: str | None = None

    @field_validator("selected_text")
    @classmethod
    def selected_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("selected_text must not be blank")
        return stripped

    @field_validator("surrounding_context", "document_title")
    @classmethod
    def empty_optional_text_becomes_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ExplanationContent(BaseModel):
    summary: str
    key_points: list[str]


class GlossaryExtractionRequest(BaseModel):
    selected_text: str = Field(min_length=1)
    surrounding_context: str | None = None
    document_title: str | None = None

    @field_validator("selected_text")
    @classmethod
    def selected_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("selected_text must not be blank")
        return stripped

    @field_validator("surrounding_context", "document_title")
    @classmethod
    def empty_optional_text_becomes_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class GlossaryTermContent(BaseModel):
    term: str
    definition: str
    source_text: str | None = None

    @field_validator("term", "definition")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("required text must not be blank")
        return stripped

    @field_validator("source_text")
    @classmethod
    def empty_source_text_becomes_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class GlossaryExtractionContent(BaseModel):
    terms: list[GlossaryTermContent] = Field(
        max_length=MAX_GLOSSARY_TERMS_PER_REQUEST
    )


class QuizGenerationRequest(BaseModel):
    selected_text: str = Field(min_length=1)
    surrounding_context: str | None = None
    document_title: str | None = None
    quiz_types: list[str] = Field(default_factory=lambda: list(ALLOWED_QUIZ_TYPES))
    max_quizzes: int = Field(
        default=DEFAULT_QUIZZES_PER_REQUEST,
        ge=1,
        le=MAX_QUIZZES_PER_REQUEST,
    )

    @field_validator("selected_text")
    @classmethod
    def selected_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("selected_text must not be blank")
        return stripped

    @field_validator("surrounding_context", "document_title")
    @classmethod
    def empty_optional_text_becomes_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("quiz_types")
    @classmethod
    def quiz_types_must_be_allowed_and_deduplicated(
        cls,
        value: list[str],
    ) -> list[str]:
        if not value:
            raise ValueError("quiz_types must not be empty")

        deduplicated: list[str] = []
        for quiz_type in value:
            normalized = quiz_type.strip()
            if normalized not in ALLOWED_QUIZ_TYPES:
                raise ValueError("unsupported quiz_type")
            if normalized not in deduplicated:
                deduplicated.append(normalized)

        return deduplicated


class QuizContent(BaseModel):
    quiz_type: str
    question: str
    answer: str
    explanation: str
    source_text: str

    @field_validator("quiz_type")
    @classmethod
    def quiz_type_must_be_allowed(cls, value: str) -> str:
        stripped = value.strip()
        if stripped not in ALLOWED_QUIZ_TYPES:
            raise ValueError("unsupported quiz_type")
        return stripped

    @field_validator("question", "answer", "explanation", "source_text")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("required text must not be blank")
        return stripped


class QuizGenerationContent(BaseModel):
    quizzes: list[QuizContent] = Field(max_length=MAX_QUIZZES_PER_REQUEST)


class ReviewCardGenerationRequest(BaseModel):
    document_title: str | None = None
    page_number: int = Field(ge=1)
    quiz_type: str
    question: str
    correct_answer: str
    user_answer: str
    quiz_explanation: str
    quiz_source_text: str

    @field_validator("document_title")
    @classmethod
    def empty_document_title_becomes_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("quiz_type")
    @classmethod
    def quiz_type_must_be_allowed(cls, value: str) -> str:
        stripped = value.strip()
        if stripped not in ALLOWED_QUIZ_TYPES:
            raise ValueError("unsupported quiz_type")
        return stripped

    @field_validator(
        "question",
        "correct_answer",
        "user_answer",
        "quiz_explanation",
        "quiz_source_text",
    )
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("required text must not be blank")
        return stripped


class ReviewCardContent(BaseModel):
    front: str
    back: str
    source_text: str | None = None

    @field_validator("front", "back")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("required text must not be blank")
        return stripped

    @field_validator("source_text")
    @classmethod
    def empty_source_text_becomes_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class LLMUsageMetadata(BaseModel):
    provider: str
    model: str
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost: Decimal = Field(ge=Decimal("0"))


class ExplanationResponse(BaseModel):
    content: ExplanationContent
    usage: LLMUsageMetadata


class GlossaryExtractionResponse(BaseModel):
    content: GlossaryExtractionContent
    usage: LLMUsageMetadata


class QuizGenerationResponse(BaseModel):
    content: QuizGenerationContent
    usage: LLMUsageMetadata


class ReviewCardGenerationResponse(BaseModel):
    content: ReviewCardContent
    usage: LLMUsageMetadata


class LLMProvider(Protocol):
    def generate_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        pass

    def generate_glossary_terms(
        self,
        request: GlossaryExtractionRequest,
    ) -> GlossaryExtractionResponse:
        pass

    def generate_quizzes(
        self,
        request: QuizGenerationRequest,
    ) -> QuizGenerationResponse:
        pass

    def generate_review_card(
        self,
        request: ReviewCardGenerationRequest,
    ) -> ReviewCardGenerationResponse:
        pass


class LLMProviderConfigError(ValueError):
    pass


class FakeLLMProvider:
    provider = FAKE_PROVIDER_NAME
    model = "fake-explanation-v1"

    def generate_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        prompt_tokens = self._count_prompt_tokens(request)
        content = ExplanationContent(
            summary=f"Fake explanation for: {request.selected_text}",
            key_points=[
                "This is a deterministic fake provider response.",
                "Use this response for local tests without external API calls.",
            ],
        )
        completion_tokens = self._count_words(content.summary) + sum(
            self._count_words(point) for point in content.key_points
        )

        return ExplanationResponse(
            content=content,
            usage=LLMUsageMetadata(
                provider=self.provider,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost=Decimal("0.000000"),
            ),
        )

    def generate_glossary_terms(
        self,
        request: GlossaryExtractionRequest,
    ) -> GlossaryExtractionResponse:
        prompt_tokens = self._count_prompt_tokens(request)
        content = GlossaryExtractionContent(
            terms=[
                GlossaryTermContent(
                    term="Fake glossary term",
                    definition=f"Fake definition for: {request.selected_text}",
                    source_text=request.selected_text,
                )
            ]
        )
        completion_tokens = sum(
            self._count_words(term.term)
            + self._count_words(term.definition)
            + self._count_words(term.source_text or "")
            for term in content.terms
        )

        return GlossaryExtractionResponse(
            content=content,
            usage=LLMUsageMetadata(
                provider=self.provider,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost=Decimal("0.000000"),
            ),
        )

    def generate_quizzes(
        self,
        request: QuizGenerationRequest,
    ) -> QuizGenerationResponse:
        prompt_tokens = self._count_prompt_tokens(request)
        content = QuizGenerationContent(
            quizzes=[
                QuizContent(
                    quiz_type=request.quiz_types[index % len(request.quiz_types)],
                    question=(
                        "Fake "
                        f"{request.quiz_types[index % len(request.quiz_types)]} "
                        f"question {index + 1} for: {request.selected_text}"
                    ),
                    answer=f"Fake answer for: {request.selected_text}",
                    explanation="This deterministic quiz is generated by the fake provider.",
                    source_text=request.selected_text,
                )
                for index in range(request.max_quizzes)
            ]
        )
        completion_tokens = sum(
            self._count_words(quiz.quiz_type)
            + self._count_words(quiz.question)
            + self._count_words(quiz.answer)
            + self._count_words(quiz.explanation)
            + self._count_words(quiz.source_text)
            for quiz in content.quizzes
        )

        return QuizGenerationResponse(
            content=content,
            usage=LLMUsageMetadata(
                provider=self.provider,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost=Decimal("0.000000"),
            ),
        )

    def generate_review_card(
        self,
        request: ReviewCardGenerationRequest,
    ) -> ReviewCardGenerationResponse:
        prompt_tokens = self._count_prompt_tokens(request)
        content = ReviewCardContent(
            front=f"Review this {request.quiz_type} question: {request.question}",
            back=(
                f"Correct answer: {request.correct_answer}\n"
                f"Explanation: {request.quiz_explanation}"
            ),
            source_text=request.quiz_source_text,
        )
        completion_tokens = (
            self._count_words(content.front)
            + self._count_words(content.back)
            + self._count_words(content.source_text or "")
        )

        return ReviewCardGenerationResponse(
            content=content,
            usage=LLMUsageMetadata(
                provider=self.provider,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                estimated_cost=Decimal("0.000000"),
            ),
        )

    def _count_prompt_tokens(
        self,
        request: (
            ExplanationRequest
            | GlossaryExtractionRequest
            | QuizGenerationRequest
            | ReviewCardGenerationRequest
        ),
    ) -> int:
        if isinstance(request, ReviewCardGenerationRequest):
            values = (
                request.document_title,
                str(request.page_number),
                request.quiz_type,
                request.question,
                request.correct_answer,
                request.user_answer,
                request.quiz_explanation,
                request.quiz_source_text,
            )
        else:
            values = (
                request.selected_text,
                request.surrounding_context,
                request.document_title,
            )

        return sum(
            self._count_words(value)
            for value in values
            if value is not None
        )

    def _count_words(self, value: str) -> int:
        return len(value.split())


class OpenAICompatibleLLMProvider:
    provider = OPENAI_COMPATIBLE_PROVIDER_NAME

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        client: Any | None = None,
    ) -> None:
        api_key = api_key.strip()
        model = model.strip()
        base_url = normalize_optional_env_value(base_url)
        if not api_key:
            raise LLMProviderConfigError(f"{OPENAI_API_KEY_ENV_VAR} is required.")
        if not model:
            raise LLMProviderConfigError(f"{OPENAI_MODEL_ENV_VAR} is required.")

        self.model = model
        self._client = client or self._build_client(api_key=api_key, base_url=base_url)

    def generate_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(request),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "infodrip_explanation",
                    "strict": True,
                    "schema": EXPLANATION_RESPONSE_SCHEMA,
                },
            },
            temperature=0,
        )
        content = self._first_message_content(completion)
        explanation = ExplanationContent.model_validate_json(content)
        prompt_tokens, completion_tokens, total_tokens = self._usage_tokens(completion)

        return ExplanationResponse(
            content=explanation,
            usage=LLMUsageMetadata(
                provider=self.provider,
                model=getattr(completion, "model", self.model) or self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=Decimal("0.000000"),
            ),
        )

    def generate_glossary_terms(
        self,
        request: GlossaryExtractionRequest,
    ) -> GlossaryExtractionResponse:
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._build_glossary_messages(request),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "infodrip_glossary_extraction",
                    "strict": True,
                    "schema": GLOSSARY_RESPONSE_SCHEMA,
                },
            },
            temperature=0,
        )
        content = self._first_message_content(completion)
        glossary = GlossaryExtractionContent.model_validate_json(content)
        prompt_tokens, completion_tokens, total_tokens = self._usage_tokens(completion)

        return GlossaryExtractionResponse(
            content=glossary,
            usage=LLMUsageMetadata(
                provider=self.provider,
                model=getattr(completion, "model", self.model) or self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=Decimal("0.000000"),
            ),
        )

    def generate_quizzes(
        self,
        request: QuizGenerationRequest,
    ) -> QuizGenerationResponse:
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._build_quiz_messages(request),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "infodrip_quiz_generation",
                    "strict": True,
                    "schema": QUIZ_RESPONSE_SCHEMA,
                },
            },
            temperature=0,
        )
        content = self._first_message_content(completion)
        quizzes = QuizGenerationContent.model_validate_json(content)
        prompt_tokens, completion_tokens, total_tokens = self._usage_tokens(completion)

        return QuizGenerationResponse(
            content=quizzes,
            usage=LLMUsageMetadata(
                provider=self.provider,
                model=getattr(completion, "model", self.model) or self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=Decimal("0.000000"),
            ),
        )

    def generate_review_card(
        self,
        request: ReviewCardGenerationRequest,
    ) -> ReviewCardGenerationResponse:
        completion = self._client.chat.completions.create(
            model=self.model,
            messages=self._build_review_card_messages(request),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "infodrip_review_card_generation",
                    "strict": True,
                    "schema": REVIEW_CARD_RESPONSE_SCHEMA,
                },
            },
            temperature=0,
        )
        content = self._first_message_content(completion)
        review_card = ReviewCardContent.model_validate_json(content)
        prompt_tokens, completion_tokens, total_tokens = self._usage_tokens(completion)

        return ReviewCardGenerationResponse(
            content=review_card,
            usage=LLMUsageMetadata(
                provider=self.provider,
                model=getattr(completion, "model", self.model) or self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=Decimal("0.000000"),
            ),
        )

    def _build_client(self, *, api_key: str, base_url: str | None) -> Any:
        from openai import OpenAI

        kwargs: dict[str, str] = {"api_key": api_key}
        if base_url is not None:
            kwargs["base_url"] = base_url
        return OpenAI(**kwargs)

    def _build_messages(self, request: ExplanationRequest) -> list[dict[str, str]]:
        user_parts = [
            "Explain this selected PDF passage for study.",
            f"Selected text:\n{request.selected_text}",
        ]
        if request.surrounding_context is not None:
            user_parts.append(f"Surrounding context:\n{request.surrounding_context}")
        if request.document_title is not None:
            user_parts.append(f"Document title:\n{request.document_title}")

        return [
            {
                "role": "system",
                "content": (
                    "You are InfoDrip's explanation task provider. Return only JSON "
                    "with summary and key_points. Do not include markdown."
                ),
            },
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

    def _build_glossary_messages(
        self,
        request: GlossaryExtractionRequest,
    ) -> list[dict[str, str]]:
        user_parts = [
            "Extract glossary terms from this selected PDF passage for study.",
            f"Selected text:\n{request.selected_text}",
            (
                "For source_text, return only a short phrase from the selected text "
                "that supports the term. Do not return full page context or long "
                "surrounding passages."
            ),
            f"Return at most {MAX_GLOSSARY_TERMS_PER_REQUEST} terms.",
        ]
        if request.surrounding_context is not None:
            user_parts.append(f"Surrounding context:\n{request.surrounding_context}")
        if request.document_title is not None:
            user_parts.append(f"Document title:\n{request.document_title}")

        return [
            {
                "role": "system",
                "content": (
                    "You are InfoDrip's glossary extraction task provider. Return "
                    "only JSON with terms. Do not include markdown."
                ),
            },
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

    def _build_quiz_messages(
        self,
        request: QuizGenerationRequest,
    ) -> list[dict[str, str]]:
        user_parts = [
            "Generate study quizzes from this selected PDF passage.",
            f"Selected text:\n{request.selected_text}",
            f"Allowed quiz types:\n{', '.join(request.quiz_types)}",
            f"Return at most {request.max_quizzes} quizzes.",
            (
                "If the selected text is too short or lacks enough distinct "
                "content, return fewer quizzes."
            ),
            (
                "Distribute quiz types as evenly as possible across the allowed "
                "quiz types."
            ),
            (
                "For source_text, return only a short phrase from the selected text "
                "that supports the quiz. Do not return full page context or long "
                "surrounding passages."
            ),
        ]
        if request.surrounding_context is not None:
            user_parts.append(
                f"Same-page surrounding context:\n{request.surrounding_context}"
            )
        if request.document_title is not None:
            user_parts.append(f"Document title:\n{request.document_title}")

        return [
            {
                "role": "system",
                "content": (
                    "You are InfoDrip's quiz generation task provider. Return only "
                    "JSON with quizzes. Use only the selected text and same-page "
                    "surrounding context provided in this request. Do not include "
                    "markdown."
                ),
            },
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

    def _build_review_card_messages(
        self,
        request: ReviewCardGenerationRequest,
    ) -> list[dict[str, str]]:
        user_parts = [
            "Generate one review card for a wrong quiz attempt.",
            f"Page number:\n{request.page_number}",
            f"Quiz type:\n{request.quiz_type}",
            f"Question:\n{request.question}",
            f"User answer:\n{request.user_answer}",
            f"Correct answer:\n{request.correct_answer}",
            f"Quiz explanation:\n{request.quiz_explanation}",
            f"Quiz source text:\n{request.quiz_source_text}",
            (
                "The front must be a self-contained review prompt. The back must "
                "include the correct answer and a short explanation. For "
                "source_text, return only a short supporting phrase when possible."
            ),
        ]
        if request.document_title is not None:
            user_parts.append(f"Document title:\n{request.document_title}")

        return [
            {
                "role": "system",
                "content": (
                    "You are InfoDrip's review card generation task provider. "
                    "Return only JSON with front, back, and source_text. Do not "
                    "include markdown."
                ),
            },
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

    def _first_message_content(self, completion: Any) -> str:
        choices = getattr(completion, "choices", None)
        if not choices:
            raise ValueError("LLM response did not include choices.")
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise ValueError("LLM response did not include message content.")
        return content

    def _usage_tokens(self, completion: Any) -> tuple[int, int, int]:
        usage = getattr(completion, "usage", None)
        prompt_tokens = self._usage_int(usage, "prompt_tokens")
        completion_tokens = self._usage_int(usage, "completion_tokens")
        total_tokens = self._usage_int(usage, "total_tokens")
        if total_tokens == 0:
            total_tokens = prompt_tokens + completion_tokens
        return prompt_tokens, completion_tokens, total_tokens

    def _usage_int(self, usage: Any, field_name: str) -> int:
        value = getattr(usage, field_name, 0)
        if value is None:
            return 0
        return int(value)


def build_llm_provider_from_env(environ: Mapping[str, str] | None = None) -> LLMProvider:
    env = os.environ if environ is None else environ
    provider_name = env_value(env, LLM_PROVIDER_ENV_VAR, default=FAKE_PROVIDER_NAME).lower()

    if provider_name == FAKE_PROVIDER_NAME:
        return FakeLLMProvider()
    if provider_name == OPENAI_COMPATIBLE_PROVIDER_NAME:
        return OpenAICompatibleLLMProvider(
            api_key=required_env_value(env, OPENAI_API_KEY_ENV_VAR),
            model=required_env_value(env, OPENAI_MODEL_ENV_VAR),
            base_url=env.get(OPENAI_BASE_URL_ENV_VAR),
        )

    raise LLMProviderConfigError(f"Unsupported LLM provider: {provider_name}")


def env_value(env: Mapping[str, str], name: str, *, default: str) -> str:
    value = normalize_optional_env_value(env.get(name))
    return value or default


def required_env_value(env: Mapping[str, str], name: str) -> str:
    value = normalize_optional_env_value(env.get(name))
    if value is None:
        raise LLMProviderConfigError(f"{name} is required.")
    return value


def normalize_optional_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
