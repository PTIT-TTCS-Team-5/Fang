import argparse
import asyncio
import sys
from pathlib import Path

# Thêm thư mục root của project vào sys.path để có thể import package 'app'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import acquire_conn, db
from app.core.logging import logger

MOCK_CLOUDINARY_URL = (
    "https://res.cloudinary.com/dfwkw1guc/image/upload/v1775987977/sample_ml2jzo.pdf"
)
TARGET_DB_NAME = "micareer_lite_db"


async def run_sql_file(conn, file_path: str):
    logger.info(f"Executing SQL file: {file_path}")
    sql = Path(file_path).read_text(encoding="utf-8")
    await conn.execute(sql)


async def reset_schema(conn):
    # Verify we are on target DB to prevent catastrophic accidental drops
    db_name = await conn.fetchval("SELECT current_database()")
    if db_name != TARGET_DB_NAME:
        raise Exception(
            f"BẢO VỆ CSDL: Không được phép drop schema trên DB '{db_name}'. Chỉ được thao tác với '{TARGET_DB_NAME}'."
        )

    logger.warning("Dropping all tables in the database (public schema)!")
    sql = """
    DROP SCHEMA public CASCADE;
    CREATE SCHEMA public;
    GRANT ALL ON SCHEMA public TO public;
    """
    await conn.execute(sql)


async def main():
    parser = argparse.ArgumentParser(description="Reset and seed DB for testing")
    parser.set_defaults(reset=True)
    parser.add_argument(
        "--reset",
        dest="reset",
        action="store_true",
        help="Drop entire database schema before seeding (default behavior)",
    )
    parser.add_argument(
        "--no-reset",
        dest="reset",
        action="store_false",
        help="Do not drop schema; run SQL files as-is",
    )
    args = parser.parse_args()

    logger.info("Initializing DB connection...")
    await db.connect()

    try:
        async with acquire_conn() as conn:
            if args.reset:
                await reset_schema(conn)

            # Define SQL execution order
            base_dir = Path("database")
            sql_files = [
                base_dir / "schema_web_core.sql",
                base_dir / "schema_ai_core.sql",
                base_dir / "root_data.sql",
                base_dir / "seed_data.sql",
            ]

            for sql_file in sql_files:
                if sql_file.exists():
                    await run_sql_file(conn, str(sql_file))
                else:
                    logger.error(
                        f"SQL file not found (make sure you are running from project root): {sql_file}"
                    )

            logger.info(
                "Updating the Cloudinary URL for Nguyễn Hải Hưng's test job application"
            )

            # Find the jobAppId for Nguyễn Hải Hưng applying to the AI position
            fetch_id_sql = """
            SELECT ja.jobAppId 
            FROM JOBAPPLICATION ja
            JOIN "user" u ON ja.candidateId = u.userId
            JOIN JOBPOSTING jp ON ja.jobPostId = jp.jobPostId
            WHERE u.userName = 'nguyenhaihung' AND jp.title LIKE '%AI Engineer%'
            LIMIT 1;
            """
            target_job_app_id = await conn.fetchval(fetch_id_sql)

            if target_job_app_id:
                await conn.execute(
                    "UPDATE JOBAPPLICATION SET cvSnapUrl = $1 WHERE jobAppId = $2",
                    MOCK_CLOUDINARY_URL,
                    target_job_app_id,
                )
                logger.info(
                    f"Successfully updated jobAppId = {target_job_app_id} with mock Cloudinary URL"
                )

                # Write to a quick hint file so the user knows what ID to test with in Postman
                logger.info(
                    f"--> LƯU Ý: Vui lòng sử dụng jobAppId: {target_job_app_id} để test trên Postman / .http"
                )
            else:
                logger.warning(
                    "No JOBAPPLICATION for 'nguyenhaihung' applying to 'AI Engineer' was found. Fallback to updating jobAppId = 1."
                )
                await conn.execute(
                    "UPDATE JOBAPPLICATION SET cvSnapUrl = $1 WHERE jobAppId = 1",
                    MOCK_CLOUDINARY_URL,
                )

            logger.info("DB Reset and Seed completed successfully!")
    except Exception as e:
        logger.error(f"An error occurred during DB initialization: {str(e)}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
