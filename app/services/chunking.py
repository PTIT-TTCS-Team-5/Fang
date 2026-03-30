from typing import List, Tuple

from app.core.logging import logger


def split_into_chunks(
    text: str, strategy: str = "recursive"
) -> Tuple[List[str], List[int]]:
    """
    Stub for chunking strategies such as token-based, recursive, and semantic.
    """
    logger.info(f"Chunking text using strategy: {strategy}")

    chunks = [text[i : i + 500] for i in range(0, len(text), 500)]
    token_counts = [len(chunk.split()) for chunk in chunks]

    return chunks, token_counts
