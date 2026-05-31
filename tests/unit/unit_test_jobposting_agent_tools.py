import unittest
from unittest.mock import AsyncMock, patch

from app.services import jobposting_tools as tools


class MockAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return None


class JobPostingAgentToolsTests(unittest.IsolatedAsyncioTestCase):
    @patch(
        "app.services.jobposting_tools._resolve_language_filter", new_callable=AsyncMock
    )
    @patch(
        "app.services.jobposting_tools._fetch_languages_for_candidates",
        new_callable=AsyncMock,
    )
    @patch(
        "app.services.jobposting_tools._fetch_application_enrichment",
        new_callable=AsyncMock,
    )
    @patch(
        "app.services.jobposting_tools.rank_candidates_for_job", new_callable=AsyncMock
    )
    async def test_ranking_caps_limit_and_warns(
        self, mock_rank, mock_apps, mock_langs, mock_lang_filter
    ) -> None:
        mock_rank.return_value = {
            "total_candidates": 1,
            "results": [{"candidate_id": 7, "candidate_name": "A", "match_score": 0.9}],
        }
        mock_apps.return_value = {
            7: {
                "job_app_id": 101,
                "application_status": "SUBMITTED",
                "province_id": "TPHCM",
            }
        }
        mock_langs.return_value = {7: []}
        mock_lang_filter.return_value = {"query": None, "code": None, "name": None}

        result = await tools.get_job_candidate_ranking(12, limit=100)

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["limit"], 25)
        self.assertEqual(result["data"]["candidates"][0]["job_app_id"], 101)
        self.assertEqual(result["warnings"][0]["type"], "limit_capped")

    @patch(
        "app.services.jobposting_tools._resolve_language_filter", new_callable=AsyncMock
    )
    @patch(
        "app.services.jobposting_tools._fetch_languages_for_candidates",
        new_callable=AsyncMock,
    )
    @patch(
        "app.services.jobposting_tools._fetch_application_enrichment",
        new_callable=AsyncMock,
    )
    @patch(
        "app.services.jobposting_tools.rank_candidates_for_job", new_callable=AsyncMock
    )
    async def test_ranking_includes_unknown_language_with_warning(
        self, mock_rank, mock_apps, mock_langs, mock_lang_filter
    ) -> None:
        mock_rank.return_value = {
            "total_candidates": 1,
            "results": [{"candidate_id": 7, "candidate_name": "A", "match_score": 0.9}],
        }
        mock_apps.return_value = {
            7: {
                "job_app_id": 101,
                "application_status": "SUBMITTED",
                "province_id": "TPHCM",
            }
        }
        mock_langs.return_value = {
            7: [{"lang_code": None, "raw_name": "Klingon", "proficiency": "ADVANCED"}]
        }
        mock_lang_filter.return_value = {
            "query": "english",
            "code": "en",
            "name": "English",
        }

        result = await tools.get_job_candidate_ranking(
            12,
            filters={"language": "English", "min_language_proficiency": "ADVANCED"},
        )

        self.assertEqual(len(result["data"]["candidates"]), 1)
        self.assertTrue(any(w["type"] == "data_quality" for w in result["warnings"]))
        candidate = result["data"]["candidates"][0]
        self.assertEqual(candidate["match_label"], "Ứng viên nổi trội")
        self.assertIn("explanation", candidate)

    @patch(
        "app.services.jobposting_tools._resolve_language_filter", new_callable=AsyncMock
    )
    @patch("app.services.jobposting_tools.acquire_conn")
    async def test_language_certificate_filter_uses_normalized_score(
        self, mock_acquire, mock_lang_filter
    ) -> None:
        conn = AsyncMock()
        conn.fetch.return_value = [
            {
                "job_app_id": 101,
                "candidate_id": 7,
                "application_status": "SUBMITTED",
                "candidate_name": "A",
                "province_id": "TPHCM",
                "province_name": "TP.HCM",
                "years_experience": 3,
                "lang_code": "en",
                "lang_name": "English",
                "proficiency": "ADVANCED",
                "cert_code": "TOEIC",
                "cert_name": "TOEIC",
                "raw_text": "TOEIC 650",
                "normalized_score": "650",
            }
        ]
        mock_acquire.return_value = MockAcquire(conn)
        mock_lang_filter.return_value = {"query": None, "code": None, "name": None}

        result = await tools.find_candidates_by_language_certificate(
            12, certificate="TOEIC", min_score=600
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["total_matches"], 1)
        cert = result["data"]["results"][0]["languages"][0]["certificate"]
        self.assertEqual(cert["score"], 650)

    @patch("app.services.jobposting_tools.acquire_conn")
    async def test_work_location_remote_includes_other_provinces(
        self, mock_acquire
    ) -> None:
        conn = AsyncMock()
        conn.fetchrow.return_value = {
            "province_id": "HANOI",
            "region_id": "NORTH",
            "work_mode": "REMOTE",
            "work_location": "Remote",
        }
        conn.fetch.return_value = [
            {
                "job_app_id": 101,
                "candidate_id": 7,
                "application_status": "SUBMITTED",
                "candidate_name": "A",
                "province_id": "TPHCM",
                "province_name": "TP.HCM",
                "region_id": "SOUTH",
                "years_experience": 3,
            }
        ]
        mock_acquire.return_value = MockAcquire(conn)

        result = await tools.filter_candidates_by_work_location(12)

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["total_matches"], 1)
        self.assertTrue(result["data"]["results"][0]["evidence"]["remote_inclusive"])

    @patch("app.services.jobposting_tools.acquire_conn")
    async def test_education_filter_normalizes_bachelor(self, mock_acquire) -> None:
        conn = AsyncMock()
        conn.fetch.return_value = [
            {
                "job_app_id": 101,
                "candidate_id": 7,
                "application_status": "SUBMITTED",
                "candidate_name": "A",
                "province_id": "TPHCM",
                "province_name": "TP.HCM",
                "years_experience": 3,
                "parsed_json": {
                    "education": [
                        {
                            "degree": "Cử nhân Công nghệ thông tin",
                            "school": "Đại học A",
                        }
                    ]
                },
            }
        ]
        mock_acquire.return_value = MockAcquire(conn)

        result = await tools.filter_candidates_by_education_level(
            12, min_degree_level="bachelor"
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["total_matches"], 1)
        self.assertEqual(result["data"]["results"][0]["degree_level"], "bachelor")

    @patch("app.services.jobposting_tools.acquire_conn")
    async def test_scope_check_blocks_other_job_application(self, mock_acquire) -> None:
        conn = AsyncMock()
        conn.fetchrow.return_value = None
        mock_acquire.return_value = MockAcquire(conn)

        result = await tools.get_job_application_summary(job_post_id=12, job_app_id=999)

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "ACCESS_DENIED")

    @patch(
        "app.services.jobposting_tools._get_application_detail", new_callable=AsyncMock
    )
    async def test_full_cv_masks_email_and_phone(self, mock_detail) -> None:
        mock_detail.return_value = (
            {"job_app_id": 101},
            {
                "job_app_id": 101,
                "candidate_id": 7,
                "candidate_name": "Nguyen Van A",
                "email": "candidate@example.com",
                "phone": "+84 912 345 678",
                "province_name": "TP.HCM",
                "parsed_json": {
                    "candidateInfo": [
                        {
                            "fullName": "Nguyen Van A",
                            "emails": ["candidate@example.com"],
                            "phones": ["0912345678"],
                            "location": "1 Street",
                        }
                    ],
                    "rawText": "Email candidate@example.com phone 0912345678",
                },
                "raw_text": "Email candidate@example.com phone 0912345678",
            },
        )

        result = await tools.get_job_application_full_cv(12, 101)
        dumped = str(result["data"])

        self.assertTrue(result["ok"])
        self.assertNotIn("candidate@example.com", dumped)
        self.assertNotIn("0912345678", dumped)
        self.assertIn("***5678", dumped)

    @patch(
        "app.services.jobposting_tools._fetch_languages_for_candidates",
        new_callable=AsyncMock,
    )
    @patch("app.services.jobposting_tools.acquire_conn")
    async def test_count_returns_total_and_respects_status_filter(
        self, mock_acquire, mock_langs
    ) -> None:
        conn = AsyncMock()
        conn.fetch.return_value = [
            {
                "job_app_id": 101,
                "candidate_id": 7,
                "application_status": "SUBMITTED",
                "province_id": "TPHCM",
            },
            {
                "job_app_id": 102,
                "candidate_id": 8,
                "application_status": "REJECTED",
                "province_id": "TPHCM",
            },
        ]
        mock_acquire.return_value = MockAcquire(conn)
        mock_langs.return_value = {7: [], 8: []}

        result = await tools.count_job_applications(12, filters={"status": "SUBMITTED"})

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["count"], 1)
        self.assertEqual(result["data"]["job_app_ids"], [101])

    @patch(
        "app.services.jobposting_tools._resolve_language_filter", new_callable=AsyncMock
    )
    @patch(
        "app.services.jobposting_tools._fetch_languages_for_candidates",
        new_callable=AsyncMock,
    )
    @patch("app.services.jobposting_tools.acquire_conn")
    async def test_text_search_is_scoped_by_job_post_id(
        self, mock_acquire, mock_langs, mock_lang_filter
    ) -> None:
        conn = AsyncMock()
        conn.fetch.return_value = [
            {
                "job_app_id": 101,
                "candidate_id": 7,
                "application_status": "SUBMITTED",
                "raw_text": "Python backend developer",
                "province_id": "TPHCM",
                "candidate_name": "A",
            }
        ]
        mock_acquire.return_value = MockAcquire(conn)
        mock_langs.return_value = {7: []}
        mock_lang_filter.return_value = {"query": None, "code": None, "name": None}

        result = await tools.search_job_applications_text(12, "Python")

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["results"][0]["job_app_id"], 101)
        self.assertIn("ja.jobPostId = $1", conn.fetch.call_args[0][0])
        self.assertEqual(conn.fetch.call_args[0][1], 12)


if __name__ == "__main__":
    unittest.main()
