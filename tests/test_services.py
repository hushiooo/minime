from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.services import (
    CACHE_EXPIRY_SECONDS,
    RATE_LIMIT_REQUESTS,
    RateLimitExceeded,
    RecordNotFound,
    UpsertFailed,
    checkRateLimit,
    findMatchingURL,
    generateSlug,
)

TEST_IP = "127.0.0.1"
TEST_SLUG = "abc1234"
TEST_URL = "https://example.com"


# Fixtures
@pytest.fixture
def mock_conn():
    return AsyncMock()


@pytest.fixture
def mock_redis():
    return AsyncMock()


# Helper
def create_rate_limit_data(request_count):
    return {
        "ip_address": TEST_IP,
        "request_count": request_count,
        "last_request": datetime.now(),
    }


# Tests checkRateLimit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "request_count, expected_exception",
    [
        (RATE_LIMIT_REQUESTS - 1, None),
        (RATE_LIMIT_REQUESTS, RateLimitExceeded),
        (RATE_LIMIT_REQUESTS + 1, RateLimitExceeded),
    ],
)
async def test_check_rate_limit(mock_conn, request_count, expected_exception):
    mock_conn.fetchrow.return_value = create_rate_limit_data(request_count)

    if expected_exception:
        with pytest.raises(expected_exception):
            await checkRateLimit(mock_conn, TEST_IP)
    else:
        await checkRateLimit(mock_conn, TEST_IP)

    mock_conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_check_rate_limit_not_found(mock_conn):
    mock_conn.fetchrow.return_value = None
    with pytest.raises(RecordNotFound):
        await checkRateLimit(mock_conn, TEST_IP)


# Tests generateSlug
@pytest.mark.asyncio
@patch("src.services.shorten_url")
async def test_generate_slug_success(mock_shorten_url, mock_conn, mock_redis):
    mock_shorten_url.return_value = TEST_SLUG
    mock_conn.fetchrow.return_value = {
        "slug": TEST_SLUG,
        "original_url": TEST_URL,
        "created_at": datetime.now(),
    }
    mock_redis.setex.return_value = True

    result = await generateSlug(mock_conn, mock_redis, TEST_URL)

    assert result.original_url == TEST_URL
    assert result.slug == TEST_SLUG
    mock_redis.setex.assert_called_once_with(
        f"url:{TEST_SLUG}", CACHE_EXPIRY_SECONDS, TEST_URL
    )


@pytest.mark.asyncio
@patch("src.services.shorten_url")
async def test_generate_slug_upsert_failed(mock_shorten_url, mock_conn, mock_redis):
    mock_shorten_url.return_value = TEST_SLUG
    mock_conn.fetchrow.return_value = None

    with pytest.raises(UpsertFailed):
        await generateSlug(mock_conn, mock_redis, TEST_URL)


# Tests findMatchingURL
@pytest.mark.asyncio
async def test_find_matching_url_cache_hit(mock_conn, mock_redis):
    mock_redis.get.return_value = TEST_URL

    result = await findMatchingURL(mock_conn, mock_redis, TEST_SLUG)

    assert result == TEST_URL
    mock_conn.fetchrow.assert_not_called()
    mock_redis.get.assert_called_once_with(f"url:{TEST_SLUG}")


@pytest.mark.asyncio
async def test_find_matching_url_cache_miss_db_hit(mock_conn, mock_redis):
    mock_redis.get.return_value = None
    mock_conn.fetchrow.return_value = {
        "slug": TEST_SLUG,
        "original_url": TEST_URL,
        "created_at": datetime.now(),
    }

    result = await findMatchingURL(mock_conn, mock_redis, TEST_SLUG)

    assert result == TEST_URL
    mock_redis.setex.assert_called_once_with(
        f"url:{TEST_SLUG}", CACHE_EXPIRY_SECONDS, TEST_URL
    )
    mock_conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_find_matching_url_not_found(mock_conn, mock_redis):
    mock_redis.get.return_value = None
    mock_conn.fetchrow.return_value = None

    with pytest.raises(RecordNotFound):
        await findMatchingURL(mock_conn, mock_redis, TEST_SLUG)
