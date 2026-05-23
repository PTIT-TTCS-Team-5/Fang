from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app.models.nmaiex_schemas import SkillMappingResult
from app.services.nmaiex_candidate_enrichment import (
    ENRICHMENT_STATUS_FAILED,
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
            "languages": ["English"],
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


if __name__ == "__main__":
    import unittest

    unittest.main()
