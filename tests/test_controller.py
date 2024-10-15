from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from asyncpg import Connection
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from src.controller import router
from src.dependencies import get_db_conn, get_redis
from src.models import URLMapping
from src.services import RateLimitExceeded, RecordNotFound, UpsertFailed

TEST_BASE_URL = "http://test"
EXAMPLE_URL = "https://example.com"
TEST_SLUG = "abc1234"


# Fixtures
@pytest.fixture
def mock_conn():
    return AsyncMock(spec=Connection)


@pytest.fixture
def mock_redis():
    return AsyncMock(spec=Redis)


@pytest.fixture
def test_app(mock_conn, mock_redis):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides.update(
        {get_db_conn: lambda: mock_conn, get_redis: lambda: mock_redis}
    )
    return app


@pytest.fixture
async def async_client(test_app):
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url=TEST_BASE_URL
    ) as client:
        yield client


# Helper
def assert_rate_limit_exceeded_response(response, ip, request_count, limit):
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert f"Rate limit exceeded for IP {ip}" in response.json()["detail"]
    assert f"Made over {request_count} requests" in response.json()["detail"]


# Test routes
@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get(f"{TEST_BASE_URL}/health")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
@patch("src.controller.checkRateLimit", new_callable=AsyncMock)
@patch("src.controller.findMatchingURL", new_callable=AsyncMock)
async def test_redirect_success(
    mock_find_matching_url, mock_check_rate_limit, async_client
):
    mock_check_rate_limit.return_value = None
    mock_find_matching_url.return_value = EXAMPLE_URL

    response = await async_client.get(f"{TEST_BASE_URL}/{TEST_SLUG}")

    assert mock_check_rate_limit.called
    assert mock_find_matching_url.called
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == EXAMPLE_URL


@pytest.mark.asyncio
@patch("src.controller.checkRateLimit", new_callable=AsyncMock)
async def test_redirect_rate_limit_exceeded(mock_check_rate_limit, async_client):
    mock_check_rate_limit.side_effect = RateLimitExceeded("192.168.1.1", 101)

    response = await async_client.get(f"{TEST_BASE_URL}/{TEST_SLUG}")

    assert_rate_limit_exceeded_response(response, "192.168.1.1", 101, 100)


@pytest.mark.asyncio
@patch("src.controller.checkRateLimit", new_callable=AsyncMock)
@patch("src.controller.findMatchingURL", new_callable=AsyncMock)
async def test_redirect_not_found(
    mock_find_matching_url, mock_check_rate_limit, async_client
):
    mock_check_rate_limit.return_value = None
    mock_find_matching_url.side_effect = RecordNotFound("Original URL", "nonexistent")

    response = await async_client.get(f"{TEST_BASE_URL}/nonexistent")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert (
        "Original URL not found for identifier: nonexistent"
        in response.json()["detail"]
    )


@pytest.mark.asyncio
@patch("src.controller.checkRateLimit", new_callable=AsyncMock)
@patch("src.controller.generateSlug", new_callable=AsyncMock)
async def test_shorten_url_success(
    mock_generate_slug, mock_check_rate_limit, async_client
):
    mock_check_rate_limit.return_value = None
    created_at = datetime.utcnow()
    mock_generate_slug.return_value = URLMapping(
        slug=TEST_SLUG, original_url=EXAMPLE_URL, created_at=created_at
    )
    response = await async_client.post(
        f"{TEST_BASE_URL}/shorten", json={"url": EXAMPLE_URL}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "slug": TEST_SLUG,
        "original_url": EXAMPLE_URL,
        "created_at": created_at.isoformat(),
    }


@pytest.mark.asyncio
@patch("src.controller.checkRateLimit", new_callable=AsyncMock)
async def test_shorten_url_rate_limit_exceeded(mock_check_rate_limit, async_client):
    mock_check_rate_limit.side_effect = RateLimitExceeded("192.168.1.1", 101)
    response = await async_client.post(
        f"{TEST_BASE_URL}/shorten", json={"url": EXAMPLE_URL}
    )
    assert_rate_limit_exceeded_response(response, "192.168.1.1", 101, 100)


@pytest.mark.asyncio
@patch("src.controller.checkRateLimit", new_callable=AsyncMock)
@patch("src.controller.generateSlug", new_callable=AsyncMock)
async def test_shorten_url_upsert_failed(
    mock_generate_slug, mock_check_rate_limit, async_client
):
    mock_check_rate_limit.return_value = None
    mock_generate_slug.side_effect = UpsertFailed(
        "URL mapping", f"Failed to create or update mapping for {EXAMPLE_URL}"
    )
    response = await async_client.post(
        f"{TEST_BASE_URL}/shorten", json={"url": EXAMPLE_URL}
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Upsert operation 'URL mapping' failed" in response.json()["detail"]
    assert (
        f"Failed to create or update mapping for {EXAMPLE_URL}"
        in response.json()["detail"]
    )
