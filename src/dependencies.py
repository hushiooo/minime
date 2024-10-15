from typing import Annotated, AsyncGenerator

from asyncpg import Connection, Pool
from fastapi import Depends
from redis.asyncio import Redis


async def get_db_pool() -> AsyncGenerator[Pool, None]:
    from src.app import app

    yield app.state.db_pool


async def get_db_conn(
    pool: Annotated[Pool, Depends(get_db_pool)],
) -> AsyncGenerator[Connection, None]:
    async with pool.acquire() as conn:
        yield conn


async def get_redis() -> AsyncGenerator[Redis, None]:
    from src.app import app

    yield app.state.redis
