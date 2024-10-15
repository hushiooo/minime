import os
from datetime import datetime, timedelta
from typing import Optional

from asyncpg import Connection

from src.models import RateLimit, URLMapping

RATE_LIMIT_DURATION_SECONDS = int(os.getenv("RATE_LIMIT_DURATION_SECONDS", 600))
RATE_LIMIT_DURATION = timedelta(seconds=RATE_LIMIT_DURATION_SECONDS)


async def upsertURLMapping(
    conn: Connection, original_url: str, slug: str
) -> Optional[URLMapping]:
    result = await conn.fetchrow(
        """
        INSERT INTO url_mappings (slug, original_url)
        VALUES ($1, $2)
        ON CONFLICT (slug) DO UPDATE
        SET original_url = EXCLUDED.original_url,
            created_at = CURRENT_TIMESTAMP
        RETURNING slug, original_url, created_at
        """,
        slug,
        original_url,
    )
    if result:
        return URLMapping(
            slug=result["slug"],
            original_url=result["original_url"],
            created_at=result["created_at"],
        )
    return None


async def getOriginalURL(conn: Connection, slug: str) -> Optional[str]:
    result = await conn.fetchrow(
        """
        SELECT original_url FROM url_mappings WHERE slug = $1
        """,
        slug,
    )

    if result:
        return result["original_url"]
    return None


async def getRateLimit(conn: Connection, client_ip: str) -> Optional[RateLimit]:
    now = datetime.utcnow()

    result = await conn.fetchrow(
        """
        INSERT INTO rate_limits (ip_address, request_count, last_request)
        VALUES ($1, 1, $2)
        ON CONFLICT (ip_address) DO UPDATE
        SET
            request_count = CASE
                WHEN rate_limits.last_request < $3 THEN 1
                ELSE rate_limits.request_count + 1
            END,
            last_request = $2
        RETURNING ip_address, request_count, last_request
    """,
        client_ip,
        now,
        now - RATE_LIMIT_DURATION,
    )

    if result:
        return RateLimit(
            ip_address=result["ip_address"],
            request_count=result["request_count"],
            last_request=result["last_request"],
        )
    return None
