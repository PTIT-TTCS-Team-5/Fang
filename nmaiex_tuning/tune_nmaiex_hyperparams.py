"""nmaiex_tuning/tune_nmaiex_hyperparams.py — Hyperparameter tuning using Optuna.

Tunes 12 parameters across 50,000 trials (2 phases x 25,000 trials) using
in-memory simulation for zero DB/API latency in the Optuna loops.
Saves the optimal parameters back to .env.nmaiex.
"""

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

import optuna

import app.services.embedding
import app.services.nmaiex_mapper_service
from app.core.config import settings
from app.core.database import acquire_conn, db
from app.core.nmaiex_config import nmaiex_settings
from app.services.nmaiex_mapper_service import PROFICIENCY_LEVELS
from app.services.nmaiex_ranking_service import (
    compute_salary_adjustment,
    estimate_expected_salary,
    load_json_field,
    safe_int,
)
from synthetic_data.config import NINE_ROUTER_KEY, NINE_ROUTER_URL

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format='{"asctime": "%(asctime)s", "levelname": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("tune_nmaiex")


# --- Monkey Patching Embedding Service to use 9Router ---
async def embed_chunks_9router(
    chunks: list[str],
    dimensions: int | None = None,
) -> list[list[float]]:
    """Monkey-patched embed_chunks that uses 9Router API proxy to bypass original API quotas."""
    if not chunks:
        return []

    import httpx

    normalized_chunks = [c.strip() for c in chunks if isinstance(c, str) and c.strip()]
    if not normalized_chunks:
        return []

    effective_dims = dimensions if dimensions is not None else settings.embedding_dim
    batch_size = (
        settings.embedding_batch_size if settings.embedding_batch_size > 0 else 32
    )
    vectors: list[list[float]] = []

    logger.info(
        f"[9Router Monkey-Patch] Embedding {len(normalized_chunks)} chunks via 9Router proxy "
        f"({effective_dims} dimensions requested)"
    )

    async with httpx.AsyncClient() as http_client:
        for start_index in range(0, len(normalized_chunks), batch_size):
            batch = normalized_chunks[start_index : start_index + batch_size]
            headers = {
                "Authorization": f"Bearer {NINE_ROUTER_KEY}",
                "Content-Type": "application/json",
            }
            payload = {"model": settings.embedding_model, "input": batch}
            resp = await http_client.post(
                f"{NINE_ROUTER_URL}/embeddings",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data["data"]:
                v = item["embedding"]
                vectors.append(v[:effective_dims])

    if len(vectors) != len(normalized_chunks):
        raise RuntimeError(
            f"9Router returned {len(vectors)} vectors for {len(normalized_chunks)} chunks."
        )

    return vectors


# Monkey patch embedding service immediately
app.services.embedding.embed_chunks = embed_chunks_9router
app.services.nmaiex_mapper_service.embed_chunks = embed_chunks_9router

# File configurations
PROJECT_ROOT = Path(__file__).parent.parent
ENV_NMAIEX_PATH = PROJECT_ROOT / ".env.nmaiex"
GT_MATRIX_PATH = PROJECT_ROOT / "nmaiex_tuning" / "output" / "ground_truth_matrix.json"


@dataclass
class JCPairData:
    """Pre-computed data for a J->C pair."""

    job_id: int
    cand_id: int
    gt_score: int
    vec_rank: int
    txt_rank: int
    exact_overlap: float
    fuzzy_overlap: float
    exp_gap_under: float
    exp_gap_over: float


@dataclass
class CJPairData:
    """Pre-computed data for a C->J pair."""

    cand_id: int
    job_id: int
    gt_score: int
    txt_rank: int
    title_rank: int
    exact_overlap: float
    fuzzy_overlap: float
    salary_adjustment: float
    lang_req_missing: int
    lang_lvl_insuf: int
    lang_pref_met: int


async def precompute_all_pairs() -> Tuple[List[JCPairData], List[CJPairData]]:
    """Loads all metadata from database and precomputes static fields for J->C and C->J."""
    logger.info("=== STARTING PRECOMPUTATION ===")

    # 1. Load Ground Truth Matrix
    if not GT_MATRIX_PATH.exists():
        raise FileNotFoundError(f"Ground truth cache not found at: {GT_MATRIX_PATH}")

    with open(GT_MATRIX_PATH, "r", encoding="utf-8") as f:
        gt_data = json.load(f)

    logger.info(f"Loaded ground truth containing {len(gt_data)} pairs.")

    gt_scores: Dict[Tuple[int, int], int] = {}
    unique_job_ids = set()
    unique_candidate_ids = set()
    for key, val in gt_data.items():
        parts = key.split("_")
        jid = int(parts[0][1:])
        cid = int(parts[1][1:])
        score = val["score"]
        gt_scores[(jid, cid)] = score
        unique_job_ids.add(jid)
        unique_candidate_ids.add(cid)

    logger.info(f"Unique jobs in GT: {len(unique_job_ids)}")
    logger.info(f"Unique candidates in GT: {len(unique_candidate_ids)}")

    async with acquire_conn() as conn:
        # 2. Get Job postings info
        logger.info("Fetching jobs from database...")
        jobs = await conn.fetch(
            "SELECT jobPostId, title, description, minSalary, maxSalary FROM JOBPOSTING"
        )
        jobs_dict = {r["jobpostid"]: r for r in jobs}

        # 3. Get Job seniority bounds
        logger.info("Fetching job seniority levels...")
        job_min_max = {}
        for jid in unique_job_ids:
            job_levels_rows = await conn.fetch(
                """
                SELECT l.minYears
                FROM JOB_LEVEL_MAP m
                JOIN JOBLEVEL l ON m.levelId = l.levelId
                WHERE m.jobPostId = $1
                """,
                jid,
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
                job_max = 9999.0
            job_min_max[jid] = (job_min, job_max)

        # 4. Fetch Job skill requirements
        logger.info("Fetching job skills requirements...")
        job_skills_rows = await conn.fetch(
            "SELECT jobPostId, skillId FROM JOBREQUIREMENT"
        )
        job_skills: Dict[int, Set[int]] = {}
        for r in job_skills_rows:
            job_skills.setdefault(r["jobpostid"], set()).add(r["skillid"])

        # 5. Fetch Candidate parsed resumes and details
        logger.info("Fetching candidates metadata...")
        candidate_rows = await conn.fetch("""
            SELECT ja.candidateId, cv.parsedJson, c.expyears, COALESCE(cv.rawText, c.bio) as raw_text
            FROM CVPARSED cv
            JOIN JOBAPPLICATION ja ON cv.jobAppId = ja.jobAppId
            JOIN CANDIDATE c ON ja.candidateId = c.userId
            """)
        candidates_dict = {}
        for r in candidate_rows:
            cid = r["candidateid"]
            parsed_cv = (
                json.loads(r["parsedjson"])
                if isinstance(r["parsedjson"], str)
                else r["parsedjson"]
            )
            candidates_dict[cid] = {
                "candidate_id": cid,
                "parsed_cv": parsed_cv,
                "expyears": r["expyears"] or 0,
                "rawText": r["raw_text"] or "",
            }

        # 6. Fetch Candidate skill catalog
        logger.info("Fetching candidate catalog skills...")
        candidate_skills_rows = await conn.fetch(
            "SELECT userId, skillId FROM CANDIDATESKILL"
        )
        candidate_skills: Dict[int, Set[int]] = {}
        for r in candidate_skills_rows:
            candidate_skills.setdefault(r["userid"], set()).add(r["skillid"])

        # 7. Fetch Fuzzy Overlaps from raw tables (Single cross-join)
        logger.info("Fetching fuzzy overlaps using database cross-join...")
        fuzzy_overlaps: Dict[Tuple[int, int], float] = {}
        fuzzy_rows = await conn.fetch("""
            SELECT jobPostId, candId, AVG(max_sim) as avg_fuzzy
            FROM (
                SELECT j.jobPostId, c.candId, j.rawId, MAX(1 - (j.embedding <=> c.embedding)) as max_sim
                FROM JOB_SKILL_RAW j
                CROSS JOIN CANDIDATE_SKILL_RAW c
                WHERE j.embedding IS NOT NULL
                  AND c.embedding IS NOT NULL
                GROUP BY j.jobPostId, c.candId, j.rawId
            ) sub
            GROUP BY jobPostId, candId
            """)
        for r in fuzzy_rows:
            jid = r["jobpostid"]
            cid = r["candid"]
            fuzzy_overlaps[(jid, cid)] = max(
                0.0, min(1.0, float(r["avg_fuzzy"] or 0.0))
            )

        logger.info(f"Loaded {len(fuzzy_overlaps)} fuzzy overlap values.")

        # 8. Fetch language requirements
        logger.info("Fetching job language requirements...")
        lang_rows = await conn.fetch("""
            SELECT r.jobPostId, l.langCode, r.reqType, r.minLevel
            FROM JOB_LANG_REQUIREMENT r
            JOIN LANGUAGE l ON r.langId = l.langId
            """)
        job_languages: Dict[int, List[dict]] = {}
        for r in lang_rows:
            job_languages.setdefault(r["jobpostid"], []).append(
                {
                    "code": r["langcode"],
                    "req_type": r["reqtype"],
                    "min_level": r["minlevel"] or "BASIC",
                }
            )

        # 9. Pre-compute Vector & Text rank positions for J->C
        logger.info("Pre-computing J->C vector and text rank positions...")
        jc_vec_ranks: Dict[int, Dict[int, int]] = {}
        jc_txt_ranks: Dict[int, Dict[int, int]] = {}
        vec_type = settings.embedding_vector_type

        for jid in unique_job_ids:
            job_row = jobs_dict.get(jid)
            if not job_row:
                continue

            job_text = f"{job_row['title']}\n{job_row['description']}"
            vectors = await embed_chunks_9router([job_text])
            if not vectors:
                continue
            job_vector = vectors[0]
            vector_str = "[" + ",".join(map(str, job_vector)) + "]"

            # Query all active candidates who applied to this job (same as service ranking)
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
                WHERE u.stat = 'ACTIVE'
            """
            rows = await conn.fetch(candidates_query, vector_str, job_text, jid)

            vec_sorted = sorted(
                rows,
                key=lambda x: (
                    x["vector_distance"] if x["vector_distance"] is not None else 999
                ),
            )
            vec_rank = {c["candidate_id"]: idx + 1 for idx, c in enumerate(vec_sorted)}

            text_sorted = sorted(
                rows,
                key=lambda x: x["text_rank"] if x["text_rank"] is not None else 0,
                reverse=True,
            )
            txt_rank = {c["candidate_id"]: idx + 1 for idx, c in enumerate(text_sorted)}

            jc_vec_ranks[jid] = vec_rank
            jc_txt_ranks[jid] = txt_rank

        # 10. Pre-compute Text & Title rank positions, Salary Adjustments, Language Requirement components for C->J
        logger.info("Pre-computing C->J text/title rank positions and metadata...")
        cj_txt_ranks: Dict[int, Dict[int, int]] = {}
        cj_title_ranks: Dict[int, Dict[int, int]] = {}
        cj_salary_adjustments: Dict[int, Dict[int, float]] = {}
        cj_lang_components: Dict[int, Dict[int, Tuple[int, int, int]]] = {}

        for cid in unique_candidate_ids:
            cand_info = candidates_dict.get(cid)
            if not cand_info:
                continue

            parsed_cv = cand_info["parsed_cv"]
            c_skills = candidate_skills.get(cid, set())

            # Reconstruct candidate text
            experiences = load_json_field(parsed_cv.get("experience"))
            recent_titles = [
                e.get("title")
                for e in experiences[:3]
                if isinstance(e, dict) and e.get("title")
            ]
            certs = load_json_field(parsed_cv.get("certificates"))
            edu_list = load_json_field(parsed_cv.get("education"))
            edu_degrees = [
                e.get("degree")
                for e in edu_list
                if isinstance(e, dict) and e.get("degree")
            ]

            profile_parts = []
            if recent_titles:
                profile_parts.append(" ".join(recent_titles))
            if cand_info["rawText"]:
                profile_parts.append(cand_info["rawText"])
            if certs:
                profile_parts.append(" ".join(certs))
            if edu_degrees:
                profile_parts.append(" ".join(edu_degrees))

            candidate_text = " ".join(filter(None, profile_parts))
            if not candidate_text.strip() and c_skills:
                candidate_text = " ".join(str(s) for s in c_skills)
            if not candidate_text.strip():
                candidate_text = "Experienced candidate"

            recent_titles_text = (
                " ".join(recent_titles) if recent_titles else candidate_text
            )

            # Expected Salary
            exp_min = safe_int(parsed_cv.get("expectedSalaryMin"))
            exp_max = safe_int(parsed_cv.get("expectedSalaryMax"))
            c_expyears = cand_info["expyears"]
            expected_salary = estimate_expected_salary(c_expyears, "DEFAULT")
            if exp_min is not None or exp_max is not None:
                if exp_min is None:
                    exp_min = exp_max
                if exp_max is None:
                    exp_max = exp_min
                expected_salary = int((exp_min + exp_max) / 2)

            # Languages
            cand_languages = load_json_field(parsed_cv.get("languages"))
            cand_lang_map = {}
            for cl in cand_languages:
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
                    code = lang_name

                prof = cl.get("proficiency", "BASIC")
                cand_lang_map[code] = PROFICIENCY_LEVELS.get(prof, 1)

            # Query ranks for all active jobs
            jobs_query = """
                WITH JobSkills AS (
                    SELECT jobPostId, array_agg(skillId) as req_skills
                    FROM JOBREQUIREMENT
                    GROUP BY jobPostId
                )
                SELECT
                    p.jobPostId as job_id,
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
                WHERE p.expAt > CURRENT_TIMESTAMP
            """
            jobs_rows = await conn.fetch(jobs_query, candidate_text, recent_titles_text)

            text_sorted = sorted(
                jobs_rows,
                key=lambda x: x["text_rank"] if x["text_rank"] is not None else 0,
                reverse=True,
            )
            txt_rank_dict = {j["job_id"]: idx + 1 for idx, j in enumerate(text_sorted)}

            title_sorted = sorted(
                jobs_rows,
                key=lambda x: x["title_rank"] if x["title_rank"] is not None else 0,
                reverse=True,
            )
            title_rank_dict = {
                j["job_id"]: idx + 1 for idx, j in enumerate(title_sorted)
            }

            cj_txt_ranks[cid] = txt_rank_dict
            cj_title_ranks[cid] = title_rank_dict
            cj_salary_adjustments[cid] = {}
            cj_lang_components[cid] = {}

            for j in jobs_rows:
                jid = j["job_id"]

                # Salary Adjustment
                cj_salary_adjustments[cid][jid] = compute_salary_adjustment(
                    min_salary=j["minsalary"],
                    max_salary=j["maxsalary"],
                    expected_salary=expected_salary,
                )

                # Language counts (missing, insufficient, preferred met)
                req_missing = 0
                lang_lvl_insuf = 0
                lang_pref_met = 0

                reqs = job_languages.get(jid, [])
                for req in reqs:
                    code = req["code"]
                    req_type = req["req_type"]
                    req_level = PROFICIENCY_LEVELS.get(req["min_level"], 1)

                    cand_level = cand_lang_map.get(code, 0)

                    if req_type == "REQUIRED":
                        if cand_level == 0:
                            req_missing += 1
                        elif cand_level < req_level:
                            lang_lvl_insuf += 1
                    elif req_type == "PREFERRED":
                        if cand_level >= req_level:
                            lang_pref_met += 1

                cj_lang_components[cid][jid] = (
                    req_missing,
                    lang_lvl_insuf,
                    lang_pref_met,
                )

    # 11. Assembly Pair Lists
    jc_pairs: List[JCPairData] = []
    cj_pairs: List[CJPairData] = []

    for (jid, cid), score in gt_scores.items():
        # J->C precomputed data
        vec_rank = jc_vec_ranks.get(jid, {}).get(cid, 999)
        txt_rank_jc = jc_txt_ranks.get(jid, {}).get(cid, 999)

        j_skills = job_skills.get(jid, set())
        c_skills = candidate_skills.get(cid, set())

        exact_overlap = len(j_skills.intersection(c_skills)) / max(len(j_skills), 1)
        fuzzy_overlap = fuzzy_overlaps.get((jid, cid), 0.0)

        c_exp = candidates_dict.get(cid, {}).get("expyears", 0.0)
        job_min, job_max = job_min_max.get(jid, (0.0, 9999.0))

        exp_gap_under = max(job_min - c_exp, 0.0)
        exp_gap_over = max(c_exp - job_max, 0.0)

        jc_pairs.append(
            JCPairData(
                job_id=jid,
                cand_id=cid,
                gt_score=score,
                vec_rank=vec_rank,
                txt_rank=txt_rank_jc,
                exact_overlap=exact_overlap,
                fuzzy_overlap=fuzzy_overlap,
                exp_gap_under=exp_gap_under,
                exp_gap_over=exp_gap_over,
            )
        )

        # C->J precomputed data
        txt_rank_cj = cj_txt_ranks.get(cid, {}).get(jid, 999)
        title_rank = cj_title_ranks.get(cid, {}).get(jid, 999)
        salary_adjustment = cj_salary_adjustments.get(cid, {}).get(jid, 0.0)
        req_missing, lang_lvl_insuf, lang_pref_met = cj_lang_components.get(
            cid, {}
        ).get(jid, (0, 0, 0))

        cj_pairs.append(
            CJPairData(
                cand_id=cid,
                job_id=jid,
                gt_score=score,
                txt_rank=txt_rank_cj,
                title_rank=title_rank,
                exact_overlap=exact_overlap,
                fuzzy_overlap=fuzzy_overlap,
                salary_adjustment=salary_adjustment,
                lang_req_missing=req_missing,
                lang_lvl_insuf=lang_lvl_insuf,
                lang_pref_met=lang_pref_met,
            )
        )

    logger.info("=== PRECOMPUTATION FINISHED ===")
    logger.info(f"Pre-computed J->C pairs: {len(jc_pairs)}")
    logger.info(f"Pre-computed C->J pairs: {len(cj_pairs)}")

    return jc_pairs, cj_pairs


# ============================================================
# Metric Evaluation Functions
# ============================================================


def compute_mrr(
    pairs: List[JCPairData],
    w_rrf: float,
    w_skill: float,
    alpha: float,
    coef: float,
    overq_ratio: float,
    enable_clip: bool = False,
) -> float:
    """Computes Mean Reciprocal Rank (MRR) based on pairs with ground_truth >= 3."""
    RRF_K = 60

    # 1. Compute scores for all J->C pairs and group them by job_id
    job_scores: Dict[int, List[Tuple[int, float]]] = {}
    for p in pairs:
        # normalized RRF score
        rrf_score = 1.0 / (RRF_K + p.vec_rank) + 1.0 / (RRF_K + p.txt_rank)
        rrf_score_norm = rrf_score * RRF_K / 2.0

        # Skill
        skill_score = alpha * p.exact_overlap + (1.0 - alpha) * p.fuzzy_overlap

        # Seniority
        seniority_penalty = coef * p.exp_gap_under + coef * overq_ratio * p.exp_gap_over

        # Final raw score
        final_score = w_rrf * rrf_score_norm + w_skill * skill_score - seniority_penalty
        if enable_clip:
            final_score = max(0.0, min(1.0, final_score))

        job_scores.setdefault(p.job_id, []).append((p.cand_id, final_score))

    # 2. Extract gt relevant set per job (gt >= 3)
    job_relevance: Dict[int, Set[int]] = {}
    for p in pairs:
        if p.gt_score >= 3:
            job_relevance.setdefault(p.job_id, set()).add(p.cand_id)

    # 3. Calculate MRR
    mrr_sum = 0.0
    n_queries = 0

    for jid, scores in job_scores.items():
        relevant = job_relevance.get(jid, set())
        if not relevant:
            continue  # Skip jobs that have zero relevant candidates in Ground Truth

        n_queries += 1

        # Sort candidates descending
        sorted_cands = sorted(scores, key=lambda x: x[1], reverse=True)

        # Find first relevant candidate rank
        for rank, (cid, _) in enumerate(sorted_cands, 1):
            if cid in relevant:
                mrr_sum += 1.0 / rank
                break

    return mrr_sum / n_queries if n_queries > 0 else 0.0


def compute_ndcg_at_k(
    pairs: List[CJPairData],
    w_rrf: float,
    w_title: float,
    w_skill: float,
    w_salary: float,
    alpha: float,
    lang_req_pen: float,
    lang_lvl_pen: float,
    lang_pref_bon: float,
    lang_bon_cap: float,
    k: int = 10,
    enable_clip: bool = False,
) -> float:
    """Computes Normalized Discounted Cumulative Gain (nDCG@10) using candidate pivoted gt scores."""
    from math import log2

    RRF_K = 60

    # 1. Compute scores for all pairs and group by candidate
    cand_scores: Dict[int, List[Tuple[int, float]]] = {}
    cand_gt: Dict[int, Dict[int, int]] = {}

    for p in pairs:
        # text / title search normalized rrf
        rrf_score_norm = (1.0 / (RRF_K + p.txt_rank)) * RRF_K
        title_score = (1.0 / (RRF_K + p.title_rank)) * RRF_K

        # skill
        skill_score = alpha * p.exact_overlap + (1.0 - alpha) * p.fuzzy_overlap

        # language
        lang_penalty = (
            p.lang_req_missing * lang_req_pen + p.lang_lvl_insuf * lang_lvl_pen
        )
        lang_bonus = min(p.lang_pref_met * lang_pref_bon, lang_bon_cap)

        # final CJ score
        final_score = (
            w_rrf * rrf_score_norm
            + w_title * title_score
            + w_skill * skill_score
            + w_salary * p.salary_adjustment
            - lang_penalty
            + lang_bonus
        )
        if enable_clip:
            final_score = max(0.0, min(1.0, final_score))

        cand_scores.setdefault(p.cand_id, []).append((p.job_id, final_score))
        cand_gt.setdefault(p.cand_id, {})[p.job_id] = p.gt_score

    # 2. Compute nDCG
    ndcg_sum = 0.0
    n_queries = 0

    for cid, scores in cand_scores.items():
        gts = cand_gt[cid]

        # Sort candidates' jobs descending
        sorted_jobs = sorted(scores, key=lambda x: x[1], reverse=True)[:k]

        # DCG
        dcg = sum(
            (2 ** gts[jid] - 1) / log2(rank + 1)
            for rank, (jid, _) in enumerate(sorted_jobs, 1)
        )

        # Ideal DCG
        ideal_rels = sorted(gts.values(), reverse=True)[:k]
        idcg = sum(
            (2**rel - 1) / log2(rank + 1) for rank, rel in enumerate(ideal_rels, 1)
        )

        if idcg > 0:
            ndcg_sum += dcg / idcg
            n_queries += 1

    return ndcg_sum / n_queries if n_queries > 0 else 0.0


# ============================================================
# Multi-Process Objective & Parallel Tuning Configuration
# ============================================================

# Global variables for worker processes on Windows
GLOBAL_JC_PAIRS: List[JCPairData] = []
GLOBAL_CJ_PAIRS: List[CJPairData] = []
GLOBAL_LOCKED_ALPHA: float = 0.80
GLOBAL_ENABLE_CLIP: bool = False


def init_globals(jc_pairs, cj_pairs, locked_alpha, enable_clip):
    """Initializes global parameters inside the newly spawned worker processes."""
    global GLOBAL_JC_PAIRS, GLOBAL_CJ_PAIRS, GLOBAL_LOCKED_ALPHA, GLOBAL_ENABLE_CLIP
    GLOBAL_JC_PAIRS = jc_pairs
    GLOBAL_CJ_PAIRS = cj_pairs
    GLOBAL_LOCKED_ALPHA = locked_alpha
    GLOBAL_ENABLE_CLIP = enable_clip


def jc_objective_proc(trial: optuna.Trial) -> float:
    """Process-safe objective function for Phase 1 J->C matching."""
    w_rrf = trial.suggest_float("jc_w_rrf", 0.10, 0.60)
    w_skill = trial.suggest_float("jc_w_skill", 0.20, 0.70)
    alpha_jc = trial.suggest_float("skill_alpha_jc", 0.40, 1.00)
    coef = trial.suggest_float("jc_sen_coef", 0.05, 0.60)
    overq_ratio = trial.suggest_float("sen_overq_ratio", 0.10, 1.00)

    mrr = compute_mrr(
        pairs=GLOBAL_JC_PAIRS,
        w_rrf=w_rrf,
        w_skill=w_skill,
        alpha=alpha_jc,
        coef=coef,
        overq_ratio=overq_ratio,
        enable_clip=GLOBAL_ENABLE_CLIP,
    )
    return mrr


def cj_objective_proc(trial: optuna.Trial) -> float:
    """Process-safe objective function for Phase 2 C->J matching."""
    w_rrf = trial.suggest_float("cj_w_rrf", 0.10, 0.60)
    w_title = trial.suggest_float("cj_w_title", 0.05, 0.40)
    w_skill = trial.suggest_float("cj_w_skill", 0.10, 0.60)
    w_salary = trial.suggest_float("cj_w_salary", 0.0, 0.50)
    alpha_cj = trial.suggest_float("skill_alpha_cj", 0.40, 1.00)

    lang_req_pen = trial.suggest_float("lang_req_pen", 0.05, 0.50)
    lang_lvl_pen = trial.suggest_float("lang_lvl_pen", 0.02, 0.30)
    lang_pref_bon = trial.suggest_float("lang_pref_bon", 0.02, 0.20)
    lang_bon_cap = trial.suggest_float("lang_bon_cap", 0.05, 0.30)

    ndcg = compute_ndcg_at_k(
        pairs=GLOBAL_CJ_PAIRS,
        w_rrf=w_rrf,
        w_title=w_title,
        w_skill=w_skill,
        w_salary=w_salary,
        alpha=alpha_cj,
        lang_req_pen=lang_req_pen,
        lang_lvl_pen=lang_lvl_pen,
        lang_pref_bon=lang_pref_bon,
        lang_bon_cap=lang_bon_cap,
        enable_clip=GLOBAL_ENABLE_CLIP,
    )
    return ndcg


def run_optimize(study_name: str, storage_url: str, objective_type: str, n_trials: int):
    """Worker entry point loading the SQLite study and performing optimization trials."""
    # Suppress output inside subprocesses
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.load_study(study_name=study_name, storage=storage_url)
    if objective_type == "jc":
        study.optimize(jc_objective_proc, n_trials=n_trials)
    elif objective_type == "cj":
        study.optimize(cj_objective_proc, n_trials=n_trials)


# ============================================================
# .env Update Functions
# ============================================================


def update_env_file(best_params: Dict[str, float]):
    """Creates a timestamped backup and updates the active parameters in .env.nmaiex."""
    if not ENV_NMAIEX_PATH.exists():
        logger.warning(
            f".env.nmaiex does not exist at {ENV_NMAIEX_PATH}. Skipping env update."
        )
        return

    # 1. Create a backup file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = ENV_NMAIEX_PATH.parent / f".env.nmaiex.backup_{timestamp}"

    with open(ENV_NMAIEX_PATH, "r", encoding="utf-8") as f:
        env_content = f.read()

    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    logger.info(f"Created backup of .env.nmaiex at: {backup_path}")

    # 2. Update parameters mapping (Map Optuna trial name to env variable name)
    env_keys_mapping = {
        "jc_w_rrf": "NMAIEX_JC_WEIGHT_RRF",
        "jc_w_skill": "NMAIEX_JC_WEIGHT_SKILL",
        "skill_alpha_jc": "NMAIEX_SKILL_ALPHA_JC",
        "jc_sen_coef": "NMAIEX_JC_PENALTY_SENIORITY_COEF",
        "sen_overq_ratio": "NMAIEX_SENIORITY_OVERQUALIFIED_PENALTY_RATIO",
        "cj_w_rrf": "NMAIEX_CJ_WEIGHT_RRF",
        "cj_w_title": "NMAIEX_CJ_WEIGHT_TITLE",
        "cj_w_skill": "NMAIEX_CJ_WEIGHT_SKILL",
        "cj_w_salary": "NMAIEX_CJ_WEIGHT_SALARY",
        "skill_alpha_cj": "NMAIEX_SKILL_ALPHA_CJ",
        "lang_req_pen": "NMAIEX_LANG_REQUIRED_PENALTY",
        "lang_lvl_pen": "NMAIEX_LANG_LEVEL_PENALTY",
        "lang_pref_bon": "NMAIEX_LANG_PREFERRED_BONUS",
        "lang_bon_cap": "NMAIEX_LANG_BONUS_CAP",
    }

    lines = env_content.splitlines()
    updated_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, val = stripped.split("=", 1)
            key = key.strip()

            # Find if this key is one of the parameters to update
            found_param = None
            for param_name, env_key in env_keys_mapping.items():
                if env_key == key:
                    found_param = param_name
                    break

            if found_param is not None and found_param in best_params:
                # Format to keep 4 decimal places
                new_val = f"{best_params[found_param]:.4f}"
                updated_lines.append(f"{key}={new_val}")
                logger.info(f"Updating {key} from {val} to {new_val}")
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    # Save the updated env file
    with open(ENV_NMAIEX_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(updated_lines) + "\n")

    logger.info("Successfully updated .env.nmaiex with optimal weights!")


# ============================================================
# Main Orchestrator (v2 — Resume + 6-Hour Budget)
# ============================================================


def parse_args():
    """Parse command-line arguments for resume and trial budget control."""
    import argparse

    parser = argparse.ArgumentParser(
        description="NMAIex Hyperparameter Tuning — Optuna Multiprocess Optimizer"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Tiếp tục từ SQLite DB hiện tại thay vì bắt đầu lại từ đầu.",
    )
    parser.add_argument(
        "--trials-per-phase",
        type=int,
        default=75000,
        help="Số trials MỚI cho mỗi phase (mặc định: 75000, khít ~5 tiếng).",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    logger.info("=== STARTING NMAIEX HYPERPARAMETER TUNING ===")
    logger.info(f"Mode: {'RESUME' if args.resume else 'FRESH'}")
    logger.info(f"Target trials per phase: {args.trials_per_phase}")

    # Connect DB to precompute static data
    await db.connect()
    try:
        jc_pairs, cj_pairs = await precompute_all_pairs()
    finally:
        await db.disconnect()

    # Setup SQLite storage engine to share optimization state between processes
    import shutil

    DB_DIR = PROJECT_ROOT / "nmaiex_tuning" / "output"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db_file = DB_DIR / "nmaiex_tuning.db"
    SQLITE_URL = f"sqlite:///{db_file.as_posix()}?timeout=60"

    # ── Automatic Backup ──
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = DB_DIR / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if db_file.exists():
        backup_db = backup_dir / f"nmaiex_tuning_{timestamp}.db"
        shutil.copy2(db_file, backup_db)
        logger.info(f"Backed up SQLite DB → {backup_db}")

    if ENV_NMAIEX_PATH.exists():
        backup_env = backup_dir / f".env.nmaiex_{timestamp}"
        shutil.copy2(ENV_NMAIEX_PATH, backup_env)
        logger.info(f"Backed up .env.nmaiex → {backup_env}")

    # ── Fresh or Resume ──
    if not args.resume and db_file.exists():
        try:
            db_file.unlink()
            logger.info("Removed existing SQLite DB for a fresh run.")
        except Exception as e:
            logger.warning(f"Could not remove SQLite database: {e}")

    # Load baseline settings
    baseline_params = {
        "jc_w_rrf": 0.30,
        "jc_w_skill": 0.40,
        "skill_alpha_jc": 0.80,
        "jc_sen_coef": 0.25,
        "sen_overq_ratio": 0.50,
        "cj_w_rrf": 0.35,
        "cj_w_title": 0.15,
        "cj_w_skill": 0.30,
        "cj_w_salary": 0.20,
        "skill_alpha_cj": 0.80,
        "lang_req_pen": 0.25,
        "lang_lvl_pen": 0.10,
        "lang_pref_bon": 0.08,
        "lang_bon_cap": 0.15,
    }

    enable_clip = nmaiex_settings.nmaiex_enable_score_clip
    logger.info(f"Score Clipping enabled: {enable_clip}")

    # Compute baseline metrics
    baseline_mrr = compute_mrr(
        pairs=jc_pairs,
        w_rrf=baseline_params["jc_w_rrf"],
        w_skill=baseline_params["jc_w_skill"],
        alpha=baseline_params["skill_alpha_jc"],
        coef=baseline_params["jc_sen_coef"],
        overq_ratio=baseline_params["sen_overq_ratio"],
        enable_clip=enable_clip,
    )
    baseline_ndcg = compute_ndcg_at_k(
        pairs=cj_pairs,
        w_rrf=baseline_params["cj_w_rrf"],
        w_title=baseline_params["cj_w_title"],
        w_skill=baseline_params["cj_w_skill"],
        w_salary=baseline_params["cj_w_salary"],
        alpha=baseline_params["skill_alpha_cj"],
        lang_req_pen=baseline_params["lang_req_pen"],
        lang_lvl_pen=baseline_params["lang_lvl_pen"],
        lang_pref_bon=baseline_params["lang_pref_bon"],
        lang_bon_cap=baseline_params["lang_bon_cap"],
        enable_clip=enable_clip,
    )

    logger.info("BASELINE METRICS:")
    logger.info(f"  J->C MRR (HR Mode): {baseline_mrr:.4f}")
    logger.info(f"  C->J nDCG@10 (Candidate Mode): {baseline_ndcg:.4f}")

    # Parallel multiprocessing workers count (Using 85% of available logical CPU cores)
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor

    num_cores = multiprocessing.cpu_count()
    num_workers = max(1, int(num_cores * 0.85))
    logger.info(
        f"Detected {num_cores} cores. Spawning {num_workers} parallel worker processes..."
    )

    # Upgraded sampler with multivariate joint distribution modeling
    sampler = optuna.samplers.TPESampler(
        n_startup_trials=1000,
        multivariate=True,
        group=True,
        seed=42,
    )

    # ============================================================
    # Phase 1: J->C (HR Search, MRR) — Continue / Resume
    # ============================================================
    study_jc = optuna.create_study(
        study_name="jc_study",
        direction="maximize",
        storage=SQLITE_URL,
        load_if_exists=True,
        sampler=sampler,
    )

    existing_jc = len(study_jc.trials)
    if args.resume and existing_jc > 0:
        remaining_jc = max(0, args.trials_per_phase - existing_jc)
        logger.info(
            f"Phase 1 RESUME: {existing_jc} trials đã có, cần chạy thêm {remaining_jc} trials."
        )
    else:
        remaining_jc = args.trials_per_phase
        logger.info(f"Phase 1 FRESH: sẽ chạy {remaining_jc} trials.")

    if remaining_jc > 0:
        trials_per_worker_jc = max(1, remaining_jc // num_workers)
        actual_jc = trials_per_worker_jc * num_workers
        logger.info(
            f"=== STARTING PHASE 1: J->C OPTIMIZATION ({actual_jc} NEW TRIALS) ==="
        )
        start_time = time.time()

        with ProcessPoolExecutor(
            max_workers=num_workers,
            initializer=init_globals,
            initargs=(
                jc_pairs,
                cj_pairs,
                baseline_params["skill_alpha_jc"],
                enable_clip,
            ),
        ) as executor:
            futures = [
                executor.submit(
                    run_optimize,
                    study_name="jc_study",
                    storage_url=SQLITE_URL,
                    objective_type="jc",
                    n_trials=trials_per_worker_jc,
                )
                for _ in range(num_workers)
            ]
            for idx, future in enumerate(futures):
                try:
                    future.result()
                except Exception as exc:
                    logger.error(f"Worker {idx} error in Phase 1: {exc}")

        phase1_time = time.time() - start_time
        logger.info(
            f"Phase 1 finished in {phase1_time:.2f} seconds ({phase1_time/60:.1f} min)."
        )
    else:
        logger.info("Phase 1: Đã đủ trials, bỏ qua chạy thêm.")

    # Reload study to get best results
    study_jc = optuna.load_study(study_name="jc_study", storage=SQLITE_URL)
    total_jc = len(study_jc.trials)
    logger.info(f"Phase 1 TOTAL trials: {total_jc}")
    logger.info(f"Best J->C Trial MRR: {study_jc.best_value:.4f}")
    logger.info("Optimal parameters from Phase 1:")
    for k, v in study_jc.best_params.items():
        logger.info(f"  {k}: {v:.4f}")

    locked_alpha = study_jc.best_params["skill_alpha_jc"]
    logger.info(f"LOCKED nmaiex_skill_alpha_jc for Phase 2 = {locked_alpha:.4f}")

    # --- IMMEDIATE SAVE: Persist Phase 1 optimal parameters to .env.nmaiex ---
    logger.info("=== SAVING PHASE 1 OPTIMAL PARAMETERS TO .ENV ===")
    update_env_file(study_jc.best_params)

    # ============================================================
    # Phase 2: C->J (Job Search, nDCG@10) — Continue / Resume
    # ============================================================
    study_cj = optuna.create_study(
        study_name="cj_study",
        direction="maximize",
        storage=SQLITE_URL,
        load_if_exists=True,
        sampler=sampler,
    )

    existing_cj = len(study_cj.trials)
    if args.resume and existing_cj > 0:
        remaining_cj = max(0, args.trials_per_phase - existing_cj)
        logger.info(
            f"Phase 2 RESUME: {existing_cj} trials đã có, cần chạy thêm {remaining_cj} trials."
        )
    else:
        remaining_cj = args.trials_per_phase
        logger.info(f"Phase 2 FRESH: sẽ chạy {remaining_cj} trials.")

    if remaining_cj > 0:
        trials_per_worker_cj = max(1, remaining_cj // num_workers)
        actual_cj = trials_per_worker_cj * num_workers
        logger.info(
            f"=== STARTING PHASE 2: C->J OPTIMIZATION ({actual_cj} NEW TRIALS) ==="
        )
        start_time = time.time()

        with ProcessPoolExecutor(
            max_workers=num_workers,
            initializer=init_globals,
            initargs=(jc_pairs, cj_pairs, locked_alpha, enable_clip),
        ) as executor:
            futures = [
                executor.submit(
                    run_optimize,
                    study_name="cj_study",
                    storage_url=SQLITE_URL,
                    objective_type="cj",
                    n_trials=trials_per_worker_cj,
                )
                for _ in range(num_workers)
            ]
            for idx, future in enumerate(futures):
                try:
                    future.result()
                except Exception as exc:
                    logger.error(f"Worker {idx} error in Phase 2: {exc}")

        phase2_time = time.time() - start_time
        logger.info(
            f"Phase 2 finished in {phase2_time:.2f} seconds ({phase2_time/60:.1f} min)."
        )
    else:
        logger.info("Phase 2: Đã đủ trials, bỏ qua chạy thêm.")

    # Reload study to get best results
    study_cj = optuna.load_study(study_name="cj_study", storage=SQLITE_URL)
    total_cj = len(study_cj.trials)
    logger.info(f"Phase 2 TOTAL trials: {total_cj}")
    logger.info(f"Best C->J Trial nDCG@10: {study_cj.best_value:.4f}")
    logger.info("Optimal parameters from Phase 2:")
    for k, v in study_cj.best_params.items():
        logger.info(f"  {k}: {v:.4f}")

    # Combine all optimized parameters
    best_params = {}
    best_params.update(study_jc.best_params)
    best_params.update(study_cj.best_params)

    # ============================================================
    # Final Summary
    # ============================================================
    tuned_mrr = study_jc.best_value
    tuned_ndcg = study_cj.best_value

    logger.info("============================================================")
    logger.info("=== OPTIMIZATION SUMMARY ===")
    logger.info("============================================================")
    logger.info(f"Total Trials: Phase 1 = {total_jc}, Phase 2 = {total_cj}")
    logger.info("Metrics Improvement:")
    logger.info("  J->C MRR (HR Search):")
    logger.info(f"    Baseline: {baseline_mrr:.4f}")
    logger.info(
        f"    Tuned:    {tuned_mrr:.4f} ({(tuned_mrr - baseline_mrr)*100:+.2f}%)"
    )
    logger.info("  C->J nDCG@10 (Job Search):")
    logger.info(f"    Baseline: {baseline_ndcg:.4f}")
    logger.info(
        f"    Tuned:    {tuned_ndcg:.4f} ({(tuned_ndcg - baseline_ndcg)*100:+.2f}%)"
    )
    logger.info("------------------------------------------------------------")
    logger.info("Optimal Parameters to apply:")
    for param_name, env_key in {
        "jc_w_rrf": "NMAIEX_JC_WEIGHT_RRF",
        "jc_w_skill": "NMAIEX_JC_WEIGHT_SKILL",
        "skill_alpha_jc": "NMAIEX_SKILL_ALPHA_JC",
        "jc_sen_coef": "NMAIEX_JC_PENALTY_SENIORITY_COEF",
        "sen_overq_ratio": "NMAIEX_SENIORITY_OVERQUALIFIED_PENALTY_RATIO",
        "cj_w_rrf": "NMAIEX_CJ_WEIGHT_RRF",
        "cj_w_title": "NMAIEX_CJ_WEIGHT_TITLE",
        "cj_w_skill": "NMAIEX_CJ_WEIGHT_SKILL",
        "cj_w_salary": "NMAIEX_CJ_WEIGHT_SALARY",
        "skill_alpha_cj": "NMAIEX_SKILL_ALPHA_CJ",
        "lang_req_pen": "NMAIEX_LANG_REQUIRED_PENALTY",
        "lang_lvl_pen": "NMAIEX_LANG_LEVEL_PENALTY",
        "lang_pref_bon": "NMAIEX_LANG_PREFERRED_BONUS",
        "lang_bon_cap": "NMAIEX_LANG_BONUS_CAP",
    }.items():
        logger.info(f"  {env_key}: {best_params[param_name]:.4f}")
    logger.info("============================================================")

    # Apply the final optimal params back to the env file
    update_env_file(best_params)
    logger.info("=== TUNING COMPLETE ===")


if __name__ == "__main__":
    asyncio.run(main())
