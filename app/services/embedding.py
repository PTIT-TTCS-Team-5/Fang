from __future__ import annotations

from typing import List, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import logger


async def embed_chunks(
    chunks: List[str],
    dimensions: Optional[int] = None,
) -> List[List[float]]:
    """Embed chunk content with the configured provider and dimensions.

    Args:
        chunks: List of non-empty strings to embed.
        dimensions: Optional override for embedding dimensions.
                    Supports OpenAI Matryoshka truncation (e.g. 256 for skill text).
                    Falls back to settings.embedding_dim if None.
    """

    if not chunks:
        return []

    provider = settings.embedding_provider.strip().lower()
    if provider != "openai":
        raise ValueError(
            f"Unsupported embedding provider: {settings.embedding_provider}"
        )
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai.")
    if settings.embedding_batch_size <= 0:
        raise ValueError("EMBEDDING_BATCH_SIZE must be greater than 0.")

    normalized_chunks: list[str] = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, str) or not chunk.strip():
            raise ValueError(f"chunks[{index}] must be a non-empty string.")
        normalized_chunks.append(chunk.strip())

    # Use provided dimensions or fallback to the default from settings
    effective_dims = dimensions if dimensions is not None else settings.embedding_dim

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    vectors: list[list[float] | None] = [None] * len(normalized_chunks)
    total_prompt_tokens = 0

    try:
        for start_index in range(
            0, len(normalized_chunks), settings.embedding_batch_size
        ):
            batch = normalized_chunks[
                start_index : start_index + settings.embedding_batch_size
            ]
            response = await client.embeddings.create(
                model=settings.embedding_model,
                input=batch,
                dimensions=effective_dims,
            )

            for item in response.data:
                vectors[start_index + item.index] = item.embedding

            usage = getattr(response, "usage", None)
            if usage is not None:
                total_prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0

        if any(vector is None for vector in vectors):
            raise RuntimeError("Embedding provider returned incomplete vector data.")

        logger.info(
            "Embedded chunks successfully",
            extra={
                "provider": provider,
                "model": settings.embedding_model,
                "dimension": effective_dims,
                "chunkCount": len(normalized_chunks),
                "batchSize": settings.embedding_batch_size,
                "promptTokens": total_prompt_tokens,
            },
        )
        return [vector for vector in vectors if vector is not None]
    finally:
        await client.close()
