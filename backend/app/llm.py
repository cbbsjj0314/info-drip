from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, Field, field_validator


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


class LLMProvider(Protocol):
    def generate_explanation(self, request: ExplanationRequest) -> ExplanationResponse:
        pass


class FakeLLMProvider:
    provider = "fake"
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

    def _count_prompt_tokens(self, request: ExplanationRequest) -> int:
        return sum(
            self._count_words(value)
            for value in (
                request.selected_text,
                request.surrounding_context,
                request.document_title,
            )
            if value is not None
        )

    def _count_words(self, value: str) -> int:
        return len(value.split())
