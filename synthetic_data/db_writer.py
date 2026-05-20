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
from app.services.markdown_builder import (
    convert_json_to_markdown,
    extract_global_metadata,
)
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
            'SELECT u.userId FROM "user" u '
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
            existing_email = await conn.fetchval(
                'SELECT userId FROM "user" WHERE email = $1', email
            )
            if existing_email:
                email = f"synth_{entry['cv_index']}_x_{entry['batch_id']}@pipeline.dev"

            # Avoid duplicate phones
            if phone:
                existing_phone = await conn.fetchval(
                    'SELECT userId FROM "user" WHERE phone = $1', phone
                )
                if existing_phone:
                    phone = f"090{entry['cv_index']:07d}"
                    still_existing = await conn.fetchval(
                        'SELECT userId FROM "user" WHERE phone = $1', phone
                    )
                    if still_existing:
                        import random

                        phone = f"09{random.randint(10000000, 99999999)}"

            # Split full_name into fName and lName
            parts = full_name.strip().split(None, 1)
            if len(parts) == 2:
                f_name, l_name = parts[0], parts[1]
            elif len(parts) == 1:
                f_name, l_name = parts[0], "N/A"
            else:
                f_name, l_name = "Synthetic", "Candidate"

            user_name = f"candidate_{entry['batch_id']}_{entry['cv_index']}"

            user_id = await conn.fetchval(
                """
                INSERT INTO "user" (userName, pwd, fName, lName, email, phone, provId, ward, street, role)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'CANDIDATE')
                RETURNING userId
                """,
                user_name,
                "synth_hash",
                f_name,
                l_name,
                email,
                phone,
                entry.get("province") or "HANOI",
                "Ward Placeholder",
                "Street Placeholder",
            )

            # --- 2. Create CANDIDATE record ---
            import random
            from datetime import date

            # Calculate DOB based on exp_years
            age = 22 + entry["exp_years"] + random.randint(-2, 4)
            if age < 18:
                age = 18
            birth_year = 2026 - age
            dob = date(birth_year, random.randint(1, 12), random.randint(1, 28))

            await conn.execute(
                """
                INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                parsed_cv.summary or "",
                f"synth://pipeline/{entry['batch_id']}/{entry['cv_index']}",
                dob,
                entry["exp_years"],
            )

            # --- 3. Create JOBAPPLICATION (jobAppId is PK of CV chunks) ---
            # Sử dụng một job posting placeholder (sẽ cập nhật sau khi jobs được insert)
            job_app_id = await conn.fetchval(
                """
                INSERT INTO JOBAPPLICATION (candidateId, jobPostId, stat, cvSnapUrl)
                SELECT $1, MIN(jobPostId), 'PENDING', $2
                FROM JOBPOSTING
                RETURNING jobAppId
                """,
                user_id,
                f"synth://pipeline/{entry['batch_id']}/{entry['cv_index']}/cvSnapUrl",
            )

            if job_app_id is None:
                logger.error(
                    "No job postings found in DB! Cannot create Job Application placeholder."
                )
                return None

        # --- 4. Save ParsedCV ---
        parsed_json = parsed_cv.model_dump(mode="json")
        cv_parsed_id = await save_parsed_cv(
            job_app_id=job_app_id,
            raw_text=parsed_cv.rawText,
            parsed_json=parsed_json,
            parser_ver="synth-pipeline-v1",
        )

        # --- 5. Build Markdown + chunk + embed ---
        cv_markdown = convert_json_to_markdown(parsed_cv)
        global_context = extract_global_metadata(parsed_cv)
        chunk_payloads = process_document_to_chunks(cv_markdown, global_context)
        chunk_contents = [p["content"] for p in chunk_payloads]
        vectors = await embed_chunks(chunk_contents) if chunk_contents else []

        metadata_items = [
            {
                "cvParsedId": cv_parsed_id,
                "parserVer": "synth-pipeline-v1",
                "candidateName": full_name,
                "chunkingStrategy": "hybrid-structure-aware",
                "contextInjected": True,
                "globalContext": global_context,
                "markdownLength": len(cv_markdown),
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
                'SELECT u.userId FROM "user" u '
                "JOIN HR h ON h.userId = u.userId "
                "WHERE h.compId = $1 LIMIT 1",
                job.comp_id,
            )
            # Fetch LANGUAGE map {lang_code: lang_id}
            lang_rows = await conn.fetch("SELECT langId, langCode FROM LANGUAGE")
            lang_map = {r["langcode"].strip().lower(): r["langid"] for r in lang_rows}

            # Determine workLoc based on provId and workMode
            work_loc = None
            if job.work_mode.upper() in ("HYBRID", "ONSITE"):
                prov_map = {
                    "HANOI": "Hà Nội",
                    "TPHCM": "TP. Hồ Chí Minh",
                    "DANANG": "Đà Nẵng",
                    "HAIPHONG": "Hải Phòng",
                    "BACNINH": "Bắc Ninh",
                    "CANTHO": "Cần Thơ",
                    "LAOCAI": "Lào Cai",
                    "QUANGNINH": "Quảng Ninh",
                    "KHANHHOA": "Khánh Hòa",
                    "GIALAI": "Gia Lai",
                    "DONGNAI": "Đồng Nai",
                    "THANHHOA": "Thanh Hóa",
                    "HUE": "Huế",
                    "LAICHAU": "Lai Châu",
                    "DIENBIEN": "Điện Biên",
                    "SONLA": "Sơn La",
                    "LANGSON": "Lạng Sơn",
                    "HATINH": "Hà Tĩnh",
                    "CAOBANG": "Cao Bằng",
                    "TUYENQUANG": "Tuyên Quang",
                    "PHUTHO": "Phú Thọ",
                    "HUNGYEN": "Hưng Yên",
                    "NINHBINH": "Ninh Bình",
                    "QUANGTRI": "Quảng Trị",
                    "QUANGNGAI": "Quảng Ngãi",
                    "LAMDONG": "Lâm Đồng",
                    "DAKLAK": "Đắk Lắk",
                    "TAYNINH": "Tây Ninh",
                    "VINHLONG": "Vĩnh Long",
                    "DONGTHAP": "Đồng Tháp",
                    "CAMAU": "Cà Mau",
                    "ANGIANG": "An Giang",
                }
                work_loc = prov_map.get(job.prov_id.upper(), job.prov_id.title())
            else:
                work_loc = "Remote"

            # --- 2. Insert JOBPOSTING ---
            job_post_id = await conn.fetchval(
                """
                INSERT INTO JOBPOSTING (
                    compId, title, description,
                    minSalary, maxSalary, workLoc, workMode, provId, expAt
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW() + INTERVAL '30 days')
                RETURNING jobPostId
                """,
                job.comp_id,
                job.title,
                job.description,
                job.min_salary,
                job.max_salary,
                work_loc,
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
                lang_code = lang_req.get("lang_code", "en").strip().lower()
                lang_id = lang_map.get(lang_code)
                if not lang_id:
                    logger.warning(
                        f"Language code '{lang_code}' not found in LANGUAGE table, skipping."
                    )
                    continue
                try:
                    await conn.execute(
                        """
                        INSERT INTO JOB_LANG_REQUIREMENT (jobPostId, langId, reqType, minLevel)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (jobPostId, langId) DO NOTHING
                        """,
                        job_post_id,
                        lang_id,
                        lang_req.get("req_type", "PREFERRED"),
                        lang_req.get("min_level", "BASIC"),
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to insert language requirement {lang_req} for jobPostId={job_post_id}: {e}"
                    )

        if job.custom_skills:
            # Filter out custom skills that are already in the catalog (skill_id_map)
            filtered_custom_skills = [
                s for s in job.custom_skills if s.strip().lower() not in skill_id_map
            ]
            if filtered_custom_skills:
                try:
                    async with acquire_conn() as conn:
                        await embed_and_store_raw_skills(
                            entity_type="job",
                            entity_id=job_post_id,
                            unmatched_texts=filtered_custom_skills,
                            conn=conn,
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
