import asyncio
import sys
from pathlib import Path

import dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
dotenv.load_dotenv(Path(__file__).parent.parent / ".env")

from app.core.database import acquire_conn, db


async def main():
    await db.connect()
    try:
        async with acquire_conn() as conn:
            # Test fuzzy query
            # Count rows
            cnt_job = await conn.fetchval("SELECT COUNT(*) FROM JOB_SKILL_RAW")
            cnt_cand = await conn.fetchval("SELECT COUNT(*) FROM CANDIDATE_SKILL_RAW")
            cnt_lang = await conn.fetchval("SELECT COUNT(*) FROM JOB_LANG_REQUIREMENT")
            print(f"JOB_SKILL_RAW count: {cnt_job}")
            print(f"CANDIDATE_SKILL_RAW count: {cnt_cand}")
            print(f"JOB_LANG_REQUIREMENT count: {cnt_lang}")

            r = await conn.fetch("""
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
                LIMIT 5
            """)
            print("Query successful. Sample rows:")
            for row in r:
                print(dict(row))
    except Exception as e:
        print("Error executing query:", e)
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
