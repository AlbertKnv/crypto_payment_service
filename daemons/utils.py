import sys
import logging
import asyncio
import signal
from typing import Coroutine

import asyncpg
import redis.asyncio as redis
import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed

from settings import settings


logging.basicConfig(
    stream=sys.stdout,
    format="%(asctime)s %(filename)s:%(lineno)d %(levelname)s %(message)s",
    level=logging.ERROR
)
base_retry = retry(stop=stop_after_attempt(5), wait=wait_fixed(2),
                   reraise=True)


class BaseDaemon:
    def __init__(
        self,
        need_postgres: bool = False,
        need_redis: bool = False,
        need_rpc: bool = False
    ):
        self.need_postgres = need_postgres
        self.need_redis = need_redis
        self.need_rpc = need_rpc
        self.tasks = set()

    def add_task(self, coro: Coroutine):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.task_result_handler)

    def task_result_handler(self, task: asyncio.Task):
        self.tasks.discard(task)

        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            logging.exception("Uncatched error -> exiting")
            sys.exit(1)

    async def handler():
        pass

    def start(self):
        asyncio.run(self.astart())

    async def astart(self):
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, self.stop)

        coros = []
        if self.need_postgres:
            coros.append(self.wait_for_postgres())
        if self.need_redis:
            coros.append(self.wait_for_redis())
        if self.need_rpc:
            coros.append(self.wait_for_rpc())

        await asyncio.gather(*coros)

        await self.handler()

    def stop(self):
        self.add_task(self.astop())

    async def astop(self):
        tasks = set()
        current_task = asyncio.current_task()
        for task in asyncio.all_tasks():
            if task is not current_task:
                task.cancel()
                tasks.add(task)

        await asyncio.gather(*tasks)

    async def get_db(self):
        db_conn = await asyncpg.connect(dsn=settings.DATABASE_URI)
        return db_conn

    @staticmethod
    @base_retry
    async def wait_for_postgres():
        db_conn = await asyncpg.connect(dsn=settings.DATABASE_URI)
        await db_conn.execute("select * from addresses limit 1")
        await db_conn.close()

    @staticmethod
    @base_retry
    async def wait_for_redis():
        redis_conn = redis.Redis(host=settings.REDIS_HOST)
        await redis_conn.ping()
        await redis_conn.close()

    @staticmethod
    @base_retry
    async def wait_for_rpc():
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            auth=aiohttp.BasicAuth(settings.RPC_USER,
                                   settings.RPC_PASSWORD)) as session:
            async with session.post(
                settings.RPC_PROVIDER,
                json={
                    "jsonrpc": "1.0",
                    "id": "0",
                    "method": "getblockchaininfo",
                },
            ) as response:
                if response.status == 200:
                    resp_json = await response.json()
                    if not resp_json["result"]["initialblockdownload"]:
                        return

                raise Exception("rpc is not ready")
