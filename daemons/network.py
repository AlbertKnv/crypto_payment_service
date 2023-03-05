import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

import zmq
import zmq.asyncio
import aiohttp
import redis.asyncio as redis
import asyncpg
from tenacity import retry, stop_after_attempt, wait_fixed

from settings import settings
from daemons.utils import BaseDaemon
from database.sql import Queries
from api_server.schemas import CallbackBody


class NetworkDaemon(BaseDaemon):
    def __init__(self):
        super().__init__(need_postgres=True, need_redis=True, need_rpc=True)
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_sock = self.zmq_context.socket(zmq.SUB)
        self.zmq_sock.setsockopt(zmq.RCVHWM, 0)
        self.zmq_sock.setsockopt(zmq.RCVTIMEO, 30000)
        self.zmq_sock.setsockopt_string(zmq.SUBSCRIBE, "rawtx")
        self.zmq_sock.setsockopt_string(zmq.SUBSCRIBE, "hashblock")
        self.rpc_session: aiohttp.ClientSession = None
        self.callback_session: aiohttp.ClientSession = None
        self.rpc_semafore = asyncio.Semaphore(10)
        self.callback_semafore = asyncio.Semaphore(10)
        self.cache_conn: redis.Redis = None
        self.block_queue = asyncio.Queue()

    async def callback_worker(self, payment: asyncpg.Record, confs: int = 0):
        callback_body = CallbackBody(**payment, confirmations=confs)
        payload = callback_body.json()

        async with self.callback_semafore:
            stop_flag = False
            async with self.callback_session.post(
                settings.CALLBACK_URL,
                data=payload
            ) as response:
                try:
                    response_json = await response.json(content_type=None)
                    stop_flag = response_json["stop"]
                except Exception:
                    pass

            if stop_flag is True:
                db_conn = await self.get_db()
                await db_conn.execute(
                    Queries.update_is_cb_active,
                    payment["id"]
                )
                await db_conn.close()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def rpc_request(self, method_name: str, params: list[Any] = None):
        async with self.rpc_semafore:
            async with self.rpc_session.post(
                settings.RPC_PROVIDER,
                json={
                    "jsonrpc": "1.0",
                    "id": "0",
                    "method": method_name,
                    "params": params,
                },
            ) as response:
                resp_json = await response.json()
                return resp_json["result"]

    async def forward_transaction(self, payment: asyncpg.Record):
        result = await self.rpc_request("estimatesmartfee", [5])
        feerate = result['feerate'] if result else 0.0001
        mining_fee = Decimal(feerate * 200 / 1024)
        inputs = [{"txid": payment["txid"], "vout": payment["vout"]}]
        outputs = [{settings.ADDRESS: f"{payment['amount'] - mining_fee:.8f}"}]

        db_conn = await self.get_db()
        key = await db_conn.fetchval(
            Queries.select_priv_key,
            payment["address"]
        )
        key_bytes = bytes.fromhex(key)
        key_wif = settings.CIPHER.decrypt(key_bytes).decode(encoding="utf-8")

        tx_hex = await self.rpc_request("createrawtransaction",
                                        [inputs, outputs])
        signed_tx = await self.rpc_request("signrawtransactionwithkey",
                                           [tx_hex, [key_wif], None, 'ALL'])
        txid = await self.rpc_request("sendrawtransaction",
                                      [signed_tx["hex"]])

        await db_conn.execute(Queries.update_forward_txid, txid, payment["id"])
        await db_conn.close()

    async def process_payment(self, txid: str, vout: int, amount: Decimal,
                              address: str, order_id: str):
        db_conn = await self.get_db()
        try:
            payment = await db_conn.fetchrow(
                Queries.insert_payment,
                txid, vout, amount, address, order_id
            )
            self.add_task(self.callback_worker(payment))
            self.add_task(self.forward_transaction(payment))
        except asyncpg.exceptions.UniqueViolationError:
            pass

        await db_conn.close()

    async def raw_tx_worker(self, body: bytes):
        tx_data = await self.rpc_request("decoderawtransaction", [body.hex()])
        for vout in tx_data["vout"]:
            script_pub_key = vout.get("scriptPubKey")
            if script_pub_key:
                address = script_pub_key.get("address")
                if address:
                    order_id_bytes = await self.cache_conn.get(address)
                    if order_id_bytes:
                        await self.process_payment(
                            tx_data["txid"],
                            int(vout["n"]),
                            Decimal(f"{vout['value']:.8f}"),
                            address,
                            order_id_bytes.decode()
                        )

    async def hash_block_worker(self):
        while True:
            await self.block_queue.get()
            dt_expire = datetime.now(tz=timezone.utc) - timedelta(days=14)
            expired_payments = []
            callback_tasks = []

            db_conn = await self.get_db()
            payments = await db_conn.fetch(Queries.select_active_payments)

            for payment in payments:
                if payment["dt_created"] < dt_expire:
                    expired_payments.append((payment["id"], ))
                    continue

                tx_data = await self.rpc_request("getrawtransaction",
                                                 [payment["txid"], True])
                confs = tx_data.get("confirmations", None)
                if confs:
                    callback_tasks.append(asyncio.create_task(
                        self.callback_worker(payment, confs)))

            await db_conn.executemany(
                Queries.update_is_cb_active,
                expired_payments
            )
            await db_conn.close()

            if callback_tasks:
                await asyncio.wait(callback_tasks)

    async def handler(self):
        self.zmq_sock.connect(settings.ZMQ_SOCKET)
        self.rpc_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=15),
            auth=aiohttp.BasicAuth(settings.RPC_USER, settings.RPC_PASSWORD),
        )
        self.callback_session = aiohttp.ClientSession(
            headers={"content-type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=15),
        )
        self.cache_conn = redis.Redis(host=settings.REDIS_HOST)
        self.add_task(self.hash_block_worker())

        try:
            while True:
                try:
                    topic, body, _ = await self.zmq_sock.recv_multipart()
                except zmq.Again:
                    self.zmq_sock.connect(settings.ZMQ_SOCKET)
                    continue

                if topic == b"rawtx":
                    self.add_task(self.raw_tx_worker(body))
                elif topic == b"hashblock":
                    self.block_queue.put_nowait(body)

        except asyncio.CancelledError:
            self.zmq_sock.close()
            await asyncio.gather([
                self.rpc_session.close(),
                self.callback_session.close(),
                self.cache_conn.close()
            ])


if __name__ == "__main__":
    daemon = NetworkDaemon()
    daemon.start()
