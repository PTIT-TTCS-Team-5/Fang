from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from app.core.config import settings
from app.services.embedding import embed_chunks

API_KEY_FIELD = "openai" + "_" + "api" + "_" + "key"


class _FakeEmbeddingsAPI:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(self, *, model: str, input: list[str], dimensions: int):
        self.calls.append(
            {
                "model": model,
                "input": list(input),
                "dimensions": dimensions,
            }
        )
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    index=index,
                    embedding=[float(index + 1)] * dimensions,
                )
                for index, _ in enumerate(input)
            ],
            usage=SimpleNamespace(prompt_tokens=len(input) * 10),
        )


class _FakeAsyncOpenAI:
    instances: list["_FakeAsyncOpenAI"] = []

    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key
        self.embeddings = _FakeEmbeddingsAPI()
        self.closed = False
        self.__class__.instances.append(self)

    async def close(self) -> None:
        self.closed = True


class EmbeddingTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.original_provider = settings.embedding_provider
        self.original_model = settings.embedding_model
        self.original_dim = settings.embedding_dim
        self.original_batch_size = settings.embedding_batch_size
        self.original_api_key = getattr(settings, API_KEY_FIELD)
        _FakeAsyncOpenAI.instances.clear()

    async def asyncTearDown(self) -> None:
        settings.embedding_provider = self.original_provider
        settings.embedding_model = self.original_model
        settings.embedding_dim = self.original_dim
        settings.embedding_batch_size = self.original_batch_size
        setattr(settings, API_KEY_FIELD, self.original_api_key)

    async def test_embed_chunks_uses_configured_model_dimensions_and_batching(
        self,
    ) -> None:
        settings.embedding_provider = "openai"
        settings.embedding_model = "text-embedding-3-small"
        settings.embedding_dim = 4
        settings.embedding_batch_size = 2
        setattr(settings, API_KEY_FIELD, "local")

        with patch("app.services.embedding.AsyncOpenAI", _FakeAsyncOpenAI):
            vectors = await embed_chunks([" chunk one ", "chunk two", "chunk three"])

        self.assertEqual(len(_FakeAsyncOpenAI.instances), 1)
        client = _FakeAsyncOpenAI.instances[0]
        self.assertEqual(client.api_key, "local")
        self.assertTrue(client.closed)
        self.assertEqual(len(client.embeddings.calls), 2)
        self.assertEqual(
            client.embeddings.calls[0]["input"], ["chunk one", "chunk two"]
        )
        self.assertEqual(client.embeddings.calls[1]["input"], ["chunk three"])
        self.assertTrue(
            all(
                call["model"] == "text-embedding-3-small"
                for call in client.embeddings.calls
            )
        )
        self.assertTrue(
            all(call["dimensions"] == 4 for call in client.embeddings.calls)
        )
        self.assertEqual(vectors, [[1.0] * 4, [2.0] * 4, [1.0] * 4])

    async def test_embed_chunks_rejects_unsupported_provider(self) -> None:
        settings.embedding_provider = "stub"
        setattr(settings, API_KEY_FIELD, "local")

        with self.assertRaisesRegex(ValueError, "Unsupported embedding provider"):
            await embed_chunks(["chunk one"])


if __name__ == "__main__":
    import unittest

    unittest.main()
