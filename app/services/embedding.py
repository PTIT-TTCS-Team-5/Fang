from typing import List

from app.core.config import settings
from app.core.logging import logger


async def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """
    Stub embedding provider call.
    """
    dim = settings.embedding_dim
    provider = settings.embedding_provider
    logger.info(f"Embedding {len(chunks)} chunks using {provider} with dimension {dim}")

    vectors = []
    for _ in chunks:
        stub_vector = [0.0] * dim
        stub_vector[0] = 1.0
        vectors.append(stub_vector)

    return vectors
