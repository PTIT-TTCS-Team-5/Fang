"""synthetic_data/db_writer.py — Persist Synthetic Data to DB.

Thin client pattern: Tái sử dụng tối đa app/services/* functions.
Orchestrates:
  1. Create User (CANDIDATE)     → userId
  2. Create JOBAPPLICATION       → jobAppId
  3. Save ParsedCV               → cvParsedId
  4. Build Markdown + chunk + embed CV (via app services)
  5. Create JOBPOSTING           → jobPostId
  6. Map levels, categories, skills
  7. Ingest Job description      → AIDOCUMENTCHUNK (via job_ingestion_service)
"""

import logging

from app.core.database import acquire_conn
from app.models.cv_models import ParsedCV
from app.services.chunking import process_document_to_chunks
from app.services.embedding import embed_chunks
from app.services.job_ingestion_service import process_job_ingestion_task
from app.services.markdown_builder import convert_json_to_markdown
from app.services.nmaiex_mapper_service import embed_and_store_raw_skills
from app.services.persistence import save_chunk_payloads, save_parsed_cv
from synthetic_data.models import SyntheticJob
from synthetic_data.personas import CVManifestEntry

logger = logging.getLogger(__name__)


# ============================================================
# Helpers — Read company IDs from DB
# ============================================================


async def fetch_company_ids() -> list[int]:
    """Lấy list compId theo thứ tự insert (ASC) — map 1:1 với comp_id_idx."""
    async with acquire_conn() as conn:
        rows = await conn.fetch("SELECT compId FROM COMPANY ORDER BY compId ASC")
    return [r["compid"] for r in rows]


async def fetch_company_map() -> dict[int, dict]:
    """Lấy {compId: {comp_name, prov_id}} cho tất cả companies."""
    async with acquire_conn() as conn:
        rows = await conn.fetch(
            "SELECT compId, compName, provId FROM COMPANY ORDER BY compId ASC"
        )
    return {
        r["compid"]: {
            "comp_name": r["compname"],
            "prov_id": r["provid"] or "HANOI",
        }
        for r in rows
    }


async def fetch_skill_id_map() -> dict[str, int]:
    """Lấy {skillName_lower: skillId} từ SKILL table."""
    async with acquire_conn() as conn:
        rows = await conn.fetch("SELECT skillId, skillName FROM SKILL")
    return {r["skillname"].strip().lower(): r["skillid"] for r in rows}


async def fetch_hr_by_company(comp_id: int) -> int | None:
    """Lấy userId của HR đầu tiên trong company."""
    async with acquire_conn() as conn:
        row = await conn.fetchrow(
            "SELECT u.userId FROM APPUSER u "
            "JOIN HR h ON h.userId = u.userId "
            "WHERE h.compId = $1 LIMIT 1",
            comp_id,
        )
    return row["userid"] if row else None


# ============================================================
# Candidate + CV Writing
# ============================================================


async def write_candidate_cv(
    entry: CVManifestEntry,
    parsed_cv: ParsedCV,
) -> int | None:
    """Full pipeline: create CANDIDATE → JOBAPPLICATION → parse+embed CV.

    Returns: jobAppId hoặc None nếu thất bại.
    """
    try:
        async with acquire_conn() as conn:
            # --- 1. Create APPUSER (CANDIDATE) ---
            candidate_info = (
                parsed_cv.candidateInfo[0] if parsed_cv.candidateInfo else None
            )
            full_name = (
                candidate_info.fullName if candidate_info else entry["full_name"]
            )
            email = (
                candidate_info.emails[0]
                if candidate_info and candidate_info.emails
                else f"synth_{entry['cv_index']}@pipeline.dev"
            )
            phone = (
                candidate_info.phones[0]
                if candidate_info and candidate_info.phones
                else f"090{entry['cv_index']:07d}"
            )

            # Avoid duplicate emails
            existing = await conn.fetchval(
                "SELECT userId FROM APPUSER WHERE email = $1", email
            )
            if existing:
                email = f"synth_{entry['cv_index']}_x@pipeline.dev"

            user_id = await conn.fetchval(
                """
                INSERT INTO APPUSER (fullName, email, phone, role, passHash)
                VALUES ($1, $2, $3, 'CANDIDATE', 'synth_hash')
                RETURNING userId
                """,
                full_name,
                email,
                phone,
            )

            # --- 2. Create CANDIDATE record ---
            await conn.execute(
                """
                INSERT INTO CANDIDATE (userId, cvUrl)
                VALUES ($1, $2)
                """,
                user_id,
                f"synth://pipeline/{entry['batch_id']}/{entry['cv_index']}",
            )

            # --- 3. Create JOBAPPLICATION (jobAppId is PK of CV chunks) ---
            # Sử dụng một job posting placeholder (sẽ cập nhật sau khi jobs được insert)
            job_app_id = await conn.fetchval(
                """
                INSERT INTO JOBAPPLICATION (userId, jobPostId, stat)
                SELECT $1, MIN(jobPostId), 'PENDING'
                FROM JOBPOSTING
                RETURNING jobAppId
                """,
                user_id,
            )

            if job_app_id is None:
                # Nếu chưa có job posting nào, tạo placeholder
                job_app_id = await conn.fetchval(
                    """
                    INSERT INTO JOBAPPLICATION (userId, stat)
                    VALUES ($1, 'PENDING')
                    RETURNING jobAppId
                    """,
                    user_id,
                )

        # --- 4. Save ParsedCV ---
        parsed_json = parsed_cv.model_dump(mode="json")
        await save_parsed_cv(
            job_app_id=job_app_id,
            raw_text=parsed_cv.rawText,
            parsed_json=parsed_json,
            parser_ver="synth-pipeline-v1",
        )

        # --- 5. Build Markdown + chunk + embed ---
        cv_markdown = convert_json_to_markdown(parsed_cv)
        global_context = f"CV của {full_name}"
        chunk_payloads = process_document_to_chunks(cv_markdown, global_context)
        chunk_contents = [p["content"] for p in chunk_payloads]
        vectors = await embed_chunks(chunk_contents) if chunk_contents else []

        metadata_items = [
            {
                "job_app_id": job_app_id,
                "persona": entry["persona"],
                "batch_id": entry["batch_id"],
            }
            for _ in chunk_payloads
        ]

        await save_chunk_payloads(
            job_app_id=job_app_id,
            source_type="CV",
            chunk_payloads=chunk_payloads,
            metadata_items=metadata_items,
            embeddings=vectors,
            replace_existing=True,
        )

        logger.info(f"CV written: jobAppId={job_app_id}, persona={entry['persona']}")
        return job_app_id

    except Exception as e:
        logger.error(
            f"Failed to write CV for index={entry['cv_index']}: {e}", exc_info=True
        )
        return None


# ============================================================
# Job Writing
# ============================================================


async def write_job_posting(
    job: SyntheticJob,
    skill_id_map: dict[str, int],
) -> int | None:
    """Persist một Job Posting + ingest chunks.

    Returns: jobPostId hoặc None nếu thất bại.
    """
    try:
        async with acquire_conn() as conn:
            # --- 1. Get HR user for this company ---
            hr_row = await conn.fetchrow(
                "SELECT u.userId FROM APPUSER u "
                "JOIN HR h ON h.userId = u.userId "
                "WHERE h.compId = $1 LIMIT 1",
                job.comp_id,
            )
            hr_user_id = hr_row["userid"] if hr_row else None
            if not hr_user_id:
                logger.warning(f"No HR found for compId={job.comp_id}, skipping job")
                return None

            # --- 2. Insert JOBPOSTING ---
            job_post_id = await conn.fetchval(
                """
                INSERT INTO JOBPOSTING (
                    userId, compId, title, description,
                    minSalary, maxSalary, workMode, provId, stat
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'ACTIVE')
                RETURNING jobPostId
                """,
                hr_user_id,
                job.comp_id,
                job.title,
                job.description,
                job.min_salary,
                job.max_salary,
                job.work_mode,
                job.prov_id,
            )

            # --- 3. Map Levels ---
            if job.level_ids:
                await conn.executemany(
                    "INSERT INTO JOB_LEVEL_MAP (jobPostId, levelId) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    [(job_post_id, lid) for lid in job.level_ids],
                )

            # --- 4. Map Categories ---
            if job.cat_ids:
                await conn.executemany(
                    "INSERT INTO JOB_CATEGORY_MAP (jobPostId, catId) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    [(job_post_id, cid) for cid in job.cat_ids],
                )

            # --- 5. Map Catalog Skills (Tier 1) ---
            catalog_skill_ids: list[int] = []
            for skill_name in job.skill_names:
                sid = skill_id_map.get(skill_name.strip().lower())
                if sid:
                    catalog_skill_ids.append(sid)
                else:
                    logger.debug(f"Skill not in catalog: '{skill_name}'")

            if catalog_skill_ids:
                await conn.executemany(
                    "INSERT INTO JOBREQUIREMENT (jobPostId, skillId) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    [(job_post_id, sid) for sid in catalog_skill_ids],
                )

            # --- 6. Language requirements ---
            for lang_req in job.lang_requirements:
                try:
                    await conn.execute(
                        """
                        INSERT INTO JOBLANG (jobPostId, langCode, reqType, minLevel)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT DO NOTHING
                        """,
                        job_post_id,
                        lang_req.get("lang_code", "en"),
                        lang_req.get("req_type", "PREFERRED"),
                        lang_req.get("min_level", "BASIC"),
                    )
                except Exception as e:
                    logger.debug(f"Lang req insert skipped: {e}")

        # --- 7. Custom skills (Tier 2) — embed + store ---
        if job.custom_skills:
            try:
                await embed_and_store_raw_skills(
                    entity_id=job_post_id,
                    entity_type="JOB",
                    raw_skills=job.custom_skills,
                )
            except Exception as e:
                logger.warning(
                    f"custom_skills embed failed for jobPostId={job_post_id}: {e}"
                )

        # --- 8. Ingest job description for RAG ---
        await process_job_ingestion_task(
            job_id=job_post_id,
            title=job.title,
            description=job.description,
        )

        logger.info(f"Job written: jobPostId={job_post_id}, title={job.title[:50]}")
        return job_post_id

    except Exception as e:
        logger.error(f"Failed to write job '{job.title}': {e}", exc_info=True)
        return None
