"""Document chunking utilities for the ingestion pipeline."""

from __future__ import annotations

from math import ceil
from types import SimpleNamespace
from typing import TypedDict

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.core.logging import logger

CHARS_PER_TOKEN = 3.5
PARENT_CHUNK_TOKEN_LIMIT = 512
CHILD_CHUNK_TARGET_TOKENS = 180
CHILD_CHUNK_OVERLAP_TOKENS = 36
HEADERS_TO_SPLIT_ON: list[tuple[str, str]] = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


class ChunkPayload(TypedDict):
    """Normalized chunk payload returned to the ingestion layer."""

    content: str
    tokenCount: int
    chunkIndex: int


def approx_token_count(text: str, chars_per_token: float = CHARS_PER_TOKEN) -> int:
    """Approximate token count using a deterministic chars-per-token ratio."""

    if not isinstance(text, str):
        raise TypeError("text must be a string.")
    if chars_per_token <= 0:
        raise ValueError("chars_per_token must be greater than 0.")

    normalized = text.strip()
    if not normalized:
        return 0

    return max(1, ceil(len(normalized) / chars_per_token))


def process_document_to_chunks(
    markdown_text: str, global_context: str
) -> list[ChunkPayload]:
    """Split markdown text into embedding-ready chunks using Small-to-Big logic."""

    normalized_markdown = _normalize_input_text(
        markdown_text, field_name="markdown_text"
    )
    normalized_context = _normalize_optional_text(
        global_context, field_name="global_context"
    )

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )
    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHILD_CHUNK_TARGET_TOKENS,
        chunk_overlap=CHILD_CHUNK_OVERLAP_TOKENS,
        length_function=approx_token_count,
        separators=["\n### ", "\n## ", "\n- ", "\n\n", "\n", ". ", " ", ""],
    )

    chunk_payloads: list[ChunkPayload] = []
    nodes = header_splitter.split_text(normalized_markdown)

    if not nodes:
        nodes = [_build_fallback_node(normalized_markdown)]

    for node in nodes:
        node_text = _normalize_optional_text(
            node.page_content, field_name="node.page_content"
        )
        if not node_text:
            continue

        child_nodes = [node_text]
        if approx_token_count(node_text) > PARENT_CHUNK_TOKEN_LIMIT:
            child_nodes = recursive_splitter.split_text(node_text)

        for child_text in child_nodes:
            normalized_child = _normalize_optional_text(
                child_text,
                field_name="child_text",
            )
            if not normalized_child:
                continue

            content = _inject_global_context(normalized_child, normalized_context)
            chunk_payloads.append(
                ChunkPayload(
                    content=content,
                    tokenCount=approx_token_count(content),
                    chunkIndex=len(chunk_payloads),
                )
            )

    return chunk_payloads


def split_into_chunks(
    text: str, strategy: str = "structured"
) -> tuple[list[str], list[int]]:
    """Backward-compatible wrapper that returns parallel content/token lists."""

    logger.info("Chunking text", extra={"strategy": strategy})
    payloads = process_document_to_chunks(markdown_text=text, global_context="")
    chunks = [payload["content"] for payload in payloads]
    token_counts = [payload["tokenCount"] for payload in payloads]
    return chunks, token_counts


def _normalize_input_text(text: str, field_name: str) -> str:
    """Validate required string input and return a trimmed version."""

    if not isinstance(text, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized = text.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")

    return normalized


def _normalize_optional_text(text: str, field_name: str) -> str:
    """Validate optional text input and normalize whitespace-only values."""

    if not isinstance(text, str):
        raise TypeError(f"{field_name} must be a string.")
    return text.strip()


def _inject_global_context(content: str, global_context: str) -> str:
    """Prefix chunk content with global context in a stable format."""

    if not global_context:
        return content
    return f"{global_context}\n\n{content}"


def _build_fallback_node(content: str) -> SimpleNamespace:
    """Create a fallback document-like object for non-markdown content."""

    return SimpleNamespace(page_content=content)
