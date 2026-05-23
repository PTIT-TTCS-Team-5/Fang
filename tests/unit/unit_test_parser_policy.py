import unittest

from app.models.cv_models import CandidateInfo, Experience, ParsedCV, ParserSelfReport
from app.services.cv_parser import (
    CVParserOrchestrator,
    ParserPolicyConfig,
    ParserTier,
    get_last_parse_trace,
)
from app.services.cv_parser_adapters import (
    NonRetryableProviderError,
    TransientProviderError,
)


class MockProvider:
    def __init__(self, provider_name: str, behaviors):
        self.provider_name = provider_name
        self.behaviors = list(behaviors)
        self.call_count = 0

    async def parse(self, cv_bytes: bytes, model_name: str):
        behavior = self.behaviors[self.call_count]
        self.call_count += 1
        if isinstance(behavior, Exception):
            raise behavior
        return behavior, model_name


def build_policy(*, retry_enabled: bool, sleep_recorder):
    return ParserPolicyConfig(
        retry_enabled=retry_enabled,
        retry_attempts=3,
        retry_base_seconds=0,
        retry_max_seconds=0,
        min_rawtext_length=40,
        min_section_signals=1,
        min_self_confidence=0.55,
        sleep=sleep_recorder,
    )


def build_good_cv(parser_ver: str | None = None) -> ParsedCV:
    return ParsedCV(
        candidateInfo=[
            CandidateInfo(
                fullName="Nguyen Van A",
                emails=["nguyenvana@example.com"],
                phones=["0123456789"],
                location="Ho Chi Minh City",
            )
        ],
        experience=[
            Experience(
                company="miCareer",
                title="Backend Engineer",
                startDate="2023-01",
                endDate="present",
                description="Built parser workflows and maintained FastAPI services.",
            )
        ],
        skills=["Python", "FastAPI"],
        summary="Backend engineer with parser and ingestion experience.",
        rawText="Nguyen Van A Backend Engineer Python FastAPI miCareer parser workflow",
        parserVer=parser_ver,
    )


def build_good_cv_with_self_report(confidence: float) -> ParsedCV:
    cv = build_good_cv()
    cv.parserSelfReport = ParserSelfReport(
        confidence=confidence,
        issues=[],
        uncertainFields=[],
    )
    return cv


def build_low_quality_cv() -> ParsedCV:
    return ParsedCV(
        candidateInfo=[CandidateInfo()],
        rawText="too short",
    )


class ParserPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_tier1_transient_error_then_recover(self):
        sleep_calls = []

        async def fake_sleep(seconds: float):
            sleep_calls.append(seconds)

        tier1_provider = MockProvider(
            "mock",
            [
                TransientProviderError("mock", "tier1-model", "temporary timeout"),
                build_good_cv(),
            ],
        )

        orchestrator = CVParserOrchestrator(
            tiers=[ParserTier(1, "tier1-model", tier1_provider)],
            policy=build_policy(retry_enabled=True, sleep_recorder=fake_sleep),
        )

        raw_text, parsed_json = await orchestrator.parse(b"pdf-bytes")
        parser_trace = get_last_parse_trace()

        self.assertTrue(raw_text.startswith("Nguyen Van A"))
        self.assertEqual(parsed_json["parserVer"], "mock:tier1-model")
        self.assertEqual(tier1_provider.call_count, 2)
        self.assertEqual(len(sleep_calls), 1)
        self.assertIsNotNone(parser_trace)
        self.assertIn("transient_error", parser_trace["fallback_path"])

    async def test_low_quality_output_falls_back_to_tier2(self):
        async def fake_sleep(seconds: float):
            return None

        tier1_provider = MockProvider("mock-one", [build_low_quality_cv()])
        tier2_provider = MockProvider("mock-two", [build_good_cv()])

        orchestrator = CVParserOrchestrator(
            tiers=[
                ParserTier(1, "tier1-model", tier1_provider),
                ParserTier(2, "tier2-model", tier2_provider),
            ],
            policy=build_policy(retry_enabled=True, sleep_recorder=fake_sleep),
        )

        _, parsed_json = await orchestrator.parse(b"pdf-bytes")
        parser_trace = get_last_parse_trace()

        self.assertEqual(parsed_json["parserVer"], "mock-two:tier2-model")
        self.assertEqual(tier1_provider.call_count, 1)
        self.assertEqual(tier2_provider.call_count, 1)
        self.assertIsNotNone(parser_trace)
        self.assertIn("low_confidence_output", parser_trace["fallback_path"])

    async def test_tier1_and_tier2_fail_then_tier3_success(self):
        async def fake_sleep(seconds: float):
            return None

        tier1_provider = MockProvider(
            "mock-one",
            [NonRetryableProviderError("mock-one", "tier1-model", "schema mismatch")],
        )
        tier2_provider = MockProvider(
            "mock-two",
            [NonRetryableProviderError("mock-two", "tier2-model", "empty response")],
        )
        tier3_provider = MockProvider("mock-three", [build_good_cv()])

        orchestrator = CVParserOrchestrator(
            tiers=[
                ParserTier(1, "tier1-model", tier1_provider),
                ParserTier(2, "tier2-model", tier2_provider),
                ParserTier(3, "tier3-model", tier3_provider),
            ],
            policy=build_policy(retry_enabled=True, sleep_recorder=fake_sleep),
        )

        _, parsed_json = await orchestrator.parse(b"pdf-bytes")
        parser_trace = get_last_parse_trace()

        self.assertEqual(parsed_json["parserVer"], "mock-three:tier3-model")
        self.assertIsNotNone(parser_trace)
        self.assertIn(
            "tier1:mock-one:tier1-model(non_retryable_error)",
            parser_trace["fallback_path"],
        )
        self.assertIn(
            "tier2:mock-two:tier2-model(non_retryable_error)",
            parser_trace["fallback_path"],
        )

    async def test_retry_disabled_does_not_sleep(self):
        sleep_calls = []

        async def fake_sleep(seconds: float):
            sleep_calls.append(seconds)

        tier1_provider = MockProvider(
            "mock-one",
            [TransientProviderError("mock-one", "tier1-model", "timeout")],
        )
        tier2_provider = MockProvider("mock-two", [build_good_cv()])

        orchestrator = CVParserOrchestrator(
            tiers=[
                ParserTier(1, "tier1-model", tier1_provider),
                ParserTier(2, "tier2-model", tier2_provider),
            ],
            policy=build_policy(retry_enabled=False, sleep_recorder=fake_sleep),
        )

        _, parsed_json = await orchestrator.parse(b"pdf-bytes")

        self.assertEqual(parsed_json["parserVer"], "mock-two:tier2-model")
        self.assertEqual(tier1_provider.call_count, 1)
        self.assertEqual(sleep_calls, [])

    async def test_low_self_confidence_falls_back(self):
        async def fake_sleep(seconds: float):
            return None

        tier1_provider = MockProvider("mock-one", [build_good_cv_with_self_report(0.2)])
        tier2_provider = MockProvider("mock-two", [build_good_cv_with_self_report(0.9)])

        orchestrator = CVParserOrchestrator(
            tiers=[
                ParserTier(1, "tier1-model", tier1_provider),
                ParserTier(2, "tier2-model", tier2_provider),
            ],
            policy=build_policy(retry_enabled=True, sleep_recorder=fake_sleep),
        )

        _, parsed_json = await orchestrator.parse(b"pdf-bytes")
        parser_trace = get_last_parse_trace()

        self.assertEqual(parsed_json["parserVer"], "mock-two:tier2-model")
        self.assertIsNotNone(parser_trace)
        self.assertIn(
            "parser_self_confidence_below_threshold",
            parser_trace["attempts"][0]["quality_reasons"],
        )
        self.assertEqual(parser_trace["attempts"][0]["parser_confidence"], 0.2)

    async def test_missing_self_report_does_not_fail_quality_gate(self):
        async def fake_sleep(seconds: float):
            return None

        tier1_provider = MockProvider("mock-one", [build_good_cv()])
        orchestrator = CVParserOrchestrator(
            tiers=[ParserTier(1, "tier1-model", tier1_provider)],
            policy=build_policy(retry_enabled=True, sleep_recorder=fake_sleep),
        )

        _, parsed_json = await orchestrator.parse(b"pdf-bytes")

        self.assertEqual(parsed_json["parserVer"], "mock-one:tier1-model")

    async def test_high_self_confidence_does_not_override_deterministic_failure(self):
        async def fake_sleep(seconds: float):
            return None

        low_quality = build_low_quality_cv()
        low_quality.parserSelfReport = ParserSelfReport(
            confidence=0.99,
            issues=[],
            uncertainFields=[],
        )
        tier1_provider = MockProvider("mock-one", [low_quality])
        tier2_provider = MockProvider("mock-two", [build_good_cv_with_self_report(0.9)])
        orchestrator = CVParserOrchestrator(
            tiers=[
                ParserTier(1, "tier1-model", tier1_provider),
                ParserTier(2, "tier2-model", tier2_provider),
            ],
            policy=build_policy(retry_enabled=True, sleep_recorder=fake_sleep),
        )

        _, parsed_json = await orchestrator.parse(b"pdf-bytes")
        parser_trace = get_last_parse_trace()

        self.assertEqual(parsed_json["parserVer"], "mock-two:tier2-model")
        self.assertIn(
            "raw_text_below_min_length",
            parser_trace["attempts"][0]["quality_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
