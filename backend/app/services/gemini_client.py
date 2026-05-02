from typing import TypeVar

from fastapi.concurrency import run_in_threadpool
from google import genai

from app.core.settings import get_settings
from app.schemas.ai import ApiModel


T = TypeVar("T", bound=ApiModel)


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiGenerationError(RuntimeError):
    pass


async def generate_structured_content(
    *,
    system_instruction: str,
    user_prompt: str,
    response_schema: type[T],
    temperature: float = 0.1,
) -> T:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        response = await run_in_threadpool(
            client.models.generate_content,
            model=settings.gemini_model,
            contents=user_prompt,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "temperature": temperature,
            },
        )
    except Exception as exc:
        raise GeminiGenerationError("Gemini request failed.") from exc

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, response_schema):
        return parsed

    if parsed is not None:
        try:
            return response_schema.model_validate(parsed)
        except ValueError as exc:
            raise GeminiGenerationError(
                "Gemini returned invalid structured data."
            ) from exc

    if not response.text:
        raise GeminiGenerationError("Gemini returned an empty response.")

    try:
        return response_schema.model_validate_json(response.text)
    except ValueError as exc:
        raise GeminiGenerationError("Gemini returned invalid JSON.") from exc
