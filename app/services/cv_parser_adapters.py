"""Provider adapters for the multi-tier CV parser."""

from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.models.cv_models import ParsedCV

CV_PARSE_PROMPT = """
Extract the candidate's CV from the uploaded PDF into the provided JSON schema.

Rules:
- Use only information explicitly present in the PDF.
- Do not invent values. Use null for unknown scalar fields and [] for unknown lists.
- Normalize startDate and endDate to YYYY-MM whenever a month is available.
- Use "present" only when the CV clearly indicates an ongoing role or education entry.
- Keep summary concise and factual.
- Put the CV's plain extracted text into rawText.
- Return only the structured data required by the schema.
""".strip()

CV_PARSE_SCHEMA = ParsedCV.model_json_schema()
ANTHROPIC_SCHEMA_PROMPT = (
    f"{CV_PARSE_PROMPT}\n\n"
    "Return only valid JSON matching this schema:\n"
    f"{json.dumps(CV_PARSE_SCHEMA, ensure_ascii=False)}"
)

OPENAI_MODEL_CANDIDATES: dict[str, list[str]] = {
    "gpt-5.4-mini": ["gpt-5.4-mini", "gpt-5-mini"],
    # Tier 5 — Pro
    "gpt-5.4": ["gpt-5.4", "gpt-5.4-pro"],
}

ANTHROPIC_MODEL_CANDIDATES: dict[str, list[str]] = {
    "claude-4.5-haiku": ["claude-4.5-haiku", "claude-3-5-haiku-latest"],
}

GEMINI_MODEL_CANDIDATES: dict[str, list[str]] = {
    "gemini-flash": [
        "gemini-flash",
        "gemini-3.1-flash",
        "gemini-3.1-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ],
    # Tier 4 — Pro
    "gemini-pro": [
        "gemini-3.1-pro-preview",
        "gemini-3.1-pro",
        "gemini-pro",
    ],
}

_GEMINI_MODEL_RESOLUTION_CACHE: dict[str, str] = {}


class ProviderInvocationError(Exception):
    """Base provider exception that carries normalized metadata."""

    def __init__(
        self,
        provider: str,
        model: str,
        message: str,
        *,
        status_code: int | None = None,
        original: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.original = original


class TransientProviderError(ProviderInvocationError):
    """Retryable provider error."""


class NonRetryableProviderError(ProviderInvocationError):
    """Non-retryable provider error."""


class ProviderConfigurationError(NonRetryableProviderError):
    """Provider configuration problem such as missing env var or SDK."""


class ProviderParseError(NonRetryableProviderError):
    """Structured-output validation or parse failure."""


class ProviderAdapter(ABC):
    """Common interface for parser providers."""

    provider_name: str
    api_key_env_var: str

    async def parse(self, cv_bytes: bytes, model_name: str) -> tuple[ParsedCV, str]:
        self._ensure_configured()
        return await self._parse(cv_bytes=cv_bytes, model_name=model_name)

    def _ensure_configured(self) -> None:
        if not self._get_api_key():
            raise ProviderConfigurationError(
                self.provider_name,
                "<unconfigured>",
                (
                    f"{self.provider_name} provider is not configured. "
                    f"Set environment variable {self.api_key_env_var}."
                ),
            )

    @abstractmethod
    def _get_api_key(self) -> str | None:
        """Return the provider API key."""

    @abstractmethod
    async def _parse(self, cv_bytes: bytes, model_name: str) -> tuple[ParsedCV, str]:
        """Perform one provider parse attempt and return parsed CV + resolved model."""


def _extract_status_code(exc: BaseException) -> int | None:
    for attr in ("status_code", "code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    return status_code if isinstance(status_code, int) else None


def _normalize_exception_message(exc: BaseException) -> str:
    message = str(exc).strip()
    return message or exc.__class__.__name__


def _is_model_not_found_error(exc: ProviderInvocationError) -> bool:
    if exc.status_code not in {400, 404}:
        return False
    message = str(exc).lower()
    return "model" in message and any(
        phrase in message
        for phrase in ("not found", "does not exist", "unsupported", "unknown")
    )


def _strip_json_fences(payload: str) -> str:
    stripped = payload.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _classify_status_error(
    provider: str,
    model: str,
    exc: BaseException,
) -> ProviderInvocationError:
    status_code = _extract_status_code(exc)
    message = _normalize_exception_message(exc)
    if status_code in {408, 409, 429} or (
        status_code is not None and status_code >= 500
    ):
        return TransientProviderError(
            provider,
            model,
            message,
            status_code=status_code,
            original=exc,
        )
    return NonRetryableProviderError(
        provider,
        model,
        message,
        status_code=status_code,
        original=exc,
    )


def _classify_transport_error(
    provider: str,
    model: str,
    exc: BaseException,
) -> TransientProviderError:
    return TransientProviderError(
        provider,
        model,
        _normalize_exception_message(exc),
        original=exc,
    )


async def _list_gemini_generate_content_models(client: Any) -> set[str]:
    async with client.aio as aio_client:
        pager = await aio_client.models.list(config={"page_size": 100})
        available_models: set[str] = set()
        async for model in pager:
            model_name = getattr(model, "name", "") or ""
            supported_actions = set(getattr(model, "supported_actions", []) or [])
            normalized_name = model_name.removeprefix("models/")
            if normalized_name and "generateContent" in supported_actions:
                available_models.add(normalized_name)
        return available_models


async def _resolve_gemini_model_name(requested_model: str, api_key: str) -> str:
    cached_model = _GEMINI_MODEL_RESOLUTION_CACHE.get(requested_model)
    if cached_model:
        return cached_model

    try:
        from google import genai
        from google.genai import errors
    except ImportError as exc:
        raise ProviderConfigurationError(
            "google",
            requested_model,
            "Gemini SDK is not installed. Install dependency for GOOGLE_API_KEY tier.",
            original=exc,
        ) from exc

    candidates = GEMINI_MODEL_CANDIDATES.get(requested_model, [requested_model])
    client = genai.Client(api_key=api_key)
    try:
        try:
            available_models = await _list_gemini_generate_content_models(client)
        except errors.APIError as exc:
            raise _classify_status_error("google", requested_model, exc) from exc
        except (
            httpx.TimeoutException,
            httpx.TransportError,
            TimeoutError,
            ConnectionResetError,
            OSError,
        ) as exc:
            raise _classify_transport_error("google", requested_model, exc) from exc
    finally:
        client.close()

    for candidate in candidates:
        if candidate in available_models:
            _GEMINI_MODEL_RESOLUTION_CACHE[requested_model] = candidate
            if candidate != requested_model:
                logger.info(
                    "Resolved Gemini model alias",
                    extra={
                        "provider": "google",
                        "requestedModel": requested_model,
                        "resolvedModel": candidate,
                    },
                )
            return candidate

    raise ProviderConfigurationError(
        "google",
        requested_model,
        (
            f"No Gemini model available for requested model '{requested_model}'. "
            f"Candidates tried: {candidates}."
        ),
    )


class GeminiProviderAdapter(ProviderAdapter):
    provider_name = "google"
    api_key_env_var = "GOOGLE_API_KEY"

    def _get_api_key(self) -> str | None:
        return settings.google_api_key

    async def _parse(self, cv_bytes: bytes, model_name: str) -> tuple[ParsedCV, str]:
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                f"Set environment variable {self.api_key_env_var} to enable this tier.",
            )

        try:
            from google import genai
            from google.genai import errors, types
        except ImportError as exc:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                "Gemini SDK is not installed. Add google-genai to the environment.",
                original=exc,
            ) from exc

        resolved_model_name = await _resolve_gemini_model_name(model_name, api_key)
        uploaded_file = None
        client = genai.Client(api_key=api_key)

        try:
            async with client.aio as aio_client:
                uploaded_file = await aio_client.files.upload(
                    file=BytesIO(cv_bytes),
                    config=types.UploadFileConfig(
                        mime_type="application/pdf",
                        display_name=f"{resolved_model_name}-cv.pdf",
                    ),
                )

                response = await aio_client.models.generate_content(
                    model=resolved_model_name,
                    contents=[CV_PARSE_PROMPT, uploaded_file],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ParsedCV,
                        temperature=0,
                    ),
                )

                parsed_payload = getattr(response, "parsed", None)
                if isinstance(parsed_payload, ParsedCV):
                    parsed_cv = parsed_payload
                elif parsed_payload is not None:
                    parsed_cv = ParsedCV.model_validate(parsed_payload)
                elif getattr(response, "text", None):
                    parsed_cv = ParsedCV.model_validate_json(response.text)
                else:
                    raise ProviderParseError(
                        self.provider_name,
                        resolved_model_name,
                        "Gemini returned an empty structured response.",
                    )

                return parsed_cv, resolved_model_name
        except ProviderInvocationError:
            raise
        except errors.APIError as exc:
            raise _classify_status_error(
                self.provider_name, resolved_model_name, exc
            ) from exc
        except (
            httpx.TimeoutException,
            TimeoutError,
            ConnectionResetError,
            OSError,
        ) as exc:
            raise _classify_transport_error(
                self.provider_name, resolved_model_name, exc
            ) from exc
        except ValidationError as exc:
            raise ProviderParseError(
                self.provider_name,
                resolved_model_name,
                "Gemini returned payload that failed ParsedCV validation.",
                original=exc,
            ) from exc
        finally:
            try:
                if uploaded_file is not None:
                    cleanup_client = genai.Client(api_key=api_key)
                    try:
                        async with cleanup_client.aio as cleanup_aio_client:
                            await cleanup_aio_client.files.delete(
                                name=uploaded_file.name
                            )
                    finally:
                        cleanup_client.close()
            except Exception:
                logger.exception(
                    "Failed to delete uploaded Gemini file",
                    extra={
                        "provider": self.provider_name,
                        "model": resolved_model_name,
                        "uploadedFileName": getattr(uploaded_file, "name", None),
                    },
                )
            finally:
                client.close()


class OpenAIProviderAdapter(ProviderAdapter):
    provider_name = "openai"
    api_key_env_var = "OPENAI_API_KEY"

    def _get_api_key(self) -> str | None:
        return settings.openai_api_key

    async def _parse(self, cv_bytes: bytes, model_name: str) -> tuple[ParsedCV, str]:
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                f"Set environment variable {self.api_key_env_var} to enable this tier.",
            )

        try:
            from openai import (
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                AsyncOpenAI,
                RateLimitError,
            )
        except ImportError as exc:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                "OpenAI SDK is not installed. Add openai to the environment.",
                original=exc,
            ) from exc

        candidate_models = OPENAI_MODEL_CANDIDATES.get(model_name, [model_name])
        last_error: ProviderInvocationError | None = None
        pdf_data = base64.b64encode(cv_bytes).decode("ascii")
        response_schema = {
            "type": "json_schema",
            "name": "parsed_cv",
            "strict": False,
            "schema": CV_PARSE_SCHEMA,
        }

        for candidate_model in candidate_models:
            try:
                async with AsyncOpenAI(api_key=api_key, max_retries=0) as client:
                    response = await client.responses.create(
                        model=candidate_model,
                        input=[
                            {
                                "role": "developer",
                                "content": [
                                    {"type": "input_text", "text": CV_PARSE_PROMPT}
                                ],
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_file",
                                        "filename": "cv.pdf",
                                        "file_data": pdf_data,
                                    },
                                    {
                                        "type": "input_text",
                                        "text": "Return only JSON matching the provided schema.",
                                    },
                                ],
                            },
                        ],
                        text={"format": response_schema},
                    )
                payload = (getattr(response, "output_text", None) or "").strip()
                if not payload:
                    raise ProviderParseError(
                        self.provider_name,
                        candidate_model,
                        "OpenAI returned an empty structured response.",
                    )
                parsed_cv = ParsedCV.model_validate_json(payload)
                return parsed_cv, candidate_model
            except ProviderInvocationError as exc:
                last_error = exc
                if (
                    _is_model_not_found_error(exc)
                    and candidate_model != candidate_models[-1]
                ):
                    logger.info(
                        "Falling back to alternate OpenAI model candidate",
                        extra={
                            "provider": self.provider_name,
                            "requestedModel": model_name,
                            "resolvedModel": candidate_model,
                        },
                    )
                    continue
                raise
            except RateLimitError as exc:
                last_error = TransientProviderError(
                    self.provider_name,
                    candidate_model,
                    _normalize_exception_message(exc),
                    status_code=_extract_status_code(exc),
                    original=exc,
                )
                raise last_error from exc
            except (APITimeoutError, APIConnectionError) as exc:
                last_error = _classify_transport_error(
                    self.provider_name, candidate_model, exc
                )
                raise last_error from exc
            except APIStatusError as exc:
                last_error = _classify_status_error(
                    self.provider_name, candidate_model, exc
                )
                if (
                    _is_model_not_found_error(last_error)
                    and candidate_model != candidate_models[-1]
                ):
                    continue
                raise last_error from exc
            except (
                httpx.TimeoutException,
                TimeoutError,
                ConnectionResetError,
                OSError,
            ) as exc:
                last_error = _classify_transport_error(
                    self.provider_name, candidate_model, exc
                )
                raise last_error from exc
            except ValidationError as exc:
                raise ProviderParseError(
                    self.provider_name,
                    candidate_model,
                    "OpenAI returned payload that failed ParsedCV validation.",
                    original=exc,
                ) from exc

        if last_error is not None:
            raise last_error
        raise ProviderConfigurationError(
            self.provider_name,
            model_name,
            "No OpenAI model candidate could be resolved.",
        )


class AnthropicProviderAdapter(ProviderAdapter):
    provider_name = "anthropic"
    api_key_env_var = "CLAUDE_API_KEY"

    def _get_api_key(self) -> str | None:
        return settings.claude_api_key

    async def _parse(self, cv_bytes: bytes, model_name: str) -> tuple[ParsedCV, str]:
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                f"Set environment variable {self.api_key_env_var} to enable this tier.",
            )

        try:
            from anthropic import (
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                AsyncAnthropic,
                RateLimitError,
            )
        except ImportError as exc:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                "Anthropic SDK is not installed. Add anthropic to the environment.",
                original=exc,
            ) from exc

        candidate_models = ANTHROPIC_MODEL_CANDIDATES.get(model_name, [model_name])
        last_error: ProviderInvocationError | None = None
        pdf_data = base64.b64encode(cv_bytes).decode("ascii")

        for candidate_model in candidate_models:
            try:
                async with AsyncAnthropic(api_key=api_key, max_retries=0) as client:
                    response = await client.messages.create(
                        model=candidate_model,
                        max_tokens=8192,
                        system=ANTHROPIC_SCHEMA_PROMPT,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "document",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "application/pdf",
                                            "data": pdf_data,
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": "Extract the CV and return only JSON.",
                                    },
                                ],
                            }
                        ],
                    )

                payload_parts = [
                    block.text
                    for block in getattr(response, "content", [])
                    if getattr(block, "type", None) == "text"
                    and getattr(block, "text", None)
                ]
                payload = _strip_json_fences("".join(payload_parts))
                if not payload:
                    raise ProviderParseError(
                        self.provider_name,
                        candidate_model,
                        "Anthropic returned an empty structured response.",
                    )

                parsed_cv = ParsedCV.model_validate_json(payload)
                return parsed_cv, candidate_model
            except ProviderInvocationError as exc:
                last_error = exc
                if (
                    _is_model_not_found_error(exc)
                    and candidate_model != candidate_models[-1]
                ):
                    continue
                raise
            except RateLimitError as exc:
                last_error = TransientProviderError(
                    self.provider_name,
                    candidate_model,
                    _normalize_exception_message(exc),
                    status_code=_extract_status_code(exc),
                    original=exc,
                )
                raise last_error from exc
            except (APITimeoutError, APIConnectionError) as exc:
                last_error = _classify_transport_error(
                    self.provider_name, candidate_model, exc
                )
                raise last_error from exc
            except APIStatusError as exc:
                last_error = _classify_status_error(
                    self.provider_name, candidate_model, exc
                )
                if (
                    _is_model_not_found_error(last_error)
                    and candidate_model != candidate_models[-1]
                ):
                    continue
                raise last_error from exc
            except (
                httpx.TimeoutException,
                TimeoutError,
                ConnectionResetError,
                OSError,
            ) as exc:
                last_error = _classify_transport_error(
                    self.provider_name, candidate_model, exc
                )
                raise last_error from exc
            except ValidationError as exc:
                raise ProviderParseError(
                    self.provider_name,
                    candidate_model,
                    "Anthropic returned payload that failed ParsedCV validation.",
                    original=exc,
                ) from exc

        if last_error is not None:
            raise last_error
        raise ProviderConfigurationError(
            self.provider_name,
            model_name,
            "No Anthropic model candidate could be resolved.",
        )
