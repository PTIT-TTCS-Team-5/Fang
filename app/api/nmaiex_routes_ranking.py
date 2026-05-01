from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.database import acquire_conn
from app.models.nmaiex_schemas import RankingResponse
from app.services.nmaiex_ranking_service import (
    rank_candidates_for_job,
    rank_jobs_for_candidate,
)

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
