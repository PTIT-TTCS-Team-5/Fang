from contextlib import asynccontextmanager

import asyncpg

from app.core.config import settings
from app.core.logging import logger


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        logger.info("Connecting to PostgreSQL pool...")
        self.pool = await asyncpg.create_pool(
            dsn=settings.database_url, min_size=2, max_size=10
        )
        logger.info("PostgreSQL pool created.")

    async def disconnect(self):
        if self.pool:
            logger.info("Closing PostgreSQL pool...")
            await self.pool.close()
            logger.info("PostgreSQL pool closed.")


db = Database()


@asynccontextmanager
async def acquire_conn():
    """Async context manager for db connections."""
    if not db.pool:
        raise RuntimeError("Database pool is not initialized")
    async with db.pool.acquire() as connection:
        yield connection
