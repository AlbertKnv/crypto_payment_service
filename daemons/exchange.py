import asyncio

import aiohttp
import redis.asyncio as redis

from settings import settings
from daemons.utils import BaseDaemon, base_retry


class BinanceDaemon(BaseDaemon):
    def __init__(self):
        super().__init__(need_redis=True)
        self.url = "https://api.binance.us/api/v3/ticker/price"
        self.params = {"symbol": "BTCUSD"}
        self.cache_conn: redis.Redis = None
        self.binance_session: aiohttp.ClientSession = None

    @base_retry
    async def fetch_rate(self):
        async with self.binance_session.get(
            self.url, params=self.params
        ) as resp:
            if resp.status == 200:
                resp_json = await resp.json()
                await self.cache_conn.set("BTCUSD", resp_json["price"])
            else:
                raise Exception(f"http status {resp.status}")

    async def handler(self):
        self.cache_conn = redis.Redis(host=settings.REDIS_HOST)
        self.binance_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15)
        )

        try:
            while True:
                await self.fetch_rate()
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            await self.cache_conn.close()


if __name__ == "__main__":
    daemon = BinanceDaemon()
    daemon.start()
