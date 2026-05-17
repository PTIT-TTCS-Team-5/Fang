import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.routes_ingestion import process_ingestion_task
from app.core.database import acquire_conn
from app.models.ingestion import IngestionJobRequest
from app.models.nmaiex_schemas import (
    CandidateCvUpdateRequest,
    JobContentUpdateRequest,
    JobStructuredUpdateRequest,
)
from app.services.job_ingestion_service import process_job_ingestion_task
from app.services.nmaiex_mapper_service import embed_and_store_raw_skills
from app.services.persistence import (
    create_index_job,
    update_candidate_cv_url,
    update_job_content_data,
    update_job_structured_data,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/management", tags=["NMAIex Management"])


@router.patch("/jobs/{job_id}/structured", status_code=status.HTTP_200_OK)
async def update_job_structured(
    job_id: int, request: JobStructuredUpdateRequest
) -> dict[str, Any]:
    """
    Cập nhật dữ liệu cấu trúc cho Job (không cần re-ingest).
    """
    try:
        await update_job_structured_data(
            job_id=job_id,
            prov_id=request.provId,
            min_salary=request.minSalary,
            max_salary=request.maxSalary,
            work_mode=request.workMode,
            level_ids=request.levelIds,
            cat_ids=request.catIds,
            skill_ids=request.skillIds,
        )

        if request.custom_skills:
            async with acquire_conn() as conn:
                await embed_and_store_raw_skills(
                    entity_type="job",
                    entity_id=job_id,
                    unmatched_texts=request.custom_skills,
                    conn=conn,
                )

        return {"status": "success", "message": "Structured data updated"}
    except Exception as e:
        logger.exception(f"Failed to update structured data for job_id={job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unexpected error occurred while updating structured data",
        )


@router.patch("/jobs/{job_id}/content", status_code=status.HTTP_202_ACCEPTED)
async def update_job_content(
    job_id: int, request: JobContentUpdateRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    """
    Cập nhật nội dung Job (title, description).
    Sẽ trigger background task để re-ingest (chunk + embed).
    """
    try:
        await update_job_content_data(
            job_id=job_id,
            title=request.title,
            description=request.description,
        )

        background_tasks.add_task(
            process_job_ingestion_task,
            job_id,
            request.title,
            request.description,
        )

        return {
            "status": "accepted",
            "message": "Content updated, re-ingestion started in background",
        }
    except Exception as e:
        logger.exception(f"Failed to update content for job_id={job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unexpected error occurred while updating job content",
        )


@router.patch("/candidates/{candidate_id}/cv", status_code=status.HTTP_200_OK)
async def update_candidate_cv(
    candidate_id: int,
    request: CandidateCvUpdateRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Cập nhật CV gốc của Candidate.
    """
    try:
        await update_candidate_cv_url(
            candidate_id=candidate_id,
            cv_url=request.cvUrl,
        )

        # Trigger background ingestion if there's a latest job application
        async with acquire_conn() as conn:
            latest_app = await conn.fetchrow(
                """
                SELECT jobAppId
                FROM JOBAPPLICATION
                WHERE candidateId = $1
                ORDER BY appliedAt DESC
                LIMIT 1
                """,
                candidate_id,
            )
            if latest_app:
                job_app_id = latest_app["jobappid"]
                await conn.execute(
                    "UPDATE JOBAPPLICATION SET cvSnapUrl = $1 WHERE jobAppId = $2",
                    request.cvUrl,
                    job_app_id,
                )

                # Create index job and spawn background ingestion task
                index_job_id = await create_index_job(job_app_id)
                ingest_req = IngestionJobRequest(
                    jobAppId=job_app_id, cvSnapUrl=request.cvUrl
                )
                background_tasks.add_task(
                    process_ingestion_task, index_job_id, ingest_req
                )
                logger.info(
                    f"[NMAIex Management] Candidate CV updated. Triggered background CV re-ingestion: "
                    f"candidate_id={candidate_id}, job_app_id={job_app_id}, index_job_id={index_job_id}"
                )

        return {
            "status": "success",
            "message": "Candidate CV URL updated and re-ingestion started",
        }
    except Exception as e:
        logger.exception(f"Failed to update CV for candidate_id={candidate_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Unexpected error occurred while updating candidate CV",
        )
