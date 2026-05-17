import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.api.routes_ingestion import process_ingestion_task
from app.core.database import acquire_conn
from app.models.ingestion import IngestionJobRequest
from app.models.nmaiex_schemas import (
    CandidateCvUpdateRequest,
    CandidateDetailResponse,
    JobContentUpdateRequest,
    JobDetailResponse,
    JobStructuredUpdateRequest,
    RankingResponse,
)
from app.services.nmaiex_mapper_service import embed_and_store_raw_skills
from app.services.nmaiex_ranking_service import (
    rank_candidates_for_job,
    rank_jobs_for_candidate,
)
from app.services.persistence import create_index_job

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/ranking/candidates/{job_id}",
    response_model=RankingResponse,
    tags=["NMAIex Ranking"],
)
async def api_rank_candidates_for_job(
    job_id: int,
    limit: int = Query(20, description="Max number of candidates to return"),
    province_id: Optional[str] = Query(None, description="Filter by province ID"),
    work_mode: Optional[str] = Query(
        None, description="Filter by work mode (ONSITE, REMOTE, HYBRID)"
    ),
):
    """
    Luồng J→C: Tìm ứng viên phù hợp cho một công việc.
    """
    try:
        result = await rank_candidates_for_job(
            job_id=job_id,
            limit=limit,
            province_id=province_id,
            work_mode=work_mode,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/ranking/jobs/{candidate_id}",
    response_model=RankingResponse,
    tags=["NMAIex Ranking"],
)
async def api_rank_jobs_for_candidate(
    candidate_id: int,
    limit: int = Query(20, description="Max number of jobs to return"),
    province_id: Optional[str] = Query(None, description="Filter by province ID"),
    work_mode: Optional[str] = Query(
        None, description="Filter by work mode (ONSITE, REMOTE, HYBRID)"
    ),
):
    """
    Luồng C→J: Tìm công việc phù hợp cho một ứng viên.
    """
    try:
        result = await rank_jobs_for_candidate(
            candidate_id=candidate_id,
            limit=limit,
            province_id=province_id,
            work_mode=work_mode,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/master/provinces", tags=["NMAIex Master Data"])
async def api_get_provinces():
    """
    Lấy danh sách tỉnh thành (đã nhóm theo Region).
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch("""
            SELECT p.provId, p.provName, r.regId, r.regName
            FROM PROVINCE p
            JOIN REGION r ON p.regId = r.regId
            ORDER BY r.regId DESC, p.provId ASC
            """)

    regions_dict = {}
    for row in rows:
        reg_id = row["regid"]
        if reg_id not in regions_dict:
            regions_dict[reg_id] = {
                "region_id": reg_id,
                "region_name": row["regname"],
                "provinces": [],
            }
        regions_dict[reg_id]["provinces"].append(
            {"province_id": row["provid"], "province_name": row["provname"]}
        )

    return list(regions_dict.values())


@router.get("/master/levels", tags=["NMAIex Master Data"])
async def api_get_levels():
    """
    Lấy danh sách Job Levels.
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(
            "SELECT levelId, levelName, description FROM JOBLEVEL ORDER BY levelId ASC"
        )
        return [
            {
                "level_id": r["levelid"],
                "level_name": r["levelname"],
                "description": r["description"],
            }
            for r in rows
        ]


@router.get("/master/categories", tags=["NMAIex Master Data"])
async def api_get_categories():
    """
    Lấy danh sách Job Categories.
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(
            "SELECT catId, catName, description FROM JOBCATEGORY ORDER BY catName ASC"
        )
        return [
            {
                "category_id": r["catid"],
                "category_name": r["catname"],
                "description": r["description"],
            }
            for r in rows
        ]


@router.get("/master/skills", tags=["NMAIex Master Data"])
async def api_get_skills():
    """
    Lấy danh sách hệ thống Skills.
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(
            "SELECT skillId, skillName FROM SKILL ORDER BY skillName ASC"
        )
        return [{"skill_id": r["skillid"], "skill_name": r["skillname"]} for r in rows]


# ===========================================================================
# Job Management Endpoints (Phase 1.5)
# ===========================================================================


@router.get(
    "/jobs/{job_id}",
    response_model=JobDetailResponse,
    tags=["NMAIex Job Management"],
)
async def api_get_job_detail(job_id: int):
    """
    Lấy chi tiết công việc kèm structured data (provId, levelIds, catIds, skillIds).
    """
    try:
        async with acquire_conn() as conn:
            # Get job basic info
            job = await conn.fetchrow(
                """
                SELECT j.jobPostId, j.title, j.description, j.minSalary, j.maxSalary,
                       j.workLoc, j.workMode, j.provId, j.createdAt, j.expAt, j.compId,
                       c.compName, p.provName
                FROM JOBPOSTING j
                LEFT JOIN COMPANY c ON j.compId = c.compId
                LEFT JOIN PROVINCE p ON j.provId = p.provId
                WHERE j.jobPostId = $1
                """,
                job_id,
            )

            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            # Get levels
            levels = await conn.fetch(
                """
                SELECT l.levelId, l.levelName
                FROM JOB_LEVEL_MAP jm
                JOIN JOBLEVEL l ON jm.levelId = l.levelId
                WHERE jm.jobPostId = $1
                ORDER BY l.levelId
                """,
                job_id,
            )

            # Get categories
            categories = await conn.fetch(
                """
                SELECT c.catId, c.catName
                FROM JOB_CATEGORY_MAP cm
                JOIN JOBCATEGORY c ON cm.catId = c.catId
                WHERE cm.jobPostId = $1
                ORDER BY c.catId
                """,
                job_id,
            )

            # Get required skills (catalog)
            skills = await conn.fetch(
                """
                SELECT s.skillId, s.skillName
                FROM JOBREQUIREMENT jr
                JOIN SKILL s ON jr.skillId = s.skillId
                WHERE jr.jobPostId = $1
                ORDER BY s.skillName
                """,
                job_id,
            )

            # Get custom skills (text-free from HR)
            custom_skills = await conn.fetch(
                """
                SELECT DISTINCT rawText
                FROM JOB_SKILL_RAW
                WHERE jobPostId = $1
                ORDER BY rawText
                """,
                job_id,
            )

            return JobDetailResponse(
                job_id=job["jobpostid"],
                title=job["title"],
                description=job["description"],
                min_salary=job["minsalary"],
                max_salary=job["maxsalary"],
                work_loc=job["workloc"],
                work_mode=job["workmode"],
                prov_id=job["provid"],
                prov_name=job["provname"],
                company_id=job["compid"],
                company_name=job["compname"],
                created_at=str(job["createdat"]),
                exp_at=str(job["expat"]),
                level_ids=[r["levelid"] for r in levels],
                level_names=[r["levelname"] for r in levels],
                category_ids=[r["catid"] for r in categories],
                category_names=[r["catname"] for r in categories],
                skill_ids=[r["skillid"] for r in skills],
                skill_names=[r["skillname"] for r in skills],
                custom_skills=[r["rawtext"] for r in custom_skills],
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/jobs/{job_id}/content",
    tags=["NMAIex Job Management"],
)
async def api_update_job_content(job_id: int, payload: JobContentUpdateRequest):
    """
    Cập nhật nội dung text của Job (title, description).

    Backend sẽ trigger re-ingest async — ranking có thể tạm thời kém chính xác.

    Returns:
        {job_id, reingestion_status: "queued"}
    """
    try:
        async with acquire_conn() as conn:
            # Update job content
            result = await conn.execute(
                """
                UPDATE JOBPOSTING
                SET title = $2, description = $3
                WHERE jobPostId = $1
                """,
                job_id,
                payload.title,
                payload.description,
            )

            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Job not found")

            # TODO: Trigger async re-ingest here (queue to message broker)
            return {"job_id": job_id, "reingestion_status": "queued"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/jobs/{job_id}/structured",
    tags=["NMAIex Job Management"],
)
async def api_update_job_structured(job_id: int, payload: JobStructuredUpdateRequest):
    """
    Cập nhật metadata cấu trúc của Job (provId, levelIds, catIds, skillIds, salary, workMode).

    Xử lý tức thì (synchronous), không trigger re-ingest.

    Returns:
        {job_id, updated_fields: [...]}
    """
    try:
        async with acquire_conn() as conn:
            updated_fields = []

            # Update provId, salary, workMode
            update_parts = []
            update_values = [job_id]
            param_idx = 2

            if payload.provId is not None:
                update_parts.append(f"provId = ${param_idx}")
                update_values.append(payload.provId)
                param_idx += 1
                updated_fields.append("provId")

            if payload.minSalary is not None:
                update_parts.append(f"minSalary = ${param_idx}")
                update_values.append(payload.minSalary)
                param_idx += 1
                updated_fields.append("minSalary")

            if payload.maxSalary is not None:
                update_parts.append(f"maxSalary = ${param_idx}")
                update_values.append(payload.maxSalary)
                param_idx += 1
                updated_fields.append("maxSalary")

            if payload.workMode is not None:
                update_parts.append(f"workMode = ${param_idx}")
                update_values.append(payload.workMode)
                param_idx += 1
                updated_fields.append("workMode")

            if update_parts:
                query = f"UPDATE JOBPOSTING SET {', '.join(update_parts)} WHERE jobPostId = $1"
                await conn.execute(query, *update_values)

            # Update level mappings
            if payload.levelIds:
                await conn.execute(
                    "DELETE FROM JOB_LEVEL_MAP WHERE jobpostid = $1",
                    job_id,
                )
                for level_id in payload.levelIds:
                    await conn.execute(
                        "INSERT INTO JOB_LEVEL_MAP (jobpostid, levelid) VALUES ($1, $2)",
                        job_id,
                        level_id,
                    )
                updated_fields.append("levelIds")

            # Update category mappings
            if payload.catIds:
                await conn.execute(
                    "DELETE FROM JOB_CATEGORY_MAP WHERE jobpostid = $1",
                    job_id,
                )
                for cat_id in payload.catIds:
                    await conn.execute(
                        "INSERT INTO JOB_CATEGORY_MAP (jobpostid, catid) VALUES ($1, $2)",
                        job_id,
                        cat_id,
                    )
                updated_fields.append("catIds")

            # Update skill requirements (catalog skills)
            if payload.skillIds:
                await conn.execute(
                    "DELETE FROM JOBREQUIREMENT WHERE jobpostid = $1",
                    job_id,
                )
                for skill_id in payload.skillIds:
                    await conn.execute(
                        "INSERT INTO JOBREQUIREMENT (jobpostid, skillid) VALUES ($1, $2)",
                        job_id,
                        skill_id,
                    )
                updated_fields.append("skillIds")

            # Update custom skills (text-free skills from HR)
            if payload.custom_skills:
                await conn.execute(
                    "DELETE FROM JOB_SKILL_RAW WHERE jobpostid = $1",
                    job_id,
                )
                # Embed and store custom skills with proper vectors
                await embed_and_store_raw_skills(
                    entity_type="job",
                    entity_id=job_id,
                    unmatched_texts=payload.custom_skills,
                    conn=conn,
                )
                updated_fields.append("customSkills")

            return {"job_id": job_id, "updated_fields": updated_fields}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# Candidate Management Endpoints
# ===========================================================================


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateDetailResponse,
    tags=["NMAIex Candidate Management"],
)
async def api_get_candidate_detail(candidate_id: int):
    """
    Lấy chi tiết ứng viên.
    """
    try:
        async with acquire_conn() as conn:
            # Get candidate info
            candidate = await conn.fetchrow(
                """
                SELECT u.userId, u.fName, u.lName, u.email, u.phone, u.provId,
                       c.bio, c.cvUrl, c.dob, c.expyears,
                       p.provName
                FROM CANDIDATE c
                JOIN "user" u ON c.userId = u.userId
                LEFT JOIN PROVINCE p ON u.provId = p.provId
                WHERE c.userId = $1
                """,
                candidate_id,
            )

            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")

            # Get candidate's skills
            skills = await conn.fetch(
                """
                SELECT s.skillId, s.skillName
                FROM CANDIDATESKILL cs
                JOIN SKILL s ON cs.skillId = s.skillId
                WHERE cs.userId = $1
                ORDER BY s.skillName
                """,
                candidate_id,
            )

            # Get custom skills (unmatched skills)
            custom_skills = await conn.fetch(
                """
                SELECT DISTINCT rawText
                FROM CANDIDATE_SKILL_RAW
                WHERE candId = $1
                ORDER BY rawText
                """,
                candidate_id,
            )

            return CandidateDetailResponse(
                candidate_id=candidate_id,
                user_id=candidate["userid"],
                first_name=candidate["fname"],
                last_name=candidate["lname"],
                email=candidate["email"],
                phone=candidate["phone"],
                prov_id=candidate["provid"],
                prov_name=candidate["provname"],
                bio=candidate["bio"],
                cv_url=candidate["cvurl"],
                dob=str(candidate["dob"]) if candidate["dob"] else None,
                exp_years=candidate["expyears"],
                skill_ids=[r["skillid"] for r in skills],
                skill_names=[r["skillname"] for r in skills],
                custom_skills=[r["rawtext"] for r in custom_skills],
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch(
    "/candidates/{candidate_id}",
    tags=["NMAIex Candidate Management"],
)
async def api_update_candidate(
    candidate_id: int,
    payload: CandidateCvUpdateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Cập nhật CV URL và bio của Candidate.

    Returns:
        {candidate_id, updated_fields: [...]}
    """
    try:
        async with acquire_conn() as conn:
            updated_fields = []

            # Validate at least one field is provided
            if payload.cvUrl is None and payload.bio is None:
                raise HTTPException(
                    status_code=400,
                    detail="At least one of cvUrl or bio must be provided",
                )

            # Update CV URL
            if payload.cvUrl is not None:
                await conn.execute(
                    "UPDATE CANDIDATE SET cvUrl = $1 WHERE userId = $2",
                    payload.cvUrl,
                    candidate_id,
                )
                updated_fields.append("cvUrl")

                # Update cvSnapUrl in the latest JOBAPPLICATION and trigger background ingestion
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
                        payload.cvUrl,
                        job_app_id,
                    )

                    # Create index job and spawn background ingestion task
                    index_job_id = await create_index_job(job_app_id)
                    ingest_req = IngestionJobRequest(
                        jobAppId=job_app_id, cvSnapUrl=payload.cvUrl
                    )
                    background_tasks.add_task(
                        process_ingestion_task, index_job_id, ingest_req
                    )
                    logger.info(
                        f"[NMAIex] Candidate cvUrl updated. Triggered background CV re-ingestion: "
                        f"candidate_id={candidate_id}, job_app_id={job_app_id}, index_job_id={index_job_id}"
                    )
            # Update bio
            if payload.bio is not None:
                await conn.execute(
                    "UPDATE CANDIDATE SET bio = $1 WHERE userId = $2",
                    payload.bio,
                    candidate_id,
                )
                updated_fields.append("bio")

            if not updated_fields:
                raise HTTPException(status_code=400, detail="No fields to update")

            return {"candidate_id": candidate_id, "updated_fields": updated_fields}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
