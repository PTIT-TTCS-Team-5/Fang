from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.nmaiex_schemas import SkillMappingResult
from app.services.nmaiex_candidate_enrichment import (
    ENRICHMENT_STATUS_FAILED,
    _coerce_enrichment_payload,
    _map_language_to_lang_id,
    _mark_failed,
    compute_exp_years,
    enqueue_missing_enrichment_jobs,
    enrich_candidate_structured_data,
    fetch_due_enrichment_jobs,
)


class FakeTransaction:
    def __init__(self):
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return False


class FakeConn:
    def __init__(self):
        self.execute = AsyncMock()
        self.executemany = AsyncMock()
        self.fetchrow = AsyncMock(return_value=None)
        self.fetchval = AsyncMock(return_value=123)
        self.tx = FakeTransaction()

    def transaction(self):
        return self.tx


class FakeAcquireContext:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


# ============================================================
# Existing tests (must still pass)
# ============================================================


class NMAIexCandidateEnrichmentTests(IsolatedAsyncioTestCase):
    def test_compute_exp_years_accepts_legacy_dict_entries(self):
        years = compute_exp_years(
            [
                {"startDate": "2020-01", "endDate": "2022-01"},
                {"startDate": "bad-date", "endDate": "2023-01"},
            ]
        )

        self.assertEqual(years, 2)

    async def test_enrich_candidate_structured_data_updates_atomically(self):
        conn = FakeConn()
        payload = {
            "experience": [{"startDate": "2020-01", "endDate": "2022-01"}],
            "skills": ["Python", "LangGraph"],
            "languages": [{"language": "English", "proficiency": "ADVANCED"}],
        }

        with (
            patch(
                "app.services.nmaiex_candidate_enrichment.map_skills",
                AsyncMock(
                    return_value=SkillMappingResult(
                        matched_ids=[1],
                        unmatched_texts=["LangGraph"],
                    )
                ),
            ) as map_skills,
            patch(
                "app.services.nmaiex_candidate_enrichment.embed_chunks",
                AsyncMock(return_value=[[0.1, 0.2]]),
            ) as embed_chunks,
            patch(
                "app.services.nmaiex_candidate_enrichment.normalize_proficiency",
                AsyncMock(return_value="ADVANCED"),
            ),
            patch(
                "app.services.nmaiex_candidate_enrichment.map_string_to_province_id",
                AsyncMock(return_value=None),
            ),
        ):
            await enrich_candidate_structured_data(
                candidate_id=42,
                parsed_payload=payload,
                conn=conn,
            )

        map_skills.assert_awaited_once_with(["Python", "LangGraph"])
        embed_chunks.assert_awaited_once()
        self.assertTrue(conn.tx.entered)
        self.assertTrue(conn.tx.exited)
        conn.execute.assert_any_await(
            "UPDATE CANDIDATE SET expyears = $1 WHERE userId = $2",
            2,
            42,
        )
        conn.executemany.assert_any_await(
            """
                    INSERT INTO CANDIDATESKILL (userId, skillId)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
            [(42, 1)],
        )
        self.assertEqual(conn.executemany.await_args_list[-1].args[1][0][0], 42)
        self.assertEqual(
            conn.executemany.await_args_list[-1].args[1][0][1], "LangGraph"
        )

    async def test_fetch_due_enrichment_jobs_filters_in_sql(self):
        class FetchConn:
            def __init__(self):
                self.execute = AsyncMock()
                self.fetch = AsyncMock(
                    return_value=[
                        {
                            "enrichmentjobid": 1,
                            "jobappid": 10,
                            "candidateid": 20,
                            "cvparsedid": 30,
                            "stat": "FAILED",
                            "retrycount": 1,
                        }
                    ]
                )

        conn = FetchConn()
        with patch(
            "app.services.nmaiex_candidate_enrichment.acquire_conn",
            return_value=FakeAcquireContext(conn),
        ):
            jobs = await fetch_due_enrichment_jobs(5)

        self.assertEqual(jobs[0]["enrichmentjobid"], 1)
        self.assertEqual(conn.fetch.await_args.args[-1], 5)

    async def test_enqueue_missing_enrichment_jobs_returns_created_ids(self):
        class FetchConn:
            def __init__(self):
                self.execute = AsyncMock()
                self.fetch = AsyncMock(
                    return_value=[
                        {"enrichmentjobid": 11},
                        {"enrichmentjobid": 12},
                    ]
                )

        conn = FetchConn()
        with patch(
            "app.services.nmaiex_candidate_enrichment.acquire_conn",
            return_value=FakeAcquireContext(conn),
        ):
            created_ids = await enqueue_missing_enrichment_jobs(10)

        self.assertEqual(created_ids, [11, 12])
        self.assertEqual(conn.fetch.await_args.args[-1], 10)

    async def test_mark_failed_increments_retry_and_schedules_next_run(self):
        class MarkConn:
            def __init__(self):
                self.fetchrow = AsyncMock(
                    return_value={"retrycount": 0, "maxretrycount": 3}
                )
                self.execute = AsyncMock()

        conn = MarkConn()
        await _mark_failed(conn, 7, error_msg="mapper down")

        args = conn.execute.await_args.args
        self.assertEqual(args[2], ENRICHMENT_STATUS_FAILED)
        self.assertEqual(args[3], 1)
        self.assertIsNotNone(args[4])
        self.assertEqual(args[5], "mapper down")

    async def test_mark_failed_does_not_schedule_when_retries_exhausted(self):
        class MarkConn:
            def __init__(self):
                self.fetchrow = AsyncMock(
                    return_value={"retrycount": 4, "maxretrycount": 5}
                )
                self.execute = AsyncMock()

        conn = MarkConn()
        await _mark_failed(conn, 7, error_msg="mapper down")

        args = conn.execute.await_args.args
        self.assertEqual(args[3], 5)
        self.assertIsNone(args[4])


# ============================================================
# [C3 WS1] New tests: payload extraction, language mapping,
# proficiency normalization, province update
# ============================================================


class WS1EnrichmentPayloadExtractionTests(IsolatedAsyncioTestCase):
    """Test _coerce_enrichment_payload extracts languages and location."""

    def test_coerce_extracts_languages_from_list_of_dicts(self):
        payload = {
            "experience": [],
            "skills": [],
            "languages": [
                {"language": "English", "proficiency": "ADVANCED"},
                {"language": "Ti\u1ebfng Nh\u1eadt", "proficiency": "N3"},
            ],
        }
        result = _coerce_enrichment_payload(payload)
        self.assertEqual(len(result.languages), 2)
        self.assertEqual(result.languages[0]["language"], "English")
        self.assertEqual(result.languages[1]["language"], "Ti\u1ebfng Nh\u1eadt")

    def test_coerce_extracts_location_from_candidate_info(self):
        payload = {
            "experience": [],
            "skills": [],
            "candidateInfo": [
                {"fullName": "Nguyen Van A", "location": "TP.HCM", "emails": []}
            ],
        }
        result = _coerce_enrichment_payload(payload)
        self.assertEqual(result.candidate_location, "TP.HCM")

    def test_coerce_returns_none_location_when_absent(self):
        payload = {"experience": [], "skills": [], "candidateInfo": []}
        result = _coerce_enrichment_payload(payload)
        self.assertIsNone(result.candidate_location)

    def test_coerce_extracts_legacy_string_languages(self):
        """Old parsers may return list[str] for languages."""
        payload = {
            "experience": [],
            "skills": [],
            "languages": ["English", "Japanese"],
        }
        result = _coerce_enrichment_payload(payload)
        self.assertEqual(len(result.languages), 2)
        self.assertEqual(result.languages[0]["language"], "English")
        self.assertIsNone(result.languages[0]["proficiency"])


class WS1LanguageMappingTests(IsolatedAsyncioTestCase):
    """Test _map_language_to_lang_id uses alias map + DB lookup."""

    async def test_tieng_anh_maps_to_english_lang_id(self):
        """'Ti\u1ebfng Anh' should resolve via alias map to langCode='en', then DB."""
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"langid": 1})

        lang_id = await _map_language_to_lang_id("Ti\u1ebfng Anh", conn)

        self.assertEqual(lang_id, 1)
        # Should have called DB lookup with 'en'
        conn.fetchrow.assert_awaited()
        call_args = conn.fetchrow.await_args_list[0].args
        self.assertIn("en", call_args[1].lower())

    async def test_english_maps_to_lang_id(self):
        """'English' (exact alias key) should resolve to langId."""
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value={"langid": 1})

        lang_id = await _map_language_to_lang_id("English", conn)
        self.assertEqual(lang_id, 1)

    async def test_unknown_language_returns_none(self):
        """A language not in alias map and not in DB should return None."""
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)

        lang_id = await _map_language_to_lang_id("Klingon", conn)
        self.assertIsNone(lang_id)

    async def test_unknown_language_writes_row_with_null_lang_id(self):
        """End-to-end: unknown language preserved in CANDIDATELANGUAGE with langId=NULL."""
        conn = FakeConn()
        # fetchrow returns None → langId=None
        conn.fetchrow = AsyncMock(return_value=None)

        raw_languages = [{"language": "Klingon", "proficiency": "ADVANCED"}]

        with patch(
            "app.services.nmaiex_candidate_enrichment.normalize_proficiency",
            AsyncMock(return_value="ADVANCED"),
        ):
            from app.services.nmaiex_candidate_enrichment import (
                _normalize_and_persist_languages,
            )

            await _normalize_and_persist_languages(
                candidate_id=10,
                raw_languages=raw_languages,
                conn=conn,
            )

        # Verify INSERT was called with langId=None
        insert_calls = [
            call
            for call in conn.fetchval.await_args_list
            if "INSERT INTO CANDIDATELANGUAGE" in call.args[0]
        ]
        self.assertEqual(len(insert_calls), 1)
        args = insert_calls[0].args
        # args: (sql, userId, langId, rawName, proficiency, rawProficiency, certification)
        self.assertEqual(args[1], 10)  # userId
        self.assertIsNone(args[2])  # langId = NULL
        self.assertEqual(args[3], "Klingon")  # rawName preserved


class WS1ProficiencyNormalizationTests(IsolatedAsyncioTestCase):
    """Test proficiency normalization passthrough for standard values."""

    async def test_standard_proficiency_passes_through_without_llm(self):
        """Already-normalized proficiency should be returned as-is (fast path)."""
        from app.services.nmaiex_mapper_service import normalize_proficiency

        result = await normalize_proficiency("ADVANCED")
        self.assertEqual(result, "ADVANCED")

    async def test_none_proficiency_returns_basic(self):
        """None proficiency should fall back to BASIC."""
        from app.services.nmaiex_mapper_service import normalize_proficiency

        result = await normalize_proficiency(None)
        self.assertEqual(result, "BASIC")

    async def test_hang_c_maps_to_advanced_via_mock(self):
        """'h\u1ea1ng C' → ADVANCED when LLM is mocked."""
        with patch(
            "app.services.nmaiex_mapper_service.invoke_generation",
            AsyncMock(return_value=MagicMock(response="ADVANCED")),
        ):
            from app.services.nmaiex_mapper_service import normalize_proficiency

            result = await normalize_proficiency("h\u1ea1ng C")
        self.assertEqual(result, "ADVANCED")


class WS1ProvinceUpdateTests(IsolatedAsyncioTestCase):
    """Test province update behavior."""

    async def test_province_update_writes_prov_id_when_mapper_returns_value(self):
        """When mapper returns a provId, user.provId must be updated."""
        conn = FakeConn()

        with patch(
            "app.services.nmaiex_candidate_enrichment.map_string_to_province_id",
            AsyncMock(return_value="TPHCM"),
        ):
            from app.services.nmaiex_candidate_enrichment import (
                _normalize_and_update_province,
            )

            await _normalize_and_update_province(
                candidate_id=99,
                raw_location="TP.HCM",
                conn=conn,
            )

        conn.execute.assert_awaited_once()
        call_args = conn.execute.await_args.args
        self.assertIn("provId", call_args[0])
        self.assertEqual(call_args[1], "TPHCM")
        self.assertEqual(call_args[2], 99)

    async def test_province_unknown_does_not_update(self):
        """When mapper returns None, user.provId must not be touched."""
        conn = FakeConn()

        with patch(
            "app.services.nmaiex_candidate_enrichment.map_string_to_province_id",
            AsyncMock(return_value=None),
        ):
            from app.services.nmaiex_candidate_enrichment import (
                _normalize_and_update_province,
            )

            await _normalize_and_update_province(
                candidate_id=99,
                raw_location="Unknown City XYZ",
                conn=conn,
            )

        conn.execute.assert_not_awaited()

    async def test_province_none_location_skips_mapper(self):
        """None location should skip the mapper entirely."""
        conn = FakeConn()
        mock_mapper = AsyncMock()

        with patch(
            "app.services.nmaiex_candidate_enrichment.map_string_to_province_id",
            mock_mapper,
        ):
            from app.services.nmaiex_candidate_enrichment import (
                _normalize_and_update_province,
            )

            await _normalize_and_update_province(
                candidate_id=99,
                raw_location=None,
                conn=conn,
            )

        mock_mapper.assert_not_awaited()
        conn.execute.assert_not_awaited()


if __name__ == "__main__":
    import unittest

    unittest.main()
