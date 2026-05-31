"""Unit tests CHAT_FULL_CV Phase 1 — pin behavior của full-CV chat path.

Cover:
  - _fetch_cv_context với parsedJson valid → markdown.
  - _fetch_cv_context legacy parsedJson invalid → fallback rawText.
  - _fetch_cv_context không có CV → CvContextMissingError.
  - _fetch_cv_context không có CVPARSED row → CvContextMissingError.
  - _fetch_cv_context tự inject rawText khi parsedJson thiếu key.
  - _check_full_context_budget tính cả system prompt + user prompt.
  - _check_full_context_budget action=block khi >= hard limit (95%).
  - _check_full_context_budget action=warn_proceed khi 80-95%.
  - _check_full_context_budget action=proceed khi < 80%.
  - summarized user/assistant turns không còn vào LLM context sau summarize.
  - rag_query module không còn import embed_chunks.
  - process_chat_query source không gọi _vector_search.
"""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import app.services.rag_query as rag_query
from app.services.rag_query import (
    ApplicationContext,
    CvContext,
    CvContextMissingError,
    _build_full_cv_system_prompt,
    _check_full_context_budget,
    _fetch_cv_context,
    _fetch_email_log,
    _fetch_offers,
    _filter_history_for_full_context,
    _format_salary_range,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


VALID_PARSED_JSON: dict = {
    "candidateInfo": [{"fullName": "Nguyen Van A"}],
    "summary": "Backend engineer with retrieval experience.",
    "experience": [
        {
            "company": "Fang Labs",
            "title": "Senior Backend Engineer",
            "startDate": "2021-01",
            "endDate": "present",
            "description": "Built CV ingestion pipelines and vector search.",
        }
    ],
    "education": [],
    "skills": ["Python", "FastAPI"],
    "certificates": [],
    "languages": [{"language": "English", "proficiency": "FLUENT"}],
    "rawText": "Sample raw CV text",
    "parserVer": "gemini:test",
}


def _make_conn_cm(fetchrow_return=None, fetch_return=None):
    """Tạo async context manager mock cho acquire_conn()."""
    conn = MagicMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    conn.fetch = AsyncMock(return_value=fetch_return or [])

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=conn)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


# ---------------------------------------------------------------------------
# _fetch_cv_context tests
# ---------------------------------------------------------------------------


class FetchCvContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_parsed_json_valid_returns_markdown(self) -> None:
        row = {
            "parsedjson": VALID_PARSED_JSON,
            "rawtext": "Sample raw CV text",
            "parserver": "gemini:test",
        }
        cm = _make_conn_cm(fetchrow_return=row)
        with patch("app.services.rag_query.acquire_conn", return_value=cm):
            result = await _fetch_cv_context(job_app_id=1)

        self.assertIsInstance(result, CvContext)
        self.assertEqual(result.source, "parsed_json")
        self.assertIn("Nguyen Van A", result.markdown)
        self.assertIn("Senior Backend Engineer", result.markdown)
        self.assertEqual(result.warnings, [])

    async def test_legacy_languages_list_str_falls_back_to_raw_text(self) -> None:
        # Pre-Phase 2.5f format: languages là list[str] thay vì list[LanguageEntry].
        legacy = {**VALID_PARSED_JSON, "languages": ["English", "Vietnamese"]}
        row = {
            "parsedjson": legacy,
            "rawtext": "Backend developer with Java/Spring Boot skills.",
            "parserver": "v1-legacy",
        }
        cm = _make_conn_cm(fetchrow_return=row)
        with patch("app.services.rag_query.acquire_conn", return_value=cm):
            result = await _fetch_cv_context(job_app_id=2)

        self.assertEqual(result.source, "raw_text")
        self.assertEqual(
            result.markdown, "Backend developer with Java/Spring Boot skills."
        )
        self.assertTrue(
            any("validation failed" in w for w in result.warnings),
            f"Expected validation-failed warning, got: {result.warnings}",
        )

    async def test_empty_parsed_and_raw_raises(self) -> None:
        row = {
            "parsedjson": None,
            "rawtext": "",
            "parserver": None,
        }
        cm = _make_conn_cm(fetchrow_return=row)
        with patch("app.services.rag_query.acquire_conn", return_value=cm):
            with self.assertRaises(CvContextMissingError):
                await _fetch_cv_context(job_app_id=3)

    async def test_no_cvparsed_row_raises(self) -> None:
        cm = _make_conn_cm(fetchrow_return=None)
        with patch("app.services.rag_query.acquire_conn", return_value=cm):
            with self.assertRaises(CvContextMissingError):
                await _fetch_cv_context(job_app_id=999)

    async def test_raw_text_injected_when_missing_in_parsed_json(self) -> None:
        # parsedJson không có key 'rawText' — code phải tự merge từ row['rawtext']
        # vì ParsedCV.rawText REQUIRED (min_length=1).
        parsed_no_raw = {k: v for k, v in VALID_PARSED_JSON.items() if k != "rawText"}
        row = {
            "parsedjson": parsed_no_raw,
            "rawtext": "Injected raw text from CVPARSED column.",
            "parserver": "v2",
        }
        cm = _make_conn_cm(fetchrow_return=row)
        with patch("app.services.rag_query.acquire_conn", return_value=cm):
            result = await _fetch_cv_context(job_app_id=4)

        self.assertEqual(result.source, "parsed_json")
        self.assertIn("Nguyen Van A", result.markdown)


# ---------------------------------------------------------------------------
# _check_full_context_budget tests
# ---------------------------------------------------------------------------


class BudgetTests(unittest.TestCase):
    def test_counts_system_prompt_and_user_prompt(self) -> None:
        # System ~ 1000 tokens (3500 chars / 3.5), user ~ 0 tokens.
        system_prompt = "A" * 3500
        result = _check_full_context_budget(
            system_prompt=system_prompt,
            history_messages=[],
            user_prompt="hi",
            model_mode="gemini-flash",
        )

        self.assertGreater(result.total_tokens, 900)
        self.assertEqual(result.action, "proceed")
        self.assertIsNone(result.warning)
        # Messages payload có system + user (history rỗng).
        self.assertEqual(len(result.messages), 2)
        self.assertEqual(result.messages[0]["role"], "system")
        self.assertEqual(result.messages[1]["role"], "user")

    def test_counts_history_messages_too(self) -> None:
        history = [
            {"role": "user", "content": "B" * 3500},  # ~1000 tokens
            {"role": "assistant", "content": "C" * 3500},  # ~1000 tokens
        ]
        result = _check_full_context_budget(
            system_prompt="sys",
            history_messages=history,
            user_prompt="?",
            model_mode="gemini-flash",
        )
        self.assertGreater(result.total_tokens, 1900)
        # 4 messages: system + 2 history + user
        self.assertEqual(len(result.messages), 4)

    def test_block_when_over_hard_limit(self) -> None:
        # Lite budget = 180_000 tokens. Hard limit = 95%.
        # 700_000 chars ≈ 200_000 tokens > 95%.
        huge = "A" * 700_000
        result = _check_full_context_budget(
            system_prompt=huge,
            history_messages=[],
            user_prompt="?",
            model_mode="gemini-flash",
        )
        self.assertEqual(result.action, "block")
        self.assertIsNotNone(result.warning)
        self.assertEqual(result.warning["type"], "budget_over_hard_limit")
        self.assertGreaterEqual(result.used_percent, 95)

    def test_warn_proceed_between_thresholds(self) -> None:
        # 525_000 chars ≈ 150_000 tokens. 150/180 ≈ 83% → warn (80-95%).
        target = "A" * 525_000
        result = _check_full_context_budget(
            system_prompt=target,
            history_messages=[],
            user_prompt="?",
            model_mode="gemini-flash",
        )
        self.assertEqual(result.action, "warn_proceed")
        self.assertIsNotNone(result.warning)
        self.assertEqual(result.warning["type"], "budget_near_limit")
        self.assertGreaterEqual(result.used_percent, 80)
        self.assertLess(result.used_percent, 95)

    def test_proceed_when_well_under(self) -> None:
        result = _check_full_context_budget(
            system_prompt="Hello world.",
            history_messages=[],
            user_prompt="?",
            model_mode="gemini-flash",
        )
        self.assertEqual(result.action, "proceed")
        self.assertIsNone(result.warning)


# ---------------------------------------------------------------------------
# History filtering tests
# ---------------------------------------------------------------------------


class HistoryFilteringTests(unittest.TestCase):
    def test_keeps_system_summary_and_unsummarized_turns_only(self) -> None:
        history = [
            {
                "messageid": 1,
                "role": "user",
                "content": "old user",
                "summarized": True,
            },
            {
                "messageid": 2,
                "role": "assistant",
                "content": "old assistant",
                "summarized": True,
            },
            {
                "messageid": 3,
                "role": "system",
                "content": "[Tóm tắt] old context",
                "summarized": False,
            },
            {
                "messageid": 4,
                "role": "assistant",
                "content": "recent assistant",
                "summarized": False,
            },
            {
                "messageid": 5,
                "role": "user",
                "content": "current prompt",
                "summarized": False,
            },
        ]

        result = _filter_history_for_full_context(
            history,
            current_user_message_id=5,
        )

        self.assertEqual([m["messageid"] for m in result], [3, 4])
        self.assertEqual(result[0]["role"], "system")
        self.assertNotIn("old user", [m["content"] for m in result])
        self.assertNotIn("current prompt", [m["content"] for m in result])


# ---------------------------------------------------------------------------
# _build_full_cv_system_prompt tests (Phase 1.5)
# ---------------------------------------------------------------------------


def _sample_app_ctx() -> ApplicationContext:
    return ApplicationContext(
        job_posting={
            "title": "Senior Backend Engineer",
            "description": "Build distributed systems.",
        },
        candidate={
            "fullname": "Nguyen Van A",
            "expyears": 3,
            "location": "Hà Nội",
            "bio": "Java/Spring developer.",
        },
        ats_history=[
            {
                "type": "interview",
                "interviewdate": "2026-04-15",
                "score": 8,
                "notes": "Strong technical, communication ok.",
            }
        ],
    )


class FullCvSystemPromptTests(unittest.TestCase):
    def test_prompt_contains_8_guardrails(self) -> None:
        """Pin 8 rules theo Decision Analysis §Prompt Policy."""
        cv = CvContext(markdown="# CV markdown body", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, _sample_app_ctx())

        # Rule 1: Scope tuyển dụng
        self.assertIn("PHẠM VI", prompt)
        # Rule 2: Evidence-only
        self.assertIn("Evidence-only", prompt)
        # Rule 3: Untrusted markers (also tested in dedicated test below)
        self.assertIn("[UNTRUSTED", prompt)
        # Rule 4: Source clarity
        self.assertIn("Source clarity", prompt)
        # Rule 5: No absolute hire/reject
        self.assertIn("tuyển/loại tuyệt đối", prompt)
        # Rule 6: No sensitive inference
        self.assertIn("nhạy cảm", prompt)
        # Rule 7: No hidden action
        self.assertIn("thao tác hệ thống", prompt)
        # Rule 8: Output tiếng Việt
        self.assertIn("tiếng Việt", prompt)

    def test_prompt_refuses_out_of_scope_examples(self) -> None:
        """Prompt liệt kê ví dụ out-of-scope: code, y tế, pháp lý."""
        cv = CvContext(markdown="x", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, _sample_app_ctx())

        for example in ("viết code", "y tế", "pháp lý"):
            self.assertIn(
                example,
                prompt,
                f"Prompt thiếu ví dụ out-of-scope '{example}'.",
            )

    def test_prompt_has_untrusted_input_policy(self) -> None:
        """Phải có hướng dẫn xử lý untrusted input (chống prompt injection)."""
        cv = CvContext(markdown="x", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, _sample_app_ctx())

        self.assertIn("XỬ LÝ DỮ LIỆU KHÔNG ĐÁNG TIN", prompt)
        self.assertIn("ignore previous instructions", prompt)

    def test_prompt_marks_all_context_blocks_as_untrusted(self) -> None:
        """Mỗi context block phải có marker [UNTRUSTED ...]."""
        cv = CvContext(markdown="# CV", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, _sample_app_ctx())

        self.assertIn("[UNTRUSTED JD", prompt)
        self.assertIn("[UNTRUSTED CANDIDATE", prompt)
        self.assertIn("[UNTRUSTED CV", prompt)
        self.assertIn("[UNTRUSTED ATS", prompt)
        self.assertIn("[END OF CONTEXT]", prompt)

    def test_cv_marker_reflects_parsed_source(self) -> None:
        """CV block marker phản ánh `cv_context.source`."""
        prompt_parsed = _build_full_cv_system_prompt(
            CvContext(markdown="# CV", source="parsed_json"),
            _sample_app_ctx(),
        )
        prompt_raw = _build_full_cv_system_prompt(
            CvContext(markdown="raw text", source="raw_text"),
            _sample_app_ctx(),
        )

        self.assertIn("FULL MARKDOWN (parsed)", prompt_parsed)
        self.assertNotIn("RAW TEXT FALLBACK", prompt_parsed)

        self.assertIn("RAW TEXT FALLBACK", prompt_raw)
        self.assertNotIn("FULL MARKDOWN (parsed)", prompt_raw)

    def test_prompt_includes_cv_markdown_body(self) -> None:
        """CV markdown body phải xuất hiện trong prompt."""
        cv = CvContext(
            markdown="# Nguyen Van A\n\n## Experience\n- Senior at Fang Labs",
            source="parsed_json",
        )
        prompt = _build_full_cv_system_prompt(cv, _sample_app_ctx())

        self.assertIn("Nguyen Van A", prompt)
        self.assertIn("Senior at Fang Labs", prompt)

    def test_prompt_omits_empty_blocks(self) -> None:
        """Khi job_posting/candidate/ats rỗng, block tương ứng không xuất hiện."""
        empty_ctx = ApplicationContext(
            job_posting=None,
            candidate=None,
            ats_history=[],
        )
        cv = CvContext(markdown="only CV here", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, empty_ctx)

        self.assertNotIn("[UNTRUSTED JD", prompt)
        self.assertNotIn("[UNTRUSTED CANDIDATE", prompt)
        self.assertNotIn("[UNTRUSTED ATS", prompt)
        # CV vẫn phải có
        self.assertIn("[UNTRUSTED CV", prompt)
        self.assertIn("only CV here", prompt)


# ---------------------------------------------------------------------------
# Phase 2 — Context enrichment tests
# ---------------------------------------------------------------------------


class FetchOffersTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_recent_offers_capped_by_setting(self) -> None:
        offer_rows = [
            {
                "offerid": 11,
                "ver": 2,
                "salary": 25_000_000,
                "description": "Final offer.",
                "stat": "SENT",
                "subat": "2026-04-20",
            },
            {
                "offerid": 10,
                "ver": 1,
                "salary": 22_000_000,
                "description": "Initial.",
                "stat": "SUPERSEDED",
                "subat": "2026-04-15",
            },
        ]
        cm = _make_conn_cm(fetch_return=offer_rows)
        with patch("app.services.rag_query.acquire_conn", return_value=cm):
            offers = await _fetch_offers(job_app_id=42)

        self.assertEqual(len(offers), 2)
        self.assertEqual(offers[0]["ver"], 2)
        self.assertEqual(offers[1]["salary"], 22_000_000)

    async def test_empty_when_no_offers(self) -> None:
        cm = _make_conn_cm(fetch_return=[])
        with patch("app.services.rag_query.acquire_conn", return_value=cm):
            offers = await _fetch_offers(job_app_id=99)
        self.assertEqual(offers, [])


class FetchEmailLogTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_emails_with_subject_join(self) -> None:
        email_rows = [
            {
                "logid": 7,
                "sentat": "2026-04-22",
                "rcvemail": "cand@example.com",
                "subject": "Offer Confirmation",
                "bodysnippet": "Chào anh, chúng tôi xin gửi anh offer...",
            }
        ]
        cm = _make_conn_cm(fetch_return=email_rows)
        with patch("app.services.rag_query.acquire_conn", return_value=cm):
            emails = await _fetch_email_log(job_app_id=42)

        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["subject"], "Offer Confirmation")
        self.assertIn("offer", emails[0]["bodysnippet"].lower())


class FormatSalaryRangeTests(unittest.TestCase):
    def test_both_min_and_max(self) -> None:
        self.assertEqual(
            _format_salary_range(15_000_000, 30_000_000),
            "15,000,000 - 30,000,000 VND",
        )

    def test_only_min(self) -> None:
        self.assertEqual(_format_salary_range(20_000_000, None), "từ 20,000,000 VND")

    def test_only_max(self) -> None:
        self.assertEqual(
            _format_salary_range(None, 50_000_000),
            "tối đa 50,000,000 VND",
        )

    def test_both_none_returns_none(self) -> None:
        self.assertIsNone(_format_salary_range(None, None))


class Phase2PromptBlocksTests(unittest.TestCase):
    def test_jd_block_includes_extended_fields(self) -> None:
        ctx = ApplicationContext(
            job_posting={
                "title": "Senior Backend Engineer",
                "description": "Build distributed systems.",
                "minsalary": 20_000_000,
                "maxsalary": 35_000_000,
                "workmode": "HYBRID",
                "workloc": "Tòa Keangnam",
                "provincename": "Hà Nội",
                "levels": ["Senior", "Lead"],
                "categories": ["Backend", "Web Development"],
                "requiredskills": ["Python", "FastAPI", "PostgreSQL"],
            },
            candidate=None,
            ats_history=[],
        )
        cv = CvContext(markdown="# CV", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, ctx)

        self.assertIn("Mức lương (gross): 20,000,000 - 35,000,000 VND", prompt)
        self.assertIn("Work mode: HYBRID", prompt)
        self.assertIn("Tòa Keangnam", prompt)
        self.assertIn("Hà Nội", prompt)
        self.assertIn("Levels: Senior, Lead", prompt)
        self.assertIn("Categories: Backend, Web Development", prompt)
        self.assertIn("Required skills: Python, FastAPI, PostgreSQL", prompt)

    def test_candidate_block_includes_skills(self) -> None:
        ctx = ApplicationContext(
            job_posting=None,
            candidate={
                "fullname": "Nguyen Van A",
                "expyears": 3,
                "skills": ["Java", "Spring Boot", "PostgreSQL"],
            },
            ats_history=[],
        )
        cv = CvContext(markdown="x", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, ctx)

        self.assertIn("Skills đã khai báo: Java, Spring Boot, PostgreSQL", prompt)

    def test_offer_block_rendered(self) -> None:
        ctx = ApplicationContext(
            job_posting=None,
            candidate=None,
            ats_history=[],
            offers=[
                {
                    "ver": 2,
                    "subat": "2026-04-20",
                    "salary": 25_000_000,
                    "stat": "SENT",
                    "description": "Final offer with stock.",
                },
                {
                    "ver": 1,
                    "subat": "2026-04-15",
                    "salary": 22_000_000,
                    "stat": "SUPERSEDED",
                    "description": "Initial proposal.",
                },
            ],
        )
        cv = CvContext(markdown="x", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, ctx)

        self.assertIn("[UNTRUSTED OFFER", prompt)
        self.assertIn("Offer v2 (2026-04-20)", prompt)
        self.assertIn("Stat: SENT", prompt)
        self.assertIn("25,000,000 VND", prompt)
        self.assertIn("Final offer with stock.", prompt)
        self.assertIn("Offer v1", prompt)

    def test_email_block_rendered(self) -> None:
        ctx = ApplicationContext(
            job_posting=None,
            candidate=None,
            ats_history=[],
            emails=[
                {
                    "sentat": "2026-04-22",
                    "rcvemail": "cand@example.com",
                    "subject": "Offer Confirmation",
                    "bodysnippet": "Chào anh, gửi anh offer...",
                }
            ],
        )
        cv = CvContext(markdown="x", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, ctx)

        self.assertIn("[UNTRUSTED EMAIL", prompt)
        self.assertIn("2026-04-22 → cand@example.com", prompt)
        self.assertIn('"Offer Confirmation"', prompt)
        self.assertIn("Chào anh, gửi anh offer", prompt)

    def test_offer_and_email_blocks_omitted_when_empty(self) -> None:
        ctx = ApplicationContext(
            job_posting=None,
            candidate=None,
            ats_history=[],
        )
        cv = CvContext(markdown="x", source="parsed_json")
        prompt = _build_full_cv_system_prompt(cv, ctx)

        self.assertNotIn("[UNTRUSTED OFFER", prompt)
        self.assertNotIn("[UNTRUSTED EMAIL", prompt)


# ---------------------------------------------------------------------------
# Module boundary tests — pin static guarantees
# ---------------------------------------------------------------------------


class ModuleBoundaryTests(unittest.TestCase):
    def test_rag_query_does_not_import_embed_chunks(self) -> None:
        """Phase 1.2: bỏ embed prompt → embed_chunks không còn xuất hiện ở module namespace."""
        self.assertFalse(
            hasattr(rag_query, "embed_chunks"),
            "rag_query.embed_chunks vẫn import — luồng full-CV không được phép dùng embedding.",
        )

    def test_vector_search_function_kept(self) -> None:
        """`_vector_search` vẫn tồn tại trong module (scope: không xóa pipeline)."""
        self.assertTrue(hasattr(rag_query, "_vector_search"))

    def test_process_chat_query_does_not_call_vector_search(self) -> None:
        """`process_chat_query` source không gọi `_vector_search(`."""
        src = inspect.getsource(rag_query.process_chat_query)
        self.assertNotIn(
            "_vector_search(",
            src,
            "process_chat_query vẫn gọi _vector_search — luồng full-CV phải bỏ.",
        )

    def test_process_chat_query_does_not_gate_on_aiindexjob(self) -> None:
        """Full-CV chat chỉ cần CVPARSED usable, không hard gate AIINDEXJOB."""
        src = inspect.getsource(rag_query.process_chat_query)
        self.assertNotIn("AIINDEXJOB", src)
        self.assertNotIn("Ingestion chưa hoàn thành", src)

    def test_process_chat_query_calls_fetch_cv_context(self) -> None:
        """`process_chat_query` source phải gọi `_fetch_cv_context(`."""
        src = inspect.getsource(rag_query.process_chat_query)
        self.assertIn(
            "_fetch_cv_context(",
            src,
            "process_chat_query thiếu gọi _fetch_cv_context.",
        )

    def test_process_chat_query_calls_full_cv_prompt_builder(self) -> None:
        """`process_chat_query` source phải gọi `_build_full_cv_system_prompt(`."""
        src = inspect.getsource(rag_query.process_chat_query)
        self.assertIn(
            "_build_full_cv_system_prompt(",
            src,
            "process_chat_query thiếu gọi _build_full_cv_system_prompt.",
        )

    def test_legacy_build_system_prompt_removed(self) -> None:
        """`_build_system_prompt` cũ đã bị thay bằng full-CV version."""
        self.assertFalse(
            hasattr(rag_query, "_build_system_prompt"),
            "_build_system_prompt cũ vẫn còn — Phase 1.5 phải rewrite.",
        )


if __name__ == "__main__":
    unittest.main()
