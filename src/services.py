import logging
import os

from asyncpg import Connection
from redis.asyncio import Redis

from src.helpers import shorten_url
from src.models import URLMapping
from src.repository import getOriginalURL, getRateLimit, upsertURLMapping

logger = logging.getLogger(__name__)

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", 100))
CACHE_EXPIRY_SECONDS = int(os.getenv("CACHE_EXPIRY_SECONDS", 3600))


class RateLimitExceeded(Exception):
    def __init__(self, client_ip: str, request_count: int):
        self.client_ip = client_ip
        self.request_count = request_count
        self.message = (
            f"Rate limit exceeded for IP {client_ip}. "
            f"Made over {request_count} requests. "
        )
        super().__init__(self.message)


class RecordNotFound(Exception):
    def __init__(self, record_type: str, identifier: str):
        self.record_type = record_type
        self.identifier = identifier
        self.message = f"{record_type} not found for identifier: {identifier}"
        super().__init__(self.message)


class UpsertFailed(Exception):
    def __init__(self, operation: str, details: str):
        self.operation = operation
        self.details = details
        self.message = f"Upsert operation '{operation}' failed: {details}"
        super().__init__(self.message)


async def checkRateLimit(conn: Connection, client_ip: str):
    rate_limit = await getRateLimit(conn, client_ip)
    if rate_limit is None:
        logger.error(f"Cannot find rate limit info for ip address: {client_ip}")
        raise RecordNotFound("Rate limit info", client_ip)
    if rate_limit.request_count >= RATE_LIMIT_REQUESTS:
        logger.warning(f"Rate limit exceeded for ip address: {client_ip}")
        raise RateLimitExceeded(client_ip, rate_limit.request_count)


async def generateSlug(conn: Connection, redis: Redis, original_url: str) -> URLMapping:
    slug = shorten_url(original_url)

    mapping = await upsertURLMapping(conn, original_url, slug)
    if mapping is None:
        logger.error(f"Could not upsert the generated slug for url: {original_url}")
        raise UpsertFailed(
            "URL mapping", f"Failed to create or update mapping for {original_url}"
        )

    await redis.setex(f"url:{mapping.slug}", CACHE_EXPIRY_SECONDS, mapping.original_url)
    logger.info(f"URL shortened and cached: {mapping.original_url} -> {mapping.slug}")

    return mapping


async def findMatchingURL(conn: Connection, redis: Redis, slug: str) -> str:
    cached_url = await redis.get(f"url:{slug}")
    if cached_url:
        logger.info(f"Cache hit - Redirecting: {slug} -> {cached_url}")
        return cached_url

    original_url = await getOriginalURL(conn, slug)
    if original_url is None:
        logger.error(f"Cannot find matching URL for slug: {slug}")
        raise RecordNotFound("Original URL", slug)

    await redis.setex(f"url:{slug}", CACHE_EXPIRY_SECONDS, original_url)
    logger.info(f"URL found and cached - Redirecting: {slug} -> {original_url}")

    return original_url
