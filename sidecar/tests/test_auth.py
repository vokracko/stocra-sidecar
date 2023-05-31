from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi import status
from fastapi.testclient import TestClient

from sidecar.config import CONFIG
from sidecar.limits import get_limits_key
from sidecar.tests.utils import make_request_for_block_by_hash


@pytest.mark.asyncio
@patch("sidecar.config.CONFIG.limit_default", 2)
async def test_no_auth(test_client: TestClient, fake_redis: FakeRedis) -> None:
    limit_key = get_limits_key(
        api_key=None, client_ip="testclient", blockchain_name=CONFIG.node_blockchain.blockchain_name
    )

    assert await fake_redis.get(limit_key) is None

    make_request_for_block_by_hash(test_client)
    assert await fake_redis.get(limit_key) == b"1"

    make_request_for_block_by_hash(test_client)
    assert await fake_redis.get(limit_key) == b"2"

    make_request_for_block_by_hash(test_client, expected_status_code=status.HTTP_429_TOO_MANY_REQUESTS)


@pytest.mark.asyncio
async def test_valid_api_key_path(test_client: TestClient, fake_redis: FakeRedis) -> None:
    API_KEY = "testclientkey"
    await fake_redis.hset(CONFIG.api_key_hash, API_KEY, 1)
    make_request_for_block_by_hash(test_client, api_key_query=API_KEY)


@pytest.mark.asyncio
async def test_invalid_api_key_path(test_client: TestClient) -> None:
    make_request_for_block_by_hash(
        test_client, api_key_query="invalid", expected_status_code=status.HTTP_401_UNAUTHORIZED
    )


@pytest.mark.asyncio
async def test_valid_api_key_header(test_client: TestClient, fake_redis: FakeRedis) -> None:
    API_KEY = "testclientkey"
    await fake_redis.hset(CONFIG.api_key_hash, API_KEY, 1)
    make_request_for_block_by_hash(test_client, api_key_header=API_KEY)


@pytest.mark.asyncio
async def test_invalid_api_key_header(test_client: TestClient, fake_redis: FakeRedis) -> None:
    API_KEY = "testclientkey"
    await fake_redis.hset(CONFIG.api_key_hash, API_KEY, 1)
    make_request_for_block_by_hash(test_client, api_key_header=API_KEY)
