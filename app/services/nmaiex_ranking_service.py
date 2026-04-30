# [NMAIex] Ranking Service — RRF + Late Fusion + Tiered Skill Scoring
# Tham chiếu: [NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md — Mục 3.4, 7.4

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.database import acquire_conn
from app.core.nmaiex_config import nmaiex_settings

logger = logging.getLogger(__name__)


# ============================================================
# Utility helpers
# ============================================================


def clip_score(score: float) -> float:
    """Clip về [0, 1] — tránh điểm âm (penalty lớn) hoặc > 1 (bonus tương lai)."""
    return max(0.0, min(1.0, score))


# ============================================================
# Tiered Skill Scoring (Strategy C)
# ============================================================


async def compute_skill_score(
    job_skill_ids: set[int],
    cand_skill_ids: set[int],
    job_post_id: int,
    cand_id: int,
    conn,
    alpha: float,
) -> tuple[float, float, float]:
    """Tính điểm skill 2 tầng: exact overlap + fuzzy overlap (cosine).

    Returns:
        (skill_score, exact_overlap, fuzzy_overlap)

    Công thức (Mục 7.4):
        exact_overlap = |job_ids ∩ cand_ids| / max(|job_ids|, 1)
        fuzzy_overlap = avg_max_cosine(job_raw_emb, cand_raw_emb)
                        = 0.0 nếu một trong hai bên rỗng
        skill_score   = alpha * exact + (1 - alpha) * fuzzy
    """
    # --- Tầng 1: Exact Overlap ---
    overlap = len(job_skill_ids.intersection(cand_skill_ids))
    exact_overlap = overlap / max(len(job_skill_ids), 1)

    # --- Tầng 2: Fuzzy Overlap từ raw skill embeddings ---
    fuzzy_overlap = 0.0

    # Lấy raw embeddings từ cả 2 phía (PostgreSQL trả về dạng list thông qua driver)
    job_raw_rows = await conn.fetch(
        "SELECT embedding FROM JOB_SKILL_RAW WHERE jobPostId = $1 AND embedding IS NOT NULL",
        job_post_id,
    )
    cand_raw_rows = await conn.fetch(
        "SELECT embedding FROM CANDIDATE_SKILL_RAW WHERE candId = $1 AND embedding IS NOT NULL",
        cand_id,
    )

    if job_raw_rows and cand_raw_rows:
        # avg_max_cosine: với mỗi job raw skill, tìm cosine max với tất cả cand raw skills
        # Dùng PostgreSQL để tính cosine similarity ngay trên DB thay vì Python loop
        # (hiệu quả hơn với số lượng skills nhỏ <20, tránh round-trip nhiều lần)
        try:
            fuzzy_row = await conn.fetchrow(
                """
                SELECT AVG(max_sim) as avg_fuzzy
                FROM (
                    SELECT MAX(1 - (j.embedding <=> c.embedding)) as max_sim
                    FROM JOB_SKILL_RAW j
                    CROSS JOIN CANDIDATE_SKILL_RAW c
                    WHERE j.jobPostId = $1
                      AND c.candId = $2
                      AND j.embedding IS NOT NULL
                      AND c.embedding IS NOT NULL
                    GROUP BY j.rawId
                ) sub
                """,
                job_post_id,
                cand_id,
            )
            if fuzzy_row and fuzzy_row["avg_fuzzy"] is not None:
                fuzzy_overlap = float(fuzzy_row["avg_fuzzy"])
                # Cosine similarity có thể âm trong lý thuyết; clip về [0,1]
                fuzzy_overlap = max(0.0, min(1.0, fuzzy_overlap))
        except Exception as e:
            logger.warning(
                f"[NMAIex] Fuzzy overlap computation failed for "
                f"job={job_post_id}, cand={cand_id}: {e}. fuzzy=0.0"
            )
            fuzzy_overlap = 0.0

    skill_score = alpha * exact_overlap + (1 - alpha) * fuzzy_overlap
    return skill_score, exact_overlap, fuzzy_overlap


# ============================================================
# J→C: Tìm ứng viên cho công việc
# ============================================================


async def rank_candidates_for_job(
    job_id: int,
    limit: int = nmaiex_settings.nmaiex_ranking_default_limit,
    province_id: Optional[str] = None,
    work_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Luồng J→C: Nhà tuyển dụng tìm ứng viên phù hợp nhất cho một job posting."""

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

        # Lấy catalog skills của job (Tầng 1 exact)
        job_skills_rows = await conn.fetch(
            "SELECT skillId FROM JOBREQUIREMENT WHERE jobPostId = $1", job_id
        )
        job_skills = {r["skillid"] for r in job_skills_rows}

        # Lấy required seniority (lấy min để penalty nhẹ nhất nếu job chấp nhiều level)
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

    # Embed job text để làm vector query
    from app.services.embedding import embed_chunks

    job_text = f"{job_row['title']}\n{job_row['description']}"
    vectors = await embed_chunks([job_text])
    if not vectors:
        return {"job_id": job_id, "total_candidates": 0, "returned": 0, "results": []}

    job_vector = vectors[0]
    vector_str = "[" + ",".join(map(str, job_vector)) + "]"

    async with acquire_conn() as conn:
        # Hard filter
        filter_parts = ["u.stat = 'ACTIVE'"]
        params: list = [vector_str, job_text]
        param_idx = 3

        if province_id:
            filter_parts.append(f"u.provId = ${param_idx}")
            params.append(province_id)
            param_idx += 1

        filter_sql = " AND ".join(filter_parts)

        # Truy vấn HNSW vector search + full-text search đồng thời
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
                ts_rank(
                    to_tsvector('english', COALESCE(cv.rawText, '')),
                    plainto_tsquery('english', $2)
                ) as text_rank
            FROM "user" u
            JOIN CANDIDATE c ON u.userId = c.userId
            JOIN LatestApp la ON u.userId = la.candidateId
            JOIN CVPARSED cv ON la.latest_app_id = cv.jobAppId
            LEFT JOIN VectorRank vr ON la.latest_app_id = vr.jobAppId
            WHERE {filter_sql}
        """

        candidates = await conn.fetch(candidates_query, *params)

        # Lấy catalog skills của từng ứng viên (batch query)
        candidate_ids = [c["candidate_id"] for c in candidates]
        candidate_skills_dict: dict[int, set[int]] = {}
        if candidate_ids:
            c_skills = await conn.fetch(
                "SELECT userId, skillId FROM CANDIDATESKILL WHERE userId = ANY($1::int[])",
                candidate_ids,
            )
            for r in c_skills:
                uid = r["userid"]
                candidate_skills_dict.setdefault(uid, set()).add(r["skillid"])

        # RRF ranking
        rrf_k = nmaiex_settings.nmaiex_rrf_k
        w_rrf = nmaiex_settings.nmaiex_jc_weight_rrf
        w_skill = nmaiex_settings.nmaiex_jc_weight_skill
        penalty_coef = nmaiex_settings.nmaiex_jc_penalty_seniority_coef
        alpha = nmaiex_settings.nmaiex_skill_alpha

        vec_sorted = sorted(
            candidates,
            key=lambda x: (
                x["vector_distance"] if x["vector_distance"] is not None else 999
            ),
        )
        vec_rank = {c["candidate_id"]: idx + 1 for idx, c in enumerate(vec_sorted)}

        text_sorted = sorted(
            candidates,
            key=lambda x: x["text_rank"] if x["text_rank"] is not None else 0,
            reverse=True,
        )
        txt_rank = {c["candidate_id"]: idx + 1 for idx, c in enumerate(text_sorted)}

        results = []
        for c in candidates:
            cid = c["candidate_id"]
            r_vec = vec_rank[cid]
            r_txt = txt_rank[cid]

            rrf_score = 1.0 / (rrf_k + r_vec) + 1.0 / (rrf_k + r_txt)
            rrf_score_norm = rrf_score * rrf_k / 2.0

            # Tiered Skill Scoring
            c_skills = candidate_skills_dict.get(cid, set())
            skill_score, exact_overlap, fuzzy_overlap = await compute_skill_score(
                job_skill_ids=job_skills,
                cand_skill_ids=c_skills,
                job_post_id=job_id,
                cand_id=cid,
                conn=conn,
                alpha=alpha,
            )

            # Seniority Penalty
            c_exp = c["expyears"] or 0
            gap = max(0, required_min_years - c_exp)
            seniority_penalty = penalty_coef * gap

            final_score = clip_score(
                w_rrf * rrf_score_norm + w_skill * skill_score - seniority_penalty
            )

            results.append(
                {
                    "candidate_id": cid,
                    "candidate_name": c["candidate_name"],
                    "match_score": round(final_score, 4),
                    "score_breakdown": {
                        "rrf_score": round(rrf_score_norm, 4),
                        "exact_overlap": round(exact_overlap, 4),
                        "fuzzy_overlap": round(fuzzy_overlap, 4),
                        "skill_score": round(skill_score, 4),
                        "skill_alpha": alpha,
                        "seniority_penalty": round(seniority_penalty, 4),
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


# ============================================================
# C→J: Tìm việc làm cho ứng viên
# ============================================================


async def rank_jobs_for_candidate(
    candidate_id: int,
    limit: int = nmaiex_settings.nmaiex_ranking_default_limit,
    province_id: Optional[str] = None,
    work_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Luồng C→J: Ứng viên tìm việc làm phù hợp nhất."""

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

    # Build candidate text cho text search
    candidate_text = candidate_row["rawtext"] or candidate_row["bio"] or ""
    if not candidate_text.strip() and c_skills:
        candidate_text = " ".join(str(s) for s in c_skills)
    if not candidate_text.strip():
        candidate_text = "Experienced candidate"

    async with acquire_conn() as conn:
        filter_parts = ["p.expAt > CURRENT_TIMESTAMP"]
        params: list = [candidate_text]
        param_idx = 2

        if province_id:
            filter_parts.append(f"p.provId = ${param_idx}")
            params.append(province_id)
            param_idx += 1

        if work_mode:
            filter_parts.append(f"p.workMode = ${param_idx}")
            params.append(work_mode)
            param_idx += 1

        filter_sql = " AND ".join(filter_parts)

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
                ts_rank(
                    to_tsvector('english', p.title || ' ' || p.description),
                    plainto_tsquery('english', $1)
                ) as text_rank
            FROM JOBPOSTING p
            LEFT JOIN JobSkills js ON p.jobPostId = js.jobPostId
            WHERE {filter_sql}
        """

        jobs = await conn.fetch(jobs_query, *params)

        rrf_k = nmaiex_settings.nmaiex_rrf_k
        w_rrf = nmaiex_settings.nmaiex_cj_weight_rrf
        w_skill = nmaiex_settings.nmaiex_jc_weight_skill
        alpha = nmaiex_settings.nmaiex_skill_alpha

        text_sorted = sorted(
            jobs,
            key=lambda x: x["text_rank"] if x["text_rank"] is not None else 0,
            reverse=True,
        )
        txt_rank = {j["job_id"]: idx + 1 for idx, j in enumerate(text_sorted)}

        results = []
        for j in jobs:
            jid = j["job_id"]
            r_txt = txt_rank[jid]

            # C→J chỉ có text rank (không có vector search từ phía job chunk → candidate)
            rrf_score_norm = (1.0 / (rrf_k + r_txt)) * rrf_k

            # Tiered Skill Scoring
            j_skills = set(j["req_skills"] or [])
            skill_score, exact_overlap, fuzzy_overlap = await compute_skill_score(
                job_skill_ids=j_skills,
                cand_skill_ids=c_skills,
                job_post_id=jid,
                cand_id=candidate_id,
                conn=conn,
                alpha=alpha,
            )

            # Salary Penalty (hiện tại = 0 vì DB chưa có expected salary của ứng viên)
            salary_penalty = 0.0

            final_score = clip_score(
                w_rrf * rrf_score_norm + w_skill * skill_score - salary_penalty
            )

            results.append(
                {
                    "job_id": jid,
                    "job_title": j["job_title"],
                    "match_score": round(final_score, 4),
                    "score_breakdown": {
                        "text_score": round(rrf_score_norm, 4),
                        "exact_overlap": round(exact_overlap, 4),
                        "fuzzy_overlap": round(fuzzy_overlap, 4),
                        "skill_score": round(skill_score, 4),
                        "skill_alpha": alpha,
                        "salary_penalty": round(salary_penalty, 4),
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
