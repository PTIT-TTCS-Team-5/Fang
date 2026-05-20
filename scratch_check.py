import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from app.core.database import acquire_conn, db


async def main():
    await db.connect()
    async with acquire_conn() as conn:
        rows = await conn.fetch("""
            SELECT u.userId, u.userName, u.role, c.bio, cv.parsedJson->'summary' as cv_summary
            FROM "user" u
            LEFT JOIN CANDIDATE c ON u.userId = c.userId
            LEFT JOIN JOBAPPLICATION ja ON u.userId = ja.candidateId
            LEFT JOIN CVPARSED cv ON ja.jobAppId = cv.jobAppId
            WHERE u.userId BETWEEN 50 AND 70
        """)
        for r in rows:
            print(
                f"userId={r['userid']} userName={r['username']} role={r['role']} bio={r['bio']} summary={r['cv_summary']}"
            )
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
