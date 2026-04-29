from typing import Any, Dict, Optional

from app.core.database import acquire_conn
from app.core.nmaiex_config import nmaiex_settings
from app.services.embedding import embed_chunks


def clip_score(score: float) -> float:
    return max(0.0, min(1.0, score))


async def rank_candidates_for_job(
    job_id: int,
    limit: int = nmaiex_settings.nmaiex_ranking_default_limit,
    province_id: Optional[str] = None,
    work_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Luồng J->C: Nhà tuyển dụng tìm ứng viên"""

    async with acquire_conn() as conn:
        job_row = await conn.fetchrow(
            """
            SELECT jobPostId, title, description, minSalary, maxSalary
            FROM JOBPOSTING
            WHERE jobPostId = $1
        """,
            job_id,
        )

        if not job_row:
            return {
                "job_id": job_id,
                "total_candidates": 0,
                "returned": 0,
                "results": [],
            }

        # Job skills
        job_skills_rows = await conn.fetch(
            "SELECT skillId FROM JOBREQUIREMENT WHERE jobPostId = $1", job_id
        )
        job_skills = {r["skillid"] for r in job_skills_rows}

        # Job levels
        job_levels_rows = await conn.fetch(
            """
            SELECT l.minYears 
            FROM JOB_LEVEL_MAP m
            JOIN JOBLEVEL l ON m.levelId = l.levelId
            WHERE m.jobPostId = $1
        """,
            job_id,
        )
        job_min_years = [r["minyears"] for r in job_levels_rows]
        required_min_years = min(job_min_years) if job_min_years else 0

    job_text = f"{job_row['title']}\n{job_row['description']}"
    vectors = await embed_chunks([job_text])
    if not vectors:
        return {"job_id": job_id, "total_candidates": 0, "returned": 0, "results": []}

    job_vector = vectors[0]
    vector_str = "[" + ",".join(map(str, job_vector)) + "]"

    async with acquire_conn() as conn:
        filter_sql = ""
        params = [vector_str, job_text]
        param_idx = 3

        if province_id:
            filter_sql += f" AND u.provId = ${param_idx}"
            params.append(province_id)
            param_idx += 1

        candidates_query = f"""
            WITH LatestApp AS (
                SELECT candidateId, MAX(jobAppId) as latest_app_id
                FROM JOBAPPLICATION
                GROUP BY candidateId
            ),
            VectorRank AS (
                SELECT c.jobAppId, 
                       MIN(c.embedding <=> $1::halfvec) as vector_distance
                FROM AIDOCUMENTCHUNK c
                GROUP BY c.jobAppId
            )
            SELECT 
                u.userId as candidate_id, 
                u.fName || ' ' || u.lName as candidate_name,
                c.expyears,
                cv.rawText,
                vr.vector_distance,
                ts_rank(to_tsvector('english', COALESCE(cv.rawText, '')), plainto_tsquery('english', $2)) as text_rank
            FROM "user" u
            JOIN CANDIDATE c ON u.userId = c.userId
            JOIN LatestApp la ON u.userId = la.candidateId
            JOIN CVPARSED cv ON la.latest_app_id = cv.jobAppId
            LEFT JOIN VectorRank vr ON la.latest_app_id = vr.jobAppId
            WHERE u.stat = 'ACTIVE' {filter_sql}
        """

        candidates = await conn.fetch(candidates_query, *params)

        candidate_ids = [c["candidate_id"] for c in candidates]
        candidate_skills_dict = {}
        if candidate_ids:
            skills_query = """
                SELECT userId, skillId 
                FROM CANDIDATESKILL 
                WHERE userId = ANY($1::int[])
            """
            c_skills = await conn.fetch(skills_query, candidate_ids)
            for r in c_skills:
                uid = r["userid"]
                if uid not in candidate_skills_dict:
                    candidate_skills_dict[uid] = set()
                candidate_skills_dict[uid].add(r["skillid"])

    results = []
    vec_sorted = sorted(
        candidates,
        key=lambda x: x["vector_distance"] if x["vector_distance"] is not None else 999,
    )
    vec_rank = {c["candidate_id"]: idx + 1 for idx, c in enumerate(vec_sorted)}

    text_sorted = sorted(
        candidates,
        key=lambda x: x["text_rank"] if x["text_rank"] is not None else 0,
        reverse=True,
    )
    txt_rank = {c["candidate_id"]: idx + 1 for idx, c in enumerate(text_sorted)}

    rrf_k = nmaiex_settings.nmaiex_rrf_k
    w_rrf = nmaiex_settings.nmaiex_jc_weight_rrf
    w_skill = nmaiex_settings.nmaiex_jc_weight_skill
    penalty_coef = nmaiex_settings.nmaiex_jc_penalty_seniority_coef

    for c in candidates:
        cid = c["candidate_id"]
        r_vec = vec_rank[cid]
        r_txt = txt_rank[cid]

        rrf_score = 1.0 / (rrf_k + r_vec) + 1.0 / (rrf_k + r_txt)
        rrf_score_norm = rrf_score * rrf_k / 2.0

        c_skills = candidate_skills_dict.get(cid, set())
        overlap = len(job_skills.intersection(c_skills))
        skill_overlap = overlap / len(job_skills) if job_skills else 1.0

        c_exp = c["expyears"] or 0
        gap = max(0, required_min_years - c_exp)
        penalty = penalty_coef * gap

        final_score = clip_score(
            w_rrf * rrf_score_norm + w_skill * skill_overlap - penalty
        )

        results.append(
            {
                "candidate_id": cid,
                "candidate_name": c["candidate_name"],
                "match_score": round(final_score, 4),
                "score_breakdown": {
                    "rrf_score": round(rrf_score_norm, 4),
                    "skill_overlap": round(skill_overlap, 4),
                    "seniority_penalty": round(penalty, 4),
                    "hard_filter_passed": True,
                },
            }
        )

    results.sort(key=lambda x: x["match_score"], reverse=True)
    results = results[:limit]

    return {
        "job_id": job_id,
        "total_candidates": len(candidates),
        "returned": len(results),
        "results": results,
    }


async def rank_jobs_for_candidate(
    candidate_id: int,
    limit: int = nmaiex_settings.nmaiex_ranking_default_limit,
    province_id: Optional[str] = None,
    work_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Luồng C->J: Ứng viên tìm công việc"""

    async with acquire_conn() as conn:
        candidate_row = await conn.fetchrow(
            """
            WITH LatestApp AS (
                SELECT candidateId, MAX(jobAppId) as latest_app_id
                FROM JOBAPPLICATION
                WHERE candidateId = $1
                GROUP BY candidateId
            )
            SELECT u.fName, u.lName, c.expyears, c.bio, cv.rawText
            FROM "user" u
            JOIN CANDIDATE c ON u.userId = c.userId
            LEFT JOIN LatestApp la ON u.userId = la.candidateId
            LEFT JOIN CVPARSED cv ON la.latest_app_id = cv.jobAppId
            WHERE u.userId = $1
        """,
            candidate_id,
        )

        if not candidate_row:
            return {
                "candidate_id": candidate_id,
                "total_jobs": 0,
                "returned": 0,
                "results": [],
            }

        c_skills_rows = await conn.fetch(
            "SELECT skillId FROM CANDIDATESKILL WHERE userId = $1", candidate_id
        )
        c_skills = {r["skillid"] for r in c_skills_rows}

    candidate_text = candidate_row["rawtext"] or candidate_row["bio"] or ""
    if not candidate_text.strip() and c_skills:
        candidate_text = " ".join(str(s) for s in c_skills)

    if not candidate_text.strip():
        # Fallback empty text
        candidate_text = "Experienced candidate"

    vectors = await embed_chunks([candidate_text])
    if not vectors:
        return {
            "candidate_id": candidate_id,
            "total_jobs": 0,
            "returned": 0,
            "results": [],
        }

    candidate_vector = vectors[0]
    vector_str = "[" + ",".join(map(str, candidate_vector)) + "]"

    async with acquire_conn() as conn:
        filter_sql = ""
        params = [vector_str, candidate_text]
        param_idx = 3

        if province_id:
            filter_sql += f" AND p.provId = ${param_idx}"
            params.append(province_id)
            param_idx += 1

        if work_mode:
            filter_sql += f" AND p.workMode = ${param_idx}"
            params.append(work_mode)
            param_idx += 1

        jobs_query = f"""
            WITH JobSkills AS (
                SELECT jobPostId, array_agg(skillId) as req_skills
                FROM JOBREQUIREMENT
                GROUP BY jobPostId
            )
            SELECT 
                p.jobPostId as job_id, 
                p.title as job_title,
                p.minSalary,
                js.req_skills,
                ts_rank(to_tsvector('english', p.title || ' ' || p.description), plainto_tsquery('english', $1)) as text_rank
            FROM JOBPOSTING p
            LEFT JOIN JobSkills js ON p.jobPostId = js.jobPostId
            WHERE p.expAt > CURRENT_TIMESTAMP {filter_sql}
        """

        jobs = await conn.fetch(jobs_query, *params)

    results = []

    # Sort by text rank (desc)
    text_sorted = sorted(
        jobs,
        key=lambda x: x["text_rank"] if x["text_rank"] is not None else 0,
        reverse=True,
    )
    txt_rank = {j["job_id"]: idx + 1 for idx, j in enumerate(text_sorted)}

    rrf_k = nmaiex_settings.nmaiex_rrf_k
    w_rrf = nmaiex_settings.nmaiex_cj_weight_rrf
    w_skill = (
        nmaiex_settings.nmaiex_jc_weight_skill
    )  # Use same if cj weight skill not in config

    for j in jobs:
        jid = j["job_id"]
        r_txt = txt_rank[jid]

        # Only have text rank for C->J since no job vectors in DB
        rrf_score_norm = (1.0 / (rrf_k + r_txt)) * rrf_k

        # Skill Overlap
        j_skills = set(j["req_skills"] or [])
        overlap = len(c_skills.intersection(j_skills))
        skill_overlap = overlap / len(j_skills) if j_skills else 1.0

        # Salary penalty (assume expected salary = 0 for now as it's not in DB schema)
        penalty = 0.0

        final_score = clip_score(
            w_rrf * rrf_score_norm + w_skill * skill_overlap - penalty
        )

        results.append(
            {
                "job_id": jid,
                "job_title": j["job_title"],
                "match_score": round(final_score, 4),
                "score_breakdown": {
                    "text_score": round(rrf_score_norm, 4),
                    "skill_overlap": round(skill_overlap, 4),
                    "salary_penalty": round(penalty, 4),
                    "hard_filter_passed": True,
                },
            }
        )

    results.sort(key=lambda x: x["match_score"], reverse=True)
    results = results[:limit]

    return {
        "candidate_id": candidate_id,
        "total_jobs": len(jobs),
        "returned": len(results),
        "results": results,
    }
