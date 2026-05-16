import json
from typing import Any, Dict, Optional

from app.core.config import settings
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
    query = 'SELECT stat, errorMsg AS "errorMsg" FROM AIINDEXJOB WHERE indexJobId = $1;'
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
) -> int:
    """Persist parsed CV raw text and structured JSON."""
    query = """
        INSERT INTO CVPARSED (jobAppId, rawText, parsedJson, parserVer)
        VALUES ($1, $2, $3::jsonb, $4)
        ON CONFLICT (jobAppId) DO UPDATE
        SET rawText = EXCLUDED.rawText, parsedJson = EXCLUDED.parsedJson, parserVer = EXCLUDED.parserVer, parseAt = CURRENT_TIMESTAMP
        RETURNING cvParsedId;
    """
    async with acquire_conn() as conn:
        return await conn.fetchval(
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
        embedding_value = _serialize_embedding(embedding)

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

    if replace_existing and not records:
        await delete_document_chunks(job_app_id, source_type)
        return

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
        embedding_value = _serialize_embedding(embedding)

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

    if replace_existing and not records:
        await delete_document_chunks(job_app_id, source_type)
        return

    await save_chunk_payload_records(records, replace_existing=replace_existing)


async def delete_document_chunks(job_app_id: int, source_type: str) -> None:
    """Delete existing chunk rows for a given document source."""

    async with acquire_conn() as conn:
        await _delete_document_chunks(conn, job_app_id, source_type)


async def save_chunk_payload_records(
    records: list[tuple[Any, ...]],
    replace_existing: bool = False,
) -> None:
    """Execute the final insert for normalized chunk records."""

    if not records:
        return

    cast_type = _resolve_pgvector_type()
    query = f"""
        INSERT INTO AIDOCUMENTCHUNK (
            jobAppId,
            sourceType,
            content,
            chunkIndex,
            tokenCount,
            metadata,
            embedding
        )
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::{cast_type});
    """
    async with acquire_conn() as conn:
        async with conn.transaction():
            if replace_existing:
                job_app_id = records[0][0]
                source_type = records[0][1]
                await _delete_document_chunks(conn, job_app_id, source_type)
            await conn.executemany(query, records)


def _serialize_embedding(embedding: list[float] | None) -> str | None:
    """Serialize an embedding vector into pgvector text format."""

    if embedding is None:
        return None
    if not embedding:
        raise ValueError("embedding must not be empty.")
    if len(embedding) != settings.embedding_dim:
        raise ValueError(
            "embedding length does not match configured EMBEDDING_DIM "
            f"({settings.embedding_dim})."
        )

    serialized_values: list[str] = []
    for index, value in enumerate(embedding):
        try:
            serialized_values.append(f"{float(value):.12g}")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"embedding[{index}] must be a numeric value.") from exc

    return f"[{','.join(serialized_values)}]"


def _resolve_pgvector_type() -> str:
    """Return the configured pgvector storage type after validation."""

    vector_type = settings.embedding_vector_type.strip().lower()
    if vector_type not in {"halfvec", "vector"}:
        raise ValueError("EMBEDDING_VECTOR_TYPE must be either 'halfvec' or 'vector'.")
    return vector_type


async def _delete_document_chunks(conn: Any, job_app_id: int, source_type: str) -> None:
    """Delete chunk rows using the provided connection context."""

    await conn.execute(
        """
        DELETE FROM AIDOCUMENTCHUNK
        WHERE jobAppId = $1 AND sourceType = $2;
        """,
        job_app_id,
        source_type,
    )


async def update_job_structured_data(
    job_id: int,
    prov_id: Optional[str] = None,
    min_salary: Optional[int] = None,
    max_salary: Optional[int] = None,
    work_mode: Optional[str] = None,
    level_ids: Optional[list[int]] = None,
    cat_ids: Optional[list[int]] = None,
    skill_ids: Optional[list[int]] = None,
) -> None:
    """Update job structured data (no re-ingest needed)."""
    async with acquire_conn() as conn:
        async with conn.transaction():
            # Update JOBPOSTING
            updates = []
            values: list[Any] = [job_id]
            idx = 2
            if prov_id is not None:
                updates.append(f"provId = ${idx}")
                values.append(prov_id)
                idx += 1
            if min_salary is not None:
                updates.append(f"minSalary = ${idx}")
                values.append(min_salary)
                idx += 1
            if max_salary is not None:
                updates.append(f"maxSalary = ${idx}")
                values.append(max_salary)
                idx += 1
            if work_mode is not None:
                updates.append(f"workMode = ${idx}")
                values.append(work_mode)
                idx += 1

            if updates:
                q = f"UPDATE JOBPOSTING SET {', '.join(updates)} WHERE jobPostId = $1"
                await conn.execute(q, *values)

            # Update JOB_LEVEL_MAP
            if level_ids is not None:
                await conn.execute(
                    "DELETE FROM JOB_LEVEL_MAP WHERE jobPostId = $1", job_id
                )
                if level_ids:
                    records = [(job_id, lid) for lid in level_ids]
                    await conn.executemany(
                        "INSERT INTO JOB_LEVEL_MAP (jobPostId, levelId) VALUES ($1, $2)",
                        records,
                    )

            # Update JOB_CATEGORY_MAP
            if cat_ids is not None:
                await conn.execute(
                    "DELETE FROM JOB_CATEGORY_MAP WHERE jobPostId = $1", job_id
                )
                if cat_ids:
                    records = [(job_id, cid) for cid in cat_ids]
                    await conn.executemany(
                        "INSERT INTO JOB_CATEGORY_MAP (jobPostId, catId) VALUES ($1, $2)",
                        records,
                    )

            # Update JOBREQUIREMENT
            if skill_ids is not None:
                await conn.execute(
                    "DELETE FROM JOBREQUIREMENT WHERE jobPostId = $1", job_id
                )
                if skill_ids:
                    records = [(job_id, sid) for sid in skill_ids]
                    await conn.executemany(
                        "INSERT INTO JOBREQUIREMENT (jobPostId, skillId) VALUES ($1, $2)",
                        records,
                    )

            # Clear JOB_SKILL_RAW if we are updating skills
            # (The custom_skills will be populated via embed_and_store_raw_skills in the API layer)
            if skill_ids is not None:
                await conn.execute(
                    "DELETE FROM JOB_SKILL_RAW WHERE jobPostId = $1", job_id
                )


async def update_job_content_data(job_id: int, title: str, description: str) -> None:
    """Update job content (title, description), which requires re-ingestion."""
    query = """
        UPDATE JOBPOSTING
        SET title = $2, description = $3
        WHERE jobPostId = $1;
    """
    async with acquire_conn() as conn:
        await conn.execute(query, job_id, title, description)


async def update_candidate_cv_url(candidate_id: int, cv_url: str) -> None:
    """Update the original CV URL for a candidate."""
    query = """
        UPDATE CANDIDATE
        SET cvUrl = $2
        WHERE userId = $1;
    """
    async with acquire_conn() as conn:
        await conn.execute(query, candidate_id, cv_url)
