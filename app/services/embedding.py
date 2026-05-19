from __future__ import annotations

import asyncio
from typing import List, Optional

import google.genai as genai

from app.core.config import settings
from app.core.logging import logger


def _sync_embed_batch(
    client: genai.Client,
    model: str,
    batch: list[str],
    output_dimensionality: int,
) -> list[list[float]]:
    """Synchronous embedding call — wrapped in asyncio.to_thread() for async use."""
    result = client.models.embed_content(
        model=model,
        contents=batch,
        config=genai.types.EmbedContentConfig(
            output_dimensionality=output_dimensionality,
        ),
    )
    return [e.values for e in result.embeddings]


async def embed_chunks(
    chunks: List[str],
    dimensions: Optional[int] = None,
) -> List[List[float]]:
    """Embed chunk content using Google Gemini embedding model.

    Args:
        chunks: List of non-empty strings to embed.
        dimensions: Optional override for embedding dimensions.
                    Uses output_dimensionality truncation (Matryoshka-compatible).
                    Falls back to settings.embedding_dim if None.
    """

    if not chunks:
        return []

    provider = settings.embedding_provider.strip().lower()
    if provider != "gemini":
        raise ValueError(
            f"Unsupported embedding provider: {settings.embedding_provider!r}. "
            "Expected 'gemini'. Check EMBEDDING_PROVIDER in .env."
        )
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is required when EMBEDDING_PROVIDER=gemini.")
    if settings.embedding_batch_size <= 0:
        raise ValueError("EMBEDDING_BATCH_SIZE must be greater than 0.")

    normalized_chunks: list[str] = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, str) or not chunk.strip():
            raise ValueError(f"chunks[{index}] must be a non-empty string.")
        normalized_chunks.append(chunk.strip())

    # Use provided dimensions or fallback to the default from settings
    effective_dims = dimensions if dimensions is not None else settings.embedding_dim

    client = genai.Client(api_key=settings.google_api_key)
    vectors: list[list[float]] = []

    try:
        for start_index in range(
            0, len(normalized_chunks), settings.embedding_batch_size
        ):
            batch = normalized_chunks[
                start_index : start_index + settings.embedding_batch_size
            ]
            batch_vectors = await asyncio.to_thread(
                _sync_embed_batch,
                client,
                settings.embedding_model,
                batch,
                effective_dims,
            )
            vectors.extend(batch_vectors)

        if len(vectors) != len(normalized_chunks):
            raise RuntimeError(
                f"Embedding provider returned {len(vectors)} vectors "
                f"for {len(normalized_chunks)} chunks."
            )

        logger.info(
            "Embedded chunks successfully",
            extra={
                "provider": provider,
                "model": settings.embedding_model,
                "dimension": effective_dims,
                "chunkCount": len(normalized_chunks),
                "batchSize": settings.embedding_batch_size,
            },
        )
        return vectors
    except Exception:
        logger.exception("Gemini embedding failed")
        raise
