from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.core.logging import logger
from app.models.ingestion import (
    IngestionJobRequest,
    IngestionJobResponse,
    JobStatusResponse,
)
from app.services.chunking import split_into_chunks
from app.services.cv_loader import download_cv
from app.services.cv_parser import parse_to_raw_and_json
from app.services.embedding import embed_chunks
from app.services.persistence import (
    create_index_job,
    get_index_job_status,
    save_document_chunks,
    save_parsed_cv,
    update_index_job_status,
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


async def process_ingestion_task(index_job_id: int, request: IngestionJobRequest):
    """
    Background task to orchestrate the ingestion pipeline.
    """
    logger.info(
        f"Starting background ingestion for indexJobId={index_job_id}, jobAppId={request.jobAppId}"
    )
    try:
        await update_index_job_status(index_job_id, "PROCESSING")

        raw_cv_bytes = await download_cv(str(request.cvSnapUrl))
        raw_text, json_obj = await parse_to_raw_and_json(raw_cv_bytes)
        parser_ver = str(json_obj.get("parserVer") or "gemini_tiered_fallback")

        await save_parsed_cv(request.jobAppId, raw_text, parser_ver)

        chunks, token_counts = split_into_chunks(raw_text)
        vectors = await embed_chunks(chunks) if chunks else []

        if chunks:
            await save_document_chunks(
                request.jobAppId,
                "CV",
                chunks,
                token_counts,
                vectors,
            )

        await update_index_job_status(index_job_id, "SUCCESS")
    except Exception as e:
        logger.error(f"Ingestion failed for indexJobId={index_job_id}: {str(e)}")
        await update_index_job_status(index_job_id, "FAILED", error_msg=str(e))


@router.post(
    "/jobs", status_code=status.HTTP_202_ACCEPTED, response_model=IngestionJobResponse
)
async def create_ingestion_job(
    request: IngestionJobRequest, background_tasks: BackgroundTasks
):
    """
    Nhan yeu cau Ingestion: {jobAppId, cvSnapUrl}
    """
    try:
        index_job_id = await create_index_job(request.jobAppId)
        background_tasks.add_task(process_ingestion_task, index_job_id, request)
        return IngestionJobResponse(indexJobId=index_job_id, status="QUEUED")
    except Exception as e:
        logger.error(f"Failed to create ingestion job: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Unexpected error occurred while creating job"
        )


@router.get("/jobs/{indexJobId}", response_model=JobStatusResponse)
async def get_job_status(indexJobId: int):
    """
    Kiem tra trang thai cua tien trinh Ingestion.
    """
    job_record = await get_index_job_status(indexJobId)
    if not job_record:
        raise HTTPException(status_code=404, detail="Index Job not found")

    return JobStatusResponse(status=job_record["stat"], errorMsg=job_record["errormsg"])
