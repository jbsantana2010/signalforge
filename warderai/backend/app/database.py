import asyncpg
from app.config import settings

pool: asyncpg.Pool | None = None


async def create_pool():
    global pool
    pool = await asyncpg.create_pool(settings.asyncpg_url, min_size=2, max_size=10)


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None


async def get_db():
    """FastAPI dependency that yields an asyncpg connection from the pool."""
    async with pool.acquire() as conn:
        yield conn
