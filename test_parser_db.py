import asyncio
import json

from app.core.database import acquire_conn, db
from app.core.logging import logger
from app.services.cv_parser import get_last_parse_trace, parse_to_raw_and_json
from app.services.persistence import save_parsed_cv


async def setup_mock_data() -> int:
    """Create minimal relational records required by CVPARSED foreign keys."""
    mock_id = 9999
    logger.info("Ensuring mock relational data exists", extra={"jobAppId": mock_id})

    mock_queries = [
        """INSERT INTO "user" (userId, userName, pwd, fName, lName, email, prov, ward, street, role)
           VALUES ($1, 'mock_candidate', 'mock_pwd', 'Candidate', 'Mock', 'mock@test.com', 'HN', 'CG', '123 Test', 'CANDIDATE')
           ON CONFLICT (userId) DO NOTHING;""",
        """INSERT INTO CANDIDATE (userId)
           VALUES ($1)
           ON CONFLICT (userId) DO NOTHING;""",
        """INSERT INTO COMPANY (compId, compName, prov, ward, street)
           VALUES ($1, 'Mock AI Company', 'HN', 'CG', '123 Test')
           ON CONFLICT (compId) DO NOTHING;""",
        """INSERT INTO JOBPOSTING (jobPostId, title, description, expAt, compId)
           VALUES ($1, 'Mock AI Engineer', 'Mock Description', CURRENT_TIMESTAMP + INTERVAL '30 days', $1)
           ON CONFLICT (jobPostId) DO NOTHING;""",
        """INSERT INTO JOBAPPLICATION (jobAppId, candidateId, jobPostId, stat, cvSnapUrl)
           VALUES ($1, $1, $1, 'PENDING', 'http://mock-url.com/sample.pdf')
           ON CONFLICT (jobAppId) DO NOTHING;""",
    ]

    async with acquire_conn() as conn:
        for query in mock_queries:
            await conn.execute(query, mock_id)

    return mock_id


async def run_db_test():
    pdf_path = "sample.pdf"
    await db.connect()

    try:
        job_app_id = await setup_mock_data()

        with open(pdf_path, "rb") as file_obj:
            cv_bytes = file_obj.read()

        logger.info("Starting parser + database integration test")
        raw_text, parsed_json = await parse_to_raw_and_json(cv_bytes)
        parser_ver = parsed_json.get("parserVer", "unknown")
        parser_trace = get_last_parse_trace() or {}

        logger.info(
            "Persisting parsed CV",
            extra={
                "jobAppId": job_app_id,
                "parserVer": parser_ver,
                "fallbackPath": parser_trace.get("fallback_path"),
            },
        )
        await save_parsed_cv(job_app_id, raw_text, parsed_json, parser_ver)

        async with acquire_conn() as conn:
            row = await conn.fetchrow(
                "SELECT parsedJson FROM CVPARSED WHERE jobAppId = $1",
                job_app_id,
            )

        if row:
            saved_json = json.loads(row["parsedjson"])
            print("\n" + "=" * 60)
            print("LUU DATABASE THANH CONG")
            print(f"parserVer: {parser_ver}")
            print(f"fallbackPath: {parser_trace.get('fallback_path')}")
            print("skills:")
            print(
                json.dumps(saved_json.get("skills", []), indent=2, ensure_ascii=False)
            )
            print("=" * 60)
    except Exception:
        parser_trace = get_last_parse_trace() or {}
        if parser_trace.get("fallback_path"):
            print(f"fallbackPath: {parser_trace.get('fallback_path')}")
        logger.exception("Parser database integration test failed")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(run_db_test())
