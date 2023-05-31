import time
from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi import status
from fastapi.testclient import TestClient
from genesis.blockchain.tests.utils import AwaitableValue

from sidecar.config import CONFIG
from sidecar.limits import broadcast_limit_consumption, get_limits_key
from sidecar.models import Limit
from sidecar.tests.utils import make_request_for_block_by_hash


@pytest.mark.asyncio
@patch("sidecar.config.CONFIG.limit_default", 2)
async def test_limits_by_ip(test_client: TestClient, fake_redis: FakeRedis) -> None:
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
async def test_limits_by_api_key(test_client: TestClient, fake_redis: FakeRedis) -> None:
    API_KEY = "testclientkey"
    limit_key_ip = get_limits_key(
        api_key=None, client_ip="testclient", blockchain_name=CONFIG.node_blockchain.blockchain_name
    )
    limit_key_api_key = get_limits_key(
        api_key=API_KEY, client_ip="testclient", blockchain_name=CONFIG.node_blockchain.blockchain_name
    )
    await fake_redis.hset(CONFIG.api_key_hash, API_KEY, 2)

    assert await fake_redis.get(limit_key_ip) is None
    assert await fake_redis.get(limit_key_api_key) is None

    make_request_for_block_by_hash(test_client, api_key_query=API_KEY)
    assert await fake_redis.get(limit_key_ip) is None
    assert await fake_redis.get(limit_key_api_key) == b"1"

    make_request_for_block_by_hash(test_client, api_key_query=API_KEY)
    assert await fake_redis.get(limit_key_ip) is None
    assert await fake_redis.get(limit_key_api_key) == b"2"

    make_request_for_block_by_hash(
        test_client, api_key_query=API_KEY, expected_status_code=status.HTTP_429_TOO_MANY_REQUESTS
    )


@pytest.mark.asyncio
@patch("sidecar.config.CONFIG.limit_default", 1)
@patch("sidecar.config.CONFIG.limit_interval", 1)
async def test_limits_expire(test_client: TestClient, fake_redis: FakeRedis) -> None:
    limit_key = get_limits_key(
        api_key=None, client_ip="testclient", blockchain_name=CONFIG.node_blockchain.blockchain_name
    )

    assert await fake_redis.get(limit_key) is None

    make_request_for_block_by_hash(test_client)
    assert await fake_redis.get(limit_key) == b"1"

    make_request_for_block_by_hash(test_client, expected_status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    time.sleep(1)
    assert await fake_redis.get(limit_key) is None
    make_request_for_block_by_hash(test_client)
    assert await fake_redis.get(limit_key) == b"1"


@pytest.mark.asyncio
@patch("sidecar.limits.broadcast_limit_consumption")
async def test_trigger_post_limit(mock, test_client: TestClient, fake_redis: FakeRedis) -> None:
    limit_key = get_limits_key(
        api_key=None, client_ip="testclient", blockchain_name=CONFIG.node_blockchain.blockchain_name
    )
    await fake_redis.set(limit_key, CONFIG.sidecar_limit_sync_interval - 1)
    await fake_redis.expire(limit_key, 1_000_000)
    make_request_for_block_by_hash(test_client)

    mock.assert_called_with(limit_key)


@pytest.mark.asyncio
@patch("sidecar.limits.broadcast_limit_consumption")
async def test_trigger_post_limit_shouldnt_be_called(mock, test_client: TestClient, fake_redis: FakeRedis) -> None:
    limit_key = get_limits_key(
        api_key=None, client_ip="testclient", blockchain_name=CONFIG.node_blockchain.blockchain_name
    )
    await fake_redis.set(limit_key, CONFIG.sidecar_limit_sync_interval - 2)
    await fake_redis.expire(limit_key, 1_000_000)
    make_request_for_block_by_hash(test_client)

    mock.assert_not_called()


@pytest.mark.asyncio
@patch("sidecar.config.CONFIG.sidecar_token", "test-sidecar-token")
async def test_post_limit_does_not_exists(test_client: TestClient, fake_redis: FakeRedis) -> None:
    test_client.post(
        "/limit",
        json=Limit(key="a", value=CONFIG.sidecar_limit_sync_interval, ttl=1_000_000).dict(),
        headers={"Authorization": f"Bearer {CONFIG.sidecar_token}"},
    )
    assert await fake_redis.get("a") == f"{CONFIG.sidecar_limit_sync_interval}".encode()
    assert await fake_redis.ttl("a") > 999_000


@pytest.mark.asyncio
async def test_post_limit_decrease_ttl(test_client: TestClient, fake_redis: FakeRedis) -> None:
    await fake_redis.set("a", 1)
    await fake_redis.expire("a", 1_000_000)
    test_client.post(
        "/limit",
        json=Limit(key="a", value=CONFIG.sidecar_limit_sync_interval, ttl=100).dict(),
        headers={"Authorization": f"Bearer {CONFIG.sidecar_token}"},
    )
    assert await fake_redis.get("a") == str(CONFIG.sidecar_limit_sync_interval + 1).encode()
    assert 0 <= await fake_redis.ttl("a") <= 100


@pytest.mark.asyncio
async def test_post_limit_keep_ttl(test_client: TestClient, fake_redis: FakeRedis) -> None:
    await fake_redis.set("a", 1)
    await fake_redis.expire("a", 1_000_000)
    test_client.post(
        "/limit",
        json=Limit(key="a", value=CONFIG.sidecar_limit_sync_interval, ttl=100_000_000).dict(),
        headers={"Authorization": f"Bearer {CONFIG.sidecar_token}"},
    )
    assert await fake_redis.get("a") == str(CONFIG.sidecar_limit_sync_interval + 1).encode()
    assert 0 <= await fake_redis.ttl("a") <= 1_000_000


@pytest.mark.asyncio
@patch("sidecar.limits.aiohttp.ClientSession.post", return_value=AwaitableValue(None))
async def test_broadcast_limit_consumption(mock, test_client: TestClient, fake_redis: FakeRedis):
    await fake_redis.set("a", CONFIG.sidecar_limit_sync_interval, ex=1_000_000)
    with patch("sidecar.config.CONFIG.sidecar_urls", set(["https://sidecar"])):
        await broadcast_limit_consumption("a")

    mock.assert_called_with(
        url="https://sidecar/limit",
        json=dict(key="a", value=CONFIG.sidecar_limit_sync_interval, ttl=1_000_000),
        headers={"Authorization": f"Bearer {CONFIG.sidecar_token}"},
        raise_for_status=True,
        allow_redirects=False,
    )
