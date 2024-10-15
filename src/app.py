import logging
import os
from logging.handlers import TimedRotatingFileHandler
from typing import cast

import asyncpg
from fastapi import FastAPI
from redis.asyncio import Redis

from src.controller import router

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(asctime)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        TimedRotatingFileHandler(
            filename="/app/logs/app.log",
            when="W0",
            interval=1,
            backupCount=4,
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)

# Set up app
app = FastAPI(title="MiniMe - URL Shortener")
app.include_router(router)


# App lifecycle
@app.on_event("startup")
async def startup_event():
    app.state.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    app.state.redis = Redis.from_url(
        cast(str, REDIS_URL), encoding="utf-8", decode_responses=True
    )
    logger.info("Application started, postgres database and redis initialized")


@app.on_event("shutdown")
async def shutdown_event():
    await app.state.db_pool.close()
    await app.state.redis.aclose()
    logger.info("Application shut down, postgres database and redis connections closed")
