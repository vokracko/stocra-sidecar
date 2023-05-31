import time
from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from flexmock import flexmock
from starlette import status

from sidecar.tests.conftest import NODE_ADAPTER
from sidecar.tests.utils import (
    make_request_for_block_by_hash,
    make_request_for_block_by_height,
)

REDIS_CACHED_KEY_BLOCK_HASH = "ethereum/cache/route_get_block_by_hash(block_hash=hash)"
REDIS_CACHED_KEY_BLOCK_HEIGHT = "ethereum/cache/route_get_block_by_height(block_height=10)"


@pytest.mark.asyncio
async def test_get_block_by_hash_response_not_cached(test_client: TestClient, fake_redis: FakeRedis) -> None:
    response_uncached = make_request_for_block_by_hash(test_client)
    assert await fake_redis.get(REDIS_CACHED_KEY_BLOCK_HASH) == response_uncached.content


@pytest.mark.asyncio
async def test_get_block_by_hash_response_from_cache(test_client: TestClient, fake_redis: FakeRedis) -> None:
    response_uncached = make_request_for_block_by_hash(test_client)
    time.sleep(1)
    first_ttl = await fake_redis.pttl(REDIS_CACHED_KEY_BLOCK_HASH)
    flexmock(NODE_ADAPTER).should_receive("get_block_by_hash").never()

    response_cached = make_request_for_block_by_hash(test_client)
    second_ttl = await fake_redis.pttl(REDIS_CACHED_KEY_BLOCK_HASH)
    assert 0 < first_ttl < second_ttl  # get_block_by_hash extends the cache TTL
    assert response_uncached.content == response_cached.content
    assert response_uncached.status_code == response_cached.status_code
    assert response_uncached.headers == response_cached.headers


@pytest.mark.asyncio
async def test_get_block_by_height_response_not_cached(test_client: TestClient, fake_redis: FakeRedis) -> None:
    response_uncached = make_request_for_block_by_height(test_client)
    assert await fake_redis.get(REDIS_CACHED_KEY_BLOCK_HEIGHT) == response_uncached.content


@pytest.mark.asyncio
async def test_get_block_by_height_response_from_cache(test_client: TestClient, fake_redis: FakeRedis) -> None:
    response_uncached = make_request_for_block_by_height(test_client)
    time.sleep(1)
    first_ttl = await fake_redis.pttl(REDIS_CACHED_KEY_BLOCK_HEIGHT)
    flexmock(NODE_ADAPTER).should_receive("get_block_by_height").never()

    response_cached = make_request_for_block_by_height(test_client)
    second_ttl = await fake_redis.pttl(REDIS_CACHED_KEY_BLOCK_HEIGHT)
    assert 0 < second_ttl < first_ttl  # get_block_by_height does not extend the cache TTL
    assert response_uncached.content == response_cached.content
    assert response_uncached.status_code == response_cached.status_code
    assert response_uncached.headers == response_cached.headers


@pytest.mark.asyncio
@patch("sidecar.routes_v1_0.get_block_by_hash", side_effect=ValueError("Wrong"))
async def test_do_not_cache_invalid_response(_mock, test_client: TestClient, fake_redis: FakeRedis) -> None:
    response = make_request_for_block_by_hash(test_client, expected_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert await fake_redis.get(REDIS_CACHED_KEY_BLOCK_HASH) is None
