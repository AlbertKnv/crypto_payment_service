import asyncio

import redis.asyncio as redis

from settings import settings
from daemons.utils import BaseDaemon
from database.sql import Queries


class CacheWarmer(BaseDaemon):
    def __init__(self):
        super().__init__(need_postgres=True, need_redis=True)
        self.cache_semafore = asyncio.Semaphore(50)
        self.cache_conn: redis.Redis = None

    async def set_value(self, address: str, order_id: str):
        async with self.cache_semafore:
            await self.cache_conn.set(address, order_id)

    async def handler(self):
        self.cache_conn = redis.Redis(host=settings.REDIS_HOST)
        db_conn = await self.get_db()

        try:
            async with db_conn.transaction():
                async for record in db_conn.cursor(
                    Queries.select_address_order_id
                ):
                    self.add_task(
                        self.set_value(record["address"], record["order_id"])
                    )
            if self.tasks:
                await asyncio.wait(self.tasks)

        except asyncio.CancelledError:
            await asyncio.gather([
                    db_conn.close(),
                    self.cache_conn.close()
                ])


if __name__ == "__main__":
    daemon = CacheWarmer()
    daemon.start()
