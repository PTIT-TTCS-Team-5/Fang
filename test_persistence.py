import unittest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.persistence import (
    _resolve_pgvector_type,
    _serialize_embedding,
    save_chunk_payloads,
)


class PersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.original_dim = settings.embedding_dim
        self.original_vector_type = settings.embedding_vector_type

    async def asyncTearDown(self) -> None:
        settings.embedding_dim = self.original_dim
        settings.embedding_vector_type = self.original_vector_type

    async def test_save_chunk_payloads_deletes_existing_rows_for_empty_replace(
        self,
    ) -> None:
        delete_document_chunks = AsyncMock()

        with patch(
            "app.services.persistence.delete_document_chunks",
            delete_document_chunks,
        ):
            await save_chunk_payloads(
                job_app_id=123,
                source_type="CV",
                chunk_payloads=[],
                replace_existing=True,
            )

        delete_document_chunks.assert_awaited_once_with(123, "CV")

    async def test_serialize_embedding_validates_dimension_and_formats_pgvector(
        self,
    ) -> None:
        settings.embedding_dim = 3

        self.assertEqual(_serialize_embedding([1, 2.5, 3.0]), "[1,2.5,3]")

        with self.assertRaisesRegex(ValueError, "EMBEDDING_DIM"):
            _serialize_embedding([1, 2])

    async def test_resolve_pgvector_type_accepts_halfvec_and_vector(self) -> None:
        settings.embedding_vector_type = "halfvec"
        self.assertEqual(_resolve_pgvector_type(), "halfvec")

        settings.embedding_vector_type = "vector"
        self.assertEqual(_resolve_pgvector_type(), "vector")

        settings.embedding_vector_type = "invalid"
        with self.assertRaisesRegex(ValueError, "EMBEDDING_VECTOR_TYPE"):
            _resolve_pgvector_type()


if __name__ == "__main__":
    unittest.main()
