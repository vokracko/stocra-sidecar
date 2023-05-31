from typing import Type
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from flexmock import flexmock
from genesis.blockchain.exceptions import (
    DoesNotExist,
    NodeNotReady,
    SkippedBlock,
    TooManyRequests,
    Unavailable,
)
from genesis.blockchain.tests.utils import AwaitableValue

from sidecar.tests.conftest import (
    BLOCK,
    BLOCK_DICT,
    NODE_ADAPTER,
    PARSER,
    TRANSACTION,
    TRANSACTION_DICT,
)


@pytest.mark.asyncio
async def test_get_status_ok(test_client: TestClient) -> None:
    flexmock(NODE_ADAPTER).should_receive("get_block_count").with_args().and_return(AwaitableValue(1)).once()
    flexmock(NODE_ADAPTER).should_receive("get_block_by_height").with_args(1).and_return(
        AwaitableValue(BLOCK_DICT)
    ).once()
    flexmock(PARSER).should_receive("decode_block").with_args(
        BLOCK_DICT,
    ).and_return(AwaitableValue(BLOCK)).once()
    response = test_client.get("/v1.0/status")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_get_status_ko(test_client: TestClient) -> None:
    flexmock(NODE_ADAPTER).should_receive("get_block_count").and_raise(Unavailable).once()
    response = test_client.get("/v1.0/status")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_get_block_latest(test_client: TestClient) -> None:
    flexmock(NODE_ADAPTER).should_receive("get_block_count").with_args().and_return(AwaitableValue(1)).once()
    flexmock(NODE_ADAPTER).should_receive("get_block_by_height").with_args(
        1,
    ).and_return(AwaitableValue(BLOCK_DICT)).once()
    flexmock(PARSER).should_receive("decode_block").with_args(
        BLOCK_DICT,
    ).and_return(AwaitableValue(BLOCK)).once()
    # from sidecar import config
    response = test_client.get("/v1.0/blocks/latest")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "block_hash",
    [
        "00000000000000000007f09e0f989cc674f87305f56cbfbad1014e7e531136ba",
        "7f09e0f989cc674f87305f56cbfbad1014e7e531136ba",
        "0xc58872fa06d01838a537fb58a1160143a3837c63da9613524fd9a101522acc58",
    ],
)
@pytest.mark.asyncio
async def test_get_block_by_hash(test_client: TestClient, block_hash: str) -> None:
    flexmock(NODE_ADAPTER).should_receive("get_block_by_hash").with_args(block_hash=block_hash).and_return(
        AwaitableValue(BLOCK_DICT)
    ).once()
    flexmock(PARSER).should_receive("decode_block").with_args(
        BLOCK_DICT,
    ).and_return(AwaitableValue(BLOCK)).once()
    response = test_client.get(f"/v1.0/blocks/{block_hash}")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@pytest.mark.parametrize("block_number", [10, 100, 1000])
async def test_get_block_by_height(test_client: TestClient, block_number: int) -> None:
    flexmock(NODE_ADAPTER).should_receive("get_block_by_height").with_args(height=block_number).and_return(
        AwaitableValue(BLOCK_DICT)
    ).once()
    flexmock(PARSER).should_receive("decode_block").with_args(BLOCK_DICT).and_return(AwaitableValue(BLOCK)).once()
    response = test_client.get(f"/v1.0/blocks/{block_number}")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method, url, exception, status_code",
    [
        ("get_block_by_hash", "/v1.0/blocks/a", Unavailable, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_by_hash", "/v1.0/blocks/a", TooManyRequests, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_by_hash", "/v1.0/blocks/a", NodeNotReady, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_by_hash", "/v1.0/blocks/a", DoesNotExist, status.HTTP_404_NOT_FOUND),
        ("get_block_by_hash", "/v1.0/blocks/a", KeyError, status.HTTP_500_INTERNAL_SERVER_ERROR),
        ("get_block_by_hash", "/v1.0/blocks/a", SkippedBlock, status.HTTP_204_NO_CONTENT),
        ("get_block_by_height", "/v1.0/blocks/10", Unavailable, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_by_height", "/v1.0/blocks/10", TooManyRequests, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_by_height", "/v1.0/blocks/10", NodeNotReady, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_by_height", "/v1.0/blocks/10", DoesNotExist, status.HTTP_404_NOT_FOUND),
        ("get_block_by_height", "/v1.0/blocks/10", KeyError, status.HTTP_500_INTERNAL_SERVER_ERROR),
        ("get_block_by_height", "/v1.0/blocks/10", SkippedBlock, status.HTTP_204_NO_CONTENT),
        ("get_block_count", "/v1.0/blocks/latest", Unavailable, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_count", "/v1.0/blocks/latest", TooManyRequests, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_count", "/v1.0/blocks/latest", NodeNotReady, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_block_count", "/v1.0/blocks/latest", DoesNotExist, status.HTTP_404_NOT_FOUND),
        ("get_block_count", "/v1.0/blocks/latest", ValueError, status.HTTP_500_INTERNAL_SERVER_ERROR),
        ("get_transaction", "/v1.0/transactions/a", Unavailable, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_transaction", "/v1.0/transactions/a", TooManyRequests, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_transaction", "/v1.0/transactions/a", NodeNotReady, status.HTTP_503_SERVICE_UNAVAILABLE),
        ("get_transaction", "/v1.0/transactions/a", DoesNotExist, status.HTTP_404_NOT_FOUND),
        ("get_transaction", "/v1.0/transactions/a", AttributeError, status.HTTP_500_INTERNAL_SERVER_ERROR),
    ],
)
@patch("sidecar.config.CONFIG.adapter", new=NODE_ADAPTER)
async def test_node_errors(
    test_client: TestClient, method: str, url: str, exception: Type[Exception], status_code: int
) -> None:
    flexmock(NODE_ADAPTER).should_receive(method).and_raise(exception).once()
    response = test_client.get(url)
    assert response.status_code == status_code


@pytest.mark.asyncio
@pytest.mark.parametrize("transaction_hash", ["a", "b"])
async def test_get_transaction(test_client: TestClient, transaction_hash: str) -> None:
    flexmock(NODE_ADAPTER).should_receive("get_transaction").with_args(transaction_hash).and_return(
        AwaitableValue(TRANSACTION_DICT)
    ).once()
    flexmock(PARSER).should_receive("decode_transaction").with_args(TRANSACTION_DICT).and_return(
        AwaitableValue(TRANSACTION)
    ).once()
    response = test_client.get(f"/v1.0/transactions/{transaction_hash}")
    assert response.status_code == status.HTTP_200_OK
