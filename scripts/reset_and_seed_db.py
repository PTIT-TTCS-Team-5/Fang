import argparse
import asyncio
import sys
from pathlib import Path

# Thêm thư mục root của project vào sys.path để có thể import package 'app'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import acquire_conn, db
from app.core.logging import logger
from app.core.nmaiex_config import nmaiex_settings

MOCK_CLOUDINARY_URL = (
    "https://res.cloudinary.com/dfwkw1guc/raw/upload/v1777525993/ttcs/sample"
)
TARGET_DB_NAME = "micareer_lite_db"


def inject_embedding_dims(sql: str) -> str:
    """Replace SQL placeholder strings with actual embedding dimensions from config.

    Placeholders:
        __TTCS_EMBEDDING_DIM__     -> settings.embedding_dim (from .env)
        __NMAIEX_SKILL_EMBEDDING_DIM__ -> nmaiex_settings.nmaiex_skill_embedding_dims (from .env.nmaiex)
    """
    sql = sql.replace("__TTCS_EMBEDDING_DIM__", str(settings.embedding_dim))
    sql = sql.replace(
        "__NMAIEX_SKILL_EMBEDDING_DIM__",
        str(nmaiex_settings.nmaiex_skill_embedding_dims),
    )
    return sql


async def run_sql_file(conn, file_path: str):
    logger.info(f"Executing SQL file: {file_path}")
    sql = Path(file_path).read_text(encoding="utf-8")
    sql = inject_embedding_dims(sql)  # [NMAIex] Infrastructure as Code: inject dims
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
                base_dir / "seed_data.sql",  # legacy: 18 candidates + 5 companies + jobs + apps (for CHAT_FULL_CV testing)
            ]

            for sql_file in sql_files:
                if sql_file.exists():
                    await run_sql_file(conn, str(sql_file))
                else:
                    logger.error(
                        f"SQL file not found (make sure you are running from project root): {sql_file}"
                    )

            logger.info("DB Reset and Seed completed successfully!")
            logger.info(
                "Infrastructure: 15 Companies + 15 HRs ready for synthetic pipeline."
            )
    except Exception as e:
        logger.error(f"An error occurred during DB initialization: {str(e)}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
