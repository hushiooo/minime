import logging
from typing import Annotated, cast

from asyncpg import Connection
from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import HttpUrl
from redis.asyncio import Redis
from starlette.datastructures import Address

from src.dependencies import get_db_conn, get_redis
from src.models import URLMapping
from src.services import (
    RateLimitExceeded,
    RecordNotFound,
    UpsertFailed,
    checkRateLimit,
    findMatchingURL,
    generateSlug,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Routes
@router.get("/health")
def health_check():
    health_status = {"status": "healthy"}
    logger.info("Health Check: OK")
    return JSONResponse(content=health_status, status_code=status.HTTP_200_OK)


@router.get("/{slug}")
async def redirect(
    request: Request,
    conn: Annotated[Connection, Depends(get_db_conn)],
    redis: Annotated[Redis, Depends(get_redis)],
    slug: str,
):
    async with conn.transaction():
        try:
            client_ip = cast(Address, request.client).host
            await checkRateLimit(conn, client_ip)

            original_url = await findMatchingURL(conn, redis, slug)
            return RedirectResponse(url=original_url)

        except RateLimitExceeded as exc:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "detail": str(exc)},
            )

        except RecordNotFound as exc:
            return JSONResponse(
                status_code=404,
                content={"error": "Content not found", "detail": str(exc)},
            )

        except Exception as exc:
            logger.error(f"Error redirecting URL: {str(exc)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(exc)},
            )


@router.post("/shorten", response_model=URLMapping)
async def shorten(
    request: Request,
    conn: Annotated[Connection, Depends(get_db_conn)],
    redis: Annotated[Redis, Depends(get_redis)],
    url: HttpUrl = Body(..., embed=True),
):
    async with conn.transaction():
        try:
            client_ip = cast(Address, request.client).host
            await checkRateLimit(conn, client_ip)

            result = await generateSlug(conn, redis, str(url))
            return result

        except RateLimitExceeded as exc:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "detail": str(exc)},
            )

        except UpsertFailed as exc:
            return JSONResponse(
                status_code=500,
                content={"error": "Internal Server Error", "detail": str(exc)},
            )

        except RecordNotFound as exc:
            return JSONResponse(
                status_code=404,
                content={"error": "Content not found", "detail": str(exc)},
            )

        except Exception as exc:
            logger.error(f"Error redirecting URL: {str(exc)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(exc)},
            )
