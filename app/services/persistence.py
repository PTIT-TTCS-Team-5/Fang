from typing import Any, Dict, List, Optional

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


async def save_parsed_cv(job_app_id: int, raw_text: str, parser_ver: str):
    """Persist parsed CV raw text."""
    query = """
        INSERT INTO CVPARSED (jobAppId, rawText, parserVer)
        VALUES ($1, $2, $3)
        ON CONFLICT (jobAppId) DO UPDATE
        SET rawText = EXCLUDED.rawText, parserVer = EXCLUDED.parserVer, parseAt = CURRENT_TIMESTAMP;
    """
    async with acquire_conn() as conn:
        await conn.execute(query, job_app_id, raw_text, parser_ver)


async def save_document_chunks(
    job_app_id: int,
    source_type: str,
    chunks: List[str],
    token_counts: List[int],
    embeddings: List[List[float]],
):
    """Persist document chunks and vectors."""
    query = """
        INSERT INTO AIDOCUMENTCHUNK (jobAppId, sourceType, content, chunkIndex, tokenCount, embedding)
        VALUES ($1, $2, $3, $4, $5, $6);
    """
    async with acquire_conn() as conn:
        async with conn.transaction():
            for i, (chunk, tokens, emb) in enumerate(
                zip(chunks, token_counts, embeddings)
            ):
                emb_str = f"[{','.join(map(str, emb))}]"
                await conn.execute(
                    query,
                    job_app_id,
                    source_type,
                    chunk,
                    i,
                    tokens,
                    emb_str,
                )
