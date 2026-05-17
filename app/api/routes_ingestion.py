import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.core.database import acquire_conn
from app.core.logging import logger
from app.models.cv_models import ParsedCV
from app.models.ingestion import (
    IngestionJobRequest,
    IngestionJobResponse,
    JobStatusResponse,
)
from app.services.chunking import process_document_to_chunks
from app.services.cv_loader import download_cv
from app.services.cv_parser import get_last_parse_trace, parse_to_raw_and_json
from app.services.embedding import embed_chunks
from app.services.markdown_builder import (
    convert_json_to_markdown,
    extract_global_metadata,
)
from app.services.nmaiex_mapper_service import embed_and_store_raw_skills, map_skills
from app.services.persistence import (
    create_index_job,
    get_index_job_status,
    save_chunk_payloads,
    save_parsed_cv,
    update_index_job_status,
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


def _build_chunk_metadata(
    cv_parsed_id: int,
    parser_ver: str,
    global_context: str,
    parsed_cv: ParsedCV,
    markdown_text: str,
    chunk_count: int,
) -> list[dict[str, object]]:
    """Build deterministic metadata payloads for persisted CV chunks."""

    candidate_name = None
    if parsed_cv.candidateInfo:
        candidate_name = parsed_cv.candidateInfo[0].fullName

    base_metadata = {
        "cvParsedId": cv_parsed_id,
        "parserVer": parser_ver,
        "candidateName": candidate_name,
        "chunkingStrategy": "hybrid-structure-aware",
        "contextInjected": True,
        "globalContext": global_context,
        "markdownLength": len(markdown_text),
    }
    return [dict(base_metadata) for _ in range(chunk_count)]


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
        parsed_cv = ParsedCV.model_validate(json_obj)
        parser_ver = str(json_obj.get("parserVer") or "unknown")
        parser_trace = get_last_parse_trace() or {}

        cv_parsed_id = await save_parsed_cv(
            request.jobAppId,
            raw_text,
            json_obj,
            parser_ver,
        )
        logger.info(
            "CV parse persisted successfully",
            extra={
                "jobAppId": request.jobAppId,
                "parserVer": parser_ver,
                "fallbackPath": parser_trace.get("fallback_path"),
            },
        )

        global_context = extract_global_metadata(parsed_cv)
        markdown_text = convert_json_to_markdown(parsed_cv)
        chunk_payloads = process_document_to_chunks(markdown_text, global_context)
        chunk_contents = [payload["content"] for payload in chunk_payloads]
        metadata_items = _build_chunk_metadata(
            cv_parsed_id=cv_parsed_id,
            parser_ver=parser_ver,
            global_context=global_context,
            parsed_cv=parsed_cv,
            markdown_text=markdown_text,
            chunk_count=len(chunk_payloads),
        )
        vectors = await embed_chunks(chunk_contents) if chunk_contents else []

        await save_chunk_payloads(
            request.jobAppId,
            "CV",
            chunk_payloads,
            metadata_items=metadata_items,
            embeddings=vectors,
            replace_existing=True,
        )

        # Update candidate's structured expyears, skills (matched and unmatched) in DB
        try:
            # Calculate experience years from parsed CV experience entries
            total_months = 0
            for exp in parsed_cv.experience:
                if not exp.startDate:
                    continue
                try:
                    start_year, start_month = map(int, exp.startDate.split("-"))
                    start_date = datetime.date(start_year, start_month, 1)

                    if not exp.endDate or exp.endDate == "present":
                        end_date = datetime.date.today()
                    else:
                        end_year, end_month = map(int, exp.endDate.split("-"))
                        end_date = datetime.date(end_year, end_month, 1)

                    months = (end_date.year - start_date.year) * 12 + (
                        end_date.month - start_date.month
                    )
                    if months > 0:
                        total_months += months
                except Exception:
                    continue
            computed_exp_years = max(
                0, total_months // 12
            )  # 0 is valid for Fresher/Intern

            async with acquire_conn() as conn:
                # Find candidateId
                cand_row = await conn.fetchrow(
                    "SELECT candidateId FROM JOBAPPLICATION WHERE jobAppId = $1",
                    request.jobAppId,
                )
                if cand_row:
                    cand_id = cand_row["candidateid"]

                    # 1. Update expyears in CANDIDATE table
                    await conn.execute(
                        "UPDATE CANDIDATE SET expyears = $1 WHERE userId = $2",
                        computed_exp_years,
                        cand_id,
                    )
                    logger.info(
                        f"[INGESTION] Calculated and updated expyears={computed_exp_years} for candidate_id={cand_id}"
                    )

                    # 2. Extract CV skills and map them
                    if parsed_cv.skills:
                        mapping_result = await map_skills(parsed_cv.skills)

                        # Clear and insert into CANDIDATESKILL (Tầng 1)
                        await conn.execute(
                            "DELETE FROM CANDIDATESKILL WHERE userId = $1", cand_id
                        )
                        for skill_id in mapping_result.matched_ids:
                            await conn.execute(
                                """
                                INSERT INTO CANDIDATESKILL (userId, skillId)
                                VALUES ($1, $2)
                                ON CONFLICT DO NOTHING
                                """,
                                cand_id,
                                skill_id,
                            )

                        # Clear and insert into CANDIDATE_SKILL_RAW (Tầng 2)
                        await conn.execute(
                            "DELETE FROM CANDIDATE_SKILL_RAW WHERE candId = $1", cand_id
                        )
                        if mapping_result.unmatched_texts:
                            await embed_and_store_raw_skills(
                                entity_type="candidate",
                                entity_id=cand_id,
                                unmatched_texts=mapping_result.unmatched_texts,
                                conn=conn,
                            )
                        logger.info(
                            f"[INGESTION] Successfully mapped and updated candidate skills in DB "
                            f"(matched: {len(mapping_result.matched_ids)}, unmatched: {len(mapping_result.unmatched_texts)})"
                        )
        except Exception as exp_err:
            logger.error(
                f"[INGESTION] Failed to update candidate expyears/skills: {exp_err}",
                exc_info=True,
            )

        logger.info(
            "Completed ingestion pipeline",
            extra={
                "indexJobId": index_job_id,
                "jobAppId": request.jobAppId,
                "cvParsedId": cv_parsed_id,
                "chunkCount": len(chunk_payloads),
            },
        )

        await update_index_job_status(index_job_id, "SUCCESS")
    except Exception as e:
        logger.exception(f"Ingestion failed for indexJobId={index_job_id}: {str(e)}")
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

    return JobStatusResponse(
        status=job_record["stat"],
        errorMsg=job_record.get("errormsg", job_record.get("errorMsg")),
    )
