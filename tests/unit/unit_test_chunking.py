import unittest

from app.models.cv_models import ParsedCV
from app.services.chunking import process_document_to_chunks
from app.services.markdown_builder import (
    convert_json_to_markdown,
    extract_global_metadata,
)


def build_sample_parsed_cv(description: str) -> ParsedCV:
    return ParsedCV.model_validate(
        {
            "candidateInfo": [
                {
                    "fullName": "Nguyen Van A",
                    "emails": ["a@example.com"],
                    "phones": ["0123456789"],
                    "location": "Ho Chi Minh City",
                }
            ],
            "summary": "Backend engineer focused on Python and retrieval systems.",
            "experience": [
                {
                    "company": "Fang Labs",
                    "title": "Senior Backend Engineer",
                    "startDate": "2020-01",
                    "endDate": "present",
                    "description": description,
                }
            ],
            "education": [
                {
                    "school": "HCMUT",
                    "degree": "Computer Science",
                    "startDate": "2015-09",
                    "endDate": "2019-06",
                }
            ],
            "skills": ["Python", "FastAPI", "PostgreSQL", "pgvector"],
            "certificates": ["AWS SAA"],
            "languages": [
                {"language": "Vietnamese", "proficiency": "NATIVE"},
                {"language": "English", "proficiency": "ADVANCED"},
            ],
            "rawText": "Sample raw CV text",
            "parserVer": "gemini:test",
        }
    )


class ChunkingTests(unittest.TestCase):
    def test_chunking_injects_global_context_and_returns_ordered_payloads(self) -> None:
        parsed_cv = build_sample_parsed_cv(
            "Built ingestion APIs. Improved search quality. Optimized PostgreSQL."
        )

        global_context = extract_global_metadata(parsed_cv)
        markdown_text = convert_json_to_markdown(parsed_cv)
        chunk_payloads = process_document_to_chunks(markdown_text, global_context)

        self.assertGreater(len(chunk_payloads), 0)
        self.assertTrue(markdown_text.startswith("# Nguyen Van A"))
        self.assertIn("Target Role: Senior Backend Engineer", global_context)

        for expected_index, payload in enumerate(chunk_payloads):
            self.assertEqual(payload["chunkIndex"], expected_index)
            self.assertGreater(payload["tokenCount"], 0)
            self.assertTrue(payload["content"].startswith(global_context))

    def test_long_parent_sections_are_split_into_multiple_child_chunks(self) -> None:
        repeated_bullet = "Designed resilient ingestion workers for parser output."
        long_description = "\n".join(f"- {repeated_bullet}" for _ in range(80))
        parsed_cv = build_sample_parsed_cv(long_description)

        global_context = extract_global_metadata(parsed_cv)
        markdown_text = convert_json_to_markdown(parsed_cv)
        chunk_payloads = process_document_to_chunks(markdown_text, global_context)

        experience_chunks = [
            payload
            for payload in chunk_payloads
            if repeated_bullet in payload["content"]
        ]

        self.assertGreater(len(experience_chunks), 1)
        self.assertTrue(all(payload["tokenCount"] <= 320 for payload in chunk_payloads))
        self.assertTrue(
            all("# Nguyen Van A" in payload["content"] for payload in experience_chunks)
        )
        self.assertTrue(
            all("## Experience" in payload["content"] for payload in experience_chunks)
        )
        self.assertTrue(
            all(
                "### Senior Backend Engineer at Fang Labs" in payload["content"]
                for payload in experience_chunks
            )
        )


if __name__ == "__main__":
    unittest.main()
