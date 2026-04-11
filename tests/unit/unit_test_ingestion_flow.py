from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from app.api.routes_ingestion import process_ingestion_task
from app.models.ingestion import IngestionJobRequest


class IngestionFlowTests(IsolatedAsyncioTestCase):
    async def test_process_ingestion_task_runs_chunking_and_persists_embeddings(
        self,
    ) -> None:
        request = IngestionJobRequest(
            jobAppId=321,
            cvSnapUrl="https://example.com/candidate.pdf",
        )
        parsed_json = {
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
            "languages": ["English"],
            "rawText": "Sample raw CV text",
            "parserVer": "gemini:test",
        }

        update_status = AsyncMock()
        save_chunk_payloads = AsyncMock()

        with (
            patch(
                "app.api.routes_ingestion.download_cv",
                AsyncMock(return_value=b"%PDF-test%"),
            ),
            patch(
                "app.api.routes_ingestion.parse_to_raw_and_json",
                AsyncMock(return_value=("Sample raw CV text", parsed_json)),
            ),
            patch(
                "app.api.routes_ingestion.save_parsed_cv",
                AsyncMock(return_value=77),
            ) as save_parsed_cv,
            patch(
                "app.api.routes_ingestion.embed_chunks",
                AsyncMock(side_effect=lambda chunks: [[0.1, 0.2] for _ in chunks]),
            ) as embed_chunks,
            patch(
                "app.api.routes_ingestion.save_chunk_payloads",
                save_chunk_payloads,
            ),
            patch(
                "app.api.routes_ingestion.update_index_job_status",
                update_status,
            ),
        ):
            await process_ingestion_task(88, request)

        update_status.assert_any_await(88, "PROCESSING")
        update_status.assert_any_await(88, "SUCCESS")
        save_parsed_cv.assert_awaited_once_with(
            321,
            "Sample raw CV text",
            parsed_json,
            "gemini:test",
        )
        embed_chunks.assert_awaited_once()
        save_chunk_payloads.assert_awaited_once()

        args, kwargs = save_chunk_payloads.await_args
        chunk_payloads = args[2]
        metadata_items = kwargs["metadata_items"]
        embeddings = kwargs["embeddings"]

        self.assertGreater(len(chunk_payloads), 0)
        self.assertEqual(len(metadata_items), len(chunk_payloads))
        self.assertEqual(len(embeddings), len(chunk_payloads))
        self.assertTrue(
            all(
                payload["content"].startswith("[Candidate:")
                for payload in chunk_payloads
            )
        )
        self.assertTrue(
            all(metadata["cvParsedId"] == 77 for metadata in metadata_items)
        )
        self.assertTrue(kwargs["replace_existing"])


if __name__ == "__main__":
    import unittest

    unittest.main()
