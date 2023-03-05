import asyncio

import asyncpg
from redis.asyncio import Redis

from settings import settings


class Database():
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        for idx in range(4):
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=settings.DATABASE_URI)
                break
            except Exception:
                if idx == 3:
                    raise
                await asyncio.sleep(idx)

    async def disconnect(self):
        await self.pool.close()


database = Database()
cache = Redis(host=settings.REDIS_HOST)
