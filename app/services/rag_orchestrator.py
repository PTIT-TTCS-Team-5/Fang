"""RAG Generation Orchestrator — điều phối 5-tier model invocation.

Xử lý 2 luồng:
1. Specific model mode (5 mode): gọi đúng 1 adapter, retry tenacity, không fallback.
2. Auto mode (auto-lite / auto-pro): chạy fallback chain, retry + quality gate mỗi tier.

API chính: `invoke_generation(messages, model_mode)` → (response_text, model_used, fallback_path)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

import tenacity

from app.core.config import settings
from app.core.logging import logger
from app.services.cv_parser_adapters import (
    ProviderInvocationError,
    TransientProviderError,
)
from app.services.rag_model_adapters import (
    AUTO_MODE_CHAINS,
    MODEL_MODE_REGISTRY,
    VALID_MODEL_MODES,
    GenerationAdapter,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FALLBACK_REASON_LOW_CONFIDENCE: Final[str] = "low_confidence_output"
FALLBACK_REASON_PROVIDER_ERROR: Final[str] = "provider_error"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GenerationError(Exception):
    """Raised when all adapters in the chain fail."""


class InvalidModelModeError(ValueError):
    """Raised when modelMode is not recognized."""


# ---------------------------------------------------------------------------
# Internal types
# ---------------------------------------------------------------------------


@dataclass
class _GenerationAttempt:
    tier: int
    provider: str
    model: str
    status: str  # "succeeded" | "failed"
    fallback_reason: str = ""


@dataclass
class GenerationTrace:
    response: str
    model: str  # resolved model name actually used
    model_mode: str
    fallback_path: str
    latency_ms: int
    attempts: list[_GenerationAttempt] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Quality gate for generation output
# ---------------------------------------------------------------------------


def _generation_quality_gate(response_text: str) -> bool:
    """Heuristic quality check. Trả True nếu response đạt chất lượng tối thiểu."""
    text = response_text.strip()
    if len(text) < 5:
        return False
    refusal_signals = [
        "tôi không thể",
        "tôi không biết",
        "i cannot",
        "i don't know",
        "không có thông tin",
        "no information",
        "không đủ dữ liệu",
    ]
    if any(s in text.lower() for s in refusal_signals):
        return False
    return True


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def _make_retry_callback(provider: str, model: str) -> tenacity.AsyncRetrying:
    """Tạo tenacity retry chỉ retry transient errors."""
    if not settings.rag_generation_retry_enabled:
        # Return a no-op retrying that runs once
        return tenacity.AsyncRetrying(stop=tenacity.stop_after_attempt(1), reraise=True)

    return tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(settings.rag_generation_retry_attempts),
        wait=tenacity.wait_exponential(
            min=settings.rag_generation_retry_base_seconds,
            max=settings.rag_generation_retry_max_seconds,
        ),
        retry=tenacity.retry_if_exception_type(TransientProviderError),
        reraise=True,
        before_sleep=tenacity.before_sleep_log(logger, 10),  # DEBUG level
    )


# ---------------------------------------------------------------------------
# Specific model mode — gọi đúng adapter, retry, không fallback
# ---------------------------------------------------------------------------


async def _invoke_specific(
    adapter: GenerationAdapter,
    model_name: str,
    messages: list[dict[str, str]],
    model_mode: str,
) -> GenerationTrace:
    """Gọi 1 adapter cụ thể với tenacity retry. Không fallback khi fail."""
    start_ms = _now_ms()
    attempt_record = _GenerationAttempt(
        tier=_tier_from_mode(model_mode),
        provider=adapter.provider_name,
        model=model_name,
        status="failed",
    )

    try:
        retrying = _make_retry_callback(adapter.provider_name, model_name)
        async for attempt in retrying:
            with attempt:
                response_text, resolved_model = await adapter.generate(
                    messages=messages,
                    model_name=model_name,
                )

        attempt_record.status = "succeeded"
        attempt_record.model = resolved_model
        return GenerationTrace(
            response=response_text,
            model=resolved_model,
            model_mode=model_mode,
            fallback_path=f"{model_mode}:{adapter.provider_name}:{resolved_model}(succeeded)",
            latency_ms=_now_ms() - start_ms,
            attempts=[attempt_record],
        )

    except ProviderInvocationError as exc:
        attempt_record.fallback_reason = FALLBACK_REASON_PROVIDER_ERROR
        logger.error(
            "Generation failed on specific model mode — no fallback",
            extra={
                "modelMode": model_mode,
                "provider": adapter.provider_name,
                "model": model_name,
                "error": str(exc),
            },
        )
        raise GenerationError(
            f"Generation failed for modelMode='{model_mode}' "
            f"(provider={adapter.provider_name}, model={model_name}): {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Auto mode — fallback chain + quality gate
# ---------------------------------------------------------------------------


async def _invoke_auto(
    chain: list[tuple[GenerationAdapter, str]],
    messages: list[dict[str, str]],
    model_mode: str,
) -> GenerationTrace:
    """Chạy fallback chain theo thứ tự. Mỗi tier retry, nếu fail → tier tiếp."""
    start_ms = _now_ms()
    attempts: list[_GenerationAttempt] = []
    path_parts: list[str] = []

    for tier_idx, (adapter, model_name) in enumerate(chain, start=1):
        attempt_record = _GenerationAttempt(
            tier=tier_idx,
            provider=adapter.provider_name,
            model=model_name,
            status="failed",
        )

        try:
            retrying = _make_retry_callback(adapter.provider_name, model_name)
            response_text: str | None = None
            resolved_model: str = model_name

            async for attempt in retrying:
                with attempt:
                    response_text, resolved_model = await adapter.generate(
                        messages=messages,
                        model_name=model_name,
                    )

            attempt_record.model = resolved_model

            # Quality gate
            if not _generation_quality_gate(response_text or ""):
                attempt_record.status = "failed"
                attempt_record.fallback_reason = FALLBACK_REASON_LOW_CONFIDENCE
                attempts.append(attempt_record)
                path_parts.append(
                    f"tier{tier_idx}:{adapter.provider_name}:{resolved_model}"
                    f"(low_quality→fallback)"
                )
                logger.info(
                    "Generation quality gate failed — trying next tier",
                    extra={
                        "modelMode": model_mode,
                        "tierIndex": tier_idx,
                        "provider": adapter.provider_name,
                        "model": resolved_model,
                    },
                )
                continue

            # Quality OK → done
            attempt_record.status = "succeeded"
            attempts.append(attempt_record)
            path_parts.append(
                f"tier{tier_idx}:{adapter.provider_name}:{resolved_model}(succeeded)"
            )

            return GenerationTrace(
                response=response_text or "",
                model=f"{adapter.provider_name}:{resolved_model}",
                model_mode=model_mode,
                fallback_path="→".join(path_parts),
                latency_ms=_now_ms() - start_ms,
                attempts=attempts,
            )

        except ProviderInvocationError as exc:
            attempt_record.fallback_reason = FALLBACK_REASON_PROVIDER_ERROR
            attempts.append(attempt_record)
            path_parts.append(
                f"tier{tier_idx}:{adapter.provider_name}:{model_name}"
                f"({type(exc).__name__}→fallback)"
            )
            logger.info(
                "Generation tier failed — trying next tier",
                extra={
                    "modelMode": model_mode,
                    "tierIndex": tier_idx,
                    "provider": adapter.provider_name,
                    "model": model_name,
                    "error": str(exc),
                },
            )
            continue

    raise GenerationError(
        f"All tiers in auto chain '{model_mode}' failed. "
        f"Path: {'→'.join(path_parts)}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def invoke_generation(
    messages: list[dict[str, str]],
    model_mode: str,
) -> GenerationTrace:
    """Điểm vào duy nhất để gọi generation.

    Args:
        messages: Danh sách message theo chuẩn OpenAI-style
                  [{"role": "system|user|assistant", "content": "..."}]
        model_mode: 1 trong 7 mode hợp lệ (xem VALID_MODEL_MODES)

    Returns:
        GenerationTrace với response, model used, fallback path, latency.

    Raises:
        InvalidModelModeError: modelMode không hợp lệ.
        GenerationError: Tất cả tier fail.
    """
    if model_mode not in VALID_MODEL_MODES:
        raise InvalidModelModeError(
            f"Invalid modelMode='{model_mode}'. "
            f"Valid values: {sorted(VALID_MODEL_MODES)}"
        )

    logger.info(
        "invoke_generation started",
        extra={"modelMode": model_mode, "messageCount": len(messages)},
    )

    # Specific model mode
    if model_mode in MODEL_MODE_REGISTRY:
        adapter, model_name = MODEL_MODE_REGISTRY[model_mode]
        return await _invoke_specific(adapter, model_name, messages, model_mode)

    # Auto mode
    chain = AUTO_MODE_CHAINS[model_mode]
    return await _invoke_auto(chain, messages, model_mode)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_ms() -> int:
    import time

    return int(time.monotonic() * 1000)


def _tier_from_mode(model_mode: str) -> int:
    """Map specific model mode sang tier index (để ghi log)."""
    _MODE_TO_TIER = {
        "gemini-flash": 1,
        "gpt-mini": 2,
        "claude-haiku": 3,
        "gemini-pro": 4,
        "gpt-full": 5,
    }
    return _MODE_TO_TIER.get(model_mode, 0)
