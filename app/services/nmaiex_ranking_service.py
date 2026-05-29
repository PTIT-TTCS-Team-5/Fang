# [NMAIex] Ranking Service — RRF + Late Fusion + Tiered Skill Scoring
# Tham chiếu: [NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md — Mục 3.4, 7.4

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.database import acquire_conn
from app.core.nmaiex_config import nmaiex_settings

logger = logging.getLogger(__name__)


# ============================================================
# Utility helpers
# ============================================================


def clip_score(score: float) -> float:
    """Optionally clip score for legacy display behavior; raw score is default."""
    if not nmaiex_settings.nmaiex_enable_score_clip:
        return score
    return max(0.0, min(1.0, score))


def safe_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None


def load_json_field(val: Any) -> Any:
    if val is None:
        return []
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            import json

            return json.loads(val)
        except Exception:
            return []
    return []


# ============================================================
# Helpers for C->J Optimization (Salary, Language)
# ============================================================


def estimate_expected_salary(expyears: float, location: str = "DEFAULT") -> int:
    """Ước lượng expected salary từ experience years"""
    base_salaries = {
        "HANOI": nmaiex_settings.nmaiex_salary_base_hanoi,
        "TPHCM": nmaiex_settings.nmaiex_salary_base_tphcm,
        "DANANG": nmaiex_settings.nmaiex_salary_base_danang,
        "DEFAULT": nmaiex_settings.nmaiex_salary_base_default,
    }
    base = base_salaries.get(location, nmaiex_settings.nmaiex_salary_base_default)

    if expyears <= 1:
        increment = nmaiex_settings.nmaiex_salary_increment_junior
    elif expyears <= 3:
        increment = nmaiex_settings.nmaiex_salary_increment_middle
    elif expyears <= 5:
        increment = nmaiex_settings.nmaiex_salary_increment_senior
    else:
        increment = nmaiex_settings.nmaiex_salary_increment_lead

    return base + int(expyears * increment)


def compute_salary_adjustment(
    min_salary: Optional[int],
    max_salary: Optional[int],
    expected_salary: int,
) -> float:
    """
    Tính điểm thưởng/phạt lương (Asymmetric).
    Trừ điểm nếu lương thấp hơn kỳ vọng, cộng điểm nếu cao hơn.
    """
    if not min_salary and not max_salary:
        return 0.0

    if not min_salary:
        min_salary = max_salary
    if not max_salary:
        max_salary = min_salary

    mid_salary = (min_salary + max_salary) / 2
    lower_tolerance = expected_salary * nmaiex_settings.nmaiex_salary_tolerance_lower
    upper_target = expected_salary * nmaiex_settings.nmaiex_salary_tolerance_upper

    # 0.20 là base weight (room còn lại của w_rrf + w_title + w_skill)
    # Vì total weights hiện tại = 0.35 + 0.15 + 0.30 = 0.80
    base_weight = 0.20

    if mid_salary < lower_tolerance * 0.8:
        # Very low
        gap_ratio = (lower_tolerance * 0.8 - mid_salary) / expected_salary
        return -base_weight * min(gap_ratio, 1.0)
    elif mid_salary < lower_tolerance:
        # Low
        gap_ratio = (lower_tolerance - mid_salary) / expected_salary
        return -base_weight * 0.5 * gap_ratio
    elif mid_salary < upper_target:
        # Acceptable (Neutral)
        return 0.0
    else:
        # High (Bonus)
        bonus_ratio = (mid_salary - upper_target) / expected_salary
        bonus = base_weight * 0.2 * bonus_ratio
        return min(bonus, nmaiex_settings.nmaiex_salary_bonus_cap)


async def compute_language_score(
    job_post_id: int,
    candidate_languages: list[
        dict
    ],  # List of {"language": "en", "proficiency": "ADVANCED"} OR normalized rows
    conn,
    *,
    use_normalized: bool = False,
) -> tuple[float, float, dict]:
    """Tính điểm ngôn ngữ.

    [NMAIex C3 WS1] Extended:
    - When use_normalized=True, candidate_languages contains rows from
      CANDIDATELANGUAGE JOIN LANGUAGE: {"langCode": str, "proficiency": str}.
      This is the preferred path for enriched candidates.
    - When use_normalized=False (legacy fallback), raw list of
      {"language": raw_name, "proficiency": raw_prof} is used.
      Raw proficiency is treated as already normalized (backward compat).

    Returns:
        (lang_penalty, lang_bonus, breakdown_dict)
    """
    req_rows = await conn.fetch(
        """
        SELECT l.langCode, r.reqType, r.minLevel
        FROM JOB_LANG_REQUIREMENT r
        JOIN LANGUAGE l ON r.langId = l.langId
        WHERE r.jobPostId = $1
        """,
        job_post_id,
    )

    if not req_rows:
        return 0.0, 0.0, {"requirements": []}

    from app.services.nmaiex_mapper_service import PROFICIENCY_LEVELS

    lang_penalty = 0.0
    lang_bonus = 0.0
    breakdown = {"requirements": []}

    # Build cand_lang_map: langCode -> proficiency numeric level
    cand_lang_map: dict[str, int] = {}

    if use_normalized:
        # Preferred path: normalized rows from CANDIDATELANGUAGE JOIN LANGUAGE
        for cl in candidate_languages:
            if not isinstance(cl, dict):
                continue
            code = (cl.get("langCode") or "").lower()
            prof_str = cl.get("proficiency") or "BASIC"
            if code:
                cand_lang_map[code] = PROFICIENCY_LEVELS.get(prof_str.upper(), 1)
    else:
        # Legacy fallback: raw dicts with simple string-based language name mapping
        for cl in candidate_languages:
            if not isinstance(cl, dict):
                continue
            lang_name = cl.get("language", "").lower()
            if "english" in lang_name or "tiếng anh" in lang_name:
                code = "en"
            elif "japanese" in lang_name or "tiếng nhật" in lang_name:
                code = "ja"
            elif "korean" in lang_name or "tiếng hàn" in lang_name:
                code = "ko"
            elif "chinese" in lang_name or "tiếng trung" in lang_name:
                code = "zh"
            elif "french" in lang_name or "tiếng pháp" in lang_name:
                code = "fr"
            elif "german" in lang_name or "tiếng đức" in lang_name:
                code = "de"
            else:
                code = lang_name  # Giữ nguyên nếu không match

            prof = cl.get("proficiency", "BASIC")
            cand_lang_map[code] = PROFICIENCY_LEVELS.get(prof, 1)

    for req in req_rows:
        code = req["langcode"]
        req_type = req["reqtype"]
        min_level_str = req["minlevel"] or "BASIC"
        req_level = PROFICIENCY_LEVELS.get(min_level_str, 1)

        cand_level = cand_lang_map.get(code, 0)  # 0 = not have this language

        req_info = {
            "lang": code,
            "req_type": req_type,
            "min_level": min_level_str,
            "cand_level_num": cand_level,
            "met": False,
            "score_diff": 0.0,
        }

        if req_type == "REQUIRED":
            if cand_level == 0:
                diff = -nmaiex_settings.nmaiex_lang_required_penalty
                lang_penalty += abs(diff)
                req_info["score_diff"] = diff
            elif cand_level < req_level:
                diff = -nmaiex_settings.nmaiex_lang_level_penalty
                lang_penalty += abs(diff)
                req_info["score_diff"] = diff
            else:
                req_info["met"] = True

        elif req_type == "PREFERRED":
            if cand_level >= req_level:
                diff = nmaiex_settings.nmaiex_lang_preferred_bonus
                lang_bonus += diff
                req_info["score_diff"] = diff
                req_info["met"] = True

        breakdown["requirements"].append(req_info)

    lang_bonus = min(lang_bonus, nmaiex_settings.nmaiex_lang_bonus_cap)
    return lang_penalty, lang_bonus, breakdown


async def fetch_candidate_languages_normalized(
    candidate_id: int,
    conn,
) -> list[dict]:
    """Fetch normalized language rows for a candidate from CANDIDATELANGUAGE.

    [NMAIex C3 WS1] Returns list of {"langCode": str | None, "proficiency": str}
    suitable for the use_normalized=True path of compute_language_score().
    Candidates with unknown langId are returned with langCode=None.
    """
    rows = await conn.fetch(
        """
        SELECT l.langCode, cl.proficiency, cl.rawName
        FROM CANDIDATELANGUAGE cl
        LEFT JOIN LANGUAGE l ON cl.langId = l.langId
        WHERE cl.userId = $1
        """,
        candidate_id,
    )
    return [
        {
            "langCode": row["langcode"],  # may be None for unknown lang
            "proficiency": row["proficiency"] or "BASIC",
            "rawName": row["rawname"],
        }
        for row in rows
    ]


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

        # Lấy required seniority với buffer dựa vào career path
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

        if job_min_years:
            job_min = min(job_min_years)
            job_max_raw = max(job_min_years)

            if job_max_raw <= 1:
                buffer = nmaiex_settings.nmaiex_buffer_very_junior
            elif job_max_raw <= 3:
                buffer = nmaiex_settings.nmaiex_buffer_junior
            elif job_max_raw <= 5:
                buffer = nmaiex_settings.nmaiex_buffer_middle
            elif job_max_raw <= 8:
                buffer = nmaiex_settings.nmaiex_buffer_senior
            else:
                buffer = nmaiex_settings.nmaiex_buffer_lead_manager

            job_max = job_max_raw + buffer
        else:
            job_min = 0
            job_max = float("inf")

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
        params: list = [vector_str, job_text, job_id]
        param_idx = 4

        if province_id:
            filter_parts.append(f"u.provId = ${param_idx}")
            params.append(province_id)
            param_idx += 1

        filter_sql = " AND ".join(filter_parts)

        vec_type = settings.embedding_vector_type  # 'halfvec' or 'vector'
        # Truy vấn HNSW vector search + full-text search đồng thời
        candidates_query = f"""
            WITH LatestApp AS (
                SELECT candidateId, MAX(jobAppId) as latest_app_id
                FROM JOBAPPLICATION
                WHERE jobPostId = $3
                GROUP BY candidateId
            ),
            VectorRank AS (
                SELECT c.jobAppId,
                       MIN(c.embedding <=> $1::{vec_type}) as vector_distance
                FROM AIDOCUMENTCHUNK c
                GROUP BY c.jobAppId
            )
            SELECT
                u.userId as candidate_id,
                u.fName || ' ' || u.lName as candidate_name,
                c.expyears,
                COALESCE(cv.rawText, c.bio) as rawText,
                vr.vector_distance,
                ts_rank(
                    to_tsvector('english', COALESCE(cv.rawText, c.bio, '')),
                    plainto_tsquery('english', $2)
                ) as text_rank
            FROM "user" u
            JOIN CANDIDATE c ON u.userId = c.userId
            JOIN LatestApp la ON u.userId = la.candidateId
            LEFT JOIN CVPARSED cv ON la.latest_app_id = cv.jobAppId
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

        # [C3 WS1] Batch-fetch normalized languages for all candidates
        cand_normalized_langs: dict[int, list[dict]] = {
            cid: [] for cid in candidate_ids
        }
        if candidate_ids:
            norm_rows = await conn.fetch(
                """
                SELECT cl.userId, l.langCode, cl.proficiency, cl.rawName
                FROM CANDIDATELANGUAGE cl
                LEFT JOIN LANGUAGE l ON cl.langId = l.langId
                WHERE cl.userId = ANY($1::int[])
                """,
                candidate_ids,
            )
            for r in norm_rows:
                uid = r["userid"]
                cand_normalized_langs.setdefault(uid, []).append(
                    {
                        "langCode": r["langcode"],
                        "proficiency": r["proficiency"] or "BASIC",
                        "rawName": r["rawname"],
                    }
                )

        # RRF ranking
        rrf_k = nmaiex_settings.nmaiex_rrf_k
        w_rrf = nmaiex_settings.nmaiex_jc_weight_rrf
        w_skill = nmaiex_settings.nmaiex_jc_weight_skill
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

            # Seniority Penalty - Asymmetric (Insufficient vs Overqualified)
            c_exp = c["expyears"] or 0
            base_penalty_coef = nmaiex_settings.nmaiex_jc_penalty_seniority_coef
            overqualified_ratio = (
                nmaiex_settings.nmaiex_seniority_overqualified_penalty_ratio
            )

            if c_exp < job_min:
                gap = job_min - c_exp
                seniority_penalty = base_penalty_coef * gap
            elif c_exp > job_max:
                gap = c_exp - job_max
                seniority_penalty = base_penalty_coef * overqualified_ratio * gap
            else:
                seniority_penalty = 0.0

            # Language Scoring — prefer normalized CANDIDATELANGUAGE if available
            norm_langs_for_cand = cand_normalized_langs.get(cid, [])
            if norm_langs_for_cand:
                lang_penalty, lang_bonus, _ = await compute_language_score(
                    job_post_id=job_id,
                    candidate_languages=norm_langs_for_cand,
                    conn=conn,
                    use_normalized=True,
                )
            else:
                # Fallback: no normalized rows yet (old candidate, not re-enriched)
                lang_penalty, lang_bonus, _ = 0.0, 0.0, {"requirements": []}

            final_score = clip_score(
                w_rrf * rrf_score_norm
                + w_skill * skill_score
                - seniority_penalty
                - lang_penalty
                + lang_bonus
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
            SELECT
                u.fName, u.lName, u.provId, c.expyears, c.bio,
                cv.rawText,
                cv.parsedJson -> 'experience' as experiences,
                cv.parsedJson -> 'certificates' as certificates_list,
                cv.parsedJson -> 'education' as education_list,
                cv.parsedJson -> 'languages' as languages,
                cv.parsedJson -> 'expectedSalaryMin' as exp_sal_min,
                cv.parsedJson -> 'expectedSalaryMax' as exp_sal_max
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

    experiences = load_json_field(candidate_row["experiences"])
    recent_titles = [
        e.get("title")
        for e in experiences[:3]
        if isinstance(e, dict) and e.get("title")
    ]
    certs = load_json_field(candidate_row["certificates_list"])
    edu_list = load_json_field(candidate_row["education_list"])
    edu_degrees = [
        e.get("degree") for e in edu_list if isinstance(e, dict) and e.get("degree")
    ]

    profile_parts = []
    if recent_titles:
        profile_parts.append(" ".join(recent_titles))
    if candidate_row["bio"]:
        profile_parts.append(candidate_row["bio"])
    if certs:
        profile_parts.append(" ".join(certs))
    if edu_degrees:
        profile_parts.append(" ".join(edu_degrees))

    # Build candidate text cho text search
    candidate_text = (
        " ".join(filter(None, profile_parts)) or candidate_row["rawtext"] or ""
    )
    if not candidate_text.strip() and c_skills:
        candidate_text = " ".join(str(s) for s in c_skills)
    if not candidate_text.strip():
        candidate_text = "Experienced candidate"

    recent_titles_text = " ".join(recent_titles) if recent_titles else candidate_text

    # Prepare salary expectation
    exp_min = safe_int(candidate_row["exp_sal_min"])
    exp_max = safe_int(candidate_row["exp_sal_max"])
    c_expyears = candidate_row["expyears"] or 0
    if exp_min is None and exp_max is None:
        expected_salary = estimate_expected_salary(
            c_expyears, candidate_row["provid"] or "DEFAULT"
        )
    else:
        # Nếu có ít nhất 1, lấy trung bình
        if exp_min is None:
            exp_min = exp_max
        if exp_max is None:
            exp_max = exp_min
        expected_salary = int((exp_min + exp_max) / 2)

    cand_languages = load_json_field(candidate_row["languages"])

    async with acquire_conn() as conn:
        filter_parts = ["p.expAt > CURRENT_TIMESTAMP"]
        params: list = [candidate_text, recent_titles_text]
        param_idx = 3

        if province_id:
            filter_parts.append(f"p.provId = ${param_idx}")
            params.append(province_id)
            param_idx += 1

        if work_mode:
            filter_parts.append(f"p.workMode = ${param_idx}")
            params.append(work_mode)
            param_idx += 1

        # Loại bỏ các job đã ứng tuyển
        filter_parts.append(
            f"p.jobPostId NOT IN (SELECT jobPostId FROM JOBAPPLICATION WHERE candidateId = ${param_idx})"
        )
        params.append(candidate_id)
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
                p.maxSalary,
                js.req_skills,
                ts_rank(
                    to_tsvector('english', p.title || ' ' || p.description),
                    plainto_tsquery('english', $1)
                ) as text_rank,
                ts_rank(
                    to_tsvector('english', p.title),
                    plainto_tsquery('english', $2)
                ) as title_rank
            FROM JOBPOSTING p
            LEFT JOIN JobSkills js ON p.jobPostId = js.jobPostId
            WHERE {filter_sql}
        """

        jobs = await conn.fetch(jobs_query, *params)

        rrf_k = nmaiex_settings.nmaiex_rrf_k
        w_rrf = nmaiex_settings.nmaiex_cj_weight_rrf
        w_title = nmaiex_settings.nmaiex_cj_weight_title
        w_skill = nmaiex_settings.nmaiex_cj_weight_skill
        alpha = nmaiex_settings.nmaiex_skill_alpha

        text_sorted = sorted(
            jobs,
            key=lambda x: x["text_rank"] if x["text_rank"] is not None else 0,
            reverse=True,
        )
        txt_rank = {j["job_id"]: idx + 1 for idx, j in enumerate(text_sorted)}

        title_sorted = sorted(
            jobs,
            key=lambda x: x["title_rank"] if x["title_rank"] is not None else 0,
            reverse=True,
        )
        title_rank_dict = {j["job_id"]: idx + 1 for idx, j in enumerate(title_sorted)}

        results = []
        for j in jobs:
            jid = j["job_id"]
            r_txt = txt_rank[jid]
            r_title = title_rank_dict[jid]

            # C→J chỉ có text rank (không có vector search từ phía job chunk → candidate)
            rrf_score_norm = (1.0 / (rrf_k + r_txt)) * rrf_k
            title_score = (1.0 / (rrf_k + r_title)) * rrf_k

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

            # Salary Adjustment
            salary_adjustment = compute_salary_adjustment(
                min_salary=j["minsalary"],
                max_salary=j["maxsalary"],
                expected_salary=expected_salary,
            )

            # Language Scoring
            lang_penalty, lang_bonus, lang_breakdown = await compute_language_score(
                job_post_id=jid, candidate_languages=cand_languages, conn=conn
            )

            final_score = clip_score(
                w_rrf * rrf_score_norm
                + w_title * title_score
                + w_skill * skill_score
                + salary_adjustment
                - lang_penalty
                + lang_bonus
            )

            results.append(
                {
                    "job_id": jid,
                    "job_title": j["job_title"],
                    "match_score": round(final_score, 4),
                    "score_breakdown": {
                        "text_score": round(rrf_score_norm, 4),
                        "title_score": round(title_score, 4),
                        "exact_overlap": round(exact_overlap, 4),
                        "fuzzy_overlap": round(fuzzy_overlap, 4),
                        "skill_score": round(skill_score, 4),
                        "skill_alpha": alpha,
                        "salary_adjustment": round(salary_adjustment, 4),
                        "lang_penalty": round(lang_penalty, 4),
                        "lang_bonus": round(lang_bonus, 4),
                        "lang_breakdown": lang_breakdown,
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
