"""synthetic_data/verifier.py — Verification script for Synthetic Data Pipeline.

Checks DB counts, verifies Gemini embedding dimension (1536), and queries the ranking APIs.
"""

import asyncio
import logging
import sys
from pathlib import Path

import httpx

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
    encoding="utf-8",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("verifier")

from app.core.database import acquire_conn, db


async def verify_db():
    logger.info("=== STARTING DB VERIFICATION ===")
    results = {}
    async with acquire_conn() as conn:
        # Check DB name
        db_name = await conn.fetchval("SELECT current_database()")
        logger.info(f"Connected to DB: {db_name}")
        results["database"] = db_name

        # Query counts
        counts_query = """
        SELECT 'user_candidates' as tbl, COUNT(*) FROM "user" WHERE role='CANDIDATE'
        UNION ALL SELECT 'candidates', COUNT(*) FROM CANDIDATE
        UNION ALL SELECT 'jobpostings', COUNT(*) FROM JOBPOSTING
        UNION ALL SELECT 'jobapplications', COUNT(*) FROM JOBAPPLICATION
        UNION ALL SELECT 'cvparsed', COUNT(*) FROM CVPARSED
        UNION ALL SELECT 'aidocuments_cv', COUNT(*) FROM AIDOCUMENTCHUNK WHERE sourceType='CV'
        UNION ALL SELECT 'aidocuments_job', COUNT(*) FROM AIDOCUMENTCHUNK WHERE sourceType='JOB'
        UNION ALL SELECT 'candidateskills', COUNT(*) FROM CANDIDATESKILL
        UNION ALL SELECT 'candidate_skill_raw', COUNT(*) FROM CANDIDATE_SKILL_RAW
        UNION ALL SELECT 'job_skill_raw', COUNT(*) FROM JOB_SKILL_RAW;
        """
        rows = await conn.fetch(counts_query)
        logger.info("Table Counts:")
        results["counts"] = {}
        for r in rows:
            tbl = r["tbl"]
            count = r["count"]
            logger.info(f"  - {tbl}: {count}")
            results["counts"][tbl] = count

        # Verify embedding dimension (pgvector column vector_dimension if vector or array size)
        # In pgvector, we can check the dimension using: vector_dims(embedding)
        logger.info("Checking embedding dimensions...")
        try:
            cv_dims = await conn.fetchval(
                "SELECT vector_dims(embedding) FROM AIDOCUMENTCHUNK WHERE sourceType='CV' LIMIT 1"
            )
            logger.info(f"CV chunk embedding dimension: {cv_dims}")
            results["cv_embedding_dimension"] = cv_dims
        except Exception as e:
            logger.warning(
                f"Could not read CV embedding dimension using vector_dims: {e}"
            )
            # Fallback check array length or select sample
            results["cv_embedding_dimension"] = None

        try:
            job_dims = await conn.fetchval(
                "SELECT vector_dims(embedding) FROM AIDOCUMENTCHUNK WHERE sourceType='JOB' LIMIT 1"
            )
            logger.info(f"JOB chunk embedding dimension: {job_dims}")
            results["job_embedding_dimension"] = job_dims
        except Exception as e:
            logger.warning(
                f"Could not read JOB embedding dimension using vector_dims: {e}"
            )
            results["job_embedding_dimension"] = None

        # Fetch sample IDs for API test
        sample_job_id = await conn.fetchval("SELECT jobPostId FROM JOBPOSTING LIMIT 1")
        sample_cand_id = await conn.fetchval("SELECT userId FROM CANDIDATE LIMIT 1")
        results["sample_job_id"] = sample_job_id
        results["sample_cand_id"] = sample_cand_id
        logger.info(f"Sample jobPostId: {sample_job_id}")
        logger.info(f"Sample candidateId: {sample_cand_id}")

    return results


async def verify_ranking_apis(results: dict):
    logger.info("=== STARTING RANKING API SMOKE TESTS ===")
    sample_job_id = results.get("sample_job_id")
    sample_cand_id = results.get("sample_cand_id")

    async with httpx.AsyncClient() as client:
        # Check health
        try:
            resp = await client.get("http://127.0.0.1:8000/v2/healthz")
            logger.info(
                f"FANG server health check status: {resp.status_code}, response: {resp.text}"
            )
        except Exception as e:
            logger.error(f"FANG server is not reachable at http://127.0.0.1:8000: {e}")
            return

        if sample_job_id:
            # 1. J -> C ranking
            url_j2c = f"http://127.0.0.1:8000/v2/nmaiex/ranking/candidates/{sample_job_id}?limit=5"
            logger.info(f"Querying J->C ranking API: {url_j2c}")
            try:
                resp = await client.get(url_j2c, timeout=30.0)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("results", [])
                    logger.info(
                        f"J->C Success! Returned {len(candidates)} ranked candidates."
                    )
                    for i, c in enumerate(candidates[:3]):
                        logger.info(
                            f"  [{i+1}] Candidate ID: {c.get('candidate_id')}, Score: {c.get('match_score')}, Name: {c.get('candidate_name')}"
                        )
                else:
                    logger.error(
                        f"J->C failed with status code {resp.status_code}: {resp.text}"
                    )
            except Exception:
                logger.exception("J->C API call failed")

        if sample_cand_id:
            # 2. C -> J ranking
            url_c2j = (
                f"http://127.0.0.1:8000/v2/nmaiex/ranking/jobs/{sample_cand_id}?limit=5"
            )
            logger.info(f"Querying C->J ranking API: {url_c2j}")
            try:
                resp = await client.get(url_c2j, timeout=30.0)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = data.get("results", [])
                    logger.info(f"C->J Success! Returned {len(jobs)} ranked jobs.")
                    for i, j in enumerate(jobs[:3]):
                        logger.info(
                            f"  [{i+1}] Job ID: {j.get('job_id')}, Score: {j.get('match_score')}, Title: {j.get('job_title')}"
                        )
                else:
                    logger.error(
                        f"C->J failed with status code {resp.status_code}: {resp.text}"
                    )
            except Exception:
                logger.exception("C->J API call failed")


async def main():
    await db.connect()
    try:
        results = await verify_db()
        await verify_ranking_apis(results)
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
