from typing import Any
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from app.core.config import settings
from app.services.embedding import embed_chunks

GOOGLE_KEY_FIELD = "google" + "_api" + "_key"


class FakeEmbedding:
    def __init__(self, values: list[float]) -> None:
        self.values = values


class FakeEmbedContentResponse:
    def __init__(self, embeddings: list[FakeEmbedding]) -> None:
        self.embeddings = embeddings


class FakeModelsAPI:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def embed_content(
        self,
        model: str,
        contents: list[str],
        config: Any,
    ) -> FakeEmbedContentResponse:
        self.calls.append(
            {
                "model": model,
                "contents": list(contents),
                "config": config,
            }
        )

        # Get output_dimensionality if it exists on the config
        output_dimensionality = getattr(config, "output_dimensionality", 1536)
        if output_dimensionality is None:
            output_dimensionality = 1536

        embeddings = []
        for index, _ in enumerate(contents):
            # Deterministic values for checking batch order:
            # First element has values [1.0, 1.0, ...], second has [2.0, 2.0, ...]
            # which perfectly mirrors the original test setup.
            values = [float(index + 1)] * output_dimensionality
            embeddings.append(FakeEmbedding(values=values))

        return FakeEmbedContentResponse(embeddings=embeddings)


class FakeGeminiClient:
    instances: list["FakeGeminiClient"] = []

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self.models = FakeModelsAPI()
        self.__class__.instances.append(self)


class EmbeddingTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.original_provider = settings.embedding_provider
        self.original_model = settings.embedding_model
        self.original_dim = settings.embedding_dim
        self.original_batch_size = settings.embedding_batch_size
        self.original_google_key = getattr(settings, GOOGLE_KEY_FIELD)
        FakeGeminiClient.instances.clear()

    async def asyncTearDown(self) -> None:
        settings.embedding_provider = self.original_provider
        settings.embedding_model = self.original_model
        settings.embedding_dim = self.original_dim
        settings.embedding_batch_size = self.original_batch_size
        setattr(settings, GOOGLE_KEY_FIELD, self.original_google_key)

    async def test_embed_chunks_uses_configured_model_dimensions_and_batching(
        self,
    ) -> None:
        settings.embedding_provider = "gemini"
        settings.embedding_model = "gemini-embedding-001"
        settings.embedding_dim = 4
        settings.embedding_batch_size = 2
        setattr(settings, GOOGLE_KEY_FIELD, "local")

        with patch("app.services.embedding.genai.Client", FakeGeminiClient):
            vectors = await embed_chunks([" chunk one ", "chunk two", "chunk three"])

        # Check client creation
        self.assertEqual(len(FakeGeminiClient.instances), 1)
        client = FakeGeminiClient.instances[0]
        self.assertEqual(client.api_key, "local")

        # Check calls (batching of size 2 means 2 calls for 3 chunks)
        self.assertEqual(len(client.models.calls), 2)

        # Batch 1: ["chunk one", "chunk two"]
        self.assertEqual(client.models.calls[0]["contents"], ["chunk one", "chunk two"])
        self.assertEqual(client.models.calls[0]["model"], "gemini-embedding-001")
        self.assertEqual(client.models.calls[0]["config"].output_dimensionality, 4)

        # Batch 2: ["chunk three"]
        self.assertEqual(client.models.calls[1]["contents"], ["chunk three"])
        self.assertEqual(client.models.calls[1]["model"], "gemini-embedding-001")
        self.assertEqual(client.models.calls[1]["config"].output_dimensionality, 4)

        # Check returned vectors order & dimension
        # Batch 1 first element: [1.0]*4
        # Batch 1 second element: [2.0]*4
        # Batch 2 first element: [1.0]*4
        self.assertEqual(vectors, [[1.0] * 4, [2.0] * 4, [1.0] * 4])

    async def test_embed_chunks_uses_explicit_dimensions_override(self) -> None:
        settings.embedding_provider = "gemini"
        settings.embedding_model = "gemini-embedding-001"
        settings.embedding_dim = 1536
        settings.embedding_batch_size = 2
        setattr(settings, GOOGLE_KEY_FIELD, "local")

        with patch("app.services.embedding.genai.Client", FakeGeminiClient):
            vectors = await embed_chunks(["chunk one"], dimensions=8)

        self.assertEqual(len(FakeGeminiClient.instances), 1)
        client = FakeGeminiClient.instances[0]
        self.assertEqual(len(client.models.calls), 1)
        self.assertEqual(client.models.calls[0]["config"].output_dimensionality, 8)
        self.assertEqual(len(vectors[0]), 8)

    async def test_embed_chunks_rejects_unsupported_provider(self) -> None:
        settings.embedding_provider = "openai"
        setattr(settings, GOOGLE_KEY_FIELD, "local")

        with self.assertRaisesRegex(ValueError, "Unsupported embedding provider"):
            await embed_chunks(["chunk one"])

    async def test_embed_chunks_rejects_missing_google_api_key(self) -> None:
        settings.embedding_provider = "gemini"
        setattr(settings, GOOGLE_KEY_FIELD, None)

        with self.assertRaisesRegex(ValueError, "GOOGLE_API_KEY is required"):
            await embed_chunks(["chunk one"])

    async def test_embed_chunks_rejects_invalid_batch_size(self) -> None:
        settings.embedding_provider = "gemini"
        setattr(settings, GOOGLE_KEY_FIELD, "local")
        settings.embedding_batch_size = 0

        with self.assertRaisesRegex(
            ValueError, "EMBEDDING_BATCH_SIZE must be greater than 0"
        ):
            await embed_chunks(["chunk one"])

    async def test_embed_chunks_rejects_empty_chunks(self) -> None:
        settings.embedding_provider = "gemini"
        setattr(settings, GOOGLE_KEY_FIELD, "local")

        # Test empty string chunk
        with self.assertRaisesRegex(ValueError, "must be a non-empty string"):
            await embed_chunks(["chunk one", "", "chunk three"])

        # Test whitespace-only string chunk
        with self.assertRaisesRegex(ValueError, "must be a non-empty string"):
            await embed_chunks(["chunk one", "   ", "chunk three"])

    async def test_embed_chunks_rejects_non_string_chunks(self) -> None:
        settings.embedding_provider = "gemini"
        setattr(settings, GOOGLE_KEY_FIELD, "local")

        # Test non-string chunk (e.g. integer)
        with self.assertRaisesRegex(ValueError, "must be a non-empty string"):
            await embed_chunks(["chunk one", 123, "chunk three"])  # type: ignore


if __name__ == "__main__":
    import unittest

    unittest.main()
