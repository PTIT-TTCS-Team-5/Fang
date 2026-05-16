from typing import Any

from app.core.logging import logger
from app.services.chunking import process_document_to_chunks
from app.services.embedding import embed_chunks
from app.services.persistence import save_chunk_payloads


async def process_job_ingestion_task(job_id: int, title: str, description: str) -> None:
    """
    Background task to process a Job Posting description, chunk it,
    embed it, and save to AIDOCUMENTCHUNK.
    """
    try:
        logger.info(f"[JOB INGESTION] Starting ingestion for job_id={job_id}")

        if not description or not description.strip():
            logger.warning(
                f"[JOB INGESTION] No description for job_id={job_id}, nothing to chunk."
            )
            # Xoá cũ nếu có
            await save_chunk_payloads(job_id, "JOB", [], replace_existing=True)
            return

        global_context = f"Thông tin chung: Vị trí {title}"
        chunk_payloads = process_document_to_chunks(description, global_context)

        chunk_contents = [payload["content"] for payload in chunk_payloads]

        vectors = await embed_chunks(chunk_contents) if chunk_contents else []

        metadata_items: list[dict[str, Any]] = [
            {"job_id": job_id, "title": title} for _ in chunk_payloads
        ]

        await save_chunk_payloads(
            job_app_id=job_id,
            source_type="JOB",
            chunk_payloads=chunk_payloads,
            metadata_items=metadata_items,
            embeddings=vectors,
            replace_existing=True,
        )

        logger.info(
            f"[JOB INGESTION] Completed for job_id={job_id}. Saved {len(chunk_payloads)} chunks."
        )

    except Exception as e:
        logger.error(f"[JOB INGESTION] Failed for job_id={job_id}: {e}", exc_info=True)
        # Log failure logic could be added here if needed
