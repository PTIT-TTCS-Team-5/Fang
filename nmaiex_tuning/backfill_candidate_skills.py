"""nmaiex_tuning/backfill_candidate_skills.py — Script to backfill Candidate Skills (Tier 1 & Tier 2).

Reads all parsed JSONs from CVPARSED table, performs exact case-insensitive matching
against SKILL table catalog, and stores mismatched skills into CANDIDATE_SKILL_RAW using pgvector.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

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
logger = logging.getLogger("backfill_skills")


# --- Monkey Patching Embedding Service to use 9Router ---
async def embed_chunks_9router(
    chunks: list[str],
    dimensions: int | None = None,
) -> list[list[float]]:
    """Monkey-patched embed_chunks that uses 9Router API proxy to bypass original API quotas."""
    if not chunks:
        return []

    import httpx

    from app.core.config import settings
    from synthetic_data.config import NINE_ROUTER_KEY, NINE_ROUTER_URL

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
                # Truncate to effective_dims to match pgvector expected size
                vectors.append(v[:effective_dims])

    if len(vectors) != len(normalized_chunks):
        raise RuntimeError(
            f"9Router returned {len(vectors)} vectors for {len(normalized_chunks)} chunks."
        )

    return vectors


import app.services.embedding
import app.services.nmaiex_mapper_service

app.services.embedding.embed_chunks = embed_chunks_9router
app.services.nmaiex_mapper_service.embed_chunks = embed_chunks_9router

from app.core.database import acquire_conn, db
from app.services.nmaiex_mapper_service import embed_and_store_raw_skills
from synthetic_data.db_writer import fetch_skill_id_map


async def backfill():
    logger.info("=== STARTING CANDIDATE SKILLS BACKFILL ===")

    # 1. Fetch Skill ID Map from Catalog
    skill_map = await fetch_skill_id_map()
    logger.info(f"Loaded {len(skill_map)} skills from SKILL catalog.")

    async with acquire_conn() as conn:
        # 2. Get all parsed CVs
        logger.info("Fetching parsed CV records from CVPARSED...")
        cv_rows = await conn.fetch("""
            SELECT cv.cvParsedId, cv.jobAppId, cv.parsedJson, ja.candidateId
            FROM CVPARSED cv
            JOIN JOBAPPLICATION ja ON cv.jobAppId = ja.jobAppId
            """)
        logger.info(f"Found {len(cv_rows)} records in CVPARSED.")

        matched_count = 0
        unmatched_count = 0
        processed_candidates = 0

        for row in cv_rows:
            cv_parsed_id = row["cvparsedid"]
            cand_id = row["candidateid"]
            job_app_id = row["jobappid"]
            parsed_json_str = row["parsedjson"]

            if not parsed_json_str:
                logger.warning(
                    f"Empty parsedJson for cvParsedId={cv_parsed_id}, skipping."
                )
                continue

            try:
                if isinstance(parsed_json_str, str):
                    parsed_cv = json.loads(parsed_json_str)
                else:
                    parsed_cv = parsed_json_str  # already parsed dict by asyncpg
            except Exception as e:
                logger.error(f"Failed to parse JSON for cvParsedId={cv_parsed_id}: {e}")
                continue

            skills = parsed_cv.get("skills", [])
            if not skills:
                logger.debug(
                    f"No skills found in parsed CV for candidate_id={cand_id}, skipping."
                )
                continue

            matched_ids = []
            unmatched_texts = []

            # 3. Exact String Matching (Case-Insensitive)
            for skill_name in skills:
                clean_name = skill_name.strip().lower()
                if clean_name in skill_map:
                    matched_ids.append(skill_map[clean_name])
                else:
                    unmatched_texts.append(skill_name.strip())

            # 4. Clear and Insert Matched Skills (Tầng 1)
            await conn.execute("DELETE FROM CANDIDATESKILL WHERE userId = $1", cand_id)
            for skill_id in matched_ids:
                await conn.execute(
                    """
                    INSERT INTO CANDIDATESKILL (userId, skillId)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    cand_id,
                    skill_id,
                )

            # 5. Clear and Insert Raw Skills (Tầng 2)
            await conn.execute(
                "DELETE FROM CANDIDATE_SKILL_RAW WHERE candId = $1", cand_id
            )
            if unmatched_texts:
                # Calls FANG's embedded mapping fallback to compute embeddings and save in DB
                await embed_and_store_raw_skills(
                    entity_type="candidate",
                    entity_id=cand_id,
                    unmatched_texts=unmatched_texts,
                    conn=conn,
                )

            matched_count += len(matched_ids)
            unmatched_count += len(unmatched_texts)
            processed_candidates += 1

            if processed_candidates % 50 == 0:
                logger.info(
                    f"Processed {processed_candidates}/{len(cv_rows)} candidates..."
                )

        logger.info("=== BACKFILL COMPLETED ===")
        logger.info(f"Successfully backfilled {processed_candidates} candidates.")
        logger.info(f"  - Total Matched Skills (Tier 1): {matched_count}")
        logger.info(f"  - Total Unmatched Skills (Tier 2): {unmatched_count}")


async def main():
    await db.connect()
    try:
        await backfill()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
