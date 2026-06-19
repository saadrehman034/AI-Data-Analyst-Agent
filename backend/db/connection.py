import asyncpg
import logging
from typing import Optional
from contextlib import asynccontextmanager

from backend.config import settings

logger = logging.getLogger(__name__)

_app_pool: Optional[asyncpg.Pool] = None
_analyst_pool: Optional[asyncpg.Pool] = None


async def create_app_pool() -> asyncpg.Pool:
    global _app_pool
    _app_pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        command_timeout=30,
    )
    logger.info("App database pool created")
    return _app_pool


async def create_analyst_pool() -> asyncpg.Pool:
    global _analyst_pool
    _analyst_pool = await asyncpg.create_pool(
        dsn=settings.analyst_db_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        command_timeout=60,
    )
    logger.info("Analyst database pool created")
    return _analyst_pool


async def close_pools():
    global _app_pool, _analyst_pool
    if _app_pool:
        await _app_pool.close()
        logger.info("App database pool closed")
    if _analyst_pool:
        await _analyst_pool.close()
        logger.info("Analyst database pool closed")


def get_app_pool() -> asyncpg.Pool:
    if _app_pool is None:
        raise RuntimeError("App database pool not initialised. Call create_app_pool() first.")
    return _app_pool


def get_analyst_pool() -> asyncpg.Pool:
    if _analyst_pool is None:
        raise RuntimeError("Analyst database pool not initialised. Call create_analyst_pool() first.")
    return _analyst_pool


@asynccontextmanager
async def get_app_connection():
    pool = get_app_pool()
    async with pool.acquire() as conn:
        yield conn


@asynccontextmanager
async def get_analyst_connection():
    pool = get_analyst_pool()
    async with pool.acquire() as conn:
        yield conn


async def check_app_db_health() -> bool:
    try:
        async with get_app_connection() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"App DB health check failed: {e}")
        return False


async def check_analyst_db_health() -> bool:
    try:
        async with get_analyst_connection() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Analyst DB health check failed: {e}")
        return False
