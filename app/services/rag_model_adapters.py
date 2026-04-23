"""Generation model adapters for RAG query — multi-provider 5-tier architecture.

Reuses the adapter pattern, MODEL_CANDIDATES dict, and error classification
from cv_parser_adapters.py. Each adapter calls the respective LLM SDK for
text generation (not CV parsing), returning (response_text, resolved_model).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.services.cv_parser_adapters import (
    ANTHROPIC_MODEL_CANDIDATES,
    OPENAI_MODEL_CANDIDATES,
    ProviderConfigurationError,
    ProviderInvocationError,
    ProviderParseError,
    TransientProviderError,
    _classify_status_error,
    _classify_transport_error,
    _is_model_not_found_error,
    _normalize_exception_message,
    _resolve_gemini_model_name,
)

# ---------------------------------------------------------------------------
# Generation-specific types
# ---------------------------------------------------------------------------

GenerationMessage = dict[
    str, str
]  # {"role": "user"|"assistant"|"system", "content": "..."}


class GenerationAdapter(ABC):
    """Common interface for generation providers."""

    provider_name: str
    api_key_env_var: str

    async def generate(
        self,
        messages: list[GenerationMessage],
        model_name: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> tuple[str, str]:
        """Generate a response and return (response_text, resolved_model_name)."""
        self._ensure_configured()
        return await self._generate(
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

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
    def _get_api_key(self) -> str | None: ...

    @abstractmethod
    async def _generate(
        self,
        messages: list[GenerationMessage],
        model_name: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, str]: ...


# ---------------------------------------------------------------------------
# Gemini Generation Adapter  (Tier 1: gemini-flash, Tier 4: gemini-pro)
# ---------------------------------------------------------------------------


class GeminiGenerationAdapter(GenerationAdapter):
    provider_name = "google"
    api_key_env_var = "GOOGLE_API_KEY"

    def _get_api_key(self) -> str | None:
        return settings.google_api_key

    async def _generate(
        self,
        messages: list[GenerationMessage],
        model_name: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, str]:
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                f"Set {self.api_key_env_var} to enable this tier.",
            )

        try:
            from google import genai
            from google.genai import errors, types
        except ImportError as exc:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                "Gemini SDK not installed. Add google-genai to dependencies.",
                original=exc,
            ) from exc

        resolved_model = await _resolve_gemini_model_name(model_name, api_key)
        client = genai.Client(api_key=api_key)

        # Build Gemini content list from messages
        gemini_contents: list[Any] = []
        system_text_parts: list[str] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_text_parts.append(content)
            elif role == "user":
                gemini_contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                gemini_contents.append({"role": "model", "parts": [{"text": content}]})

        system_instruction = (
            "\n\n".join(system_text_parts) if system_text_parts else None
        )

        try:
            async with client.aio as aio_client:
                config_kwargs: dict[str, Any] = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction

                response = await aio_client.models.generate_content(
                    model=resolved_model,
                    contents=gemini_contents,
                    config=types.GenerateContentConfig(**config_kwargs),
                )

            text = getattr(response, "text", None)
            if not text:
                raise ProviderParseError(
                    self.provider_name,
                    resolved_model,
                    "Gemini returned empty generation response.",
                )
            return text.strip(), resolved_model

        except ProviderInvocationError:
            raise
        except errors.APIError as exc:
            raise _classify_status_error(
                self.provider_name, resolved_model, exc
            ) from exc
        except (
            httpx.TimeoutException,
            TimeoutError,
            ConnectionResetError,
            OSError,
        ) as exc:
            raise _classify_transport_error(
                self.provider_name, resolved_model, exc
            ) from exc
        finally:
            client.close()


# ---------------------------------------------------------------------------
# OpenAI Generation Adapter  (Tier 2: gpt-5.4-mini, Tier 5: gpt-5.4)
# ---------------------------------------------------------------------------


class OpenAIGenerationAdapter(GenerationAdapter):
    provider_name = "openai"
    api_key_env_var = "OPENAI_API_KEY"

    def _get_api_key(self) -> str | None:
        return settings.openai_api_key

    async def _generate(
        self,
        messages: list[GenerationMessage],
        model_name: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, str]:
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                f"Set {self.api_key_env_var} to enable this tier.",
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
                "OpenAI SDK not installed. Add openai to dependencies.",
                original=exc,
            ) from exc

        candidate_models = OPENAI_MODEL_CANDIDATES.get(model_name, [model_name])
        last_error: ProviderInvocationError | None = None

        for candidate_model in candidate_models:
            try:
                async with AsyncOpenAI(api_key=api_key, max_retries=0) as client:
                    response = await client.chat.completions.create(
                        model=candidate_model,
                        messages=messages,  # type: ignore[arg-type]
                        temperature=temperature,
                        max_completion_tokens=max_tokens,
                    )

                text = (response.choices[0].message.content or "").strip()
                if not text:
                    raise ProviderParseError(
                        self.provider_name,
                        candidate_model,
                        "OpenAI returned empty generation response.",
                    )
                return text, candidate_model

            except ProviderInvocationError as exc:
                last_error = exc
                if (
                    _is_model_not_found_error(exc)
                    and candidate_model != candidate_models[-1]
                ):
                    logger.info(
                        "Falling back to alternate OpenAI generation model candidate",
                        extra={
                            "requestedModel": model_name,
                            "triedModel": candidate_model,
                        },
                    )
                    continue
                raise
            except RateLimitError as exc:
                last_error = TransientProviderError(
                    self.provider_name,
                    candidate_model,
                    _normalize_exception_message(exc),
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

        if last_error is not None:
            raise last_error
        raise ProviderConfigurationError(
            self.provider_name,
            model_name,
            "No OpenAI generation model candidate could be resolved.",
        )


# ---------------------------------------------------------------------------
# Anthropic Generation Adapter  (Tier 3: claude-4.5-haiku)
# ---------------------------------------------------------------------------


class AnthropicGenerationAdapter(GenerationAdapter):
    provider_name = "anthropic"
    api_key_env_var = "CLAUDE_API_KEY"

    def _get_api_key(self) -> str | None:
        return settings.claude_api_key

    async def _generate(
        self,
        messages: list[GenerationMessage],
        model_name: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, str]:
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderConfigurationError(
                self.provider_name,
                model_name,
                f"Set {self.api_key_env_var} to enable this tier.",
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
                "Anthropic SDK not installed. Add anthropic to dependencies.",
                original=exc,
            ) from exc

        candidate_models = ANTHROPIC_MODEL_CANDIDATES.get(model_name, [model_name])
        last_error: ProviderInvocationError | None = None

        # Separate system and conversation messages
        system_parts = [m["content"] for m in messages if m.get("role") == "system"]
        conv_messages = [m for m in messages if m.get("role") != "system"]
        system_prompt = "\n\n".join(system_parts) if system_parts else None

        for candidate_model in candidate_models:
            try:
                async with AsyncAnthropic(api_key=api_key, max_retries=0) as client:
                    kwargs: dict[str, Any] = {
                        "model": candidate_model,
                        "max_tokens": max_tokens,
                        "messages": conv_messages,  # type: ignore[arg-type]
                        "temperature": temperature,
                    }
                    if system_prompt:
                        kwargs["system"] = system_prompt

                    response = await client.messages.create(**kwargs)

                text_parts = [
                    block.text
                    for block in getattr(response, "content", [])
                    if getattr(block, "type", None) == "text"
                    and getattr(block, "text", None)
                ]
                text = "".join(text_parts).strip()
                if not text:
                    raise ProviderParseError(
                        self.provider_name,
                        candidate_model,
                        "Anthropic returned empty generation response.",
                    )
                return text, candidate_model

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

        if last_error is not None:
            raise last_error
        raise ProviderConfigurationError(
            self.provider_name,
            model_name,
            "No Anthropic generation model candidate could be resolved.",
        )


# ---------------------------------------------------------------------------
# Registry: modelMode → (GenerationAdapter, model_name)
# ---------------------------------------------------------------------------

#: Map từ modelMode string → (adapter instance, general model name)
MODEL_MODE_REGISTRY: dict[str, tuple[GenerationAdapter, str]] = {
    # 💚 Lite — model cụ thể
    "gemini-flash": (GeminiGenerationAdapter(), "gemini-flash"),
    "gpt-mini": (OpenAIGenerationAdapter(), "gpt-5.4-mini"),
    "claude-haiku": (AnthropicGenerationAdapter(), "claude-4.5-haiku"),
    # 🔶 Pro — model cụ thể
    "gemini-pro": (GeminiGenerationAdapter(), "gemini-pro"),
    "gpt-full": (OpenAIGenerationAdapter(), "gpt-5.4"),
}

#: Map từ auto mode → danh sách (adapter, model_name) theo thứ tự fallback
AUTO_MODE_CHAINS: dict[str, list[tuple[GenerationAdapter, str]]] = {
    "auto-lite": [
        (GeminiGenerationAdapter(), "gemini-flash"),
        (OpenAIGenerationAdapter(), "gpt-5.4-mini"),
        (AnthropicGenerationAdapter(), "claude-4.5-haiku"),
    ],
    "auto-pro": [
        (GeminiGenerationAdapter(), "gemini-pro"),
        (OpenAIGenerationAdapter(), "gpt-5.4"),
    ],
}

VALID_MODEL_MODES = set(MODEL_MODE_REGISTRY) | set(AUTO_MODE_CHAINS)


def get_model_budget(model_mode: str) -> int:
    """Trả về token budget cho chat history theo model mode."""
    if model_mode in ("gemini-pro", "gpt-full", "auto-pro"):
        return settings.context_budget_pro
    # Lite models — dùng budget nhỏ nhất (Gemini Flash)
    return settings.context_budget_lite
