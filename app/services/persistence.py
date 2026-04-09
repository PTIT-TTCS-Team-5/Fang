import json
from typing import Any, Dict, Optional

from app.core.database import acquire_conn


async def create_index_job(job_app_id: int) -> int:
    """Create a queued record in AIINDEXJOB."""
    query = """
        INSERT INTO AIINDEXJOB (jobAppId, stat)
        VALUES ($1, 'QUEUED')
        RETURNING indexJobId;
    """
    async with acquire_conn() as conn:
        index_job_id = await conn.fetchval(query, job_app_id)
        return index_job_id


async def get_index_job_status(index_job_id: int) -> Optional[Dict[str, Any]]:
    """Fetch ingestion status by job id."""
    query = "SELECT stat, errorMsg FROM AIINDEXJOB WHERE indexJobId = $1;"
    async with acquire_conn() as conn:
        record = await conn.fetchrow(query, index_job_id)
        return dict(record) if record else None


async def update_index_job_status(
    index_job_id: int, status: str, error_msg: Optional[str] = None
):
    """Update ingestion status."""
    query = """
        UPDATE AIINDEXJOB
        SET stat = $2, errorMsg = $3
        WHERE indexJobId = $1;
    """
    async with acquire_conn() as conn:
        await conn.execute(query, index_job_id, status, error_msg)


async def save_parsed_cv(
    job_app_id: int, raw_text: str, parsed_json: dict, parser_ver: str
):
    """Persist parsed CV raw text and structured JSON."""
    query = """
        INSERT INTO CVPARSED (jobAppId, rawText, parsedJson, parserVer)
        VALUES ($1, $2, $3::jsonb, $4)
        ON CONFLICT (jobAppId) DO UPDATE
        SET rawText = EXCLUDED.rawText, parsedJson = EXCLUDED.parsedJson, parserVer = EXCLUDED.parserVer, parseAt = CURRENT_TIMESTAMP;
    """
    async with acquire_conn() as conn:
        await conn.execute(
            query, job_app_id, raw_text, json.dumps(parsed_json), parser_ver
        )


async def save_document_chunks(
    job_app_id: int,
    source_type: str,
    chunks: list[str],
    token_counts: list[int],
    embeddings: list[list[float]] | None = None,
    metadata_items: list[dict[str, Any] | None] | None = None,
    replace_existing: bool = False,
):
    """Persist document chunks with optional metadata and embeddings."""

    if len(chunks) != len(token_counts):
        raise ValueError("chunks and token_counts must have the same length.")

    if embeddings is not None and len(embeddings) != len(chunks):
        raise ValueError("embeddings and chunks must have the same length.")

    if metadata_items is not None and len(metadata_items) != len(chunks):
        raise ValueError("metadata_items and chunks must have the same length.")

    records: list[tuple[Any, ...]] = []
    for index, chunk in enumerate(chunks):
        metadata = metadata_items[index] if metadata_items is not None else None
        embedding = embeddings[index] if embeddings is not None else None
        embedding_value = None
        if embedding is not None:
            embedding_value = f"[{','.join(map(str, embedding))}]"

        records.append(
            (
                job_app_id,
                source_type,
                chunk,
                index,
                token_counts[index],
                json.dumps(metadata) if metadata is not None else None,
                embedding_value,
            )
        )

    await save_chunk_payload_records(records, replace_existing=replace_existing)


async def save_chunk_payloads(
    job_app_id: int,
    source_type: str,
    chunk_payloads: list[dict[str, Any]],
    metadata_items: list[dict[str, Any] | None] | None = None,
    embeddings: list[list[float] | None] | None = None,
    replace_existing: bool = False,
) -> None:
    """Persist normalized chunk payloads into AIDOCUMENTCHUNK."""

    if metadata_items is not None and len(metadata_items) != len(chunk_payloads):
        raise ValueError("metadata_items and chunk_payloads must have the same length.")

    if embeddings is not None and len(embeddings) != len(chunk_payloads):
        raise ValueError("embeddings and chunk_payloads must have the same length.")

    records: list[tuple[Any, ...]] = []
    for index, payload in enumerate(chunk_payloads):
        content = payload.get("content")
        chunk_index = payload.get("chunkIndex")
        token_count = payload.get("tokenCount")

        if not isinstance(content, str) or not content.strip():
            raise ValueError(
                f"chunk_payloads[{index}]['content'] must be a non-empty string."
            )
        if not isinstance(chunk_index, int):
            raise ValueError(f"chunk_payloads[{index}]['chunkIndex'] must be an int.")
        if not isinstance(token_count, int):
            raise ValueError(f"chunk_payloads[{index}]['tokenCount'] must be an int.")

        metadata = metadata_items[index] if metadata_items is not None else None
        embedding = embeddings[index] if embeddings is not None else None
        embedding_value = None
        if embedding is not None:
            embedding_value = f"[{','.join(map(str, embedding))}]"

        records.append(
            (
                job_app_id,
                source_type,
                content,
                chunk_index,
                token_count,
                json.dumps(metadata) if metadata is not None else None,
                embedding_value,
            )
        )

    await save_chunk_payload_records(records, replace_existing=replace_existing)


async def save_chunk_payload_records(
    records: list[tuple[Any, ...]],
    replace_existing: bool = False,
) -> None:
    """Execute the final insert for normalized chunk records."""

    if not records:
        return

    query = """
        INSERT INTO AIDOCUMENTCHUNK (
            jobAppId,
            sourceType,
            content,
            chunkIndex,
            tokenCount,
            metadata,
            embedding
        )
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7);
    """
    async with acquire_conn() as conn:
        async with conn.transaction():
            if replace_existing:
                job_app_id = records[0][0]
                source_type = records[0][1]
                await conn.execute(
                    """
                    DELETE FROM AIDOCUMENTCHUNK
                    WHERE jobAppId = $1 AND sourceType = $2;
                    """,
                    job_app_id,
                    source_type,
                )
            await conn.executemany(query, records)
