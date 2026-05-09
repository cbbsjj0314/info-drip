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
