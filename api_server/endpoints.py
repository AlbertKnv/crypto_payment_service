import asyncio
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
from bitcoinaddress import Wallet
from asyncpg.exceptions import UniqueViolationError

from settings import settings
from database.sql import Queries
from api_server.deps import database, cache
from api_server import schemas


callback_router = APIRouter()


@callback_router.post(
    "CALLBACK_URL_from_settings",
    response_model=schemas.CallbackResponse
)
async def callback_notification(body: schemas.CallbackBody) -> Any:
    pass


router = APIRouter()


@router.post(
    "",
    response_model=schemas.AddressOut,
    callbacks=callback_router.routes
)
async def create_address(body: schemas.AddressIn) -> Any:
    order_id = body.order_id

    wallet = Wallet()
    if settings.TESTNET:
        address = wallet.address.testnet.pubaddrtb1_P2WPKH
        priv_key = wallet.key.testnet.wifc
    else:
        address = wallet.address.mainnet.pubaddrbc1_P2WPKH
        priv_key = wallet.key.mainnet.wifc

    priv_key = settings.CIPHER.encrypt(priv_key.encode(encoding="utf-8")).hex()

    async with database.pool.acquire() as connection:
        async with connection.transaction():
            try:
                coros = (
                    connection.fetchrow(
                        Queries.insert_address,
                        address, priv_key, order_id
                    ),
                    cache.set(address, order_id),
                    cache.get("BTCUSD")
                )

                payment, _, exchange_rate = await asyncio.gather(*coros)

                amount = None
                if body.usd_amount:
                    amount = body.usd_amount / Decimal(exchange_rate.decode())
                    amount = amount.quantize(Decimal("0.00000000"))

            except UniqueViolationError:
                raise HTTPException(status_code=400, detail="Already exists")

            return schemas.AddressOut(**payment, amount=amount)


@router.get(
    "/{address}",
    response_model=schemas.AddressOut,
)
async def read_address(address: str) -> Any:
    async with database.pool.acquire() as connection:
        payment = await connection.fetchrow(Queries.select_address, address)
        if payment:
            return payment

    raise HTTPException(404, detail="Address not found")


@router.get(
    "",
    response_model=schemas.AddressOut,
)
async def find_address(order_id: str) -> Any:
    async with database.pool.acquire() as connection:
        payment = await connection.fetchrow(Queries.find_address, order_id)
        if payment:
            return payment

    raise HTTPException(404, detail="Address not found")


@router.get(
    "/{address}/payments",
    response_model=list[schemas.PaymentOut]
)
async def read_address_payments(address: str) -> Any:
    async with database.pool.acquire() as connection:
        payments = await connection.fetch(Queries.select_address_payments,
                                          address)
        if payments:
            return payments

    raise HTTPException(404, detail="Payments not found")
