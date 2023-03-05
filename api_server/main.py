import asyncio
from fastapi import FastAPI

from api_server import endpoints
from api_server.deps import database, cache


app = FastAPI()
app.include_router(endpoints.router, prefix="/addresses")


@app.on_event("startup")
async def startup_event():
    await database.connect()


@app.on_event("shutdown")
async def shutdown_event():
    asyncio.gather(
        database.disconnect(),
        cache.close()
    )
