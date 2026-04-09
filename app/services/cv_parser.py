"""CV parser orchestration with multi-provider tiering, retry, and quality gates."""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from time import monotonic
from typing import Any, Awaitable, Callable, Protocol, Sequence

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import logger
from app.models.cv_models import ParsedCV
from app.services.cv_parser_adapters import (
    AnthropicProviderAdapter,
    GeminiProviderAdapter,
    NonRetryableProviderError,
    OpenAIProviderAdapter,
    ProviderInvocationError,
    ProviderParseError,
    TransientProviderError,
)

FALLBACK_REASON_TRANSIENT = "transient_error"
FALLBACK_REASON_NON_RETRYABLE = "non_retryable_error"
FALLBACK_REASON_LOW_CONFIDENCE = "low_confidence_output"


class CVParsingError(Exception):
    """Raised when all parser tiers fail or produce low-quality output."""


class SupportsParse(Protocol):
    """Protocol used by the parser orchestrator for dependency injection."""

    provider_name: str

    async def parse(self, cv_bytes: bytes, model_name: str) -> tuple[ParsedCV, str]:
        """Return parsed CV and resolved model name."""


SleepFn = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class ParserTier:
    tier_index: int
    model_name: str
    provider: SupportsParse


@dataclass(frozen=True)
class ParserPolicyConfig:
    retry_enabled: bool
    retry_attempts: int
    retry_base_seconds: float
    retry_max_seconds: float
    min_rawtext_length: int
    min_section_signals: int
    sleep: SleepFn = asyncio.sleep

    @classmethod
    def from_settings(cls) -> "ParserPolicyConfig":
        return cls(
            retry_enabled=settings.parser_retry_enabled,
            retry_attempts=max(1, settings.parser_retry_attempts),
            retry_base_seconds=max(0.0, settings.parser_retry_base_seconds),
            retry_max_seconds=max(0.0, settings.parser_retry_max_seconds),
            min_rawtext_length=max(1, settings.parser_quality_min_rawtext_length),
            min_section_signals=max(1, settings.parser_quality_min_section_signals),
        )


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    reasons: tuple[str, ...]
    section_signals: int
    raw_text_length: int
    has_candidate_signal: bool


@dataclass(frozen=True)
class ParserAttemptRecord:
    tier_index: int
    provider: str
    model: str
    duration_ms: int
    retry_count: int
    fallback_reason: str | None
    status: str
    quality_reasons: tuple[str, ...] = ()
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ParserTrace:
    parser_ver: str | None
    fallback_path: str
    selected_tier_index: int | None
    attempts: tuple[ParserAttemptRecord, ...]


_LAST_PARSE_TRACE: ContextVar[ParserTrace | None] = ContextVar(
    "last_parser_trace", default=None
)


def _default_tiers() -> tuple[ParserTier, ...]:
    return (
        ParserTier(1, "gemini-flash", GeminiProviderAdapter()),
        ParserTier(2, "gpt-5.4-mini", OpenAIProviderAdapter()),
        ParserTier(3, "claude-4.5-haiku", AnthropicProviderAdapter()),
    )


def _build_quality_gate(
    parsed_cv: ParsedCV,
    *,
    min_rawtext_length: int,
    min_section_signals: int,
) -> QualityGateResult:
    raw_text = (parsed_cv.rawText or "").strip()
    raw_text_length = len(raw_text)

    has_candidate_signal = any(
        bool((candidate.fullName or "").strip())
        or bool(candidate.emails)
        or bool(candidate.phones)
        or bool((candidate.location or "").strip())
        for candidate in parsed_cv.candidateInfo
    )

    section_signals = sum(
        [
            int(bool(parsed_cv.experience)),
            int(bool(parsed_cv.education)),
            int(bool(parsed_cv.skills)),
            int(bool(parsed_cv.certificates)),
            int(bool(parsed_cv.languages)),
            int(bool((parsed_cv.summary or "").strip())),
        ]
    )

    reasons: list[str] = []
    if raw_text_length < min_rawtext_length:
        reasons.append("raw_text_below_min_length")
    if not has_candidate_signal:
        reasons.append("missing_candidate_identity_signal")
    if section_signals < min_section_signals:
        reasons.append("insufficient_non_empty_sections")

    return QualityGateResult(
        passed=not reasons,
        reasons=tuple(reasons),
        section_signals=section_signals,
        raw_text_length=raw_text_length,
        has_candidate_signal=has_candidate_signal,
    )


def _format_fallback_path(attempts: Sequence[ParserAttemptRecord]) -> str:
    return " -> ".join(
        (
            f"tier{attempt.tier_index}:{attempt.provider}:{attempt.model}"
            f"({attempt.fallback_reason or attempt.status})"
        )
        for attempt in attempts
    )


def _build_trace(
    attempts: Sequence[ParserAttemptRecord],
    selected_tier_index: int | None,
    parser_ver: str | None,
) -> ParserTrace:
    return ParserTrace(
        parser_ver=parser_ver,
        fallback_path=_format_fallback_path(attempts) if attempts else "",
        selected_tier_index=selected_tier_index,
        attempts=tuple(attempts),
    )


def get_last_parse_trace() -> dict[str, Any] | None:
    """Return the latest parser trace for the current async context."""
    trace = _LAST_PARSE_TRACE.get()
    return asdict(trace) if trace is not None else None


class CVParserOrchestrator:
    """Coordinates tiered parser execution with retry and quality fallback."""

    def __init__(
        self,
        tiers: Sequence[ParserTier] | None = None,
        policy: ParserPolicyConfig | None = None,
    ) -> None:
        self.tiers = tuple(tiers or _default_tiers())
        self.policy = policy or ParserPolicyConfig.from_settings()

    async def parse(self, cv_bytes: bytes) -> tuple[str, dict[str, Any]]:
        logger.info(
            "Starting CV parsing pipeline",
            extra={
                "tierCount": len(self.tiers),
                "tiers": [
                    {
                        "tierIndex": tier.tier_index,
                        "provider": tier.provider.provider_name,
                        "model": tier.model_name,
                    }
                    for tier in self.tiers
                ],
                "retryEnabled": self.policy.retry_enabled,
                "retryAttempts": self.policy.retry_attempts,
                "retryBaseSeconds": self.policy.retry_base_seconds,
                "retryMaxSeconds": self.policy.retry_max_seconds,
                "qualityMinRawTextLength": self.policy.min_rawtext_length,
                "qualityMinSectionSignals": self.policy.min_section_signals,
                "cvBytes": len(cv_bytes),
            },
        )

        attempts: list[ParserAttemptRecord] = []
        _LAST_PARSE_TRACE.set(_build_trace(attempts, None, None))

        for tier in self.tiers:
            try:
                parsed_cv = await self._run_tier(
                    tier=tier, cv_bytes=cv_bytes, attempts=attempts
                )
                trace = _build_trace(
                    attempts,
                    selected_tier_index=tier.tier_index,
                    parser_ver=parsed_cv.parserVer,
                )
                _LAST_PARSE_TRACE.set(trace)
                logger.info(
                    "CV parsing pipeline succeeded",
                    extra={
                        "parserVer": parsed_cv.parserVer,
                        "selectedTierIndex": tier.tier_index,
                        "fallbackPath": trace.fallback_path,
                    },
                )
                return parsed_cv.rawText, parsed_cv.model_dump()
            except ProviderInvocationError:
                continue
            except _LowQualityOutputError:
                continue

        trace = _build_trace(attempts, selected_tier_index=None, parser_ver=None)
        _LAST_PARSE_TRACE.set(trace)
        raise CVParsingError(
            "CV parsing failed across all tiers. "
            f"Fallback path: {trace.fallback_path or 'no-attempts'}."
        )

    async def _run_tier(
        self,
        *,
        tier: ParserTier,
        cv_bytes: bytes,
        attempts: list[ParserAttemptRecord],
    ) -> ParsedCV:
        retry_attempt_limit = (
            self.policy.retry_attempts if self.policy.retry_enabled else 1
        )
        retrying = AsyncRetrying(
            stop=stop_after_attempt(retry_attempt_limit),
            wait=wait_exponential(
                multiplier=self.policy.retry_base_seconds,
                min=self.policy.retry_base_seconds,
                max=self.policy.retry_max_seconds,
            ),
            retry=retry_if_exception_type(TransientProviderError),
            reraise=True,
            sleep=self.policy.sleep,
        )

        async for retry_state in retrying:
            retry_count = retry_state.retry_state.attempt_number - 1
            started_at = monotonic()
            model_for_trace = tier.model_name
            successful_attempt: ParserAttemptRecord | None = None
            parsed_result: ParsedCV | None = None
            try:
                with retry_state:
                    try:
                        parsed_cv, resolved_model = await tier.provider.parse(
                            cv_bytes=cv_bytes,
                            model_name=tier.model_name,
                        )
                        model_for_trace = resolved_model
                        parsed_cv.parserVer = (
                            f"{tier.provider.provider_name}:{resolved_model}"
                        )

                        quality = _build_quality_gate(
                            parsed_cv,
                            min_rawtext_length=self.policy.min_rawtext_length,
                            min_section_signals=self.policy.min_section_signals,
                        )
                        if not quality.passed:
                            low_quality_attempt = self._build_attempt_record(
                                tier=tier,
                                model=model_for_trace,
                                duration_ms=int((monotonic() - started_at) * 1000),
                                retry_count=retry_count,
                                fallback_reason=FALLBACK_REASON_LOW_CONFIDENCE,
                                status="failed",
                                quality_reasons=quality.reasons,
                                error_type="LowQualityOutput",
                                error_message=", ".join(quality.reasons),
                            )
                            attempts.append(low_quality_attempt)
                            self._log_attempt(low_quality_attempt)
                            raise _LowQualityOutputError(low_quality_attempt)

                        successful_attempt = self._build_attempt_record(
                            tier=tier,
                            model=model_for_trace,
                            duration_ms=int((monotonic() - started_at) * 1000),
                            retry_count=retry_count,
                            fallback_reason=None,
                            status="succeeded",
                        )
                        parsed_result = parsed_cv
                    except TransientProviderError as exc:
                        attempt = self._build_attempt_record(
                            tier=tier,
                            model=exc.model or model_for_trace,
                            duration_ms=int((monotonic() - started_at) * 1000),
                            retry_count=retry_count,
                            fallback_reason=FALLBACK_REASON_TRANSIENT,
                            status="failed",
                            error_type=exc.__class__.__name__,
                            error_message=str(exc),
                        )
                        attempts.append(attempt)
                        self._log_attempt(attempt)
                        raise
                    except (NonRetryableProviderError, ProviderParseError) as exc:
                        attempt = self._build_attempt_record(
                            tier=tier,
                            model=exc.model or model_for_trace,
                            duration_ms=int((monotonic() - started_at) * 1000),
                            retry_count=retry_count,
                            fallback_reason=FALLBACK_REASON_NON_RETRYABLE,
                            status="failed",
                            error_type=exc.__class__.__name__,
                            error_message=str(exc),
                        )
                        attempts.append(attempt)
                        self._log_attempt(attempt)
                        raise
            except _LowQualityOutputError:
                raise
            except (NonRetryableProviderError, ProviderParseError):
                raise

            if successful_attempt is not None and parsed_result is not None:
                attempts.append(successful_attempt)
                self._log_attempt(successful_attempt)
                return parsed_result

        raise CVParsingError("Retry loop ended unexpectedly without a parser result.")

    def _build_attempt_record(
        self,
        *,
        tier: ParserTier,
        model: str,
        duration_ms: int,
        retry_count: int,
        fallback_reason: str | None,
        status: str,
        quality_reasons: tuple[str, ...] = (),
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> ParserAttemptRecord:
        return ParserAttemptRecord(
            tier_index=tier.tier_index,
            provider=tier.provider.provider_name,
            model=model,
            duration_ms=duration_ms,
            retry_count=retry_count,
            fallback_reason=fallback_reason,
            status=status,
            quality_reasons=quality_reasons,
            error_type=error_type,
            error_message=error_message,
        )

    def _log_attempt(self, attempt: ParserAttemptRecord) -> None:
        log_kwargs = {
            "extra": {
                "tierIndex": attempt.tier_index,
                "provider": attempt.provider,
                "model": attempt.model,
                "durationMs": attempt.duration_ms,
                "retryCount": attempt.retry_count,
                "fallbackReason": attempt.fallback_reason,
                "status": attempt.status,
                "qualityReasons": list(attempt.quality_reasons),
                "errorType": attempt.error_type,
            }
        }
        if attempt.status == "succeeded":
            logger.info("CV parser attempt succeeded", **log_kwargs)
        else:
            logger.warning("CV parser attempt failed", **log_kwargs)


class _LowQualityOutputError(Exception):
    """Internal control-flow exception used to trigger tier fallback."""

    def __init__(self, attempt_record: ParserAttemptRecord) -> None:
        super().__init__(attempt_record.error_message or FALLBACK_REASON_LOW_CONFIDENCE)
        self.attempt_record = attempt_record


async def parse_to_raw_and_json(cv_bytes: bytes) -> tuple[str, dict[str, Any]]:
    """Parse a CV into raw text and structured JSON while preserving the old contract."""
    orchestrator = CVParserOrchestrator()
    return await orchestrator.parse(cv_bytes)
